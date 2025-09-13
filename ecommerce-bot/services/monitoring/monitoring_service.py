"""
Production Monitoring and Observability Service
- Prometheus metrics
- Distributed tracing
- Structured logging
- Performance monitoring
- Alert management
"""

import time
import logging
import json
import asyncio
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from contextlib import asynccontextmanager
from functools import wraps
import traceback
from enum import Enum

from prometheus_client import (
    Counter, Histogram, Gauge, Summary,
    generate_latest, CONTENT_TYPE_LATEST
)
from prometheus_client.core import CollectorRegistry
import structlog
from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.sdk.resources import Resource
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.redis import RedisInstrumentor
from opentelemetry.instrumentation.pymongo import PymongoInstrumentor

# Configure structured logging
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        structlog.processors.JSONRenderer()
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger()

class MetricType(Enum):
    COUNTER = "counter"
    GAUGE = "gauge"
    HISTOGRAM = "histogram"
    SUMMARY = "summary"

class MonitoringService:
    """Centralized monitoring service for production observability"""
    
    def __init__(self, service_name="ecommerce-bot", environment="production"):
        self.service_name = service_name
        self.environment = environment
        self.registry = CollectorRegistry()
        self.metrics = {}
        self.tracer = None
        self.logger = structlog.get_logger(service=service_name)
        
        # Initialize metrics
        self._initialize_metrics()
        
        # Initialize tracing
        self._initialize_tracing()
        
        # Alert thresholds
        self.alert_thresholds = {
            "error_rate": 0.01,  # 1% error rate
            "latency_p99": 1000,  # 1 second
            "memory_usage": 0.8,  # 80% memory
            "cpu_usage": 0.7,  # 70% CPU
        }
        
        # Background tasks
        self._background_tasks = []
        self._shutdown = False
    
    def _initialize_metrics(self):
        """Initialize Prometheus metrics"""
        
        # Request metrics
        self.metrics["requests_total"] = Counter(
            "requests_total",
            "Total number of requests",
            ["method", "endpoint", "status"],
            registry=self.registry
        )
        
        self.metrics["request_duration"] = Histogram(
            "request_duration_seconds",
            "Request duration in seconds",
            ["method", "endpoint"],
            buckets=(0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1, 2.5, 5, 10),
            registry=self.registry
        )
        
        # Business metrics
        self.metrics["orders_total"] = Counter(
            "orders_total",
            "Total number of orders placed",
            ["status"],
            registry=self.registry
        )
        
        self.metrics["cart_operations"] = Counter(
            "cart_operations_total",
            "Cart operations",
            ["operation", "status"],
            registry=self.registry
        )
        
        self.metrics["revenue_total"] = Counter(
            "revenue_total",
            "Total revenue",
            ["currency"],
            registry=self.registry
        )
        
        # System metrics
        self.metrics["active_sessions"] = Gauge(
            "active_sessions",
            "Number of active user sessions",
            registry=self.registry
        )
        
        self.metrics["redis_connections"] = Gauge(
            "redis_connections",
            "Number of Redis connections",
            ["pool"],
            registry=self.registry
        )
        
        self.metrics["mongodb_connections"] = Gauge(
            "mongodb_connections",
            "Number of MongoDB connections",
            registry=self.registry
        )
        
        # Error metrics
        self.metrics["errors_total"] = Counter(
            "errors_total",
            "Total number of errors",
            ["error_type", "component"],
            registry=self.registry
        )
        
        self.metrics["circuit_breaker_state"] = Gauge(
            "circuit_breaker_state",
            "Circuit breaker state (0=closed, 1=open, 2=half-open)",
            ["service"],
            registry=self.registry
        )
        
        # Performance metrics
        self.metrics["llm_latency"] = Histogram(
            "llm_latency_seconds",
            "LLM response latency",
            ["provider", "model"],
            buckets=(0.1, 0.5, 1, 2, 5, 10, 30),
            registry=self.registry
        )
        
        self.metrics["tool_execution_duration"] = Histogram(
            "tool_execution_duration_seconds",
            "MCP tool execution duration",
            ["tool_name"],
            registry=self.registry
        )
        
        # Cache metrics
        self.metrics["cache_hits"] = Counter(
            "cache_hits_total",
            "Cache hits",
            ["cache_type"],
            registry=self.registry
        )
        
        self.metrics["cache_misses"] = Counter(
            "cache_misses_total",
            "Cache misses",
            ["cache_type"],
            registry=self.registry
        )
        
        logger.info("Metrics initialized", count=len(self.metrics))
    
    def _initialize_tracing(self):
        """Initialize OpenTelemetry tracing"""
        try:
            # Configure resource
            resource = Resource.create({
                "service.name": self.service_name,
                "service.version": "1.0.0",
                "deployment.environment": self.environment
            })
            
            # Configure tracer provider
            provider = TracerProvider(resource=resource)
            
            # Add OTLP exporter (for Jaeger, Zipkin, etc.)
            otlp_exporter = OTLPSpanExporter(
                endpoint="localhost:4317",  # OTLP collector endpoint
                insecure=True
            )
            
            span_processor = BatchSpanProcessor(otlp_exporter)
            provider.add_span_processor(span_processor)
            
            # Set global tracer provider
            trace.set_tracer_provider(provider)
            
            # Get tracer
            self.tracer = trace.get_tracer(__name__)
            
            # Auto-instrument libraries
            FastAPIInstrumentor.instrument()
            RedisInstrumentor.instrument()
            PymongoInstrumentor.instrument()
            
            logger.info("Tracing initialized")
            
        except Exception as e:
            logger.error("Failed to initialize tracing", error=str(e))
    
    def record_metric(self, metric_name: str, value: float, labels: Dict[str, str] = None):
        """Record a metric value"""
        try:
            if metric_name not in self.metrics:
                logger.warning(f"Unknown metric: {metric_name}")
                return
            
            metric = self.metrics[metric_name]
            
            if isinstance(metric, Counter):
                if labels:
                    metric.labels(**labels).inc(value)
                else:
                    metric.inc(value)
            
            elif isinstance(metric, Gauge):
                if labels:
                    metric.labels(**labels).set(value)
                else:
                    metric.set(value)
            
            elif isinstance(metric, Histogram):
                if labels:
                    metric.labels(**labels).observe(value)
                else:
                    metric.observe(value)
            
            elif isinstance(metric, Summary):
                if labels:
                    metric.labels(**labels).observe(value)
                else:
                    metric.observe(value)
                    
        except Exception as e:
            logger.error("Error recording metric", metric=metric_name, error=str(e))
    
    @asynccontextmanager
    async def track_request(self, method: str, endpoint: str):
        """Context manager to track request metrics"""
        start_time = time.time()
        span = None
        
        if self.tracer:
            span = self.tracer.start_span(f"{method} {endpoint}")
            span.set_attribute("http.method", method)
            span.set_attribute("http.route", endpoint)
        
        try:
            yield span
            
            # Record success metrics
            duration = time.time() - start_time
            self.record_metric("requests_total", 1, {
                "method": method,
                "endpoint": endpoint,
                "status": "success"
            })
            self.record_metric("request_duration", duration, {
                "method": method,
                "endpoint": endpoint
            })
            
            if span:
                span.set_attribute("http.status_code", 200)
                
        except Exception as e:
            # Record error metrics
            duration = time.time() - start_time
            self.record_metric("requests_total", 1, {
                "method": method,
                "endpoint": endpoint,
                "status": "error"
            })
            self.record_metric("request_duration", duration, {
                "method": method,
                "endpoint": endpoint
            })
            self.record_metric("errors_total", 1, {
                "error_type": type(e).__name__,
                "component": "request_handler"
            })
            
            if span:
                span.set_attribute("http.status_code", 500)
                span.set_attribute("error", True)
                span.set_attribute("error.message", str(e))
            
            raise
            
        finally:
            if span:
                span.end()
    
    @asynccontextmanager
    async def track_tool_execution(self, tool_name: str):
        """Track MCP tool execution"""
        start_time = time.time()
        span = None
        
        if self.tracer:
            span = self.tracer.start_span(f"tool.{tool_name}")
            span.set_attribute("tool.name", tool_name)
        
        try:
            yield span
            
            duration = time.time() - start_time
            self.record_metric("tool_execution_duration", duration, {
                "tool_name": tool_name
            })
            
            if span:
                span.set_attribute("tool.success", True)
                
        except Exception as e:
            self.record_metric("errors_total", 1, {
                "error_type": type(e).__name__,
                "component": f"tool_{tool_name}"
            })
            
            if span:
                span.set_attribute("tool.success", False)
                span.set_attribute("error.message", str(e))
            
            raise
            
        finally:
            if span:
                span.end()
    
    def log_structured(self, level: str, message: str, **kwargs):
        """Log structured message with context"""
        log_method = getattr(self.logger, level.lower(), self.logger.info)
        log_method(message, **kwargs)
    
    async def check_health(self) -> Dict[str, Any]:
        """Perform health check and return status"""
        health = {
            "status": "healthy",
            "timestamp": datetime.utcnow().isoformat(),
            "service": self.service_name,
            "environment": self.environment,
            "checks": {}
        }
        
        # Check error rate
        try:
            # Calculate error rate from metrics
            # This is simplified - in production, query Prometheus
            health["checks"]["error_rate"] = {
                "status": "healthy",
                "threshold": self.alert_thresholds["error_rate"]
            }
        except Exception as e:
            health["checks"]["error_rate"] = {
                "status": "unhealthy",
                "error": str(e)
            }
            health["status"] = "degraded"
        
        return health
    
    async def start_background_monitoring(self):
        """Start background monitoring tasks"""
        self._background_tasks.append(
            asyncio.create_task(self._metrics_aggregator())
        )
        self._background_tasks.append(
            asyncio.create_task(self._alert_checker())
        )
        self._background_tasks.append(
            asyncio.create_task(self._performance_profiler())
        )
    
    async def _metrics_aggregator(self):
        """Aggregate and process metrics periodically"""
        while not self._shutdown:
            try:
                await asyncio.sleep(60)  # Every minute
                
                # Log current metrics summary
                self.log_structured(
                    "info",
                    "Metrics summary",
                    active_sessions=self.metrics["active_sessions"]._value.get(),
                    total_requests=self.metrics["requests_total"]._value._value
                )
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error("Error in metrics aggregator", error=str(e))
    
    async def _alert_checker(self):
        """Check metrics against thresholds and trigger alerts"""
        while not self._shutdown:
            try:
                await asyncio.sleep(30)  # Every 30 seconds
                
                # Check thresholds
                alerts = []
                
                # This is simplified - in production, query metrics properly
                # and send alerts via PagerDuty, Slack, etc.
                
                if alerts:
                    await self._send_alerts(alerts)
                    
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error("Error in alert checker", error=str(e))
    
    async def _performance_profiler(self):
        """Profile application performance"""
        while not self._shutdown:
            try:
                await asyncio.sleep(300)  # Every 5 minutes
                
                # Collect performance metrics
                import psutil
                process = psutil.Process()
                
                self.log_structured(
                    "info",
                    "Performance profile",
                    cpu_percent=process.cpu_percent(),
                    memory_mb=process.memory_info().rss / 1024 / 1024,
                    num_threads=process.num_threads(),
                    open_files=len(process.open_files())
                )
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error("Error in performance profiler", error=str(e))
    
    async def _send_alerts(self, alerts: List[Dict]):
        """Send alerts to notification channels"""
        for alert in alerts:
            self.log_structured(
                "warning",
                "Alert triggered",
                alert_type=alert["type"],
                severity=alert["severity"],
                message=alert["message"]
            )
            
            # In production, integrate with:
            # - PagerDuty
            # - Slack
            # - Email
            # - SMS
    
    def get_metrics(self) -> bytes:
        """Get Prometheus metrics in text format"""
        return generate_latest(self.registry)
    
    async def shutdown(self):
        """Gracefully shutdown monitoring"""
        self._shutdown = True
        
        # Cancel background tasks
        for task in self._background_tasks:
            task.cancel()
        
        await asyncio.gather(*self._background_tasks, return_exceptions=True)
        
        logger.info("Monitoring service shutdown complete")

# Decorator for monitoring functions
def monitor_performance(operation_name: str = None):
    """Decorator to monitor function performance"""
    def decorator(func):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            name = operation_name or func.__name__
            monitoring = MonitoringService()
            
            async with monitoring.track_tool_execution(name):
                return await func(*args, **kwargs)
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            name = operation_name or func.__name__
            start_time = time.time()
            
            try:
                result = func(*args, **kwargs)
                duration = time.time() - start_time
                logger.info(f"Operation completed", operation=name, duration=duration)
                return result
                
            except Exception as e:
                duration = time.time() - start_time
                logger.error(f"Operation failed", operation=name, duration=duration, error=str(e))
                raise
        
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper
            
    return decorator

# Global monitoring instance
monitoring_service = MonitoringService()