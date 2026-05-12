"""redis prompt provider - hot-reload from redis cache"""

from optorch.llm.prompts import PromptProvider
from typing import Any, Optional, TYPE_CHECKING
from optorch.logging import get_logger

if TYPE_CHECKING:
    from redis import Redis

logger = get_logger(__name__)


class RedisPromptProvider(PromptProvider):
    """load prompts from redis cache with hot-reload support"""
    
    def __init__(self, redis_url: str) -> None:
        self._redis_url = redis_url
        self._redis: Optional['Redis'] = None
        logger.debug("redis prompt provider initialized")
    
    def _get_redis(self) -> Optional['Redis']:
        """lazy redis client initialization"""
        if self._redis is None:
            try:
                import redis
                self._redis = redis.from_url(self._redis_url, decode_responses=True)
                logger.info(f"connected to redis: {self._redis_url}")
            except ImportError:
                logger.warning("redis package not installed - pip install redis")
                self._redis = None
                return None
            except Exception as e:
                logger.warning(f"failed to connect to redis: {self._redis_url}")
                self._redis = None
                return None
        return self._redis
    
    async def load(self, prompt_name: str, fragments: dict[str, Any]) -> str | None:
        """load prompt from redis with key pattern: prompt:{name}"""
        redis_client = self._get_redis()
        if not redis_client:
            return None
        
        try:
            template = redis_client.get(f"prompt:{prompt_name}")
            if not template or not isinstance(template, str):
                return None
            
            # fragment injection
            for key, value in fragments.items():
                template = template.replace(f"{{{key}}}", value if value else "")
            
            logger.info(f"loaded '{prompt_name}' from redis")
            return template
        except Exception as e:
            logger.error(f"redis load failed for '{prompt_name}': {e}")
            return None
    
    @property
    def name(self) -> str:
        return "Redis"
