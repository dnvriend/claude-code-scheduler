"""OpenTelemetry observability integration for distributed tracing and metrics.

This module provides centralized configuration for traces, metrics, and logs
with support for existing verbosity levels (-v, -vv, -vvv).

Key Components:
    - setup_observability: Configure OTLP exporters for traces, metrics, logs
    - get_tracer: Get tracer instance for creating spans
    - get_meter: Get meter instance for recording metrics
    - add_span_attributes: Add attributes to current span
    - add_span_event: Add event to current span
    - record_exception: Record exception in current span
    - get_health_status: Check observability health
    - shutdown_observability: Graceful shutdown

Dependencies:
    - opentelemetry-sdk: OpenTelemetry SDK
    - opentelemetry-exporter-otlp-proto-grpc: OTLP exporters
    - opentelemetry-instrumentation-logging: Log instrumentation
    - opentelemetry-instrumentation-aiohttp-client: HTTP client tracing

Related Modules:
    - logging_config: Verbosity levels that control OTel log levels
    - services: May use tracing for operation spans

Environment Variables:
    OTEL_ENABLED: Enable/disable OpenTelemetry (default: false)
    OTEL_SERVICE_NAME: Service name for telemetry (default: claude-scheduler)
    OTEL_EXPORTER_OTLP_ENDPOINT: OTLP collector endpoint (default: http://localhost:4317)
    OTEL_EXPORTER_OTLP_INSECURE: Use insecure connection (default: true)
    OTEL_LOGS_EXPORTER: Log exporter type (otlp, console, none)

Example:
    >>> from claude_code_scheduler.observability import setup_observability, get_tracer
    >>> setup_observability(service_name="scheduler-daemon", verbose_count=2)
    >>> tracer = get_tracer(__name__)
    >>> with tracer.start_as_current_span("process_task"):
    ...     # Your code here
    ...     pass

Note:
    This code was generated with assistance from AI coding tools
    and has been reviewed and tested by a human.
"""

import logging
import os
from typing import Any

from opentelemetry import metrics, trace
from opentelemetry._logs import set_logger_provider
from opentelemetry.exporter.otlp.proto.grpc._log_exporter import OTLPLogExporter
from opentelemetry.exporter.otlp.proto.grpc.metric_exporter import OTLPMetricExporter
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.aiohttp_client import AioHttpClientInstrumentor
from opentelemetry.instrumentation.logging import LoggingInstrumentor
from opentelemetry.sdk._logs import LoggerProvider, LoggingHandler
from opentelemetry.sdk._logs.export import BatchLogRecordProcessor
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor

from claude_code_scheduler._version import __version__

logger = logging.getLogger(__name__)

# Global state
_observability_enabled = False
_service_name = "claude-scheduler"
_logger_provider: LoggerProvider | None = None
_trace_provider: TracerProvider | None = None
_meter_provider: MeterProvider | None = None


def is_enabled() -> bool:
    """Check if observability is enabled.

    Returns:
        True if OpenTelemetry is configured and enabled.
    """
    return _observability_enabled


def get_service_name() -> str:
    """Get the configured service name.

    Returns:
        Service name for telemetry.
    """
    return _service_name


def setup_observability(
    service_name: str = "claude-scheduler",
    verbose_count: int = 0,
    enable: bool | None = None,
) -> None:
    """Configure OpenTelemetry for traces, metrics, and logs.

    Args:
        service_name: Service name for telemetry identification.
        verbose_count: Verbosity level (0=WARNING, 1=INFO, 2=DEBUG, 3+=TRACE).
        enable: Explicitly enable/disable. If None, reads from OTEL_ENABLED env var.

    Environment Variables:
        OTEL_ENABLED: Enable/disable OTel (default: false)
        OTEL_SERVICE_NAME: Override service name
        OTEL_EXPORTER_OTLP_ENDPOINT: Collector endpoint (default: http://localhost:4317)
        OTEL_EXPORTER_OTLP_INSECURE: Use insecure connection (default: true)
        OTEL_LOGS_EXPORTER: Log exporter type (otlp, console, none)

    Example:
        >>> setup_observability("scheduler-daemon", verbose_count=2)
    """
    global _observability_enabled, _service_name
    global _logger_provider, _trace_provider, _meter_provider

    # Determine if observability should be enabled
    # Default to disabled - no collectors configured yet
    if enable is None:
        enable = os.getenv("OTEL_ENABLED", "false").lower() in ("true", "1", "yes")

    if not enable:
        logger.info("OpenTelemetry observability disabled")
        _observability_enabled = False
        return

    _service_name = os.getenv("OTEL_SERVICE_NAME", service_name)
    otlp_endpoint = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "http://localhost:4317")
    otlp_insecure = os.getenv("OTEL_EXPORTER_OTLP_INSECURE", "true").lower() in (
        "true",
        "1",
        "yes",
    )
    log_exporter_type = os.getenv("OTEL_LOGS_EXPORTER", "otlp").lower()

    # Create resource with service identification
    resource = Resource.create(
        {
            "service.name": _service_name,
            "service.version": __version__,
        }
    )

    # Setup tracing
    try:
        trace_exporter = OTLPSpanExporter(
            endpoint=otlp_endpoint,
            insecure=otlp_insecure,
        )
        _trace_provider = TracerProvider(resource=resource)
        _trace_provider.add_span_processor(BatchSpanProcessor(trace_exporter))
        trace.set_tracer_provider(_trace_provider)

        if verbose_count >= 1:
            logger.info(
                "OpenTelemetry tracing configured: service=%s, endpoint=%s",
                _service_name,
                otlp_endpoint,
            )
    except Exception as e:
        logger.warning("Failed to setup OpenTelemetry tracing: %s", e)

    # Setup metrics
    try:
        metric_exporter = OTLPMetricExporter(
            endpoint=otlp_endpoint,
            insecure=otlp_insecure,
        )
        metric_reader = PeriodicExportingMetricReader(
            exporter=metric_exporter,
            export_interval_millis=60000,  # Export every 60s
        )
        _meter_provider = MeterProvider(
            resource=resource,
            metric_readers=[metric_reader],
        )
        metrics.set_meter_provider(_meter_provider)

        if verbose_count >= 1:
            logger.info("OpenTelemetry metrics configured")
    except Exception as e:
        logger.warning("Failed to setup OpenTelemetry metrics: %s", e)

    # Setup log export (bridges Python logging to OTel)
    if log_exporter_type != "none":
        try:
            from opentelemetry.sdk._logs.export import ConsoleLogExporter, LogExporter

            _logger_provider = LoggerProvider(resource=resource)

            log_exporter: LogExporter
            if log_exporter_type == "otlp":
                log_exporter = OTLPLogExporter(
                    endpoint=otlp_endpoint,
                    insecure=otlp_insecure,
                )
            elif log_exporter_type == "console":
                log_exporter = ConsoleLogExporter()
            else:
                raise ValueError(f"Unknown OTEL_LOGS_EXPORTER: {log_exporter_type}")

            _logger_provider.add_log_record_processor(BatchLogRecordProcessor(log_exporter))
            set_logger_provider(_logger_provider)

            # Bridge Python logging to OTel - adds handler to root logger
            otel_handler = LoggingHandler(logger_provider=_logger_provider)
            logging.getLogger().addHandler(otel_handler)

            if verbose_count >= 1:
                logger.info(
                    "OpenTelemetry log export configured: exporter=%s, endpoint=%s",
                    log_exporter_type,
                    otlp_endpoint if log_exporter_type == "otlp" else "stdout",
                )
        except Exception as e:
            logger.warning("Failed to setup OpenTelemetry log export: %s", e)

    # Setup logging instrumentation (adds trace context to logs)
    try:
        LoggingInstrumentor().instrument(set_logging_format=False)
        if verbose_count >= 2:
            logger.debug("OpenTelemetry logging instrumentation enabled")
    except Exception as e:
        logger.warning("Failed to setup OpenTelemetry logging: %s", e)

    # Instrument aiohttp client
    try:
        AioHttpClientInstrumentor().instrument()
        if verbose_count >= 2:
            logger.debug("OpenTelemetry aiohttp instrumentation enabled")
    except Exception as e:
        logger.warning("Failed to setup OpenTelemetry aiohttp instrumentation: %s", e)

    _observability_enabled = True
    logger.info("OpenTelemetry observability enabled for service: %s", _service_name)


def get_tracer(name: str) -> trace.Tracer:
    """Get a tracer instance for creating spans.

    Args:
        name: Module or component name (use __name__).

    Returns:
        Tracer instance for creating spans.

    Example:
        >>> tracer = get_tracer(__name__)
        >>> with tracer.start_as_current_span("operation"):
        ...     # Your code here
        ...     pass
    """
    return trace.get_tracer(name)


def get_meter(name: str) -> metrics.Meter:
    """Get a meter instance for recording metrics.

    Args:
        name: Module or component name (use __name__).

    Returns:
        Meter instance for creating instruments.

    Example:
        >>> meter = get_meter(__name__)
        >>> counter = meter.create_counter("requests", description="Request count")
        >>> counter.add(1, {"endpoint": "/api/tasks"})
    """
    return metrics.get_meter(name)


def add_span_attributes(**attributes: Any) -> None:
    """Add attributes to the current span.

    Args:
        **attributes: Key-value pairs to add as span attributes.

    Example:
        >>> add_span_attributes(node_id="alpha", task_id="123")
    """
    current_span = trace.get_current_span()
    if current_span.is_recording():
        for key, value in attributes.items():
            current_span.set_attribute(key, value)


def add_span_event(name: str, **attributes: Any) -> None:
    """Add an event to the current span.

    Args:
        name: Event name.
        **attributes: Event attributes.

    Example:
        >>> add_span_event("task_dispatched", task_id="123", node_id="alpha")
    """
    current_span = trace.get_current_span()
    if current_span.is_recording():
        current_span.add_event(name, attributes=attributes)


def record_exception(exception: Exception) -> None:
    """Record an exception in the current span.

    Args:
        exception: Exception to record.

    Example:
        >>> try:
        ...     risky_operation()
        ... except Exception as e:
        ...     record_exception(e)
        ...     raise
    """
    current_span = trace.get_current_span()
    if current_span.is_recording():
        current_span.record_exception(exception)
        current_span.set_status(trace.Status(trace.StatusCode.ERROR, str(exception)))


def get_health_status() -> dict[str, Any]:
    """Get observability health status.

    Returns:
        Dict with health information.

    Example:
        >>> status = get_health_status()
        >>> print(status["enabled"])
    """
    return {
        "enabled": _observability_enabled,
        "service_name": _service_name,
        "tracing": _trace_provider is not None,
        "metrics": _meter_provider is not None,
        "logs": _logger_provider is not None,
    }


def shutdown_observability() -> None:
    """Gracefully shutdown OpenTelemetry providers.

    Flushes pending telemetry data and releases resources.
    Call this during application shutdown to ensure all data is exported.

    Example:
        >>> import atexit
        >>> atexit.register(shutdown_observability)
    """
    global _logger_provider, _trace_provider, _meter_provider, _observability_enabled

    if not _observability_enabled:
        return

    logger.debug("Shutting down OpenTelemetry providers")

    if _logger_provider:
        try:
            _logger_provider.shutdown()  # type: ignore[no-untyped-call]
            logger.debug("Log provider shutdown complete")
        except Exception as e:
            logger.warning("Error shutting down log provider: %s", e)
        _logger_provider = None

    if _trace_provider:
        try:
            _trace_provider.shutdown()
            logger.debug("Trace provider shutdown complete")
        except Exception as e:
            logger.warning("Error shutting down trace provider: %s", e)
        _trace_provider = None

    if _meter_provider:
        try:
            _meter_provider.shutdown()
            logger.debug("Meter provider shutdown complete")
        except Exception as e:
            logger.warning("Error shutting down meter provider: %s", e)
        _meter_provider = None

    _observability_enabled = False
    logger.info("OpenTelemetry shutdown complete")
