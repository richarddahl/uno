import logging
from collections.abc import Generator

import pytest


@pytest.fixture(autouse=True)
def suppress_logs(monkeypatch: pytest.MonkeyPatch) -> Generator[None]:
    """
    Suppress log output below WARNING level for most tests.
    Disable this fixture with @pytest.mark.usefixtures('allow_logging')
    """
    root_logger = logging.getLogger()
    original_level = root_logger.level
    root_logger.setLevel(logging.WARNING)
    try:
        yield
    finally:
        root_logger.setLevel(original_level)


@pytest.fixture
def allow_logging() -> None:
    """
    Dummy fixture to allow log output in selected tests.
    Use with @pytest.mark.usefixtures('allow_logging').
    """
    pass
