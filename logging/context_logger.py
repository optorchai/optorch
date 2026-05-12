import logging
from typing import Optional, Any, Dict, Union


class ContextLogger:    
    def __init__(self, logger: Union[logging.Logger, str], component: Optional[str] = None) -> None:
        if isinstance(logger, str):
            self._logger = logging.getLogger(logger)
        else:
            self._logger = logger
        self._component = component
    
    def _enrich_context(self, extra: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        ctx = extra.copy() if extra else {}
        
        if self._component:
            ctx.setdefault('component', self._component)
        elif not ctx.get('component'):
            ctx['component'] = self._logger.name.split('.')[0]
        
        if 'session_id' not in ctx:
            try:
                from optorch.session.session_manager import _current_session
                session_id = _current_session.get()
                if session_id:
                    ctx['session_id'] = session_id
            except:
                pass
        
        return ctx
    
    def debug(self, msg: str, *args, **kwargs) -> None:
        kwargs['extra'] = self._enrich_context(kwargs.get('extra'))
        self._logger.debug(msg, *args, **kwargs)
    
    def info(self, msg: str, *args, **kwargs) -> None:
        kwargs['extra'] = self._enrich_context(kwargs.get('extra'))
        self._logger.info(msg, *args, **kwargs)
    
    def warning(self, msg: str, *args, **kwargs) -> None:
        kwargs['extra'] = self._enrich_context(kwargs.get('extra'))
        self._logger.warning(msg, *args, **kwargs)
    
    def error(self, msg: str, *args, **kwargs) -> None:
        kwargs['extra'] = self._enrich_context(kwargs.get('extra'))
        self._logger.error(msg, *args, **kwargs)
    
    def critical(self, msg: str, *args, **kwargs) -> None:
        kwargs['extra'] = self._enrich_context(kwargs.get('extra'))
        self._logger.critical(msg, *args, **kwargs)
    
    @property
    def name(self) -> str:
        return self._logger.name
    
    @property
    def level(self) -> int:
        return self._logger.level
    
    def setLevel(self, level: int) -> None:
        self._logger.setLevel(level)


def get_logger(name: str, component: Optional[str] = None) -> ContextLogger:
    return ContextLogger(logging.getLogger(name), component)
