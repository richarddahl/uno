# SPDX-FileCopyrightText: 2024-present Richard Dahl <richard@dahl.us>
# SPDX-License-Identifier: MIT
# SPDX-Package-Name: uno framework
"""
CLI Command extractor for documenting command-line interface commands.

This extractor discovers and documents CLI commands, extracting command structures,
arguments, options, and usage patterns.
"""

from __future__ import annotations

import inspect
import sys
import re
from typing import Any, cast, get_type_hints

from uno.docs.protocols import SchemaExtractorProtocol
from uno.docs.schema import DocumentationType, ExampleInfo, FieldInfo, SchemaInfo


class CliCommandExtractor:
    """
    Extractor for CLI command classes to generate schema documentation.

    This extractor identifies and documents command-line interfaces, including
    commands, subcommands, arguments, options, and usage examples.
    """

    # Command handler patterns
    COMMAND_PATTERNS = [
        r"Command$",
        r"Cli$",
        r"App$",
    ]

    # Supported CLI frameworks - for detection
    CLI_FRAMEWORKS = {
        "click": ["click.Command", "click.Group", "click.MultiCommand"],
        "typer": ["typer.Typer", "typer.core.Typer"],
        "argparse": ["argparse.ArgumentParser"],
    }

    async def can_extract(self, item: Any) -> bool:
        """
        Determine if this extractor can handle a given item.

        Args:
            item: The item to check

        Returns:
            True if this item is a CLI command class or function
        """
        # Check for CLI framework objects
        if self._is_cli_framework_object(item):
            return True

        # Check if it's a function decorated with CLI framework decorators
        if inspect.isfunction(item):
            # Check for common CLI decorators in function attributes
            for attr_name in dir(item):
                if attr_name.startswith("_"):
                    continue

                # Look for typer/click attributes
                if any(
                    kw in attr_name.lower()
                    for kw in ["command", "cli", "typer", "click", "app"]
                ):
                    return True

            # Check if docstring has CLI usage information
            doc = inspect.getdoc(item)
            if doc and ("usage:" in doc.lower() or "options:" in doc.lower()):
                return True

        # Check for class with CLI-related naming patterns
        if inspect.isclass(item):
            for pattern in self.COMMAND_PATTERNS:
                if re.search(pattern, item.__name__):
                    return True

        return False

    def _is_cli_framework_object(self, item: Any) -> bool:
        """Check if an item is a CLI framework object (click, typer, etc.)."""
        if not item:
            return False

        item_type = type(item)
        item_module = getattr(item_type, "__module__", "")
        item_class = f"{item_module}.{item_type.__name__}"

        # Check against known CLI framework types
        for framework, classes in self.CLI_FRAMEWORKS.items():
            for cls_name in classes:
                if cls_name in item_class or hasattr(item, framework):
                    return True

        # Also check class name for CLI framework names
        for framework in self.CLI_FRAMEWORKS:
            if framework in item_class.lower():
                return True

        return False

    async def extract_schema(self, item: Any) -> SchemaInfo:
        """
        Extract documentation schema from a CLI command.

        Args:
            item: The CLI command to extract schema from

        Returns:
            Documentation schema for the CLI command
        """
        # Determine what type of CLI command we're dealing with
        cli_type = self._detect_cli_type(item)

        # Extract based on the type
        if cli_type == "click":
            return await self._extract_click_command(item)
        elif cli_type == "typer":
            return await self._extract_typer_command(item)
        elif cli_type == "argparse":
            return await self._extract_argparse_command(item)
        else:
            # Generic CLI command
            return await self._extract_generic_command(item)

    def _detect_cli_type(self, item: Any) -> str:
        """Detect what CLI framework the command uses."""
        # Check by module
        item_module = getattr(item, "__module__", "")

        if "click" in item_module or hasattr(item, "click") or hasattr(item, "command"):
            return "click"
        elif "typer" in item_module or hasattr(item, "typer"):
            return "typer"
        elif "argparse" in item_module or hasattr(item, "add_argument"):
            return "argparse"

        # Check by class
        item_type = type(item)
        type_name = getattr(item_type, "__name__", "")

        if "click" in type_name.lower():
            return "click"
        elif "typer" in type_name.lower():
            return "typer"
        elif "argparse" in type_name.lower():
            return "argparse"

        # Default
        return "generic"

    async def _extract_click_command(self, item: Any) -> SchemaInfo:
        """Extract schema from a Click command."""
        # Get basic info
        name = getattr(item, "name", getattr(item, "__name__", type(item).__name__))
        module = getattr(item, "__module__", "")

        # Get command help text
        description = item.help or getattr(item, "__doc__", "") or f"{name} command"

        # Get command parameters
        parameters = []
        options = []
        arguments = []

        # Handle Click commands
        if hasattr(item, "params"):
            for param in item.params:
                param_name = param.name
                param_type = getattr(param, "type", Any)
                param_help = getattr(param, "help", "")
                param_required = getattr(param, "required", False)
                param_default = getattr(param, "default", None)

                # Determine if it's an option or argument
                is_option = bool(getattr(param, "opts", None))

                field_info = FieldInfo(
                    name=param_name,
                    type_name=str(param_type),
                    type_hint=str(param_type),
                    default_value=(
                        str(param_default) if param_default is not None else None
                    ),
                    description=param_help,
                    is_required=param_required,
                    extra_info={
                        "is_option": is_option,
                        "opts": getattr(param, "opts", []),
                    },
                )

                parameters.append(field_info)
                if is_option:
                    options.append(field_info)
                else:
                    arguments.append(field_info)

        # Check for subcommands (if it's a group)
        subcommands = []
        if hasattr(item, "commands") and item.commands:
            for cmd_name, cmd in item.commands.items():
                subcommands.append(
                    {
                        "name": cmd_name,
                        "help": getattr(cmd, "help", ""),
                    }
                )

        # Create examples
        examples = await self._create_click_examples(
            item, name, parameters, subcommands
        )

        # Create schema
        schema = SchemaInfo(
            name=name,
            module=module,
            description=description,
            type=DocumentationType.CLI,
            fields=parameters,
            extra_info={
                "cli_type": "click",
                "options": options,
                "arguments": arguments,
                "subcommands": subcommands,
            },
            examples=examples,
        )

        return schema

    async def _extract_typer_command(self, item: Any) -> SchemaInfo:
        """Extract schema from a Typer command."""
        # Get basic info
        name = getattr(item, "name", getattr(item, "__name__", type(item).__name__))
        module = getattr(item, "__module__", "")

        # Get command help text
        description = (
            getattr(item, "info", {}).get("help")
            or getattr(item, "__doc__", "")
            or f"{name} command"
        )

        # Try to get commands if this is a Typer app
        commands = []
        command_parameters = []

        # Extract from typer internal structures
        try:
            if hasattr(item, "registered_commands"):
                for cmd in item.registered_commands:
                    cmd_name = cmd.name
                    cmd_help = cmd.help
                    cmd_params = []

                    for param in cmd.parameters:
                        param_info = FieldInfo(
                            name=param.name,
                            type_name=str(param.type),
                            type_hint=str(param.type),
                            default_value=(
                                str(param.default)
                                if param.default is not param.empty
                                else None
                            ),
                            description=param.help,
                            is_required=param.default is param.empty,
                            extra_info={
                                "is_option": param.param_type == "option",
                            },
                        )
                        cmd_params.append(param_info)

                    commands.append(
                        {
                            "name": cmd_name,
                            "help": cmd_help,
                            "parameters": cmd_params,
                        }
                    )
                    command_parameters.extend(cmd_params)
        except (AttributeError, TypeError):
            # Fallback for simpler extraction
            pass

        # Create examples
        examples = await self._create_typer_examples(item, name, commands)

        # Create schema
        schema = SchemaInfo(
            name=name,
            module=module,
            description=description,
            type=DocumentationType.CLI,
            fields=command_parameters,
            extra_info={
                "cli_type": "typer",
                "commands": commands,
            },
            examples=examples,
        )

        return schema

    async def _extract_argparse_command(self, item: Any) -> SchemaInfo:
        """Extract schema from an argparse command."""
        # Get basic info
        name = getattr(item, "prog", getattr(item, "__name__", type(item).__name__))
        module = getattr(item, "__module__", "")

        # Get description
        description = (
            getattr(item, "description", getattr(item, "__doc__", ""))
            or f"{name} command"
        )

        # Get arguments
        arguments = []

        if hasattr(item, "_actions"):
            for action in item._actions:
                # Skip help action
                if action.dest == "help":
                    continue

                arg_name = action.dest
                arg_help = action.help or ""
                arg_required = action.required
                arg_default = action.default

                # Get type information
                arg_type = getattr(action, "type", None)
                type_name = str(arg_type.__name__) if callable(arg_type) else "str"

                # Get options (flags)
                options = getattr(action, "option_strings", [])

                field_info = FieldInfo(
                    name=arg_name,
                    type_name=type_name,
                    type_hint=type_name,
                    default_value=str(arg_default) if arg_default is not None else None,
                    description=arg_help,
                    is_required=arg_required,
                    extra_info={
                        "is_option": bool(options),
                        "options": options,
                        "nargs": getattr(action, "nargs", None),
                        "choices": getattr(action, "choices", None),
                    },
                )

                arguments.append(field_info)

        # Check for subparsers
        subcommands = []
        if hasattr(item, "_subparsers"):
            for action in item._actions:
                if hasattr(action, "choices"):
                    for name, subparser in action.choices.items():
                        subcommands.append(
                            {
                                "name": name,
                                "help": getattr(subparser, "description", ""),
                            }
                        )

        # Create examples
        examples = await self._create_argparse_examples(
            item, name, arguments, subcommands
        )

        # Create schema
        schema = SchemaInfo(
            name=name,
            module=module,
            description=description,
            type=DocumentationType.CLI,
            fields=arguments,
            extra_info={
                "cli_type": "argparse",
                "subcommands": subcommands,
                "epilog": getattr(item, "epilog", ""),
            },
            examples=examples,
        )

        return schema

    async def _extract_generic_command(self, item: Any) -> SchemaInfo:
        """Extract schema from a generic CLI command."""
        # Get basic info
        if inspect.isfunction(item) or inspect.ismethod(item):
            name = item.__name__
            module = item.__module__
            description = inspect.getdoc(item) or f"{name} command"

            # Extract parameters from function signature
            sig = inspect.signature(item)
            parameters = []

            for param_name, param in sig.parameters.items():
                # Skip self/cls
                if param_name in ("self", "cls"):
                    continue

                # Get type information
                type_hints = get_type_hints(item)
                type_hint = type_hints.get(param_name, Any)
                type_name = str(type_hint).replace("typing.", "")

                # Determine if parameter is required
                is_required = param.default is inspect.Parameter.empty
                default_value = None if is_required else str(param.default)

                # Create field info
                field_info = FieldInfo(
                    name=param_name,
                    type_name=type_name,
                    type_hint=type_name,
                    default_value=default_value,
                    description=f"{param_name} parameter",
                    is_required=is_required,
                )

                parameters.append(field_info)

            # Create examples
            examples = await self._create_generic_examples(item, name, parameters)

            # Create schema
            schema = SchemaInfo(
                name=name,
                module=module,
                description=description,
                type=DocumentationType.CLI,
                fields=parameters,
                extra_info={
                    "cli_type": "generic",
                    "is_function": True,
                },
                examples=examples,
            )

        else:
            # It's a class
            name = item.__name__
            module = item.__module__
            description = inspect.getdoc(item) or f"{name} command"

            # Try to find CLI-related methods
            methods = []
            for method_name, method in inspect.getmembers(
                item, predicate=inspect.isfunction
            ):
                if method_name.startswith("_"):
                    continue

                if any(
                    kw in method_name.lower()
                    for kw in ["command", "run", "execute", "main", "cli"]
                ):
                    methods.append(
                        {
                            "name": method_name,
                            "doc": inspect.getdoc(method) or f"{method_name} method",
                        }
                    )

            # Create examples
            examples = await self._create_class_examples(item, name, methods)

            # Create schema
            schema = SchemaInfo(
                name=name,
                module=module,
                description=description,
                type=DocumentationType.CLI,
                fields=[],  # No direct fields for class
                extra_info={
                    "cli_type": "generic",
                    "is_class": True,
                    "methods": methods,
                },
                examples=examples,
            )

        return schema

    async def _create_click_examples(
        self,
        command: Any,
        name: str,
        parameters: list[FieldInfo],
        subcommands: list[dict],
    ) -> list[ExampleInfo]:
        """Create examples for a Click command."""
        examples = []

        # Basic usage example
        cmd_name = getattr(command, "name", name)
        usage_parts = [cmd_name]

        # Add required arguments
        required_args = []
        optional_args = []

        for param in parameters:
            if param.extra_info.get("is_option", False):
                # It's an option
                opts = param.extra_info.get("opts", [])
                if opts:
                    opt = opts[0]  # Use first option
                    if param.is_required:
                        required_args.append(f"{opt} VALUE")
                    else:
                        optional_args.append(f"{opt} VALUE")
            else:
                # It's an argument
                if param.is_required:
                    required_args.append(param.name.upper())
                else:
                    optional_args.append(f"[{param.name.upper()}]")

        # Create usage string
        usage_str = f"{cmd_name} {' '.join(required_args)} {' '.join(optional_args)}"

        # Create example
        basic_example = ExampleInfo(
            title="Basic Usage",
            code=f"# Command usage\n{usage_str.strip()}\n",
            language="bash",
            description=f"Basic usage of the {cmd_name} command",
        )
        examples.append(basic_example)

        # If there are subcommands, show an example
        if subcommands:
            subcommand_example_parts = [f"# Subcommands of {cmd_name}"]

            for subcmd in subcommands[:5]:  # Limit to 5 examples
                subcmd_name = subcmd["name"]
                subcmd_help = subcmd.get("help", "")

                subcommand_example_parts.append(
                    f"{cmd_name} {subcmd_name}  # {subcmd_help}"
                )

            subcommand_example = ExampleInfo(
                title="Subcommands",
                code="\n".join(subcommand_example_parts),
                language="bash",
                description=f"Available subcommands for {cmd_name}",
            )
            examples.append(subcommand_example)

        # Help example
        help_example = ExampleInfo(
            title="Show Help",
            code=f"{cmd_name} --help",
            language="bash",
            description=f"Display help information for {cmd_name}",
        )
        examples.append(help_example)

        return examples

    async def _create_typer_examples(
        self,
        app: Any,
        name: str,
        commands: list[dict],
    ) -> list[ExampleInfo]:
        """Create examples for a Typer app."""
        examples = []

        # Get the app name
        app_name = getattr(app, "info", {}).get("name") or name

        # If we have commands, create examples for them
        if commands:
            command_examples = [f"# Available commands for {app_name}"]

            for cmd in commands[:5]:  # Limit to 5 examples
                cmd_name = cmd["name"]
                cmd_help = cmd.get("help", "")

                # Create command usage example
                usage = f"{app_name} {cmd_name}"

                # Add parameters if available
                params = cmd.get("parameters", [])
                for param in params:
                    if param.is_required:
                        if param.extra_info.get("is_option", False):
                            usage += f" --{param.name} VALUE"
                        else:
                            usage += f" {param.name.upper()}"

                command_examples.append(f"{usage}  # {cmd_help}")

            command_example = ExampleInfo(
                title="Commands",
                code="\n".join(command_examples),
                language="bash",
                description=f"Available commands for {app_name}",
            )
            examples.append(command_example)
        else:
            # No commands found, create a basic example
            basic_example = ExampleInfo(
                title="Basic Usage",
                code=f"# Run the application\n{app_name} [OPTIONS] [ARGUMENTS]",
                language="bash",
                description=f"Basic usage of {app_name}",
            )
            examples.append(basic_example)

        # Help example
        help_example = ExampleInfo(
            title="Show Help",
            code=f"{app_name} --help",
            language="bash",
            description=f"Display help information for {app_name}",
        )
        examples.append(help_example)

        return examples

    async def _create_argparse_examples(
        self,
        parser: Any,
        name: str,
        arguments: list[FieldInfo],
        subcommands: list[dict],
    ) -> list[ExampleInfo]:
        """Create examples for an argparse command."""
        examples = []

        # Get the program name
        prog = getattr(parser, "prog", name)

        # Basic usage example
        usage_parts = [prog]

        # Add required arguments
        for arg in arguments:
            if arg.is_required:
                if arg.extra_info.get("is_option", False):
                    # Use first option string
                    options = arg.extra_info.get("options", [])
                    if options:
                        usage_parts.append(f"{options[0]} VALUE")
                else:
                    usage_parts.append(arg.name.upper())

        # Create usage string
        usage_str = " ".join(usage_parts)

        # Create example
        basic_example = ExampleInfo(
            title="Basic Usage",
            code=f"# Command usage\n{usage_str}\n",
            language="bash",
            description=f"Basic usage of the {prog} command",
        )
        examples.append(basic_example)

        # If there are subcommands, show an example
        if subcommands:
            subcommand_example_parts = [f"# Subcommands of {prog}"]

            for subcmd in subcommands[:5]:  # Limit to 5 examples
                subcmd_name = subcmd["name"]
                subcmd_help = subcmd.get("help", "")

                subcommand_example_parts.append(
                    f"{prog} {subcmd_name}  # {subcmd_help}"
                )

            subcommand_example = ExampleInfo(
                title="Subcommands",
                code="\n".join(subcommand_example_parts),
                language="bash",
                description=f"Available subcommands for {prog}",
            )
            examples.append(subcommand_example)

        # Help example
        help_example = ExampleInfo(
            title="Show Help",
            code=f"{prog} --help",
            language="bash",
            description=f"Display help information for {prog}",
        )
        examples.append(help_example)

        return examples

    async def _create_generic_examples(
        self,
        function: Any,
        name: str,
        parameters: list[FieldInfo],
    ) -> list[ExampleInfo]:
        """Create examples for a generic CLI function."""
        examples = []

        # Create a Python example for calling the function
        call_parts = [f"from {function.__module__} import {name}", ""]

        # Add parameters for the call
        param_parts = []
        for param in parameters:
            param_name = param.name

            # Generate a sample value based on type
            if "int" in param.type_name:
                param_parts.append(f"{param_name}=42")
            elif "float" in param.type_name:
                param_parts.append(f"{param_name}=3.14")
            elif "bool" in param.type_name:
                param_parts.append(f"{param_name}=True")
            elif "list" in param.type_name or "List" in param.type_name:
                param_parts.append(f"{param_name}=[]")
            elif "dict" in param.type_name or "Dict" in param.type_name:
                param_parts.append(f"{param_name}={{}}")
            else:
                param_parts.append(f'{param_name}="value"')

        # Create function call
        param_str = ", ".join(param_parts)
        call_parts.append(f"result = {name}({param_str})")
        call_parts.append('print(f"Result: {result}")')

        # Create example
        python_example = ExampleInfo(
            title="Python Function Call",
            code="\n".join(call_parts),
            language="python",
            description=f"Example of calling the {name} function",
        )
        examples.append(python_example)

        # Create a CLI usage example if applicable
        cli_parts = [f"# Command-line usage for {name}"]
        cli_parts.append(f"{name}")

        for param in parameters:
            param_name = param.name

            # Skip parameters with default values for simplicity
            if not param.is_required:
                continue

            # Format as option (--param value)
            cli_parts.append(f"--{param_name} VALUE")

        # Create example
        cli_example = ExampleInfo(
            title="Command-line Usage",
            code="\n".join(cli_parts),
            language="bash",
            description=f"Command-line usage for {name}",
        )
        examples.append(cli_example)

        return examples

    async def _create_class_examples(
        self,
        cls: type,
        name: str,
        methods: list[dict],
    ) -> list[ExampleInfo]:
        """Create examples for a CLI class."""
        examples = []

        # Create a Python example for using the class
        usage_parts = [f"from {cls.__module__} import {name}", ""]

        # Create an instance
        usage_parts.append(f"# Create an instance")
        usage_parts.append(f"cli = {name}()")
        usage_parts.append("")

        # Show method usage if available
        if methods:
            usage_parts.append("# Execute CLI commands")

            for method in methods[:3]:  # Limit to 3 examples
                method_name = method["name"]
                usage_parts.append(f"cli.{method_name}()")

        # Create example
        python_example = ExampleInfo(
            title="Python Class Usage",
            code="\n".join(usage_parts),
            language="python",
            description=f"Example of using the {name} class",
        )
        examples.append(python_example)

        # Create a CLI usage example
        cli_parts = [f"# Command-line usage for {name}"]

        # Basic command
        cli_parts.append(f"{name.lower()}")

        # Add examples for methods
        if methods:
            cli_parts.append("")
            cli_parts.append("# Available commands:")

            for method in methods[:5]:  # Limit to 5 examples
                method_name = method["name"]
                cli_parts.append(f"{name.lower()} {method_name}")

        # Create example
        cli_example = ExampleInfo(
            title="Command-line Usage",
            code="\n".join(cli_parts),
            language="bash",
            description=f"Command-line usage for {name}",
        )
        examples.append(cli_example)

        return examples
