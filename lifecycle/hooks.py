from enum import Enum


class LifecycleHook(str, Enum):
    PRE_DISPATCH = "pre_dispatch"
    EXECUTE = "execute"
    POST_DISPATCH = "post_dispatch"
    ROUTE = "route"
    
    @classmethod
    def ordered(cls) -> list["LifecycleHook"]:
        return [
            cls.PRE_DISPATCH,
            cls.EXECUTE,
            cls.POST_DISPATCH,
            cls.ROUTE
        ]
