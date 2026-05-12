"""
Routing type and config key constants for node routing configuration.
"""

class RouteTypes:
    STATIC = "static"
    CONDITIONAL = "conditional"
    DYNAMIC = "dynamic"
    END = "end"


class RouteKeys:
    TYPE = "type"
    NEXT = "next"
    ON = "on"
    CONDITIONS = "conditions"
    DEFAULT = "default"
    IF = "if"
    THEN = "then"
