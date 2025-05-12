from uno.logging.protocols import LoggerProtocol


class FakeLogger(LoggerProtocol):
    def debug(self, message: str, **kwargs):
        pass

    def info(self, message: str, **kwargs):
        pass

    def warning(self, message: str, **kwargs):
        pass

    def error(self, message: str, **kwargs):
        pass

    def critical(self, message: str, **kwargs):
        pass

    def structured_log(self, level, message: str, **kwargs):
        pass

    def bind(self, **kwargs):
        return self

    def with_correlation_id(self, correlation_id: str):
        return self

    def set_level(self, level):
        pass

    def context(self, **kwargs):
        class DummyContext:
            def __enter__(self):
                return None

            def __exit__(self, exc_type, exc_val, exc_tb):
                return False

        return DummyContext()

    async def async_context(self, **kwargs):
        class DummyAsyncContext:
            async def __aenter__(self):
                return None

            async def __aexit__(self, exc_type, exc_val, exc_tb):
                return False

        return DummyAsyncContext()

    async def __aenter__(self) -> LoggerProtocol:
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        pass

    # Async versions for compatibility with async code
    async def debug_async(self, message: str, **kwargs):
        pass

    async def info_async(self, message: str, **kwargs):
        pass

    async def warning_async(self, message: str, **kwargs):
        pass

    async def error_async(self, message: str, **kwargs):
        pass

    async def critical_async(self, message: str, **kwargs):
        pass

    async def structured_log_async(self, level, message: str, **kwargs):
        pass
