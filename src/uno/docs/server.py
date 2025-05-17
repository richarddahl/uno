# SPDX-FileCopyrightText: 2024-present Richard Dahl <richard@dahl.us>
# SPDX-License-Identifier: MIT
# SPDX-Package-Name: uno framework
"""
Live documentation server for real-time documentation viewing.

This module provides a web server for viewing and searching documentation.
"""

from __future__ import annotations

import asyncio
import os
import signal
import sys
import tempfile
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from uno.config import Config
from uno.docs.discovery import discover_documentable_items
from uno.docs.providers import MkDocsProvider, JsonProvider
from uno.docs.schema import DocumentationType
from uno.docs.relationships import (
    build_relationship_graph,
    filter_graph,
    detect_impl_protocol_relationships,
)
from uno.docs.search import search_items, create_search_index, SearchIndex
from uno.docs.api_playground import (
    ApiExecutionRequest,
    ApiExecutionResponse,
    execute_api_call,
    generate_api_playground_html,
)
from uno.docs.landing_page import (
    LandingPageConfig,
    LandingPageSection,
    generate_landing_page,
    generate_default_landing_page,
)


class DocServerConfig(Config):
    """Configuration for the documentation server."""

    title: str = "Uno Documentation"
    module_names: list[str]
    port: int = 8000
    host: str = "127.0.0.1"
    theme: str = "material"
    enable_search: bool = True
    watch_paths: list[str] | None = None
    poll_interval: int = 5  # seconds
    enable_api_docs: bool = True  # Enable OpenAPI docs for discovered API endpoints
    api_docs_url: str = "/api-docs"  # URL for OpenAPI docs
    api_redoc_url: str = "/api-redoc"  # URL for ReDoc
    syntax_highlighting: bool = True  # Enable syntax highlighting for code examples
    highlight_theme: str = "github-dark"  # Theme for syntax highlighting
    enable_relationship_graphs: bool = True  # Enable relationship graph visualization
    search_min_score: float = 0.1  # Minimum score for search results
    search_max_results: int = 50  # Maximum number of search results
    enable_api_playground: bool = True  # Enable API playground for testing endpoints
    api_playground_base_url: str | None = None  # Base URL for API playground requests
    enable_landing_page: bool = True  # Enable custom landing page
    landing_page_config: LandingPageConfig | None = None  # Custom landing page config


class DocServer:
    """Server for live documentation viewing."""

    def __init__(self, config: DocServerConfig) -> None:
        """Initialize the documentation server."""
        self.config = config
        self.temp_dir = Path(tempfile.mkdtemp(prefix="uno-docs-"))
        self.app = FastAPI(
            title=config.title,
            docs_url=config.api_docs_url if config.enable_api_docs else None,
            redoc_url=config.api_redoc_url if config.enable_api_docs else None,
        )
        self.setup_routes()
        self.last_modified_times: dict[str, float] = {}
        self.running = False
        self.search_index: SearchIndex | None = None

    def setup_routes(self) -> None:
        """Set up the FastAPI routes."""

        # Landing page route
        @self.app.get("/", response_class=HTMLResponse)
        async def get_landing_page(request: Request):
            """Get the landing page."""
            if not self.config.enable_landing_page:
                # Fall back to the standard MkDocs index page
                return self.app.url_path_for("/")

            # Get all items for component listings
            all_items = []
            for module_name in self.config.module_names:
                items = await discover_documentable_items(module_name)
                all_items.extend(items)

            # Determine base URL from request
            base_url = "/"
            if self.config.api_playground_base_url:
                base_url = self.config.api_playground_base_url
                if not base_url.endswith("/"):
                    base_url += "/"

            # Use custom config or generate default
            if self.config.landing_page_config:
                html = await generate_landing_page(
                    self.config.landing_page_config, all_items, base_url
                )
            else:
                html = await generate_default_landing_page(
                    all_items, title=self.config.title, base_url=base_url
                )

            return html

        # API routes for JSON data
        @self.app.get("/api/docs")
        async def get_docs():
            """Get all documentable items as JSON."""
            all_items = []
            for module_name in self.config.module_names:
                items = await discover_documentable_items(module_name)
                all_items.extend(items)

            provider = JsonProvider()
            return await provider.generate_items_dict(all_items)

        @self.app.get("/api/docs/{name}")
        async def get_doc_by_name(name: str):
            """Get a specific documentable item by name."""
            for module_name in self.config.module_names:
                items = await discover_documentable_items(module_name)
                for item in items:
                    if item.schema_info.name.lower() == name.lower():
                        provider = JsonProvider()
                        return await provider.generate_for_item(item)

            raise HTTPException(
                status_code=404, detail=f"Documentation for '{name}' not found"
            )

        @self.app.get("/api/endpoints")
        async def get_api_endpoints():
            """Get all documented API endpoints."""
            api_items = []
            for module_name in self.config.module_names:
                items = await discover_documentable_items(module_name)
                for item in items:
                    if item.schema_info.type == DocumentationType.API:
                        api_items.append(item)

            if not api_items:
                return {"endpoints": []}

            provider = JsonProvider()
            return await provider.generate_items_dict(api_items)

        # Enhanced search API
        @self.app.get("/api/search")
        async def search_docs(
            q: str,
            types: list[str] = Query(None),
            modules: list[str] = Query(None),
            max_results: int | None = None,
        ):
            """
            Search documentation with enhanced relevance ranking.

            Args:
                q: Search query
                types: Filter by document types
                modules: Filter by modules
                max_results: Maximum number of results
            """
            if not self.config.enable_search:
                raise HTTPException(status_code=404, detail="Search is not enabled")

            # If query is empty, return empty results
            if not q.strip():
                return {"results": [], "count": 0}

            # Get all items
            all_items = []
            for module_name in self.config.module_names:
                items = await discover_documentable_items(module_name)
                all_items.extend(items)

            # Convert string types to enum values
            doc_types = None
            if types:
                doc_types = []
                for t in types:
                    try:
                        doc_types.append(DocumentationType(t))
                    except ValueError:
                        pass

            # Set max results
            limit = max_results or self.config.search_max_results

            # Perform search
            results = await search_items(
                all_items,
                q,
                doc_types=doc_types,
                modules=modules,
                max_results=limit,
                min_score=self.config.search_min_score,
            )

            return {
                "results": results,
                "count": len(results),
                "query": q,
            }

        # Search UI
        @self.app.get("/search", response_class=HTMLResponse)
        async def search_page():
            """Get search page."""
            if not self.config.enable_search:
                raise HTTPException(status_code=404, detail="Search is not enabled")

            # Create HTML for search page
            html = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <title>{self.config.title} - Search</title>
                <meta charset="utf-8">
                <meta name="viewport" content="width=device-width, initial-scale=1">
                <style>
                    body, html {{
                        margin: 0;
                        padding: 0;
                        width: 100%;
                        height: 100%;
                        font-family: Arial, sans-serif;
                    }}
                    .container {{
                        max-width: 1200px;
                        margin: 0 auto;
                        padding: 20px;
                    }}
                    .search-form {{
                        margin-bottom: 30px;
                    }}
                    .search-input {{
                        width: 70%;
                        padding: 10px;
                        font-size: 16px;
                        border: 1px solid #ddd;
                        border-radius: 4px;
                    }}
                    .search-button {{
                        padding: 10px 20px;
                        font-size: 16px;
                        background-color: #4285f4;
                        color: white;
                        border: none;
                        border-radius: 4px;
                        cursor: pointer;
                    }}
                    .search-button:hover {{
                        background-color: #3275e4;
                    }}
                    .filters {{
                        margin: 20px 0;
                        display: flex;
                        gap: 20px;
                    }}
                    .filter-group {{
                        display: flex;
                        flex-direction: column;
                    }}
                    .filter-label {{
                        font-weight: bold;
                        margin-bottom: 5px;
                    }}
                    select {{
                        padding: 8px;
                        border-radius: 4px;
                        border: 1px solid #ddd;
                    }}
                    .results {{
                        margin-top: 20px;
                    }}
                    .result-item {{
                        margin-bottom: 20px;
                        padding: 15px;
                        border: 1px solid #eee;
                        border-radius: 4px;
                        transition: box-shadow 0.3s;
                    }}
                    .result-item:hover {{
                        box-shadow: 0 2px 5px rgba(0,0,0,0.1);
                    }}
                    .result-title {{
                        font-size: 18px;
                        margin-bottom: 5px;
                        color: #1a0dab;
                        text-decoration: none;
                    }}
                    .result-title:hover {{
                        text-decoration: underline;
                    }}
                    .result-path {{
                        color: #006621;
                        font-size: 14px;
                        margin-bottom: 8px;
                    }}
                    .result-matches {{
                        font-size: 14px;
                        line-height: 1.5;
                    }}
                    .match-fragment {{
                        background-color: #f8f9fa;
                        padding: 5px;
                        border-radius: 2px;
                        margin-bottom: 5px;
                        display: block;
                    }}
                    .match-highlight {{
                        background-color: #ffffc0;
                        font-weight: bold;
                    }}
                    .type-badge {{
                        display: inline-block;
                        padding: 2px 8px;
                        border-radius: 12px;
                        font-size: 12px;
                        color: white;
                        margin-right: 8px;
                    }}
                    .type-config {{
                        background-color: #8dd3c7;
                        color: #333;
                    }}
                    .type-api {{
                        background-color: #ffffb3;
                        color: #333;
                    }}
                    .type-model {{
                        background-color: #bebada;
                        color: #333;
                    }}
                    .type-service {{
                        background-color: #fb8072;
                        color: white;
                    }}
                    .type-cli {{
                        background-color: #80b1d3;
                        color: white;
                    }}
                    .type-other {{
                        background-color: #d9d9d9;
                        color: #333;
                    }}
                    .no-results {{
                        text-align: center;
                        margin-top: 40px;
                        color: #666;
                    }}
                    .loading {{
                        text-align: center;
                        margin-top: 40px;
                        color: #666;
                        display: none;
                    }}
                    .results-count {{
                        margin-bottom: 20px;
                        color: #666;
                    }}
                </style>
            </head>
            <body>
                <div class="container">
                    <h1>Search Documentation</h1>
                    
                    <div class="search-form">
                        <input type="text" id="search-input" class="search-input" placeholder="Search for..." autofocus>
                        <button id="search-button" class="search-button">Search</button>
                    </div>
                    
                    <div class="filters">
                        <div class="filter-group">
                            <span class="filter-label">Component Type:</span>
                            <select id="type-filter" multiple>
                                <option value="all" selected>All Types</option>
                                <option value="config">Config</option>
                                <option value="api">API</option>
                                <option value="model">Model</option>
                                <option value="service">Service</option>
                                <option value="cli">CLI</option>
                                <option value="other">Other</option>
                            </select>
                        </div>
                        
                        <div class="filter-group">
                            <span class="filter-label">Module:</span>
                            <select id="module-filter" multiple>
                                <option value="all" selected>All Modules</option>
                                <!-- Will be populated dynamically -->
                            </select>
                        </div>
                    </div>
                    
                    <div class="loading" id="loading">Searching...</div>
                    
                    <div class="results" id="results">
                        <div class="no-results" id="no-results">
                            <p>Enter a search term to find documentation.</p>
                        </div>
                    </div>
                </div>
                
                <script>
                    document.addEventListener('DOMContentLoaded', function() {{
                        const searchInput = document.getElementById('search-input');
                        const searchButton = document.getElementById('search-button');
                        const typeFilter = document.getElementById('type-filter');
                        const moduleFilter = document.getElementById('module-filter');
                        const resultsContainer = document.getElementById('results');
                        const noResults = document.getElementById('no-results');
                        const loading = document.getElementById('loading');
                        
                        // Load modules for filter
                        loadModules();
                        
                        // Perform search on button click
                        searchButton.addEventListener('click', () => performSearch());
                        
                        // Perform search on enter key
                        searchInput.addEventListener('keydown', (e) => {{
                            if (e.key === 'Enter') {{
                                performSearch();
                            }}
                        }});
                        
                        // Check for URL parameters
                        const urlParams = new URLSearchParams(window.location.search);
                        if (urlParams.has('q')) {{
                            searchInput.value = urlParams.get('q');
                            performSearch();
                        }}
                        
                        async function loadModules() {{
                            try {{
                                const response = await fetch('/api/docs');
                                const data = await response.json();
                                
                                // Extract unique modules
                                const modules = new Set();
                                data.items.forEach(item => {{
                                    if (item.module) {{
                                        const parts = item.module.split('.');
                                        let currentPath = '';
                                        for (const part of parts) {{
                                            currentPath = currentPath ? `${{currentPath}}.${{part}}` : part;
                                            modules.add(currentPath);
                                        }}
                                    }}
                                }});
                                
                                // Add modules to filter
                                Array.from(modules).sort().forEach(module => {{
                                    const option = document.createElement('option');
                                    option.value = module;
                                    option.textContent = module;
                                    moduleFilter.appendChild(option);
                                }});
                            }} catch (error) {{
                                console.error('Error loading modules:', error);
                            }}
                        }}
                        
                        async function performSearch() {{
                            const query = searchInput.value.trim();
                            if (!query) return;
                            
                            // Show loading
                            loading.style.display = 'block';
                            noResults.style.display = 'none';
                            resultsContainer.innerHTML = '';
                            
                            // Build search URL
                            let url = `/api/search?q=${{encodeURIComponent(query)}}`;
                            
                            // Add type filters
                            const selectedTypes = Array.from(typeFilter.selectedOptions).map(opt => opt.value);
                            if (selectedTypes.length > 0 && !selectedTypes.includes('all')) {{
                                selectedTypes.forEach(t => {{
                                    if (t !== 'all') {{
                                        url += `&types=${{t}}`;
                                    }}
                                }});
                            }}
                            
                            // Add module filters
                            const selectedModules = Array.from(moduleFilter.selectedOptions).map(opt => opt.value);
                            if (selectedModules.length > 0 && !selectedModules.includes('all')) {{
                                selectedModules.forEach(m => {{
                                    if (m !== 'all') {{
                                        url += `&modules=${{m}}`;
                                    }}
                                }});
                            }}
                            
                            try {{
                                const response = await fetch(url);
                                const data = await response.json();
                                
                                // Hide loading
                                loading.style.display = 'none';
                                
                                // Display results
                                if (data.results && data.results.length > 0) {{
                                    // Create results count
                                    const countEl = document.createElement('div');
                                    countEl.className = 'results-count';
                                    countEl.textContent = `Found ${{data.count}} results for "${{query}}"`;
                                    resultsContainer.appendChild(countEl);
                                    
                                    // Create results
                                    data.results.forEach(result => {{
                                        const resultItem = document.createElement('div');
                                        resultItem.className = 'result-item';
                                        
                                        // Determine doc page URL based on type
                                        const docUrl = `/${{result.item_type}}/${{result.item_name}}.html`;
                                        
                                        // Create title with type badge
                                        const title = document.createElement('a');
                                        title.className = 'result-title';
                                        title.href = docUrl;
                                        
                                        const typeBadge = document.createElement('span');
                                        typeBadge.className = `type-badge type-${{result.item_type}}`;
                                        typeBadge.textContent = result.item_type.toUpperCase();
                                        
                                        title.appendChild(typeBadge);
                                        title.appendChild(document.createTextNode(result.item_name));
                                        
                                        // Create path element
                                        const path = document.createElement('div');
                                        path.className = 'result-path';
                                        path.textContent = result.item_module;
                                        
                                        // Create matches container
                                        const matches = document.createElement('div');
                                        matches.className = 'result-matches';
                                        
                                        // Add match fragments
                                        const uniqueFragments = new Set();
                                        result.matches.slice(0, 3).forEach(match => {{
                                            if (match.fragment && !uniqueFragments.has(match.fragment)) {{
                                                uniqueFragments.add(match.fragment);
                                                
                                                const fragment = document.createElement('span');
                                                fragment.className = 'match-fragment';
                                                
                                                // Highlight the search term in the fragment
                                                const regex = new RegExp(`(${{escapeRegex(match.text)}})`, 'gi');
                                                const highlightedText = match.fragment.replace(
                                                    regex, 
                                                    '<span class="match-highlight">$1</span>'
                                                );
                                                fragment.innerHTML = highlightedText;
                                                
                                                matches.appendChild(fragment);
                                            }}
                                        }});
                                        
                                        // Add elements to result item
                                        resultItem.appendChild(title);
                                        resultItem.appendChild(path);
                                        resultItem.appendChild(matches);
                                        
                                        // Add to results container
                                        resultsContainer.appendChild(resultItem);
                                    }});
                                }} else {{
                                    // No results
                                    noResults.textContent = `No results found for "${{query}}".`;
                                    noResults.style.display = 'block';
                                }}
                                
                                // Update URL to include search query
                                const newUrl = new URL(window.location);
                                newUrl.searchParams.set('q', query);
                                window.history.pushState({{}}, '', newUrl);
                            }} catch (error) {{
                                console.error('Error performing search:', error);
                                loading.style.display = 'none';
                                noResults.textContent = 'An error occurred while searching.';
                                noResults.style.display = 'block';
                            }}
                        }}
                        
                        // Helper function to escape regex special characters
                        function escapeRegex(string) {{
                            return string.replace(/[.*+?^${{}}()|[\]\\]/g, '\\$&');
                        }}
                    }});
                </script>
            </body>
            </html>
            """
            return html

        # Relationship graph endpoint
        @self.app.get("/api/graph")
        async def get_relationship_graph(
            types: list[str] = Query(None),
            modules: list[str] = Query(None),
        ):
            """Get relationship graph for components."""
            if not self.config.enable_relationship_graphs:
                raise HTTPException(
                    status_code=404, detail="Relationship graphs are not enabled"
                )

            # Get all items
            all_items = []
            for module_name in self.config.module_names:
                items = await discover_documentable_items(module_name)
                all_items.extend(items)

            # Build graph
            graph = await build_relationship_graph(all_items)

            # Detect protocol implementations
            await detect_impl_protocol_relationships(graph, all_items)

            # Apply filters if provided
            if types or modules:
                # Convert string types to enum values
                type_filters = None
                if types:
                    type_filters = []
                    for t in types:
                        try:
                            type_filters.append(DocumentationType(t))
                        except ValueError:
                            pass

                # Filter graph
                graph = await filter_graph(graph, type_filters, modules)

            # Return graph data
            return graph.to_dict()

        # Graph visualization UI
        @self.app.get("/relationships", response_class=HTMLResponse)
        async def get_relationship_page():
            """Get relationship graph visualization page."""
            if not self.config.enable_relationship_graphs:
                raise HTTPException(
                    status_code=404, detail="Relationship graphs are not enabled"
                )

            # Create HTML for graph visualization
            html = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <title>{self.config.title} - Component Relationships</title>
                <meta charset="utf-8">
                <meta name="viewport" content="width=device-width, initial-scale=1">
                <script src="https://cdn.jsdelivr.net/npm/d3@7"></script>
                <script src="https://cdn.jsdelivr.net/npm/cytoscape@3.23.0/dist/cytoscape.min.js"></script>
                <style>
                    body, html {{
                        margin: 0;
                        padding: 0;
                        width: 100%;
                        height: 100%;
                        font-family: Arial, sans-serif;
                    }}
                    #app {{
                        display: flex;
                        flex-direction: column;
                        height: 100%;
                    }}
                    #toolbar {{
                        padding: 10px;
                        background-color: #f0f0f0;
                        border-bottom: 1px solid #ddd;
                    }}
                    #graph {{
                        flex-grow: 1;
                        width: 100%;
                    }}
                    .legend {{
                        position: absolute;
                        bottom: 20px;
                        right: 20px;
                        background-color: white;
                        border: 1px solid #ddd;
                        padding: 10px;
                        border-radius: 5px;
                        box-shadow: 0 2px 5px rgba(0,0,0,0.1);
                    }}
                    .legend-item {{
                        display: flex;
                        align-items: center;
                        margin-bottom: 5px;
                    }}
                    .legend-item .color-box {{
                        width: 20px;
                        height: 20px;
                        margin-right: 8px;
                    }}
                    .filter-group {{
                        margin-right: 20px;
                        display: inline-block;
                    }}
                    label {{
                        margin-right: 10px;
                    }}
                    select {{
                        padding: 5px;
                        margin-right: 10px;
                    }}
                    button {{
                        padding: 5px 10px;
                        cursor: pointer;
                    }}
                </style>
            </head>
            <body>
                <div id="app">
                    <div id="toolbar">
                        <div class="filter-group">
                            <label for="module-filter">Module:</label>
                            <select id="module-filter" multiple size="1">
                                <option value="all" selected>All Modules</option>
                            </select>
                        </div>
                        <div class="filter-group">
                            <label for="type-filter">Types:</label>
                            <select id="type-filter" multiple size="1">
                                <option value="all" selected>All Types</option>
                                <option value="config">Config</option>
                                <option value="api">API</option>
                                <option value="model">Model</option>
                                <option value="service">Service</option>
                                <option value="cli">CLI</option>
                            </select>
                        </div>
                        <button id="apply-filters">Apply Filters</button>
                        <button id="reset-filters">Reset Filters</button>
                        <button id="reset-layout">Reset Layout</button>
                    </div>
                    <div id="graph"></div>
                    <div class="legend">
                        <h3 style="margin-top: 0;">Legend</h3>
                        <div class="legend-item">
                            <div class="color-box" style="background-color: #8dd3c7;"></div>
                            <span>Config</span>
                        </div>
                        <div class="legend-item">
                            <div class="color-box" style="background-color: #ffffb3;"></div>
                            <span>API</span>
                        </div>
                        <div class="legend-item">
                            <div class="color-box" style="background-color: #bebada;"></div>
                            <span>Model</span>
                        </div>
                        <div class="legend-item">
                            <div class="color-box" style="background-color: #fb8072;"></div>
                            <span>Service</span>
                        </div>
                        <div class="legend-item">
                            <div class="color-box" style="background-color: #80b1d3;"></div>
                            <span>CLI</span>
                        </div>
                        <div class="legend-item">
                            <div class="color-box" style="background-color: #d9d9d9;"></div>
                            <span>Other</span>
                        </div>
                    </div>
                </div>
                <script>
                    document.addEventListener('DOMContentLoaded', function() {{
                        const graphContainer = document.getElementById('graph');
                        const moduleFilter = document.getElementById('module-filter');
                        const typeFilter = document.getElementById('type-filter');
                        const applyFiltersBtn = document.getElementById('apply-filters');
                        const resetFiltersBtn = document.getElementById('reset-filters');
                        const resetLayoutBtn = document.getElementById('reset-layout');
                        
                        // Initialize Cytoscape
                        const cy = cytoscape({{
                            container: graphContainer,
                            style: [
                                {{
                                    selector: 'node',
                                    style: {{
                                        'label': 'data(name)',
                                        'text-valign': 'center',
                                        'text-halign': 'center',
                                        'background-color': function(ele) {{
                                            const type = ele.data('type');
                                            switch(type) {{
                                                case 'config': return '#8dd3c7';
                                                case 'api': return '#ffffb3';
                                                case 'model': return '#bebada';
                                                case 'service': return '#fb8072';
                                                case 'cli': return '#80b1d3';
                                                default: return '#d9d9d9';
                                            }}
                                        }},
                                        'width': 'label',
                                        'height': 'label',
                                        'padding': '10px',
                                        'shape': 'round-rectangle',
                                        'text-wrap': 'wrap',
                                        'text-max-width': '80px'
                                    }}
                                }},
                                {{
                                    selector: 'edge',
                                    style: {{
                                        'width': 2,
                                        'line-color': function(ele) {{
                                            const type = ele.data('type');
                                            switch(type) {{
                                                case 'inherits': return '#ff7f00';
                                                case 'implements': return '#e41a1c';
                                                case 'depends': return '#377eb8';
                                                case 'uses': return '#4daf4a';
                                                case 'returns': return '#984ea3';
                                                case 'in': return '#999999';
                                                default: return '#999999';
                                            }}
                                        }},
                                        'target-arrow-shape': 'triangle',
                                        'target-arrow-color': function(ele) {{
                                            const type = ele.data('type');
                                            switch(type) {{
                                                case 'inherits': return '#ff7f00';
                                                case 'implements': return '#e41a1c';
                                                case 'depends': return '#377eb8';
                                                case 'uses': return '#4daf4a';
                                                case 'returns': return '#984ea3';
                                                case 'in': return '#999999';
                                                default: return '#999999';
                                            }}
                                        }},
                                        'curve-style': 'bezier',
                                        'label': 'data(type)',
                                        'font-size': '10px',
                                        'text-rotation': 'autorotate'
                                    }}
                                }}
                            ],
                            layout: {{
                                name: 'cose',
                                padding: 50,
                                nodeRepulsion: 8000,
                                idealEdgeLength: 100,
                                edgeElasticity: 100,
                                fit: true
                            }}
                        }});
                        
                        // Add tooltips
                        cy.on('mouseover', 'node', function(e) {{
                            const node = e.target;
                            node.popperRefObj = node.popper({{
                                content: () => {{
                                    const div = document.createElement('div');
                                    div.style.background = 'white';
                                    div.style.padding = '8px';
                                    div.style.borderRadius = '4px';
                                    div.style.boxShadow = '0 2px 4px rgba(0,0,0,0.2)';
                                    div.style.fontSize = '12px';
                                    div.innerHTML = `
                                        <strong>${{node.data('name')}}</strong><br>
                                        Type: ${{node.data('type')}}<br>
                                        Module: ${{node.data('module')}}<br>
                                    `;
                                    return div;
                                }},
                                popper: {{
                                    placement: 'top',
                                    removeOnDestroy: true
                                }}
                            }});
                        }});
                        
                        cy.on('mouseout', 'node', function(e) {{
                            const node = e.target;
                            if (node.popperRefObj) {{
                                node.popperRefObj.destroy();
                                node.popperRefObj = null;
                            }}
                        }});
                        
                        cy.on('mouseover', 'edge', function(e) {{
                            const edge = e.target;
                            if (edge.data('description')) {{
                                edge.popperRefObj = edge.popper({{
                                    content: () => {{
                                        const div = document.createElement('div');
                                        div.style.background = 'white';
                                        div.style.padding: '8px';
                                        div.style.borderRadius = '4px';
                                        div.style.boxShadow = '0 2px 4px rgba(0,0,0,0.2)';
                                        div.style.fontSize: '12px';
                                        div.innerHTML = edge.data('description');
                                        return div;
                                    }},
                                    popper: {{
                                        placement: 'top',
                                        removeOnDestroy: true
                                    }}
                                }});
                            }}
                        }});
                        
                        cy.on('mouseout', 'edge', function(e) {{
                            const edge = e.target;
                            if (edge.popperRefObj) {{
                                edge.popperRefObj.destroy();
                                edge.popperRefObj = null;
                            }}
                        }});
                        
                        // Load graph data
                        loadGraphData();
                        
                        async function loadGraphData(typeFilters = [], moduleFilters = []) {{
                            let url = '/api/graph';
                            const params = new URLSearchParams();
                            
                            if (typeFilters.length > 0 && !typeFilters.includes('all')) {{
                                typeFilters.forEach(t => params.append('types', t));
                            }}
                            
                            if (moduleFilters.length > 0 && !moduleFilters.includes('all')) {{
                                moduleFilters.forEach(m => params.append('modules', m));
                            }}
                            
                            if (params.toString()) {{
                                url += '?' + params.toString();
                            }}
                            
                            try {{
                                const response = await fetch(url);
                                const data = await response.json();
                                
                                // Update module filter options
                                const modules = new Set();
                                data.nodes.forEach(node => {{
                                    if (node.module) {{
                                        const parts = node.module.split('.');
                                        let currentPath = '';
                                        for (const part of parts) {{
                                            currentPath = currentPath ? `${{currentPath}}.${{part}}` : part;
                                            modules.add(currentPath);
                                        }}
                                        modules.add(node.module);
                                    }}
                                }});
                                
                                // Only update options on first load
                                if (moduleFilter.options.length <= 1) {{
                                    Array.from(modules).sort().forEach(module => {{
                                        const option = document.createElement('option');
                                        option.value = module;
                                        option.textContent = module;
                                        moduleFilter.appendChild(option);
                                    }});
                                }}
                                
                                // Load the graph
                                cy.elements().remove();
                                cy.add({{
                                    nodes: data.nodes.map(n => ({{
                                        data: {{ 
                                            id: n.id, 
                                            name: n.name,
                                            type: n.type,
                                            module: n.module
                                        }}
                                    }})),
                                    edges: data.edges.map(e => ({{
                                        data: {{ 
                                            id: `${{e.source}}-${{e.target}}-${{e.type}}`,
                                            source: e.source, 
                                            target: e.target,
                                            type: e.type,
                                            weight: e.weight,
                                            description: e.description
                                        }}
                                    }}))
                                }});
                                
                                // Apply layout
                                const layout = cy.layout({{
                                    name: 'cose',
                                    padding: 50,
                                    nodeRepulsion: 8000,
                                    idealEdgeLength: 100,
                                    edgeElasticity: 100,
                                    fit: true
                                }});
                                layout.run();
                            }} catch (error) {{
                                console.error('Error loading graph data:', error);
                            }}
                        }}
                        
                        // Set up filter controls
                        applyFiltersBtn.addEventListener('click', () => {{
                            const selectedTypes = Array.from(typeFilter.selectedOptions).map(opt => opt.value);
                            const selectedModules = Array.from(moduleFilter.selectedOptions).map(opt => opt.value);
                            loadGraphData(selectedTypes, selectedModules);
                        }});
                        
                        resetFiltersBtn.addEventListener('click', () => {{
                            typeFilter.value = 'all';
                            moduleFilter.value = 'all';
                            loadGraphData();
                        }});
                        
                        resetLayoutBtn.addEventListener('click', () => {{
                            const layout = cy.layout({{
                                name: 'cose',
                                padding: 50,
                                nodeRepulsion: 8000,
                                idealEdgeLength: 100,
                                edgeElasticity: 100,
                                fit: true
                            }});
                            layout.run();
                        }});
                    }});
                </script>
            </body>
            </html>
            """
            return html

        # API Playground route
        @self.app.get("/api-playground/{name}", response_class=HTMLResponse)
        async def get_api_playground(name: str, request: Request):
            """Get API playground page for a specific endpoint."""
            if not self.config.enable_api_playground:
                raise HTTPException(
                    status_code=404, detail="API Playground is not enabled"
                )

            # Find the API endpoint
            endpoint_item = None
            for module_name in self.config.module_names:
                items = await discover_documentable_items(module_name)
                for item in items:
                    if (
                        item.schema_info.name.lower() == name.lower()
                        and item.schema_info.type == DocumentationType.API
                    ):
                        endpoint_item = item
                        break
                if endpoint_item:
                    break

            if not endpoint_item:
                raise HTTPException(
                    status_code=404, detail=f"API endpoint '{name}' not found"
                )

            # Determine base URL for API calls
            base_url = self.config.api_playground_base_url
            if not base_url:
                # Try to determine base URL from request
                host = request.headers.get("host", "localhost:8000")
                scheme = request.headers.get("x-forwarded-proto", "http")
                base_url = f"{scheme}://{host}"

            # Generate API playground HTML
            playground_html = await generate_api_playground_html(
                endpoint_item, base_url
            )

            # Create full page HTML
            html = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <title>{self.config.title} - API Playground - {name}</title>
                <meta charset="utf-8">
                <meta name="viewport" content="width=device-width, initial-scale=1">
                <style>
                    body {{
                        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
                        line-height: 1.5;
                        margin: 0;
                        padding: 0;
                        color: #333;
                    }}
                    .container {{
                        max-width: 1200px;
                        margin: 0 auto;
                        padding: 20px;
                    }}
                    .header {{
                        margin-bottom: 20px;
                        padding-bottom: 10px;
                        border-bottom: 1px solid #eee;
                    }}
                    .header h1 {{
                        margin: 0;
                    }}
                    .breadcrumb {{
                        margin-bottom: 20px;
                    }}
                    .breadcrumb a {{
                        color: #0366d6;
                        text-decoration: none;
                    }}
                    .breadcrumb a:hover {{
                        text-decoration: underline;
                    }}
                </style>
            </head>
            <body>
                <div class="container">
                    <div class="header">
                        <h1>API Playground - {name}</h1>
                    </div>
                    <div class="breadcrumb">
                        <a href="/">Home</a> &raquo; 
                        <a href="/api/{name}.html">API: {name}</a> &raquo; 
                        Playground
                    </div>
                    <div class="content">
                        {playground_html}
                    </div>
                </div>
            </body>
            </html>
            """
            return html

        # API Endpoint execution
        @self.app.post("/api/playground/execute")
        async def execute_endpoint(
            request: ApiExecutionRequest,
        ) -> ApiExecutionResponse:
            """Execute an API endpoint call."""
            if not self.config.enable_api_playground:
                raise HTTPException(
                    status_code=404, detail="API Playground is not enabled"
                )

            # Execute the request
            return await execute_api_call(request)

        # Serve static files for the MkDocs site (lower priority than API routes)
        self.app.mount(
            "/", StaticFiles(directory=self.temp_dir / "site", html=True), name="docs"
        )

    async def build_docs(self) -> None:
        """Build the documentation using MkDocs."""
        # Collect all items
        all_items = []
        for module_name in self.config.module_names:
            items = await discover_documentable_items(module_name)
            all_items.extend(items)

        # Generate MkDocs site
        provider = MkDocsProvider()
        await provider.generate(
            all_items,
            output_path=str(self.temp_dir),
            site_name=self.config.title,
            theme=self.config.theme,
            build=True,
            enable_search=self.config.enable_search,
            syntax_highlighting=self.config.syntax_highlighting,
            highlight_theme=self.config.highlight_theme,
        )

    async def watch_for_changes(self) -> None:
        """Watch for changes in source files and rebuild docs."""
        if not self.config.watch_paths:
            return

        self.running = True

        # Get initial modified times
        for path in self.config.watch_paths:
            self._update_modified_times(Path(path))

        while self.running:
            changes_detected = False

            # Check all paths for changes
            for path in self.config.watch_paths:
                if self._check_for_changes(Path(path)):
                    changes_detected = True

            # Rebuild if changes detected
            if changes_detected:
                print("Changes detected, rebuilding documentation...")
                await self.build_docs()

            # Wait before checking again
            await asyncio.sleep(self.config.poll_interval)

    def _update_modified_times(self, path: Path) -> None:
        """Update the last modified times for all files."""
        if path.is_file() and path.suffix == ".py":
            self.last_modified_times[str(path)] = path.stat().st_mtime
        elif path.is_dir():
            for item in path.iterdir():
                self._update_modified_times(item)

    def _check_for_changes(self, path: Path) -> bool:
        """Check if any files have changed."""
        changes = False

        if path.is_file() and path.suffix == ".py":
            current_mtime = path.stat().st_mtime
            last_mtime = self.last_modified_times.get(str(path), 0)

            if current_mtime > last_mtime:
                self.last_modified_times[str(path)] = current_mtime
                changes = True

        elif path.is_dir():
            for item in path.iterdir():
                if self._check_for_changes(item):
                    changes = True

        return changes

    async def run(self) -> None:
        """Run the documentation server."""
        # Build initial docs
        await self.build_docs()

        # Start file watcher
        watcher_task = asyncio.create_task(self.watch_for_changes())

        # Register signal handlers
        for sig in (signal.SIGINT, signal.SIGTERM):
            signal.signal(sig, self._handle_exit)

        # Import uvicorn here to avoid dependency issues
        import uvicorn

        # Start the server
        config = uvicorn.Config(
            app=self.app,
            host=self.config.host,
            port=self.config.port,
        )
        server = uvicorn.Server(config)
        await server.serve()

        # Clean up
        watcher_task.cancel()
        self._cleanup()

    def _handle_exit(self, sig, frame):
        """Handle exit signals."""
        print("Shutting down documentation server...")
        self.running = False
        self._cleanup()
        sys.exit(0)

    def _cleanup(self) -> None:
        """Clean up temporary files."""
        try:
            import shutil

            shutil.rmtree(self.temp_dir)
        except Exception as e:
            print(f"Error cleaning up temporary files: {e}")


async def start_doc_server(config: DocServerConfig) -> None:
    """Start a documentation server with the given configuration."""
    server = DocServer(config)
    await server.run()
