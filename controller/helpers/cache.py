from typing import TYPE_CHECKING, Optional, Any

from optorch.cache.manager import CacheManager

if TYPE_CHECKING:
    from optorch.controller.node_controller import NodeController
    from optorch.controller.node_context import NodeContext


class CacheHelper:
    def __init__(self, controller: 'NodeController', context: Optional['NodeContext'] = None):
        self._controller = controller
        self._context = context
    
    def configure(self, cache_manager: CacheManager) -> None:
        self._controller._cache_manager = cache_manager

    def get(self) -> Optional[CacheManager]:
        return self._controller._cache_manager

    async def get_cached(self, key: str) -> Any:
        if not self._controller._cache_manager:
            return None
        return await self._controller._cache_manager.get(key, self._context)

    async def set_cached(self, key: str, value: Any, ttl: Any = None) -> None:
        if not self._controller._cache_manager:
            return
        await self._controller._cache_manager.set(key, value, ttl, self._context)
