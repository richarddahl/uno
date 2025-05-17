"""Unit of Work exceptions."""

class UnitOfWorkError(Exception):
    """Base exception for all UoW related errors."""
    pass

class ConcurrencyError(UnitOfWorkError):
    """Raised when a concurrency conflict is detected."""
    pass

class RepositoryError(UnitOfWorkError):
    """Raised when a repository operation fails."""
    pass

class TransactionError(UnitOfWorkError):
    """Raised when a transaction operation fails."""
    pass
