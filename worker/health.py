"""health check endpoint for worker monitoring"""
from typing import Dict, Any, TYPE_CHECKING
import time

if TYPE_CHECKING:
    import psutil  # type: ignore[import-not-found]

try:
    import psutil  # type: ignore[import-not-found]
    HAS_PSUTIL = True
except ImportError:
    HAS_PSUTIL = False


class WorkerHealth:
    """health metrics for worker"""
    
    def __init__(self):
        self.start_time = time.time()
        self.tasks_processed = 0
        self.tasks_failed = 0
    
    def record_success(self) -> None:
        """record successful task"""
        self.tasks_processed += 1
    
    def record_failure(self) -> None:
        """record failed task"""
        self.tasks_failed += 1
    
    def get_status(self) -> Dict[str, Any]:
        """get health status"""
        uptime = time.time() - self.start_time
        
        status = {
            "status": "healthy",
            "uptime_seconds": uptime,
            "tasks_processed": self.tasks_processed,
            "tasks_failed": self.tasks_failed,
            "success_rate": self._calculate_success_rate()
        }
        
        if HAS_PSUTIL:
            status["cpu_percent"] = psutil.cpu_percent()
            status["memory_mb"] = psutil.Process().memory_info().rss / 1024 / 1024
        
        return status
    
    def _calculate_success_rate(self) -> float:
        """calculate success rate percentage"""
        total = self.tasks_processed + self.tasks_failed
        if total == 0:
            return 100.0
        return (self.tasks_processed / total) * 100.0
