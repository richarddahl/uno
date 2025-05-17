# SPDX-FileCopyrightText: 2024-present Richard Dahl <richard@dahl.us>
# SPDX-License-Identifier: MIT
# SPDX-Package-Name: uno framework
"""
Service extractor for documenting service classes in the Uno framework.

This extractor discovers and documents service classes, extracting method signatures,
dependencies, and behaviors that implement business logic.
"""

from __future__ import annotations

import asyncio
import inspect
import re
from typing import Any, get_origin, get_args, get_type_hints

from pydantic import BaseModel

from uno.docs.protocols import SchemaExtractorProtocol
from uno.docs.schema import DocumentationType, ExampleInfo, FieldInfo, SchemaInfo


class ServiceExtractor:
    """
    Extractor for service classes to generate schema documentation.

    This extractor identifies and documents service classes in the Uno framework,
    including their methods, dependencies, and lifecycle patterns.
    """

    # Patterns that indicate a class is a service
    SERVICE_PATTERNS = [
        r"Service$",  # Classes ending with "Service"
        r"Repository$",  # Classes ending with "Repository"
        r"Manager$",  # Classes ending with "Manager"
        r"Provider$",  # Classes ending with "Provider"
        r"Handler$",  # Classes ending with "Handler"
        r"Client$",  # Classes ending with "Client"
    ]

    # Method patterns that indicate lifecycle methods
    LIFECYCLE_METHODS = {
        "initialize": "Initialization",
        "start": "Service start",
        "stop": "Service stop",
        "shutdown": "Service shutdown",
        "connect": "Connection establishment",
        "disconnect": "Connection termination",
    }

    async def can_extract(self, item: Any) -> bool:
        """
        Determine if this extractor can handle a given item.

        Args:
            item: The item to check

        Returns:
            True if this item is a service class
        """
        # Must be a class
        if not inspect.isclass(item):
            return False

        # Check class name against service patterns
        for pattern in self.SERVICE_PATTERNS:
            if re.search(pattern, item.__name__):
                return True

        # Check for service-like methods
        # If class has multiple async methods, it might be a service
        async_method_count = 0
        for _, method in inspect.getmembers(item, predicate=inspect.isfunction):
            if inspect.iscoroutinefunction(method):
                async_method_count += 1

            # Check for lifecycle methods
            for lifecycle_name in self.LIFECYCLE_METHODS:
                if method.__name__ == lifecycle_name:
                    return True

        # If class has multiple async methods, consider it a service
        if async_method_count >= 2:
            return True

        # Not identified as a service
        return False

    async def extract_schema(self, item: Any) -> SchemaInfo:
        """
        Extract documentation schema from a service class.

        Args:
            item: The service class to extract schema from

        Returns:
            Documentation schema for the service
        """
        # Get basic class info
        name = item.__name__
        module = item.__module__
        description = inspect.getdoc(item) or f"{name} service"

        # Extract dependencies from constructor
        dependencies = await self._extract_dependencies(item)

        # Extract methods as fields
        methods = await self._extract_methods(item)

        # Extract lifecycle info
        lifecycle_info = await self._extract_lifecycle_info(item)

        # Create examples
        examples = await self._create_examples(item, dependencies, methods)

        # Create schema info
        schema = SchemaInfo(
            name=name,
            module=module,
            description=description,
            type=DocumentationType.SERVICE,
            fields=methods,
            extra_info={
                "dependencies": dependencies,
                "lifecycle": lifecycle_info,
            },
            examples=examples,
        )

        return schema

    async def _extract_dependencies(self, cls: type) -> list[dict[str, Any]]:
        """Extract dependencies from the constructor of a service class."""
        dependencies = []

        # Get constructor
        init = getattr(cls, "__init__", None)
        if not init or init is object.__init__:
            return dependencies

        # Get signature of constructor
        try:
            sig = inspect.signature(init)
        except (ValueError, TypeError):
            return dependencies

        # Get type hints
        type_hints = get_type_hints(init)

        # Process each parameter
        for name, param in sig.parameters.items():
            # Skip self
            if name == "self":
                continue

            # Get type from annotation
            if name in type_hints:
                type_name = self._format_type_hint(type_hints[name])
            else:
                type_name = (
                    str(param.annotation)
                    if param.annotation != inspect.Parameter.empty
                    else "Any"
                )

            # Determine if optional (has default)
            optional = param.default != inspect.Parameter.empty

            # Get default value
            default_value = (
                None if param.default == inspect.Parameter.empty else str(param.default)
            )

            # Add dependency
            dependencies.append(
                {
                    "name": name,
                    "type": type_name,
                    "optional": optional,
                    "default": default_value,
                }
            )

        return dependencies

    async def _extract_methods(self, cls: type) -> list[FieldInfo]:
        """Extract methods as fields from a service class."""
        methods = []

        # Get all methods
        for name, method in inspect.getmembers(cls, predicate=inspect.isfunction):
            # Skip private methods
            if name.startswith("_") and name != "__init__":
                continue

            # Skip __init__ as it's handled separately
            if name == "__init__":
                continue

            # Get method signature
            try:
                sig = inspect.signature(method)
            except (ValueError, TypeError):
                continue

            # Get docstring
            doc = inspect.getdoc(method) or f"{name} method"

            # Get return type
            return_type = "None"
            type_hints = get_type_hints(method)
            if "return" in type_hints:
                return_type = self._format_type_hint(type_hints["return"])

            # Is method async?
            is_async = inspect.iscoroutinefunction(method)

            # Create method parameters string
            params_list = []
            for param_name, param in sig.parameters.items():
                if param_name == "self":
                    continue

                # Get type from annotation
                param_type = "Any"
                if param_name in type_hints:
                    param_type = self._format_type_hint(type_hints[param_name])
                elif param.annotation != inspect.Parameter.empty:
                    param_type = str(param.annotation)

                # Check if parameter has default
                if param.default != inspect.Parameter.empty:
                    default_val = repr(param.default)
                    params_list.append(f"{param_name}: {param_type} = {default_val}")
                else:
                    params_list.append(f"{param_name}: {param_type}")

            params_str = ", ".join(params_list)

            # Format method signature
            if is_async:
                method_type = f"async def {name}(self, {params_str}) -> {return_type}"
            else:
                method_type = f"def {name}(self, {params_str}) -> {return_type}"

            # Check if this is a lifecycle method
            is_lifecycle = name in self.LIFECYCLE_METHODS

            # Create field info for method
            method_field = FieldInfo(
                name=name,
                type_name=method_type,
                type_hint=return_type,
                description=doc,
                extra_info={
                    "is_async": is_async,
                    "is_lifecycle": is_lifecycle,
                    "parameters": params_list,
                    "return_type": return_type,
                },
            )

            methods.append(method_field)

        return methods

    async def _extract_lifecycle_info(self, cls: type) -> dict[str, str]:
        """Extract lifecycle information from the service class."""
        lifecycle = {}

        # Check for common lifecycle methods
        for method_name, description in self.LIFECYCLE_METHODS.items():
            if hasattr(cls, method_name) and callable(getattr(cls, method_name)):
                lifecycle[method_name] = description

        return lifecycle

    async def _create_examples(
        self, cls: type, dependencies: list[dict[str, Any]], methods: list[FieldInfo]
    ) -> list[ExampleInfo]:
        """Create usage examples for the service class."""
        examples = []

        # Basic instantiation example
        instantiation_example = await self._create_instantiation_example(
            cls, dependencies
        )
        if instantiation_example:
            examples.append(instantiation_example)

        # Usage example showing some methods
        usage_example = await self._create_usage_example(cls, methods)
        if usage_example:
            examples.append(usage_example)

        # Lifecycle example if applicable
        lifecycle_example = await self._create_lifecycle_example(cls, methods)
        if lifecycle_example:
            examples.append(lifecycle_example)

        return examples

    async def _create_instantiation_example(
        self, cls: type, dependencies: list[dict[str, Any]]
    ) -> ExampleInfo | None:
        """Create an example of instantiating the service."""
        class_name = cls.__name__
        module_name = cls.__module__

        # Generate dependency instantiation code
        dep_init_lines = []
        dep_params = []

        for dep in dependencies:
            dep_name = dep["name"]
            dep_type = dep["type"]

            # Skip deps with default values for simplicity
            if dep["optional"]:
                continue

            # Create a simple instantiation for the dependency
            # This is simplified and might need adjustment for real dependencies
            if "str" in dep_type.lower():
                dep_init_lines.append(f'{dep_name} = "example_{dep_name}"')
            elif "int" in dep_type.lower():
                dep_init_lines.append(f"{dep_name} = 42")
            elif "bool" in dep_type.lower():
                dep_init_lines.append(f"{dep_name} = True")
            elif "list" in dep_type.lower():
                dep_init_lines.append(f"{dep_name} = []")
            elif "dict" in dep_type.lower():
                dep_init_lines.append(f"{dep_name} = {{}}")
            else:
                # For complex types, create a mock or use dependency injection
                dep_init_lines.append(f"# Create or inject {dep_name}: {dep_type}")
                dep_init_lines.append(f"{dep_name} = get_{dep_name}()")

            dep_params.append(f"{dep_name}={dep_name}")

        # Create instantiation line
        if dep_params:
            instantiation = f"{class_name}({', '.join(dep_params)})"
        else:
            instantiation = f"{class_name}()"

        # Build example code
        code_lines = [
            f"from {module_name} import {class_name}",
            "",
            "# Prepare dependencies",
        ]

        # Add dependency initialization lines
        if dep_init_lines:
            code_lines.extend(dep_init_lines)
        else:
            code_lines.append("# No dependencies required")

        code_lines.extend(
            [
                "",
                "# Create service instance",
                f"service = {instantiation}",
            ]
        )

        return ExampleInfo(
            title="Service Instantiation",
            code="\n".join(code_lines),
            language="python",
            description=f"Example of creating a {class_name} instance",
        )

    async def _create_usage_example(
        self, cls: type, methods: list[FieldInfo]
    ) -> ExampleInfo | None:
        """Create an example of using the service methods."""
        class_name = cls.__name__
        module_name = cls.__module__

        # Find non-lifecycle methods that might be good examples
        example_methods = []
        for method in methods:
            # Skip lifecycle methods
            if method.extra_info.get("is_lifecycle", False):
                continue

            # Prefer methods with descriptive names that aren't getters/setters
            if not (method.name.startswith("get_") or method.name.startswith("set_")):
                example_methods.append(method)

            # If we have 2 good examples, stop looking
            if len(example_methods) >= 2:
                break

        # If we didn't find good examples, take what we can get
        if not example_methods and methods:
            example_methods = methods[: min(2, len(methods))]

        # If no methods at all, can't create an example
        if not example_methods:
            return None

        # Build example code
        code_lines = [
            f"from {module_name} import {class_name}",
            "",
            "# Create service instance (see instantiation example)",
            f"service = {class_name}()",
            "",
            "# Examples of using service methods",
        ]

        # Add example method calls
        for method in example_methods:
            method_name = method.name
            is_async = method.extra_info.get("is_async", False)

            # Generate parameter values
            params = []
            for param in method.extra_info.get("parameters", []):
                # Extract param name and type
                param_parts = param.split(":")
                param_name = param_parts[0].strip()

                # Generate sample value based on param name
                if "id" in param_name:
                    params.append(f"{param_name}=123")
                elif "name" in param_name:
                    params.append(f'{param_name}="example"')
                elif "date" in param_name or "time" in param_name:
                    params.append(f'{param_name}="2024-06-01"')
                elif "enabled" in param_name or "active" in param_name:
                    params.append(f"{param_name}=True")
                elif "config" in param_name or "settings" in param_name:
                    params.append(f"{param_name}={{}}")
                elif "items" in param_name or "list" in param_name:
                    params.append(f"{param_name}=[]")
                else:
                    params.append(f"{param_name}=...")

            # Create method call
            params_str = ", ".join(params)
            if is_async:
                code_lines.append(f"# Call async method")
                code_lines.append(f"result = await service.{method_name}({params_str})")
            else:
                code_lines.append(f"# Call method")
                code_lines.append(f"result = service.{method_name}({params_str})")

            code_lines.append(f'print(f"Result: {result}")')
            code_lines.append("")

        return ExampleInfo(
            title="Service Usage",
            code="\n".join(code_lines),
            language="python",
            description=f"Example of using {class_name} methods",
        )

    async def _create_lifecycle_example(
        self, cls: type, methods: list[FieldInfo]
    ) -> ExampleInfo | None:
        """Create an example of service lifecycle management."""
        class_name = cls.__name__
        module_name = cls.__module__

        # Find lifecycle methods
        has_init = False
        has_start = False
        has_stop = False

        for method in methods:
            if method.name == "initialize":
                has_init = True
            elif method.name == "start":
                has_start = True
            elif method.name in ["stop", "shutdown"]:
                has_stop = True

        # If no lifecycle methods, skip this example
        if not (has_init or has_start or has_stop):
            return None

        # Build example code
        code_lines = [
            f"import asyncio",
            f"from {module_name} import {class_name}",
            "",
            "async def main():",
            f"    # Create service instance",
            f"    service = {class_name}()",
            "",
        ]

        # Add lifecycle method calls
        if has_init:
            code_lines.append("    # Initialize the service")
            code_lines.append("    await service.initialize()")

        if has_start:
            code_lines.append("    # Start the service")
            code_lines.append("    await service.start()")
            code_lines.append("")
            code_lines.append("    # Service is now running")
            code_lines.append('    print("Service is running...")')
            code_lines.append("    await asyncio.sleep(10)  # Run for a while")

        if has_stop:
            code_lines.append("    # Stop the service")
            code_lines.append("    await service.stop()")

        code_lines.extend(
            [
                "",
                'if __name__ == "__main__":',
                "    asyncio.run(main())",
            ]
        )

        return ExampleInfo(
            title="Service Lifecycle",
            code="\n".join(code_lines),
            language="python",
            description=f"Example of managing {class_name} lifecycle",
        )

    def _format_type_hint(self, type_hint: Any) -> str:
        """Format a type hint in a readable way."""
        # Get origin and args for generics like list[str]
        origin = get_origin(type_hint)
        args = get_args(type_hint)

        # None type
        if type_hint is type(None):
            return "None"

        # Union types (X | Y)
        if (
            origin is not None
            and origin.__name__ in ("Union", "_Union")
            or origin is tuple
            and Ellipsis in args
        ):
            if type(None) in args or None in args:
                # Optional type (X | None)
                non_none_args = [
                    arg for arg in args if arg is not type(None) and arg is not None
                ]
                if len(non_none_args) == 1:
                    return f"{self._format_type_hint(non_none_args[0])} | None"
                else:
                    formatted_args = [
                        self._format_type_hint(arg) for arg in non_none_args
                    ]
                    return " | ".join(formatted_args) + " | None"
            else:
                # Regular union
                formatted_args = [self._format_type_hint(arg) for arg in args]
                return " | ".join(formatted_args)

        # Generic types
        if origin is not None:
            if origin is list:
                return f"list[{self._format_type_hint(args[0])}]"
            elif origin is dict:
                return f"dict[{self._format_type_hint(args[0])}, {self._format_type_hint(args[1])}]"
            elif origin is set:
                return f"set[{self._format_type_hint(args[0])}]"
            elif origin is tuple:
                if Ellipsis in args:
                    # Tuple of indefinite length
                    return f"tuple[{self._format_type_hint(args[0])}, ...]"
                else:
                    # Fixed length tuple
                    formatted_args = [self._format_type_hint(arg) for arg in args]
                    return f"tuple[{', '.join(formatted_args)}]"
            else:
                # Other generic types
                if args:
                    formatted_args = [self._format_type_hint(arg) for arg in args]
                    return f"{origin.__name__}[{', '.join(formatted_args)}]"
                return origin.__name__

        # Simple types with __name__
        if hasattr(type_hint, "__name__"):
            return type_hint.__name__

        # Fallback for other types
        return str(type_hint).replace("typing.", "")
