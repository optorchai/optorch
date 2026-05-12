"""Prometheus server integration - self-contained registration"""
from optorch.logging import get_logger

logger = get_logger(__name__)


def register_with_server(middleware_manager, route_manager, config: dict) -> None:
    """Register Prometheus middleware and routes - called by ServerManager
    
    This is the ONLY entry point for Prometheus server integration.
    All registration logic stays within the prometheus package.
    """
    from optorch.prometheus import PrometheusMiddleware, routes
    
    prometheus_config = config.get("prometheus", {})
    if prometheus_config.get("enabled", True):
        middleware_manager.register("prometheus", PrometheusMiddleware, priority=300)
        logger.info("Prometheus middleware registered")
    
    route_manager.register_router("", routes.router, ["Observability"])
    logger.info("Prometheus /metrics route registered")

