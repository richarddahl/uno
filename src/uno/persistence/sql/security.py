"""
SQL security management.
"""

from __future__ import annotations

import re
from datetime import datetime
from typing import Any, cast, Optional
from pydantic import BaseModel, Field
from uno.persistence.sql.config import SQLConfig
from uno.logging.protocols import LoggerProtocol
from uno.errors import UnoError


class SecurityViolation(BaseModel):
    """Represents a security violation."""

    timestamp: datetime = Field(default_factory=datetime.now)
    statement: str
    user_id: str | None = None
    ip_address: str | None = None
    violation_type: str
    details: dict[str, Any] = Field(default_factory=dict)


class SQLSecurityManager:
    """Manages SQL security features."""

    def __init__(
        self,
        config: SQLConfig,
        logger: LoggerProtocol,
        allowed_sql_keywords: set[str] | None = None,
        blocked_sql_keywords: set[str] | None = None,
    ) -> None:
        """Initialize SQL security manager.

        Args:
            config: SQL configuration
            logger: Logger service
            allowed_sql_keywords: Set of allowed SQL keywords
            blocked_sql_keywords: Set of blocked SQL keywords
        """
        self._config = config
        self._logger = logger
        self._allowed_keywords = allowed_sql_keywords or {
            "SELECT",
            "INSERT",
            "UPDATE",
            "DELETE",
            "FROM",
            "WHERE",
            "JOIN",
            "LEFT",
            "RIGHT",
            "INNER",
            "OUTER",
            "GROUP",
            "BY",
            "ORDER",
            "HAVING",
            "LIMIT",
            "OFFSET",
            "AND",
            "OR",
            "NOT",
            "IN",
            "EXISTS",
            "BETWEEN",
            "LIKE",
            "IS",
            "NULL",
            "TRUE",
            "FALSE",
            "ASC",
            "DESC",
        }
        self._blocked_keywords = blocked_sql_keywords or {
            "DROP",
            "TRUNCATE",
            "ALTER",
            "CREATE",
            "GRANT",
            "REVOKE",
            "EXECUTE",
            "EXEC",
            "UNION",
            "ALL",
            "ANY",
            "SOME",
            "WITH",
        }
        self._violations: list[SecurityViolation] = []
        self._injection_patterns = [
            r"\b(?:SELECT|INSERT|UPDATE|DELETE|DROP|ALTER|CREATE)\b.*\bFROM\b.*\bWHERE\b.*\b1=1\b",
            r"\b(?:SELECT|INSERT|UPDATE|DELETE|DROP|ALTER|CREATE)\b.*\bFROM\b.*\bWHERE\b.*\b1=0\b",
            r"\b(?:SELECT|INSERT|UPDATE|DELETE|DROP|ALTER|CREATE)\b.*\bFROM\b.*\bWHERE\b.*\b\' OR \'.*\'=\'\'\b",
            r"\b(?:SELECT|INSERT|UPDATE|DELETE|DROP|ALTER|CREATE)\b.*\bFROM\b.*\bWHERE\b.*\b\' OR \'.*\'=\'\'\b",
            r"\b(?:SELECT|INSERT|UPDATE|DELETE|DROP|ALTER|CREATE)\b.*\bFROM\b.*\bWHERE\b.*\b\' OR \'.*\'=\'\'\b",
        ]

    def sanitize_statement(self, statement: str) -> str:
        """Sanitize SQL statement to prevent injection.

        Args:
            statement: SQL statement to sanitize

        Raises:
            UnoError: If the statement contains blocked keywords or injection patterns

        Returns:
            The sanitized statement
        """
        try:
            # Check for blocked keywords
            for keyword in self._blocked_keywords:
                if re.search(rf"\b{keyword}\b", statement, re.IGNORECASE):
                    self._log_violation(
                        "blocked_keyword",
                        statement,
                        {},
                        details={"blocked_keyword": keyword},
                    )
                    raise UnoError(
                        "Statement contains blocked keyword",
                        "SQL_SECURITY_ERROR",
                        details={"blocked_keyword": keyword},
                    )

            # Validate allowed keywords
            words = re.findall(r"\b\w+\b", statement.upper())
            unknown_keywords = set(words) - self._allowed_keywords
            if unknown_keywords:
                self._log_violation(
                    "unknown_keyword",
                    statement,
                    {},
                    details={"unknown_keyword": next(iter(unknown_keywords))},
                )
                raise UnoError(
                    "Statement contains unknown keyword",
                    "SQL_SECURITY_ERROR",
                    details={"unknown_keyword": next(iter(unknown_keywords))},
                )

            # Check for injection patterns
            for pattern in self._injection_patterns:
                if re.search(pattern, statement, re.IGNORECASE):
                    self._log_violation(
                        "injection_pattern", statement, {}, details={"pattern": pattern}
                    )
                    raise UnoError(
                        "Statement contains potential injection pattern",
                        "SQL_SECURITY_ERROR",
                        details={"pattern": pattern},
                    )

            return statement
        except Exception as e:
            self._logger.structured_log(
                "ERROR",
                f"Failed to sanitize statement: {str(e)}",
                name="uno.sql.security",
                error=e,
            )
            raise UnoError(
                f"Failed to sanitize statement: {str(e)}",
                "SQL_SECURITY_ERROR",
            ) from e

    def check_permissions(
        self,
        statement: str,
        user_id: Optional[str] = None,
        required_permissions: Optional[set[str]] = None,
    ) -> None:
        """Check if user has required permissions for statement.

        Args:
            statement: SQL statement to check
            user_id: User ID to check permissions for
            required_permissions: Set of required permissions

        Raises:
            UnoError: If permission checks fail
        """
        try:
            if not self._config.DB_CHECK_PERMISSIONS:
                return

            if not user_id:
                self._log_violation(
                    "missing_user", statement, {}, details={"user_id": user_id}
                )
                raise UnoError(
                    "User ID is required for permission checks",
                    "SQL_SECURITY_ERROR",
                    details={"user_id": user_id},
                )

            # Get user permissions from cache or database
            user_permissions = self._get_user_permissions(user_id)
            if not user_permissions:
                self._log_violation(
                    "no_permissions", statement, {}, details={"user_id": user_id}
                )
                raise UnoError(
                    "User has no permissions",
                    "SQL_SECURITY_ERROR",
                    details={"user_id": user_id},
                )

            # Check required permissions
            if required_permissions and not required_permissions.issubset(
                user_permissions
            ):
                missing_permissions = required_permissions - user_permissions
                self._log_violation(
                    "missing_permissions",
                    statement,
                    {},
                    details={
                        "user_id": user_id,
                        "missing_permissions": list(missing_permissions),
                    },
                )
                raise UnoError(
                    f"Missing required permissions: {missing_permissions}",
                    "SQL_SECURITY_ERROR",
                    details={
                        "user_id": user_id,
                        "missing_permissions": list(missing_permissions),
                    },
                )

        except Exception as e:
            self._logger.structured_log(
                "ERROR",
                f"Failed to check permissions: {str(e)}",
                name="uno.sql.security",
                error=e,
            )
            raise UnoError(
                f"Failed to check permissions: {str(e)}",
                "SQL_SECURITY_ERROR",
            ) from e

    def audit_statement(
        self,
        statement: str,
        parameters: dict[str, Any],
        user_id: Optional[str] = None,
        ip_address: Optional[str] = None,
    ) -> None:
        """Audit SQL statement execution.

        Args:
            statement: SQL statement being executed
            parameters: Dictionary of parameters
            user_id: User ID executing statement
            ip_address: IP address of execution

        Raises:
            UnoError: If audit logging fails
        """
        try:
            if not self._config.DB_AUDIT_LOGGING:
                return

            def _store_audit_log(self, audit_log: dict[str, Any]) -> None:
                """Store audit log entry.

                Args:
                    audit_log: Audit log entry to store
                """
                try:
                    # TODO: Implement actual audit log storage
                    # This could be to a database, file, or external service
                    self._logger.info(
                        "Storing audit log",
                        name="uno.sql.security",
                        audit_log=audit_log,
                    )
                except Exception as e:
                    self._logger.error(
                        "Failed to store audit log",
                        name="uno.sql.security",
                        error=e,
                    )
                    raise UnoError(
                        "Failed to store audit log",
                        "SQL_SECURITY_ERROR",
                        details={"error": str(e)},
                    ) from e

            # Create audit log entry
            audit_log = {
                "timestamp": datetime.now().isoformat(),
                "user_id": user_id,
{{ ... }}
                "statement": statement,
                "parameters": parameters,
            }

            # Store audit log
            self._store_audit_log(audit_log)

        except Exception as e:
            cast(Any, self._logger).structured_log(
                "ERROR",
                f"Failed to audit statement: {str(e)}",
                name="uno.sql.security",
                error=e,
            )
            raise UnoError(
                f"Failed to audit statement: {str(e)}",
                "SQL_SECURITY_ERROR",
            ) from e

    def _log_violation(
        self,
        violation_type: str,
        statement: str,
        parameters: dict[str, Any],
        details: dict[str, Any],
    ) -> None:
        """Log a security violation.

        Args:
            violation_type: Type of violation
            statement: SQL statement
            parameters: Statement parameters
            details: Additional violation details
        """
        violation = SecurityViolation(
            statement=statement,
            violation_type=violation_type,
            details=details,
        )
        self._violations.append(violation)

        # Cast LoggerProtocol to Any to bypass type checking for structured_log
        cast("Any", self._logger).structured_log(
            "WARNING",
            f"Security violation: {violation_type}",
            name="uno.sql.security",
            violation=violation,
            statement=statement,
            parameters=parameters,
        )

    @property
    def violations(self) -> list[SecurityViolation]:
        """Get list of security violations.

        Returns:
            List of security violations
        """
        return self._violations
