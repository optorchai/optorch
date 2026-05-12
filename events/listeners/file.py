import json
from pathlib import Path
from typing import Dict, Any
from .base import BaseListener
from optorch.utils.json_encoder import DecimalEncoder


class FileListener(BaseListener):
    def __init__(self, filepath: str = "logs/trace.jsonl") -> None:
        self.filepath = Path(filepath)
        self.filepath.parent.mkdir(parents=True, exist_ok=True)
    
    def on_event(self, event: Dict[str, Any]):
        with open(self.filepath, "a") as f:
            f.write(json.dumps(event, cls=DecimalEncoder) + "\n")
