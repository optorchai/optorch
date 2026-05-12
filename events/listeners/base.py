from typing import Dict, Any

class BaseListener:
    """Base class for event listeners
    
    Attributes:
        needs_initialization: If True, listener requires async initialization before use.
                            Used for listeners with DB connections or external resources.
    """
    
    def __init__(self):
        self.needs_initialization = False
    
    def on_event(self, event: Dict[str, Any]):
        raise NotImplementedError

    async def cleanup(self):
        """Remove listener from event emitter - called at FINALIZE hook"""
        pass
