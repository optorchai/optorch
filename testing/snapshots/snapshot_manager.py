"""JSON snapshot testing"""

import json
import os
from pathlib import Path
from typing import Any, Dict, Optional

from optorch.testing.snapshots.serializer import SnapshotSerializer


class SnapshotManager:
    """Manages test snapshots with approve/update workflow"""
    
    def __init__(self, test_file: str, update_snapshots: bool = False):
        self.test_file = test_file
        self.update_snapshots = update_snapshots
        self.serializer = SnapshotSerializer()
        
        # snapshots live next to test files
        test_path = Path(test_file)
        self.snapshot_dir = test_path.parent / "__snapshots__" / f"{test_path.stem}.json"
        self.snapshot_dir.parent.mkdir(parents=True, exist_ok=True)
        
        self._snapshots: Dict[str, Any] = {}
        self._load_snapshots()
    
    def _load_snapshots(self) -> None:
        """Load existing snapshots"""
        if self.snapshot_dir.exists():
            with open(self.snapshot_dir, 'r') as f:
                self._snapshots = json.load(f)
    
    def _save_snapshots(self) -> None:
        """Write snapshots to disk"""
        with open(self.snapshot_dir, 'w') as f:
            json.dump(self._snapshots, f, indent=2, sort_keys=True)
    
    def assert_matches(self, snapshot_name: str, value: Any) -> None:
        """Assert value matches stored snapshot"""
        serialized = self.serializer.serialize(value)
        
        if snapshot_name not in self._snapshots:
            if self.update_snapshots:
                self._snapshots[snapshot_name] = serialized
                self._save_snapshots()
                return
            else:
                raise AssertionError(f"No snapshot found for '{snapshot_name}'. Run with --update-snapshots")
        
        stored = self._snapshots[snapshot_name]
        if serialized != stored:
            if self.update_snapshots:
                self._snapshots[snapshot_name] = serialized
                self._save_snapshots()
                return
            
            # detailed diff for failures
            from optorch.testing.snapshots.diff import SnapshotDiff
            diff = SnapshotDiff(stored, serialized)
            raise AssertionError(f"Snapshot mismatch for '{snapshot_name}':\n{diff.format()}")
    
    def get_snapshot_count(self) -> int:
        """Count stored snapshots"""
        return len(self._snapshots)