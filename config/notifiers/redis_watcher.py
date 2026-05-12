"""
Watch Redis key for config version changes
"""
from typing import Callable
import threading
from optorch.logging import get_logger

from optorch.config.notifiers.base import ConfigChangeNotifier

logger = get_logger(__name__)


class RedisWatcher(ConfigChangeNotifier):
    """Watch Redis key for config version changes"""
    
    def __init__(self, redis_url: str, key: str = "optorch:config:version"):
        self.redis_url = redis_url
        self.key = key
        self._pubsub = None
        self._running = False
    
    def start(self, on_change: Callable[[], None]) -> None:
        try:
            import redis
        except ImportError:
            logger.warning("redis not installed, Redis watching disabled")
            return
        
        r = redis.from_url(self.redis_url)
        self._pubsub = r.pubsub()
        
        # keyspace notifications must be enabled: config set notify-keyspace-events KEA
        self._pubsub.psubscribe(f"__keyspace@0__:{self.key}")
        self._running = True
        
        def listen():
            logger.info(f"Redis watcher started on {self.redis_url}, key {self.key}")
            if not self._pubsub:
                return
            for msg in self._pubsub.listen():  # type: ignore[union-attr]
                if not self._running:
                    break
                msg_dict = msg if isinstance(msg, dict) else {}
                if msg_dict.get('type') == 'pmessage':
                    logger.info(f"Config change event received from Redis")
                    on_change()
        
        threading.Thread(target=listen, daemon=True).start()
    
    def stop(self) -> None:
        self._running = False
        if self._pubsub:
            self._pubsub.close()
            logger.info("Redis watcher stopped")
