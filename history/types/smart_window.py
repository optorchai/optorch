"""Smart window memory strategy"""

from typing import List
from optorch.messaging import Message
from optorch.history.filters import CompositeFilter, ErrorFilter, DuplicateFilter, NoiseFilter


class SmartWindow:
    
    def __init__(
        self,
        window_size: int = 20,
        keep_errors: bool = False,
        remove_duplicates: bool = True,
        remove_noise: bool = True
    ):
        self.window_size = window_size
        
        filters = []
        if not keep_errors:
            filters.append(ErrorFilter(keep_errors=False))
        if remove_duplicates:
            filters.append(DuplicateFilter(by_content=True))
        if remove_noise:
            filters.append(NoiseFilter())
        
        self.filter = CompositeFilter(filters) if filters else None
    
    def get_messages(self, messages: List[Message]) -> List[Message]:
        if self.filter:
            messages = self.filter.filter(messages)
        
        # Apply window
        return messages[-self.window_size:] if len(messages) > self.window_size else messages
