"""Snapshot diff formatting"""

import json
from typing import Any
from difflib import unified_diff


class SnapshotDiff:
    """Formats snapshot differences for readable output"""
    
    def __init__(self, expected: Any, actual: Any):
        self.expected = expected
        self.actual = actual
    
    def format(self) -> str:
        """Generate diff string"""
        expected_json = json.dumps(self.expected, indent=2, sort_keys=True)
        actual_json = json.dumps(self.actual, indent=2, sort_keys=True)
        
        expected_lines = expected_json.splitlines(keepends=True)
        actual_lines = actual_json.splitlines(keepends=True)
        
        diff = unified_diff(
            expected_lines,
            actual_lines,
            fromfile="expected",
            tofile="actual",
            lineterm=""
        )
        
        return "".join(diff)