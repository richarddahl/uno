# SPDX-FileCopyrightText: 2024-present Richard Dahl <richard@dahl.us>
# SPDX-License-Identifier: MIT
# SPDX-Package-Name: uno framework
"""
API playground functionality for testing endpoints directly from documentation.

This module provides utilities to render and execute API endpoint tests
interactively from the documentation.
"""

from __future__ import annotations

import asyncio
import inspect
import json
import re
from enum import Enum
from typing import Any, cast
from urllib.parse import urljoin

import httpx
from pydantic import BaseModel, Field, create_model

from uno.docs.schema import DocumentableItem, ExampleInfo, FieldInfo, SchemaInfo


class HttpMethod(str, Enum):
    """HTTP methods for API endpoints."""

    GET = "get"
    POST = "post"
    PUT = "put"
    PATCH = "patch"
    DELETE = "delete"
    HEAD = "head"
    OPTIONS = "options"


class ApiEndpointInfo(BaseModel):
    """Information about an API endpoint for the playground."""

    path: str
    method: HttpMethod
    summary: str = ""
    description: str = ""
    parameters: list[FieldInfo] = Field(default_factory=list)
    request_body: list[FieldInfo] = Field(default_factory=list)
    responses: dict[str, dict[str, Any]] = Field(default_factory=dict)
    examples: list[ExampleInfo] = Field(default_factory=list)
    requires_auth: bool = False


class ApiExecutionRequest(BaseModel):
    """Request for executing an API endpoint test."""

    endpoint_path: str
    method: HttpMethod
    base_url: str
    query_params: dict[str, Any] = Field(default_factory=dict)
    path_params: dict[str, Any] = Field(default_factory=dict)
    headers: dict[str, str] = Field(default_factory=dict)
    body: dict[str, Any] | str | None = None
    timeout: float = 10.0


class ApiExecutionResponse(BaseModel):
    """Response from executing an API endpoint test."""

    status_code: int
    headers: dict[str, str]
    body: dict[str, Any] | str | None = None
    content_type: str = ""
    duration_ms: float
    error: str | None = None


async def extract_api_endpoint_info(item: DocumentableItem) -> ApiEndpointInfo | None:
    """
    Extract API endpoint information from a documentable item.

    Args:
        item: Documentable item to extract from

    Returns:
        API endpoint information or None if not an API endpoint
    """
    schema = item.schema_info

    # Skip if not an API endpoint
    if schema.type.value != "api":
        return None

    # Get the path and method from the schema
    path = schema.extra_info.get("path", "")
    method_str = schema.extra_info.get("method", "get")

    try:
        method = HttpMethod(method_str.lower())
    except ValueError:
        method = HttpMethod.GET

    # Extract parameters, request body, and responses
    parameters = []
    request_body = []
    responses = {}

    # Process fields to categorize them
    for field in schema.fields:
        if (
            field.extra_info.get("in") == "path"
            or field.extra_info.get("in") == "query"
        ):
            parameters.append(field)
        elif field.extra_info.get("in") == "body":
            request_body.append(field)
        elif field.name == "responses":
            # Extract response information
            response_info = field.extra_info.get("response_info", {})
            responses = response_info if isinstance(response_info, dict) else {}

    # Check if auth is required
    requires_auth = any(
        field.name == "authorization" or "auth" in field.name.lower()
        for field in parameters + request_body
    )

    return ApiEndpointInfo(
        path=path,
        method=method,
        summary=schema.extra_info.get("summary", ""),
        description=schema.description,
        parameters=parameters,
        request_body=request_body,
        responses=responses,
        examples=schema.examples,
        requires_auth=requires_auth,
    )


async def generate_api_playground_html(
    item: DocumentableItem, base_url: str | None = None
) -> str:
    """
    Generate HTML for the API playground for an endpoint.

    Args:
        item: Documentable item representing an API endpoint
        base_url: Base URL for API calls (defaults to current host)

    Returns:
        HTML content for the API playground
    """
    endpoint_info = await extract_api_endpoint_info(item)
    if not endpoint_info:
        return "<div>Not an API endpoint</div>"

    if not base_url:
        base_url = "/"

    # Build the HTML
    path_html = _build_path_param_inputs(endpoint_info.path, endpoint_info.parameters)
    query_html = _build_query_param_inputs(endpoint_info.parameters)
    body_html = _build_request_body_inputs(endpoint_info.request_body)
    examples_html = _build_examples_section(
        endpoint_info.examples, endpoint_info.method
    )
    responses_html = _build_responses_section(endpoint_info.responses)

    # Generate a clean method badge class based on HTTP method
    method_class = f"method-{endpoint_info.method.value.lower()}"

    html = f"""
    <div class="api-playground">
        <div class="endpoint-header">
            <span class="method-badge {method_class}">{endpoint_info.method.value.upper()}</span>
            <span class="path-display">{endpoint_info.path}</span>
        </div>
        
        <div class="endpoint-description">
            {endpoint_info.description}
        </div>
        
        <div class="test-form">
            <h3>Test this endpoint</h3>
            
            <div class="form-row">
                <label>Base URL:</label>
                <input type="text" id="base-url" class="form-control" value="{base_url}">
            </div>
            
            {path_html}
            
            {query_html}
            
            {body_html}
            
            <div class="form-row">
                <label>Headers:</label>
                <textarea id="headers" class="form-control code-textarea" rows="3">{{
  "Content-Type": "application/json"
}}</textarea>
                <small>Headers as JSON</small>
            </div>
            
            <div class="form-actions">
                <button id="send-request" class="send-button">Send Request</button>
                <button id="clear-form" class="clear-button">Clear</button>
            </div>
        </div>
        
        <div class="response-section" style="display: none;">
            <h3>Response</h3>
            
            <div class="response-info">
                <span class="status-badge" id="status-badge">200</span>
                <span class="duration" id="duration">0ms</span>
            </div>
            
            <div class="response-tabs">
                <div class="tab-headers">
                    <span class="tab-header active" data-tab="body">Body</span>
                    <span class="tab-header" data-tab="headers">Headers</span>
                </div>
                
                <div class="tab-content active" id="tab-body">
                    <pre id="response-body" class="code-block"></pre>
                </div>
                
                <div class="tab-content" id="tab-headers">
                    <pre id="response-headers" class="code-block"></pre>
                </div>
            </div>
        </div>
        
        {examples_html}
        
        {responses_html}
    </div>
    
    <script>
        document.addEventListener('DOMContentLoaded', function() {{
            // Get elements
            const sendButton = document.getElementById('send-request');
            const clearButton = document.getElementById('clear-form');
            const baseUrlInput = document.getElementById('base-url');
            const headersInput = document.getElementById('headers');
            const responseSection = document.querySelector('.response-section');
            const statusBadge = document.getElementById('status-badge');
            const durationEl = document.getElementById('duration');
            const responseBody = document.getElementById('response-body');
            const responseHeaders = document.getElementById('response-headers');
            const tabHeaders = document.querySelectorAll('.tab-header');
            const exampleButtons = document.querySelectorAll('.load-example-button');
            
            // Tab switching
            tabHeaders.forEach(header => {{
                header.addEventListener('click', () => {{
                    // Remove active class from all tabs
                    tabHeaders.forEach(h => h.classList.remove('active'));
                    document.querySelectorAll('.tab-content').forEach(
                        c => c.classList.remove('active')
                    );
                    
                    // Add active class to selected tab
                    header.classList.add('active');
                    document.getElementById('tab-' + header.dataset.tab).classList.add('active');
                }});
            }});
            
            // Load examples
            exampleButtons.forEach(button => {{
                button.addEventListener('click', () => {{
                    const exampleId = button.dataset.example;
                    const example = document.getElementById(exampleId);
                    
                    // Parse example data
                    try {{
                        const exampleData = JSON.parse(example.textContent);
                        
                        // Fill in path params
                        const pathParams = document.querySelectorAll('.path-param-input');
                        pathParams.forEach(input => {{
                            const paramName = input.dataset.param;
                            if (exampleData.path_params && paramName in exampleData.path_params) {{
                                input.value = exampleData.path_params[paramName];
                            }}
                        }});
                        
                        // Fill in query params
                        const queryParams = document.querySelectorAll('.query-param-input');
                        queryParams.forEach(input => {{
                            const paramName = input.dataset.param;
                            if (exampleData.query_params && paramName in exampleData.query_params) {{
                                input.value = exampleData.query_params[paramName];
                            }}
                        }});
                        
                        // Fill in body
                        const bodyInput = document.getElementById('request-body');
                        if (bodyInput && exampleData.body) {{
                            bodyInput.value = typeof exampleData.body === 'string' 
                                ? exampleData.body 
                                : JSON.stringify(exampleData.body, null, 2);
                        }}
                        
                        // Fill in headers
                        if (exampleData.headers) {{
                            headersInput.value = JSON.stringify(exampleData.headers, null, 2);
                        }}
                    }} catch (error) {{
                        console.error('Error loading example:', error);
                    }}
                }});
            }});
            
            // Format JSON function
            function formatJSON(jsonStr) {{
                try {{
                    const obj = JSON.parse(jsonStr);
                    return JSON.stringify(obj, null, 2);
                }} catch (e) {{
                    return jsonStr;
                }}
            }}
            
            // Send request
            sendButton.addEventListener('click', async () => {{
                // Show loading state
                sendButton.disabled = true;
                sendButton.textContent = 'Sending...';
                
                // Collect path parameters
                const pathParams = {{}};
                document.querySelectorAll('.path-param-input').forEach(input => {{
                    pathParams[input.dataset.param] = input.value;
                }});
                
                // Collect query parameters
                const queryParams = {{}};
                document.querySelectorAll('.query-param-input').forEach(input => {{
                    if (input.value) {{
                        queryParams[input.dataset.param] = input.value;
                    }}
                }});
                
                // Get body if present
                let body = null;
                const bodyInput = document.getElementById('request-body');
                if (bodyInput && bodyInput.value) {{
                    try {{
                        // Try to parse as JSON first
                        body = JSON.parse(bodyInput.value);
                    }} catch (e) {{
                        // Use as raw string if not valid JSON
                        body = bodyInput.value;
                    }}
                }}
                
                // Parse headers
                let headers = {{}};
                try {{
                    headers = JSON.parse(headersInput.value);
                }} catch (e) {{
                    console.error('Invalid headers JSON:', e);
                }}
                
                // Prepare request
                const request = {{
                    endpoint_path: "{endpoint_info.path}",
                    method: "{endpoint_info.method.value}",
                    base_url: baseUrlInput.value,
                    query_params: queryParams,
                    path_params: pathParams,
                    headers: headers,
                    body: body
                }};
                
                try {{
                    // Execute request
                    const response = await fetch('/api/playground/execute', {{
                        method: 'POST',
                        headers: {{
                            'Content-Type': 'application/json',
                        }},
                        body: JSON.stringify(request)
                    }});
                    
                    const result = await response.json();
                    
                    // Update response UI
                    responseSection.style.display = 'block';
                    statusBadge.textContent = result.status_code;
                    statusBadge.className = 'status-badge';
                    statusBadge.classList.add(getStatusClass(result.status_code));
                    
                    durationEl.textContent = `${{result.duration_ms.toFixed(0)}}ms`;
                    
                    // Format and display body
                    if (result.body) {{
                        if (typeof result.body === 'object') {{
                            responseBody.innerHTML = syntaxHighlight(JSON.stringify(result.body, null, 2));
                        }} else {{
                            responseBody.textContent = result.body;
                        }}
                    }} else {{
                        responseBody.textContent = '(No body)';
                    }}
                    
                    // Format and display headers
                    responseHeaders.innerHTML = syntaxHighlight(JSON.stringify(result.headers, null, 2));
                    
                }} catch (error) {{
                    console.error('Error executing request:', error);
                    
                    responseSection.style.display = 'block';
                    statusBadge.textContent = 'ERR';
                    statusBadge.className = 'status-badge status-error';
                    
                    responseBody.textContent = `Error: ${{error.message || 'Unknown error'}}`;
                }} finally {{
                    // Reset button
                    sendButton.disabled = false;
                    sendButton.textContent = 'Send Request';
                }}
            }});
            
            // Function to get status class
            function getStatusClass(status) {{
                if (status < 300) return 'status-success';
                if (status < 400) return 'status-redirect';
                if (status < 500) return 'status-client-error';
                return 'status-server-error';
            }}
            
            // Syntax highlighting
            function syntaxHighlight(json) {{
                if (!json) return '';
                
                json = json.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
                return json.replace(
                    /("(\\\\u[a-zA-Z0-9]{{4}}|\\\\[^u]|[^\\\\"])*"(\\s*:)?|\\b(true|false|null)\\b|-?\\d+(?:\\.\\d*)?(?:[eE][+\\-]?\\d+)?)/g,
                    function (match) {{
                        let cls = 'json-number';
                        if (/^"/.test(match)) {{
                            if (/:$/.test(match)) {{
                                cls = 'json-key';
                            }} else {{
                                cls = 'json-string';
                            }}
                        }} else if (/true|false/.test(match)) {{
                            cls = 'json-boolean';
                        }} else if (/null/.test(match)) {{
                            cls = 'json-null';
                        }}
                        return '<span class="' + cls + '">' + match + '</span>';
                    }}
                );
            }}
            
            // Clear form
            clearButton.addEventListener('click', () => {{
                // Reset path parameters
                document.querySelectorAll('.path-param-input').forEach(input => {{
                    input.value = '';
                }});
                
                // Reset query parameters
                document.querySelectorAll('.query-param-input').forEach(input => {{
                    input.value = '';
                }});
                
                // Reset body
                const bodyInput = document.getElementById('request-body');
                if (bodyInput) {{
                    bodyInput.value = '';
                }}
                
                // Reset headers
                headersInput.value = '{{\n  "Content-Type": "application/json"\n}}';
                
                // Hide response section
                responseSection.style.display = 'none';
            }});
        }});
    </script>
    
    <style>
        .api-playground {{
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
            background-color: #f8f9fa;
            border: 1px solid #e9ecef;
            border-radius: 4px;
            padding: 20px;
            margin: 20px 0;
        }}
        
        .endpoint-header {{
            display: flex;
            align-items: center;
            margin-bottom: 15px;
        }}
        
        .method-badge {{
            font-weight: bold;
            padding: 5px 10px;
            border-radius: 4px;
            margin-right: 10px;
            font-size: 14px;
        }}
        
        .method-get {{ background-color: #61affe; color: white; }}
        .method-post {{ background-color: #49cc90; color: white; }}
        .method-put {{ background-color: #fca130; color: white; }}
        .method-delete {{ background-color: #f93e3e; color: white; }}
        .method-patch {{ background-color: #50e3c2; color: white; }}
        .method-head {{ background-color: #9012fe; color: white; }}
        .method-options {{ background-color: #0d5aa7; color: white; }}
        
        .path-display {{
            font-family: monospace;
            font-size: 16px;
            background-color: #e9ecef;
            padding: 5px 10px;
            border-radius: 2px;
            overflow-x: auto;
            max-width: 100%;
        }}
        
        .endpoint-description {{
            margin-bottom: 20px;
            color: #495057;
        }}
        
        .test-form {{
            background-color: white;
            border: 1px solid #dee2e6;
            border-radius: 4px;
            padding: 15px;
            margin-bottom: 20px;
        }}
        
        .form-row {{
            margin-bottom: 15px;
        }}
        
        .form-row label {{
            display: block;
            margin-bottom: 5px;
            font-weight: 500;
        }}
        
        .form-control {{
            width: 100%;
            padding: 8px;
            border: 1px solid #ced4da;
            border-radius: 4px;
            font-size: 14px;
        }}
        
        .code-textarea {{
            font-family: monospace;
            white-space: pre;
            tab-size: 2;
        }}
        
        small {{
            color: #6c757d;
            font-size: 12px;
            margin-top: 2px;
            display: block;
        }}
        
        .form-actions {{
            display: flex;
            gap: 10px;
        }}
        
        .send-button {{
            background-color: #007bff;
            color: white;
            border: none;
            padding: 8px 16px;
            border-radius: 4px;
            cursor: pointer;
            font-weight: 500;
        }}
        
        .send-button:hover {{
            background-color: #0069d9;
        }}
        
        .send-button:disabled {{
            background-color: #6c757d;
            cursor: not-allowed;
        }}
        
        .clear-button {{
            background-color: #6c757d;
            color: white;
            border: none;
            padding: 8px 16px;
            border-radius: 4px;
            cursor: pointer;
        }}
        
        .clear-button:hover {{
            background-color: #5a6268;
        }}
        
        .response-section {{
            background-color: white;
            border: 1px solid #dee2e6;
            border-radius: 4px;
            padding: 15px;
            margin-bottom: 20px;
        }}
        
        .response-info {{
            display: flex;
            align-items: center;
            margin-bottom: 10px;
        }}
        
        .status-badge {{
            padding: 5px 10px;
            border-radius: 4px;
            font-weight: bold;
            margin-right: 10px;
            font-size: 14px;
        }}
        
        .status-success {{ background-color: #28a745; color: white; }}
        .status-redirect {{ background-color: #ffc107; color: black; }}
        .status-client-error {{ background-color: #f93e3e; color: white; }}
        .status-server-error {{ background-color: #d9534f; color: white; }}
        .status-error {{ background-color: #dc3545; color: white; }}
        
        .duration {{
            font-family: monospace;
            color: #6c757d;
        }}
        
        .response-tabs {{
            border: 1px solid #dee2e6;
            border-radius: 4px;
            overflow: hidden;
        }}
        
        .tab-headers {{
            display: flex;
            background-color: #f8f9fa;
            border-bottom: 1px solid #dee2e6;
        }}
        
        .tab-header {{
            padding: 10px 15px;
            cursor: pointer;
            border-right: 1px solid #dee2e6;
        }}
        
        .tab-header:hover {{
            background-color: #e9ecef;
        }}
        
        .tab-header.active {{
            background-color: white;
            border-bottom: 2px solid #007bff;
            font-weight: 500;
        }}
        
        .tab-content {{
            display: none;
            padding: 10px;
            overflow: auto;
            max-height: 400px;
        }}
        
        .tab-content.active {{
            display: block;
        }}
        
        .code-block {{
            margin: 0;
            font-family: monospace;
            tab-size: 2;
            white-space: pre-wrap;
            word-break: break-all;
        }}
        
        /* JSON Syntax Highlighting */
        .json-key {{ color: #0451a5; }}
        .json-string {{ color: #a31515; }}
        .json-number {{ color: #098658; }}
        .json-boolean {{ color: #0000ff; }}
        .json-null {{ color: #0000ff; }}
        
        /* Examples section */
        .examples-section {{
            margin-top: 20px;
        }}
        
        .example-item {{
            margin-bottom: 10px;
        }}
        
        .example-header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            background-color: #f8f9fa;
            padding: 10px;
            border: 1px solid #dee2e6;
            border-top-left-radius: 4px;
            border-top-right-radius: 4px;
        }}
        
        .example-title {{
            font-weight: 500;
        }}
        
        .load-example-button {{
            background-color: #6c757d;
            color: white;
            border: none;
            padding: 4px 8px;
            border-radius: 4px;
            font-size: 12px;
            cursor: pointer;
        }}
        
        .load-example-button:hover {{
            background-color: #5a6268;
        }}
        
        .example-content {{
            border: 1px solid #dee2e6;
            border-top: none;
            border-bottom-left-radius: 4px;
            border-bottom-right-radius: 4px;
            padding: 10px;
            background-color: white;
            overflow: auto;
            max-height: 300px;
        }}
        
        .example-code {{
            margin: 0;
            font-family: monospace;
            tab-size: 2;
            white-space: pre-wrap;
            word-break: break-all;
        }}
        
        /* Responses section */
        .responses-section {{
            margin-top: 20px;
        }}
        
        .response-item {{
            margin-bottom: 10px;
        }}
        
        .response-header {{
            display: flex;
            align-items: center;
            background-color: #f8f9fa;
            padding: 10px;
            border: 1px solid #dee2e6;
            border-top-left-radius: 4px;
            border-top-right-radius: 4px;
        }}
        
        .response-status {{
            font-weight: 500;
            margin-right: 10px;
        }}
        
        .response-description {{
            color: #6c757d;
        }}
        
        .response-content {{
            border: 1px solid #dee2e6;
            border-top: none;
            border-bottom-left-radius: 4px;
            border-bottom-right-radius: 4px;
            padding: 10px;
            background-color: white;
            overflow: auto;
            max-height: 300px;
        }}
    </style>
    """

    return html


async def execute_api_call(request: ApiExecutionRequest) -> ApiExecutionResponse:
    """
    Execute an API call based on the request.

    Args:
        request: API execution request details

    Returns:
        API execution response
    """
    # Prepare the full URL
    endpoint_path = request.endpoint_path

    # Replace path parameters
    for name, value in request.path_params.items():
        endpoint_path = endpoint_path.replace(f"{{{name}}}", str(value))

    # Build the full URL
    url = urljoin(request.base_url, endpoint_path)

    # Prepare headers (convert all keys to strings)
    headers = {str(k): str(v) for k, v in request.headers.items()}

    # Convert body to JSON if it's a dict
    body = request.body
    if isinstance(body, dict):
        body = json.dumps(body)

    # Prepare client options
    timeout = httpx.Timeout(request.timeout)

    # Prepare for response measuring
    start_time = asyncio.get_event_loop().time()

    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            # Get the appropriate HTTP method
            http_method = getattr(client, request.method.value)

            # Send the request
            response = await http_method(
                url,
                params=request.query_params,
                headers=headers,
                content=body,
            )

            # Calculate duration
            duration = (asyncio.get_event_loop().time() - start_time) * 1000  # in ms

            # Parse content type
            content_type = response.headers.get("content-type", "")

            # Try to parse body based on content type
            response_body: dict[str, Any] | str | None = None

            if response.content:
                if "application/json" in content_type:
                    try:
                        response_body = response.json()
                    except Exception:
                        response_body = response.text
                else:
                    response_body = response.text

            # Convert headers to dict (all values as strings)
            response_headers = {str(k): str(v) for k, v in response.headers.items()}

            return ApiExecutionResponse(
                status_code=response.status_code,
                headers=response_headers,
                body=response_body,
                content_type=content_type,
                duration_ms=duration,
                error=None,
            )
    except Exception as e:
        # Calculate duration even for errors
        duration = (asyncio.get_event_loop().time() - start_time) * 1000  # in ms

        return ApiExecutionResponse(
            status_code=0,
            headers={},
            body=None,
            content_type="",
            duration_ms=duration,
            error=str(e),
        )


def _build_path_param_inputs(path: str, parameters: list[FieldInfo]) -> str:
    """Build HTML for path parameter inputs."""
    # Extract path parameter names from the path
    path_param_names = re.findall(r"{([^}]+)}", path)

    if not path_param_names:
        return ""

    # Find path parameter details
    path_params = [
        field
        for field in parameters
        if field.name in path_param_names and field.extra_info.get("in") == "path"
    ]

    html = '<div class="form-row"><label>Path Parameters:</label>'

    for param_name in path_param_names:
        # Find parameter info
        param_info = next((p for p in path_params if p.name == param_name), None)

        description = param_info.description if param_info else ""
        required = param_info.is_required if param_info else True

        html += f"""
        <div class="path-param">
            <label>{param_name}{'*' if required else ''}:</label>
            <input 
                type="text" 
                class="form-control path-param-input" 
                data-param="{param_name}" 
                {'required' if required else ''}
            >
            <small>{description}</small>
        </div>
        """

    html += "</div>"
    return html


def _build_query_param_inputs(parameters: list[FieldInfo]) -> str:
    """Build HTML for query parameter inputs."""
    # Find query parameters
    query_params = [
        field for field in parameters if field.extra_info.get("in") == "query"
    ]

    if not query_params:
        return ""

    html = '<div class="form-row"><label>Query Parameters:</label>'

    for param in query_params:
        html += f"""
        <div class="query-param">
            <label>{param.name}{'*' if param.is_required else ''}:</label>
            <input 
                type="text" 
                class="form-control query-param-input" 
                data-param="{param.name}" 
                {'required' if param.is_required else ''}
            >
            <small>{param.description}</small>
        </div>
        """

    html += "</div>"
    return html


def _build_request_body_inputs(body_fields: list[FieldInfo]) -> str:
    """Build HTML for request body inputs."""
    if not body_fields:
        return ""

    # If body fields exist, create a textarea for the request body
    html = """
    <div class="form-row">
        <label>Request Body:</label>
        <textarea id="request-body" class="form-control code-textarea" rows="5"></textarea>
        <small>Request body (usually JSON)</small>
    </div>
    """

    return html


def _build_examples_section(examples: list[ExampleInfo], method: HttpMethod) -> str:
    """Build HTML for examples section."""
    if not examples:
        return ""

    html = '<div class="examples-section"><h3>Examples</h3>'

    for i, example in enumerate(examples):
        # Generate a unique ID for this example
        example_id = f"example-{i}"

        # Format example as JSON with method, path params, query params, and body
        try:
            # Try to parse example as JSON
            example_json = json.loads(example.code)
        except Exception:
            # If not valid JSON, use code as is
            example_json = {
                "body": example.code,
                "method": method.value,
            }

        html += f"""
        <div class="example-item">
            <div class="example-header">
                <span class="example-title">{example.title}</span>
                <button class="load-example-button" data-example="{example_id}">Load Example</button>
            </div>
            <div class="example-content">
                <pre class="example-code" id="{example_id}">{json.dumps(example_json, indent=2)}</pre>
            </div>
        </div>
        """

    html += "</div>"
    return html


def _build_responses_section(responses: dict[str, dict[str, Any]]) -> str:
    """Build HTML for responses section."""
    if not responses:
        return ""

    html = '<div class="responses-section"><h3>Responses</h3>'

    for status_code, response_info in sorted(responses.items()):
        description = response_info.get("description", "")

        # Get response schema or example if available
        schema = response_info.get("schema", {})
        example = response_info.get("example", None)

        content = ""
        if example:
            # Format example as JSON
            if isinstance(example, dict):
                content = json.dumps(example, indent=2)
            else:
                content = str(example)
        elif schema:
            # Show schema if no example
            content = json.dumps(schema, indent=2)

        html += f"""
        <div class="response-item">
            <div class="response-header">
                <span class="response-status">{status_code}</span>
                <span class="response-description">{description}</span>
            </div>
            <div class="response-content">
                <pre class="response-code">{content}</pre>
            </div>
        </div>
        """

    html += "</div>"
    return html
