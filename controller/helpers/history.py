from typing import TYPE_CHECKING, Optional, Any

from optorch.history.config import HistoryConfig
from optorch.history.manager import History

if TYPE_CHECKING:
    from optorch.controller.node_controller import NodeController


class HistoryHelper:
    def __init__(self, controller: 'NodeController'):
        self._controller = controller
    
    def configure(
        self,
        cache_manager: Any,
        history_config: HistoryConfig,
        session_manager: Optional[Any] = None
    ) -> None:
        from optorch.history.sources.session import SessionMessageSource

        source = SessionMessageSource(session_manager=session_manager)
        self._controller._history = History(
            cache=cache_manager,
            config=history_config,
            source=source
        )

    def get(self) -> Optional[History]:
        return self._controller._history
