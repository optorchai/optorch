"""
Watch config directory for YAML changes
"""
from pathlib import Path
from typing import Callable
import time
from optorch.logging import get_logger

from optorch.config.notifiers.base import ConfigChangeNotifier

logger = get_logger(__name__)


class FileWatcher(ConfigChangeNotifier):
    """Watch config directory for YAML changes"""
    
    def __init__(self, config_dir: Path, debounce_ms: int = 500):
        self.config_dir = config_dir
        self.debounce_ms = debounce_ms
        self._observer = None
    
    def start(self, on_change: Callable[[], None]) -> None:
        from watchdog.observers import Observer
        from watchdog.events import FileSystemEventHandler
        
        last_trigger = [0.0]
        debounce_sec = self.debounce_ms / 1000
        
        class YAMLHandler(FileSystemEventHandler):
            def on_modified(self, event):
                if not str(event.src_path).endswith('.yaml'):
                    return
                
                now = time.time()
                if now - last_trigger[0] < debounce_sec:
                    return
                
                last_trigger[0] = now
                logger.info(f"Config file changed: {event.src_path}")
                on_change()
        
        self._observer = Observer()
        self._observer.schedule(YAMLHandler(), str(self.config_dir), recursive=False)
        self._observer.start()
        logger.info(f"File watcher started on {self.config_dir}")
    
    def stop(self) -> None:
        if self._observer:
            self._observer.stop()
            self._observer.join()
            logger.info("File watcher stopped")
