"""Prometheus metrics middleware for FastAPI/Starlette apps"""
import time
import re
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
from optorch.prometheus.registry import MetricsRegistry


class PrometheusMiddleware(BaseHTTPMiddleware):
    """Tracks HTTP request metrics for Prometheus
    
    Automatically records:
    - Request duration
    - HTTP method
    - Endpoint (with ID sanitization to prevent cardinality explosion)
    - Status code
    """
    
    def __init__(self, app):
        super().__init__(app)
        self.metrics = MetricsRegistry()
    
    async def dispatch(self, request: Request, call_next):
        start_time = time.time()
        endpoint = self._get_endpoint(request)
        method = request.method
        
        response = None
        status_code = 500
        
        try:
            response = await call_next(request)
            status_code = response.status_code
            return response
        except Exception:
            raise
        finally:
            duration = time.time() - start_time
            
            self.metrics.track_http_request(
                method=method,
                endpoint=endpoint,
                status_code=status_code,
                duration=duration
            )
    
    def _get_endpoint(self, request: Request) -> str:
        """Extract endpoint with ID sanitization"""
        if request.scope.get("route"):
            return request.scope["route"].path
        
        path = request.url.path
        path = re.sub(r'/[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}', '/{id}', path)
        path = re.sub(r'/session-[0-9]+-[a-z0-9]+', '/session-{id}', path)
        path = re.sub(r'/\d+', '/{id}', path)
        
        return path
