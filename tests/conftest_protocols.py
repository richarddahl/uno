from typing import Any, TypeVar

T = TypeVar("T")


def validate_protocol_implementation(
    protocol: type[T], implementation: Any
) -> dict[str, bool]:
    """Validate if a class implements all methods of a protocol."""
    results = {}
    for attr_name in dir(protocol):
        if attr_name.startswith("_"):
            continue
        protocol_attr = getattr(protocol, attr_name)
        if callable(protocol_attr):
            has_method = hasattr(implementation, attr_name)
            impl_attr = getattr(implementation, attr_name, None)
            is_callable = callable(impl_attr) if impl_attr is not None else False
            results[attr_name] = has_method and is_callable
    return results


def assert_implements_protocol(protocol: type[T], implementation: Any) -> None:
    """Assert that a class implements all methods of a protocol."""
    validation = validate_protocol_implementation(protocol, implementation)
    missing = [name for name, valid in validation.items() if not valid]
    if missing:
        raise AssertionError(
            f"{type(implementation).__name__} does not fully implement {protocol.__name__}. "
            f"Missing or incompatible methods: {', '.join(missing)}"
        )
