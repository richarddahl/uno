# SPDX-FileCopyrightText: 2024-present Richard Dahl <richard@dahl.us>
#
# SPDX-License-Identifier: MIT

"""SQL trigger builder."""

from pydantic import BaseModel, field_validator, ValidationError

class SQLTriggerBuilderConfig(BaseModel):
    schema: str
    table_name: str
    trigger_name: str
    function_name: str
    timing: str
    operation: str

    @field_validator("schema", "table_name", "trigger_name", "function_name", "timing", "operation")
    @classmethod
    def not_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Field must not be empty")
        return v

class SQLTriggerBuilder:
    """Builder for SQL triggers.
    
    This class provides a fluent interface for building SQL trigger
    statements with proper validation and formatting.
    
    Example:
        ```python
        trigger_sql = (
            SQLTriggerBuilder()
            .with_schema("public")
            .with_table("users")
            .with_name("users_update_trigger")
            .with_function("my_function")
            .with_timing("BEFORE")
            .with_operation("UPDATE")
            .build()
        )
        ```
    """
    def __init__(self):
        """Initialize the SQL trigger builder."""
        self.schema: str | None = None
        self.table_name: str | None = None
        self.trigger_name: str | None = None
        self.function_name: str | None = None
        self.timing: str = "BEFORE"
        self.operation: str = "UPDATE"
        self.for_each: str = "ROW"

    def with_schema(self, schema: str) -> "SQLTriggerBuilder":
        """Set the schema for the trigger.
        
        Args:
            schema: Schema name
            
        Returns:
            Self for method chaining
        """
        self.schema = schema
        return self
        
    def with_table(self, table_name: str) -> "SQLTriggerBuilder":
        """Set the table for the trigger.
        
        Args:
            table_name: Table name
            
        Returns:
            Self for method chaining
        """
        self.table_name = table_name
        return self
        
    def with_name(self, trigger_name: str) -> "SQLTriggerBuilder":
        """Set the name of the trigger.
        
        Args:
            trigger_name: Trigger name
            
        Returns:
            Self for method chaining
        """
        self.trigger_name = trigger_name
        return self
        
    def with_function(self, function_name: str) -> "SQLTriggerBuilder":
        """Set the function to be called by the trigger.
        
        Args:
            function_name: Function name
            
        Returns:
            Self for method chaining
        """
        self.function_name = function_name
        return self
        
    def with_timing(self, timing: str) -> "SQLTriggerBuilder":
        """Set the timing for the trigger.
        
        Args:
            timing: Timing ('BEFORE', 'AFTER', or 'INSTEAD OF')
            
        Returns:
            Self for method chaining
            
        Raises:
            ValueError: If timing is not valid
        """
        valid_timings = ["BEFORE", "AFTER", "INSTEAD OF"]
        if timing not in valid_timings:
            raise ValueError(f"Invalid timing: {timing}. Must be one of {valid_timings}")
        self.timing = timing
        return self
        
    def with_operation(self, operation: str) -> "SQLTriggerBuilder":
        """Set the operation(s) for the trigger.
        
        Args:
            operation: Operation ('INSERT', 'UPDATE', 'DELETE', 'TRUNCATE')
                      or composite operations like 'INSERT OR UPDATE'
            
        Returns:
            Self for method chaining
            
        Raises:
            ValueError: If operation is not valid
        """
        base_operations = {"INSERT", "UPDATE", "DELETE", "TRUNCATE"}
        operations = [op.strip() for op in operation.split("OR")]
        if not all(op in base_operations for op in operations):
            raise ValueError(f"Invalid operation(s): {operation}")
        self.operation = operation
        return self
        
    def with_for_each(self, for_each: str) -> "SQLTriggerBuilder":
        """Set the for_each clause for the trigger.
        
        Args:
            for_each: For each ('ROW' or 'STATEMENT')
            
        Returns:
            Self for method chaining
            
        Raises:
            ValueError: If for_each is not valid
        """
        valid_for_each = ["ROW", "STATEMENT"]
        if for_each not in valid_for_each:
            raise ValueError(f"Invalid for_each: {for_each}. Must be one of {valid_for_each}")
        self.for_each = for_each
        return self
    
    def build(self) -> str:
        """Build the SQL trigger statement, validating required fields.

        Returns:
            SQL trigger statement

        Raises:
            pydantic.ValidationError: If required parameters are missing or invalid
        """
        config = SQLTriggerBuilderConfig(
            schema=self.schema or "",
            table_name=self.table_name or "",
            trigger_name=self.trigger_name or "",
            function_name=self.function_name or "",
            timing=self.timing or "",
            operation=self.operation or ""
        )
        return f"""
            CREATE TRIGGER {config.trigger_name}
            {config.timing} {config.operation} ON {config.schema}.{config.table_name}
            FOR EACH {self.for_each}
            EXECUTE FUNCTION {config.function_name}();
        """
