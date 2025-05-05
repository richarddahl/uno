from enum import Enum, auto


class EventPriority(Enum):
    """
    Priority levels for event handling.

    This enum defines the priority levels for event handlers. Higher priority
    handlers will be executed before lower priority handlers.
    """

    HIGH = auto()  # Execute first
    NORMAL = auto()  # Execute in middle (default)
    LOW = auto()  # Execute last
