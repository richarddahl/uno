"""
SQL security management.
"""

from __future__ import annotations
from typing import Any, Dict, List, Optional, Set
import re
from datetime import datetime
from pydantic import BaseModel, Field
from sqlalchemy import text
from uno.core.errors.result import Result, Success, Failure
from uno.infrastructure.sql.config import SQLConfig
from uno.infrastructure.logging.logger import LoggerService


class SecurityViolation(BaseModel):
    """Security violation details."""
    
    timestamp: datetime
    violation_type: str
    statement: str
    parameters: dict[str, Any]
    user_id: Optional[str]
    ip_address: Optional[str]
    details: dict[str, Any]


class SQLSecurityManager:
    """Manages SQL security features."""

    def __init__(
        self,
        config: SQLConfig,
        logger: LoggerService,
        allowed_sql_keywords: Optional[set[str]] = None,
        blocked_sql_keywords: Optional[set[str]] = None,
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
            "SELECT", "INSERT", "UPDATE", "DELETE", "FROM", "WHERE", "JOIN",
            "LEFT", "RIGHT", "INNER", "OUTER", "GROUP", "BY", "ORDER", "HAVING",
            "LIMIT", "OFFSET", "AND", "OR", "NOT", "IN", "EXISTS", "BETWEEN",
            "LIKE", "IS", "NULL", "TRUE", "FALSE", "ASC", "DESC"
        }
        self._blocked_keywords = blocked_sql_keywords or {
            "DROP", "TRUNCATE", "ALTER", "CREATE", "GRANT", "REVOKE",
            "EXECUTE", "EXEC", "UNION", "ALL", "ANY", "SOME", "WITH"
        }
        self._violations: list[SecurityViolation] = []

    def sanitize_statement(self, statement: str) -> Result[str, str]:
        """Sanitize SQL statement to prevent injection.
        
        Args:
            statement: SQL statement to sanitize
            
        Returns:
            Result containing sanitized statement or error
        """
        try:
            # Check for blocked keywords
            for keyword in self._blocked_keywords:
                if re.search(rf"\b{keyword}\b", statement, re.IGNORECASE):
                    self._log_violation(
                        "blocked_keyword",
                        statement,
                        {},
                        details={"blocked_keyword": keyword}
                    )
                    return Failure(f"Statement contains blocked keyword: {keyword}")

            # Validate allowed keywords
            words = re.findall(r'\b\w+\b', statement.upper())
            for word in words:
                if word in self._allowed_keywords or word in self._blocked_keywords:
                    continue
                if not word.isdigit() and not word.startswith(':'):
                    self._log_violation(
                        "unknown_keyword",
                        statement,
                        {},
                        details={"unknown_keyword": word}
                    )
                    return Failure(f"Statement contains unknown keyword: {word}")

            # Check for common injection patterns
            injection_patterns = [
                r"'.*--",  # SQL comments
                r"'.*;.*",  # Multiple statements
                r"'.*/\*.*\*/",  # Multi-line comments
                r"'.*xp_",  # Extended stored procedures
                r"'.*sp_",  # Stored procedures
                r"'.*0x",  # Hex encoding
                r"'.*WAITFOR",  # Time-based attacks
                r"'.*BENCHMARK",  # Performance-based attacks
            ]
            
            for pattern in injection_patterns:
                if re.search(pattern, statement, re.IGNORECASE):
                    self._log_violation(
                        "injection_pattern",
                        statement,
                        {},
                        details={"pattern": pattern}
                    )
                    return Failure("Statement contains potential injection pattern")

            return Success(statement)
        except Exception as e:
            self._logger.structured_log(
                "ERROR",
                f"Failed to sanitize statement: {str(e)}",
                name="uno.sql.security",
                error=e
            )
            return Failure(f"Failed to sanitize statement: {str(e)}")

    def check_permissions(
        self,
        statement: str,
        user_id: Optional[str] = None,
        required_permissions: Optional[set[str]] = None
    ) -> Result[None, str]:
        """Check if user has required permissions for statement.
        
        Args:
            statement: SQL statement to check
            user_id: User ID to check permissions for
            required_permissions: Set of required permissions
            
        Returns:
            Result indicating success or failure
        """
        try:
            if not self._config.DB_CHECK_PERMISSIONS:
                return Success(None)

            if not user_id:
                self._log_violation(
                    "missing_user",
                    statement,
                    {},
                    user_id=user_id
                )
                return Failure("User ID required for permission check")

            # TODO: Implement actual permission checking
            # This would typically check against a permissions database
            # For now, we'll just log the check
            self._logger.structured_log(
                "INFO",
                f"Checking permissions for user {user_id}",
                name="uno.sql.security",
                statement=statement,
                required_permissions=required_permissions
            )
            return Success(None)
        except Exception as e:
            self._logger.structured_log(
                "ERROR",
                f"Failed to check permissions: {str(e)}",
                name="uno.sql.security",
                error=e
            )
            return Failure(f"Failed to check permissions: {str(e)}")

    def audit_statement(
        self,
        statement: str,
        parameters: dict[str, Any],
        user_id: Optional[str] = None,
        ip_address: Optional[str] = None
    ) -> Result[None, str]:
        """Audit SQL statement execution.
        
        Args:
            statement: SQL statement to audit
            parameters: Statement parameters
            user_id: User ID executing statement
            ip_address: IP address of execution
            
        Returns:
            Result indicating success or failure
        """
        try:
            if not self._config.DB_AUDIT_LOGGING:
                return Success(None)

            self._logger.structured_log(
                "INFO",
                "Auditing SQL statement",
                name="uno.sql.security",
                statement=statement,
                parameters=parameters,
                user_id=user_id,
                ip_address=ip_address
            )
            return Success(None)
        except Exception as e:
            self._logger.structured_log(
                "ERROR",
                f"Failed to audit statement: {str(e)}",
                name="uno.sql.security",
                error=e
            )
            return Failure(f"Failed to audit statement: {str(e)}")

    def _log_violation(
        self,
        violation_type: str,
        statement: str,
        parameters: dict[str, Any],
        user_id: Optional[str] = None,
        ip_address: Optional[str] = None,
        details: Optional[dict[str, Any]] = None
    ) -> None:
        """Log security violation.
        
        Args:
            violation_type: Type of violation
            statement: SQL statement
            parameters: Statement parameters
            user_id: User ID
            ip_address: IP address
            details: Additional violation details
        """
        violation = SecurityViolation(
            timestamp=datetime.now(),
            violation_type=violation_type,
            statement=statement,
            parameters=parameters,
            user_id=user_id,
            ip_address=ip_address,
            details=details or {}
        )
        self._violations.append(violation)
        
        self._logger.structured_log(
            "WARNING",
            f"SQL security violation: {violation_type}",
            name="uno.sql.security",
            violation=violation.dict()
        )

    @property
    def violations(self) -> list[SecurityViolation]:
        """Get list of security violations.
        
        Returns:
            List of security violations
        """
        return self._violations 