"""Prometheus metrics routes"""
from fastapi import APIRouter
from fastapi.responses import PlainTextResponse
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST, REGISTRY

router = APIRouter()


@router.get(
    "/metrics",
    response_class=PlainTextResponse,
    summary="Prometheus metrics endpoint",
    description="""Expose system metrics in Prometheus exposition format for monitoring and observability.
    
    This endpoint is designed to be scraped by Prometheus, Grafana, Datadog, or other monitoring tools.
    Provides comprehensive operational metrics including:
    
    **HTTP Metrics:**
    - Request counts by method, endpoint, and status code
    - Request latency histograms (p50, p95, p99)
    
    **LLM Metrics:**
    - API call counts by provider (OpenAI, Groq, Ollama) and model
    - Token consumption (prompt and completion tokens)
    - Cost tracking in USD for budget monitoring
    - Request duration by model
    
    **Tool & Node Metrics:**
    - Tool call frequencies and execution times
    - Node execution counts and durations
    - Node transition flows for workflow analysis
    
    **System Health:**
    - Error counts categorized by type, severity, and component
    - Active session counts
    - Cache hit rates and operation counts
    - Message throughput per session
    
    Perfect for setting up alerts, dashboards, and capacity planning.
    """
)
async def get_metrics():
    """Prometheus scrape endpoint - returns metrics in text exposition format"""
    return PlainTextResponse(content=generate_latest(REGISTRY), media_type=CONTENT_TYPE_LATEST)
