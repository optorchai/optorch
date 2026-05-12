import json
import logging
from datetime import datetime


class JSONFormatter(logging.Formatter):
    # frontend-consumable json with session_id
    
    def format(self, record: logging.LogRecord) -> str:
        log_obj = {
            "timestamp": datetime.fromtimestamp(record.created).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        
        for field in ['session_id', 'phase', 'component', 'error_type', 'severity']:
            val = getattr(record, field, None)
            if val:
                log_obj[field] = val
        
        if record.exc_info:
            log_obj['exception'] = self.formatException(record.exc_info)
        
        if hasattr(record, 'error_details'):
            log_obj['error_details'] = getattr(record, 'error_details')
        
        return json.dumps(log_obj)
