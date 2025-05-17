# SPDX-FileCopyrightText: 2024-present Richard Dahl <richard@dahl.us>
# SPDX-License-Identifier: MIT
# SPDX-Package-Name: uno framework
"""
API Endpoint extractor for documenting FastAPI and other web framework endpoints.

This extractor discovers and documents API endpoints from FastAPI applications
and routers, extracting route paths, HTTP methods, parameters, and responses.
"""

from __future__ import annotations

import inspect
from typing import Any, cast

from fastapi import FastAPI, APIRouter
from fastapi.routing import APIRoute
from pydantic import BaseModel, create_model

from uno.docs.protocols import SchemaExtractorProtocol
from uno.docs.schema import DocumentationType, ExampleInfo, FieldInfo, SchemaInfo


class ApiEndpointExtractor:
    """
    Extractor for FastAPI endpoints to generate schema documentation.
    
    This extractor works with FastAPI applications and routers to document
    API endpoints, their parameters, response models, and example usage.
    """
    
    async def can_extract(self, item: Any) -> bool:
        """
        Determine if this extractor can handle a given item.
        
        Args:
            item: The item to check
            
        Returns:
            True if this item is a FastAPI application or router
        """
        return isinstance(item, (FastAPI, APIRouter))
    
    async def extract_schema(self, item: Any) -> SchemaInfo:
        """
        Extract documentation schema from a FastAPI application or router.
        
        Args:
            item: The FastAPI app or router to extract schema from
            
        Returns:
            Documentation schema for the API endpoints
        """
        # Get name and module
        name = getattr(item, "title", "API") if isinstance(item, FastAPI) else "APIRouter"
        module = item.__module__
        
        # Get routes
        routes = self._get_routes(item)
        
        # Create schema info
        schema = SchemaInfo(
            name=name,
            module=module,
            description=self._get_description(item),
            type=DocumentationType.API,
            fields=await self._extract_endpoints(routes),
            examples=await self._create_examples(routes),
        )
        
        return schema
    
    def _get_routes(self, item: FastAPI | APIRouter) -> list[APIRoute]:
        """Get all API routes from a FastAPI app or router."""
        routes = []
        
        # FastAPI app routes are in the routes attribute
        if isinstance(item, FastAPI):
            for route in item.routes:
                if isinstance(route, APIRouter):
                    routes.extend(self._get_routes(route))
                elif isinstance(route, APIRoute):
                    routes.append(route)
        
        # APIRouter routes are in the routes attribute
        elif isinstance(item, APIRouter):
            for route in item.routes:
                if isinstance(route, APIRoute):
                    routes.append(route)
        
        return routes
    
    def _get_description(self, item: FastAPI | APIRouter) -> str:
        """Get the description from a FastAPI app or router."""
        if isinstance(item, FastAPI):
            return item.description or f"{item.title} API"
        
        # Try to get docstring for router
        return inspect.getdoc(item) or "API Router"
    
    async def _extract_endpoints(self, routes: list[APIRoute]) -> list[FieldInfo]:
        """Extract endpoint information as fields."""
        fields = []
        
        for route in routes:
            # Get HTTP method
            methods = route.methods or {"GET"}
            methods_str = ", ".join(sorted(methods))
            
            # Create field for this endpoint
            field = FieldInfo(
                name=route.path,
                type_name=methods_str,
                type_hint=str(route.response_model) if route.response_model else "Any",
                description=route.description or inspect.getdoc(route.endpoint) or "",
                extra_info={
                    "methods": list(methods),
                    "tags": route.tags or [],
                    "parameters": await self._extract_parameters(route),
                    "response_model": str(route.response_model) if route.response_model else None,
                    "status_code": route.status_code,
                    "deprecated": route.deprecated,
                    "summary": route.summary,
                },
            )
            
            fields.append(field)
        
        return fields
    
    async def _extract_parameters(self, route: APIRoute) -> list[dict[str, Any]]:
        """Extract parameter information from a route."""
        params = []
        
        # Get signature of the endpoint function
        sig = inspect.signature(route.endpoint)
        
        # Process each parameter
        for name, param in sig.parameters.items():
            # Skip self and kwargs
            if name in ("self", "kwargs"):
                continue
                
            # Get annotation and default
            annotation = param.annotation if param.annotation != inspect.Parameter.empty else Any
            default = None if param.default == inspect.Parameter.empty else param.default
            
            # Add parameter info
            params.append({
                "name": name,
                "type": str(annotation),
                "default": str(default) if default is not None else None,
                "required": default is None and param.default == inspect.Parameter.empty,
            })
        
        return params
    
    async def _create_examples(self, routes: list[APIRoute]) -> list[ExampleInfo]:
        """Create example usage for API endpoints."""
        examples = []
        
        # Create example for each route (limited to first 5 for brevity)
        for route in routes[:5]:
            methods = route.methods or {"GET"}
            method = next(iter(methods))
            
            # Create example code based on method
            if method == "GET":
                code = self._create_get_example(route)
            elif method in ("POST", "PUT", "PATCH"):
                code = self._create_post_example(route)
            elif method == "DELETE":
                code = self._create_delete_example(route)
            else:
                code = self._create_generic_example(route, method)
            
            # Create example info
            example = ExampleInfo(
                title=f"{method} {route.path}",
                code=code,
                language="python",
                description=f"Example for {method} {route.path}",
            )
            
            examples.append(example)
        
        return examples
    
    def _create_get_example(self, route: APIRoute) -> str:
        """Create example for GET request."""
        path = route.path.replace("{", "").replace("}", "")  # Simplify for example
        return f"""import requests

response = requests.get("https://api.example.com{path}")
data = response.json()
print(data)
"""
    
    def _create_post_example(self, route: APIRoute) -> str:
        """Create example for POST request."""
        path = route.path.replace("{", "").replace("}", "")  # Simplify for example
        
        # Try to generate example payload based on request model
        payload = "{\n    \"key\": \"value\"\n}"
        
        return f"""import requests

payload = {payload}
response = requests.post("https://api.example.com{path}", json=payload)
data = response.json()
print(data)
"""
    
    def _create_delete_example(self, route: APIRoute) -> str:
        """Create example for DELETE request."""
        path = route.path.replace("{", "").replace("}", "")  # Simplify for example
        return f"""import requests

response = requests.delete("https://api.example.com{path}")
if response.status_code == 204:
    print("Resource deleted successfully")
else:
    print(f"Error: {{response.status_code}}")
"""
    
    def _create_generic_example(self, route: APIRoute, method: str) -> str:
        """Create example for other HTTP methods."""
        path = route.path.replace("{", "").replace("}", "")  # Simplify for example
        return f"""import requests

response = requests.request("{method}", "https://api.example.com{path}")
print(response.status_code)
print(response.json())
"""
```
