"""
SQLExecutionProtocol: Protocol for SQL execution services.
"""

from typing import Protocol, Any


class SQLExecutionProtocol(Protocol):
    def execute_ddl(self, ddl: str) -> None: ...
    def execute_script(self, script: str) -> None: ...
    def execute_emitter(self, emitter: Any, dry_run: bool = False) -> list[Any]: ...
