import logging
from collections.abc import Generator

import pytest

from typing import Any


def assert_domain_event_equivalent(a: Any, b: Any, exclude: set[str] = {"event_id", "timestamp"}):
    """
    Assert that two event or value objects are equivalent for domain purposes,
    ignoring non-business fields like event_id and timestamp by default.
    """
    a_dict = a.model_dump(exclude=exclude)
    b_dict = b.model_dump(exclude=exclude)
    assert a_dict == b_dict, f"Domain event/value object mismatch:\n{a_dict}\n!=\n{b_dict}"


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
