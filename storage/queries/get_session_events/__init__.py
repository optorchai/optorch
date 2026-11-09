import time
from datetime import datetime, timezone


def _created_at_to_ms(created_at: object) -> int:
    try:
        if isinstance(created_at, str):
            dt = datetime.fromisoformat(created_at.replace(" ", "T"))
        elif isinstance(created_at, datetime):
            dt = created_at
        else:
            return int(time.time() * 1000)
        
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
            
        return int(dt.timestamp() * 1000)
    except Exception:
        return int(time.time() * 1000)
