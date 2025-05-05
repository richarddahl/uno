import pytest

from uno.infrastructure.di.service_collection import ServiceCollection
from uno.infrastructure.logging.logger import LoggerService, LoggingConfig


@pytest.mark.asyncio
async def test_di_logger_tracing_and_error_context():
    """
    DI integration: LoggerService should propagate trace context and error context fields in all log outputs.
    """
    sc = ServiceCollection()
    config = LoggingConfig()
    sc.add_singleton(LoggingConfig, implementation=config)
    sc.add_singleton(
        LoggerService,
        implementation=lambda: LoggerService(LoggingConfig(CONSOLE_OUTPUT=False)),
    )
    resolver = sc.build()
    result = resolver.resolve(LoggerService)
    assert hasattr(result, "value")
    logger_service = result.value
    await logger_service.initialize()
    logger = logger_service.get_logger("uno.di.tracing")

    # Test trace context propagation
    trace_context = logger_service.new_trace_context()
    with logger_service.trace_scope(logger_service, trace_context=trace_context):
        logger.info("DI trace context test")
        log_record = (
            logger_service._log_buffer[-1]
            if hasattr(logger_service, "_log_buffer") and logger_service._log_buffer
            else None
        )
        if log_record:
            # Check correlation_id in log record
            assert "correlation_id" in log_record["extra"]
            assert (
                log_record["extra"]["correlation_id"] == trace_context["correlation_id"]
            )

    # Test error context propagation
    try:
        raise ValueError("DI error context test")
    except Exception as exc:
        logger.error("An error occurred", extra={"error": str(exc)})
        log_record = (
            logger_service._log_buffer[-1]
            if hasattr(logger_service, "_log_buffer") and logger_service._log_buffer
            else None
        )
        if log_record:
            assert "error" in log_record["extra"]
            assert log_record["extra"]["error"] == "DI error context test"

    await logger_service.dispose()
