"""pattern-based buffering for extracting marked content"""
import re
from typing import List, Tuple, Optional
from optorch.llm.responses.accumulators.base_accumulator import BaseAccumulator

class PatternAccumulator(BaseAccumulator):
    """buffers until pattern detected, then yields accumulated content"""
    
    def __init__(self, patterns: List[Tuple[str, str]], pre_buffer: int = 50, post_buffer: int = 10):
        """
        patterns: list of (start_regex, end_regex) tuples
        pre_buffer: chars to accumulate before pattern detection (needs to be >= longest pattern length)
        post_buffer: chars to include after end pattern (for closing backticks)
        """
        self.patterns = patterns
        self.buffer = ""
        self.in_pattern = None
        self.pre_buffer = pre_buffer
        self.post_buffer = post_buffer
        self.rolling_window = ""
        self.chunk_count = 0
    
    def consume(self, chunk: str) -> Optional[str]:
        """accumulate chunks, return content when pattern complete"""
        self.chunk_count += 1
        
        if not self.in_pattern:
            combined = self.rolling_window + self.buffer + chunk
            
            for start_pattern, end_pattern in self.patterns:
                match = re.search(start_pattern, combined)
                if match:
                    self.in_pattern = (start_pattern, end_pattern)
                    pattern_start_pos = match.start()
                    self.buffer = combined[pattern_start_pos:]
                    pre_pattern = combined[:pattern_start_pos]
                    self.rolling_window = ""
                    return pre_pattern if pre_pattern else None
            
            if not self.in_pattern:
                self.rolling_window += chunk
                if len(self.rolling_window) > self.pre_buffer:
                    excess = self.rolling_window[:-self.pre_buffer]
                    self.rolling_window = self.rolling_window[-self.pre_buffer:]
                    return excess

        else:
            self.buffer += chunk
        
        if self.in_pattern and re.search(self.in_pattern[1], self.buffer):
            if not hasattr(self, '_post_buffer_count'):
                self._post_buffer_count = 0
            
            self._post_buffer_count += len(chunk)
            
            if self._post_buffer_count >= self.post_buffer:
                result = self.buffer
                self.buffer = ""
                self.in_pattern = None
                self._post_buffer_count = 0
                return result
        
        return None
    
    def should_passthrough(self) -> bool:
        """dont passthrough if buffering pattern OR accumulating rolling window"""
        return not self.in_pattern and not self.buffer and not self.rolling_window
    
    def flush(self) -> Optional[str]:
        """return remaining buffer and rolling window"""
        result = self.buffer + self.rolling_window
        self.buffer = ""
        self.rolling_window = ""
        self.in_pattern = None
        return result if result else None