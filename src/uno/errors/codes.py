"""Standardized error codes for the Uno framework.

This module defines a comprehensive set of error codes used throughout the application.
Error codes follow the format:

    E[Category][Subcategory][Number]

Where:
- E: Prefix for error codes
- Category: 1 digit (0-9) representing the main component
- Subcategory: 1 digit (0-9) representing the subcomponent
- Number: 3 digits (000-999) for the specific error

Categories:
0: Framework/System errors
1: Event system
2: Domain/Application
3: Infrastructure
4: Validation
5: Authentication/Authorization
6: External services
7: Configuration
8: Serialization/Deserialization
9: Deprecated/Reserved
"""

from __future__ import annotations

from strenum import StrEnum

# Global code map to store error code values to enum members
_error_code_map: dict[str, ErrorCode] = {}

class ErrorCode(StrEnum):
    """Standard error codes for the application.
    
    Each error code has a unique identifier and a human-readable description.
    """
    
    # =========================================================================
    # 0xx: Framework/System errors (0)
    # =========================================================================
    
    # 00x: Core framework errors
    UNKNOWN_ERROR = "E0000"
    """An unknown error occurred."""
    
    INTERNAL_ERROR = "E0001"
    """An internal error occurred."""
    
    NOT_IMPLEMENTED = "E0002"
    """The requested functionality is not implemented."""
    
    # 01x: Configuration errors
    CONFIGURATION_ERROR = "E0010"
    """A configuration error occurred."""
    
    MISSING_REQUIRED_PARAMETER = "E0011"
    """A required parameter is missing."""
    
    INVALID_CONFIGURATION = "E0012"
    """The configuration is invalid."""
    
    # 02x: Dependency Injection errors
    DEPENDENCY_ERROR = "E0020"
    """A dependency error occurred."""
    
    CIRCULAR_DEPENDENCY = "E0021"
    """A circular dependency was detected."""
    
    DEPENDENCY_NOT_FOUND = "E0022"
    """A required dependency was not found."""
    
    # =========================================================================
    # 1xx: Event system (1)
    # =========================================================================
    
    # 10x: Event handling
    EVENT_HANDLER_FAILED = "E1000"
    """An event handler failed to process an event."""
    
    EVENT_VALIDATION_ERROR = "E1001"
    """An event failed validation."""
    
    EVENT_PROCESSING_ERROR = "E1002"
    """An error occurred while processing an event."""
    
    # 11x: Event serialization
    EVENT_SERIALIZATION_ERROR = "E1100"
    """An error occurred while serializing an event."""
    
    EVENT_DESERIALIZATION_ERROR = "E1101"
    """An error occurred while deserializing an event."""
    
    EVENT_VERSION_MISMATCH = "E1102"
    """The event version is not supported."""
    
    # 12x: Event store
    EVENT_STORE_ERROR = "E1200"
    """An error occurred in the event store."""
    
    AGGREGATE_NOT_FOUND = "E1201"
    """The requested aggregate was not found."""
    
    CONCURRENCY_ERROR = "E1202"
    """A concurrency conflict occurred."""
    
    # =========================================================================
    # 2xx: Domain/Application (2)
    # =========================================================================
    
    # 20x: General domain errors
    DOMAIN_ERROR = "E2000"
    """A domain error occurred."""
    
    INVALID_STATE = "E2001"
    """The operation is not valid in the current state."""
    
    # 21x: Validation errors
    VALIDATION_ERROR = "E2100"
    """A validation error occurred."""
    
    INVALID_INPUT = "E2101"
    """The input is invalid."""
    
    REQUIRED_FIELD = "E2102"
    """A required field is missing."""
    
    INVALID_FORMAT = "E2103"
    """The format is invalid."""
    
    OUT_OF_RANGE = "E2104"
    """The value is out of range."""
    
    # 22x: Business rules
    BUSINESS_RULE_VIOLATION = "E2200"
    """A business rule was violated."""
    
    DUPLICATE_ENTITY = "E2201"
    """An entity with the same identifier already exists."""
    
    ENTITY_NOT_FOUND = "E2202"
    """The requested entity was not found."""
    
    # =========================================================================
    # 3xx: Infrastructure (3)
    # =========================================================================
    
    # 30x: Database errors
    DATABASE_ERROR = "E3000"
    """A database error occurred."""
    
    CONNECTION_ERROR = "E3001"
    """A database connection error occurred."""
    
    QUERY_ERROR = "E3002"
    """A database query error occurred."""
    
    TRANSACTION_ERROR = "E3003"
    """A database transaction error occurred."""
    
    # 31x: Cache errors
    CACHE_ERROR = "E3100"
    """A cache error occurred."""
    
    CACHE_MISS = "E3101"
    """The requested item was not found in the cache."""
    
    # 32x: File I/O errors
    IO_ERROR = "E3200"
    """An I/O error occurred."""
    
    FILE_NOT_FOUND = "E3201"
    """The requested file was not found."""
    
    # =========================================================================
    # 4xx: Authentication/Authorization (4)
    # =========================================================================
    
    # 40x: Authentication
    UNAUTHENTICATED = "E4000"
    """The request is not authenticated."""
    
    AUTHENTICATION_FAILED = "E4001"
    """Authentication failed."""
    
    INVALID_CREDENTIALS = "E4002"
    """The provided credentials are invalid."""
    
    ACCOUNT_LOCKED = "E4003"
    """The account is locked."""
    
    # 41x: Authorization
    UNAUTHORIZED = "E4100"
    """The request is not authorized."""
    
    PERMISSION_DENIED = "E4101"
    """The request is not permitted."""
    
    INSUFFICIENT_PERMISSIONS = "E4102"
    """The user has insufficient permissions."""
    
    # 42x: Tokens
    INVALID_TOKEN = "E4200"
    """The provided token is invalid."""
    
    TOKEN_EXPIRED = "E4201"
    """The provided token has expired."""
    
    TOKEN_REVOKED = "E4202"
    """The provided token has been revoked."""
    
    # =========================================================================
    # 5xx: External Services (5)
    # =========================================================================
    
    # 50x: General external service errors
    EXTERNAL_SERVICE_ERROR = "E5000"
    """An external service error occurred."""
    
    SERVICE_UNAVAILABLE = "E5001"
    """The external service is unavailable."""
    
    TIMEOUT = "E5002"
    """The request to the external service timed out."""
    
    # 51x: HTTP client errors
    HTTP_ERROR = "E5100"
    """An HTTP error occurred."""
    
    BAD_REQUEST = "E5101"
    """The request was invalid."""
    
    NOT_FOUND = "E5102"
    """The requested resource was not found."""
    
    RATE_LIMIT_EXCEEDED = "E5103"
    """The rate limit was exceeded."""
    
    # 52x: Message queue errors
    MESSAGE_QUEUE_ERROR = "E5200"
    """A message queue error occurred."""
    
    MESSAGE_PUBLISH_ERROR = "E5201"
    """Failed to publish a message."""
    
    MESSAGE_CONSUME_ERROR = "E5202"
    """Failed to consume a message."""
    
    # =========================================================================
    # 9xx: Deprecated/Reserved (9)
    # =========================================================================
    
    # 99x: Reserved for future use
    RESERVED = "E9999"
    """Reserved for future use."""
    
    # 100x: Event correlation
    EVENT_CORRELATION_ERROR = "E1003"
    """An error occurred while correlating events."""
    
    # =========================================================================
    # Class methods
    # =========================================================================
    
    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        # Clear the code map when subclassing to avoid duplicate entries
        global _error_code_map
        _error_code_map = {}
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Register this error code in the global code map
        global _error_code_map
        if self.value not in _error_code_map:
            _error_code_map[self.value] = self
    
    @classmethod
    def _missing_(cls, value):
        # Try to find a matching error code by value
        for member in cls:
            if member.value == value:
                return member
        return None
    
    @classmethod
    def from_value(cls, value: str) -> "ErrorCode":
        """Get an error code by its value.
        
        Args:
            value: The error code value (e.g., "E1000")
            
        Returns:
            The matching ErrorCode instance
            
        Raises:
            ValueError: If no matching error code is found
        """
        if code := _error_code_map.get(value):
            return code
        raise ValueError(f"No error code with value {value}")
    
    def get_description(self) -> str:
        """Get the description of this error code.
        
        Returns:
            The error code description, or the code value if no description is available
        """
        return self.__doc__ or self.value
    
    def get_category(self) -> str:
        """Get the category of this error code.
        
        Returns:
            The error category as a string
        """
        categories = {
            "0": "Framework/System",
            "1": "Event System",
            "2": "Domain/Application",
            "3": "Infrastructure",
            "4": "Authentication/Authorization",
            "5": "External Services",
            "9": "Deprecated/Reserved"
        }
        return categories.get(self.value[1], "Unknown")
    
    def is_in_category(self, category_prefix: str) -> bool:
        """Check if this error code is in the specified category.
        
        Args:
            category_prefix: The category prefix to check (e.g., "1" for Event System)
            
        Returns:
            True if the error code is in the specified category, False otherwise
        """
        return self.value.startswith(f"E{category_prefix}")


# Alias for backward compatibility
ErrorCodes = ErrorCode
