# SPDX-FileCopyrightText: 2024-present Richard Dahl <richard@dahl.us>
# SPDX-License-Identifier: MIT
# SPDX-Package-Name: uno framework
"""
Landing page generator for documentation.

This module provides utilities to create customizable landing pages for
the documentation site.
"""

from __future__ import annotations

import asyncio
import re
from pathlib import Path
from typing import Any

import markdown
from pydantic import BaseModel, Field

from uno.docs.schema import DocumentationType


class LandingPageSection(BaseModel):
    """Configuration for a section on the landing page."""

    title: str
    content: str = ""  # Markdown content
    type: str = "markdown"  # markdown, components, links, etc.
    doc_types: list[DocumentationType] | None = None  # For component listing
    include_modules: list[str] | None = None  # For component listing
    exclude_modules: list[str] | None = None  # For component listing
    links: list[dict[str, str]] | None = None  # For links section
    image_url: str | None = None  # Optional image
    order: int = 0  # Order in the page
    extra: dict[str, Any] = Field(default_factory=dict)  # Extra settings


class LandingPageConfig(BaseModel):
    """Configuration for the documentation landing page."""

    title: str = "Documentation"
    subtitle: str = "Explore the API and components"
    description: str = ""  # Overall page description
    sections: list[LandingPageSection] = Field(default_factory=list)
    quick_links: list[dict[str, str]] = Field(default_factory=list)
    theme: dict[str, str] = Field(default_factory=dict)  # Theme customization
    logo_url: str | None = None  # Optional logo
    footer_text: str | None = None  # Footer content
    include_stats: bool = True  # Show component statistics
    include_search: bool = True  # Show search box
    include_navigation: bool = True  # Show navigation links


async def generate_landing_page(
    config: LandingPageConfig,
    all_items: list[Any] | None = None,
    base_url: str = "/",
) -> str:
    """
    Generate the HTML for a customized landing page.

    Args:
        config: Landing page configuration
        all_items: Documentable items from the system
        base_url: Base URL for links

    Returns:
        HTML for the landing page
    """
    # Extract components by type
    components_by_type = {}
    if all_items:
        for item in all_items:
            schema = item.schema_info
            item_type = schema.type.value
            if item_type not in components_by_type:
                components_by_type[item_type] = []
            components_by_type[item_type].append(item)

    # Generate section HTML
    section_html = ""

    # Sort sections by order
    sorted_sections = sorted(config.sections, key=lambda s: s.order)

    for section in sorted_sections:
        # Skip empty sections
        if not section.content and section.type == "markdown":
            continue

        section_html += f"<section class='landing-section'>\n"
        section_html += f"<h2>{section.title}</h2>\n"

        # Different section types
        if section.type == "markdown":
            # Render markdown to HTML
            content_html = markdown.markdown(
                section.content, extensions=["tables", "fenced_code"]
            )
            section_html += f"<div class='markdown-content'>\n{content_html}\n</div>\n"

        elif section.type == "components":
            # Component listing
            section_html += "<div class='component-grid'>\n"

            # Filter component types
            types_to_show = section.doc_types or list(
                map(DocumentationType, components_by_type.keys())
            )

            for comp_type in types_to_show:
                # Skip if no components of this type
                if comp_type.value not in components_by_type:
                    continue

                components = components_by_type[comp_type.value]

                # Apply module filters
                if section.include_modules:
                    components = [
                        c
                        for c in components
                        if any(
                            c.schema_info.module.startswith(m)
                            for m in section.include_modules
                        )
                    ]

                if section.exclude_modules:
                    components = [
                        c
                        for c in components
                        if not any(
                            c.schema_info.module.startswith(m)
                            for m in section.exclude_modules
                        )
                    ]

                # Skip if no components after filtering
                if not components:
                    continue

                section_html += f"<div class='component-type'>\n"
                section_html += f"<h3>{comp_type.value.title()}</h3>\n"
                section_html += "<ul class='component-list'>\n"

                # Sort components by name
                sorted_components = sorted(components, key=lambda c: c.schema_info.name)

                for component in sorted_components:
                    name = component.schema_info.name
                    desc = component.schema_info.description
                    # Truncate description if needed
                    if len(desc) > 100:
                        desc = desc[:97] + "..."

                    # Create link to component doc
                    link = f"{base_url}{comp_type.value}/{name}.html"

                    section_html += "<li class='component-item'>\n"
                    section_html += f"<a href='{link}' class='component-link'>\n"
                    section_html += f"<span class='component-name'>{name}</span>\n"
                    section_html += f"<span class='component-desc'>{desc}</span>\n"
                    section_html += "</a>\n</li>\n"

                section_html += "</ul>\n</div>\n"

            section_html += "</div>\n"

        elif section.type == "links":
            # Links display
            if section.links:
                section_html += "<div class='links-grid'>\n"

                for link in section.links:
                    title = link.get("title", "Link")
                    url = link.get("url", "#")
                    description = link.get("description", "")
                    icon = link.get("icon", "")

                    section_html += "<div class='link-card'>\n"

                    if icon:
                        section_html += f"<div class='link-icon'>{icon}</div>\n"

                    section_html += (
                        f"<h3 class='link-title'><a href='{url}'>{title}</a></h3>\n"
                    )

                    if description:
                        section_html += f"<p class='link-desc'>{description}</p>\n"

                    section_html += "</div>\n"

                section_html += "</div>\n"

        section_html += "</section>\n"

    # Generate quick links bar
    quick_links_html = ""
    if config.quick_links:
        quick_links_html = "<div class='quick-links'>\n<ul>\n"

        for link in config.quick_links:
            title = link.get("title", "Link")
            url = link.get("url", "#")
            icon = link.get("icon", "")

            quick_links_html += "<li>\n"

            if icon:
                quick_links_html += f"<span class='link-icon'>{icon}</span>\n"

            quick_links_html += f"<a href='{url}'>{title}</a>\n"
            quick_links_html += "</li>\n"

        quick_links_html += "</ul>\n</div>\n"

    # Generate component statistics
    stats_html = ""
    if config.include_stats and all_items:
        # Count components by type
        stats = {}
        for key, items in components_by_type.items():
            stats[key] = len(items)

        total_components = sum(stats.values())

        stats_html = "<div class='component-stats'>\n"
        stats_html += f"<div class='stat-item'><span class='stat-value'>{total_components}</span> <span class='stat-label'>Total Components</span></div>\n"

        for comp_type, count in stats.items():
            stats_html += f"<div class='stat-item'><span class='stat-value'>{count}</span> <span class='stat-label'>{comp_type.title()}s</span></div>\n"

        stats_html += "</div>\n"

    # Generate search box
    search_html = ""
    if config.include_search:
        search_html = """
        <div class="search-container">
            <form action="/search" method="get">
                <input type="text" name="q" placeholder="Search documentation..." class="search-input">
                <button type="submit" class="search-button">Search</button>
            </form>
        </div>
        """

    # Generate navigation bar
    nav_html = ""
    if config.include_navigation:
        nav_items = [
            {"title": "Search", "url": "/search"},
            {"title": "Components", "url": "#components"},
            {"title": "APIs", "url": "#apis"},
            {"title": "Visualize", "url": "/relationships"},
        ]

        nav_html = "<nav class='main-nav'>\n<ul>\n"

        for item in nav_items:
            nav_html += f"<li><a href='{item['url']}'>{item['title']}</a></li>\n"

        nav_html += "</ul>\n</nav>\n"

    # Extract theme settings with defaults
    theme = {
        "primary_color": "#0366d6",
        "secondary_color": "#28a745",
        "background_color": "#ffffff",
        "text_color": "#24292e",
        "heading_color": "#24292e",
        "accent_color": "#f9826c",
        "link_color": "#0366d6",
        "font_family": "-apple-system, BlinkMacSystemFont, 'Segoe UI', Helvetica, Arial, sans-serif",
        "heading_font": "-apple-system, BlinkMacSystemFont, 'Segoe UI', Helvetica, Arial, sans-serif",
    }

    # Override with user settings
    if config.theme:
        theme.update(config.theme)

    # Combine all parts to create the final HTML
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>{config.title}</title>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <style>
            :root {{
                --primary-color: {theme['primary_color']};
                --secondary-color: {theme['secondary_color']};
                --background-color: {theme['background_color']};
                --text-color: {theme['text_color']};
                --heading-color: {theme['heading_color']};
                --accent-color: {theme['accent_color']};
                --link-color: {theme['link_color']};
                --light-bg: #f6f8fa;
                --border-color: #e1e4e8;
                --card-shadow: 0 2px 4px rgba(0,0,0,0.1);
            }}
            
            body, html {{
                margin: 0;
                padding: 0;
                font-family: {theme['font_family']};
                color: var(--text-color);
                background-color: var(--background-color);
                line-height: 1.6;
            }}
            
            .container {{
                max-width: 1200px;
                margin: 0 auto;
                padding: 0 20px;
            }}
            
            /* Header */
            header {{
                background-color: var(--primary-color);
                color: white;
                padding: 40px 0;
                text-align: center;
            }}
            
            header h1 {{
                margin: 0;
                font-size: 2.5rem;
                font-weight: 600;
                font-family: {theme['heading_font']};
            }}
            
            header p.subtitle {{
                font-size: 1.2rem;
                margin: 10px 0 0;
                opacity: 0.9;
            }}
            
            /* Navigation */
            .main-nav {{
                background-color: var(--primary-color);
                padding: 10px 0;
                border-bottom: 1px solid rgba(255,255,255,0.1);
            }}
            
            .main-nav ul {{
                display: flex;
                list-style: none;
                margin: 0;
                padding: 0;
                justify-content: center;
            }}
            
            .main-nav li {{
                margin: 0 15px;
            }}
            
            .main-nav a {{
                color: white;
                text-decoration: none;
                font-weight: 500;
                transition: opacity 0.2s;
            }}
            
            .main-nav a:hover {{
                opacity: 0.8;
            }}
            
            /* Quick Links */
            .quick-links {{
                background-color: var(--light-bg);
                padding: 15px 0;
                border-bottom: 1px solid var(--border-color);
            }}
            
            .quick-links ul {{
                display: flex;
                list-style: none;
                margin: 0;
                padding: 0;
                justify-content: center;
                flex-wrap: wrap;
            }}
            
            .quick-links li {{
                margin: 5px 15px;
                display: flex;
                align-items: center;
            }}
            
            .quick-links a {{
                color: var(--link-color);
                text-decoration: none;
                font-weight: 500;
                transition: color 0.2s;
            }}
            
            .quick-links a:hover {{
                text-decoration: underline;
            }}
            
            .quick-links .link-icon {{
                margin-right: 8px;
            }}
            
            /* Search */
            .search-container {{
                display: flex;
                justify-content: center;
                padding: 30px 20px;
                background-color: var(--light-bg);
                border-bottom: 1px solid var(--border-color);
            }}
            
            .search-input {{
                width: 600px;
                max-width: 100%;
                padding: 12px 15px;
                font-size: 16px;
                border: 1px solid var(--border-color);
                border-radius: 4px 0 0 4px;
                outline: none;
            }}
            
            .search-input:focus {{
                border-color: var(--primary-color);
            }}
            
            .search-button {{
                background-color: var(--primary-color);
                color: white;
                border: none;
                padding: 12px 20px;
                font-size: 16px;
                cursor: pointer;
                border-radius: 0 4px 4px 0;
            }}
            
            .search-button:hover {{
                background-color: #0256b9;
            }}
            
            /* Component Stats */
            .component-stats {{
                display: flex;
                justify-content: center;
                flex-wrap: wrap;
                padding: 30px 0;
                background-color: white;
                border-bottom: 1px solid var(--border-color);
            }}
            
            .stat-item {{
                text-align: center;
                margin: 0 20px;
                min-width: 120px;
            }}
            
            .stat-value {{
                display: block;
                font-size: 2.5rem;
                font-weight: 600;
                color: var(--primary-color);
            }}
            
            .stat-label {{
                font-size: 1rem;
                color: #6a737d;
            }}
            
            /* Sections */
            .landing-section {{
                padding: 40px 0;
                border-bottom: 1px solid var(--border-color);
            }}
            
            .landing-section h2 {{
                margin-top: 0;
                margin-bottom: 20px;
                color: var(--heading-color);
                font-size: 1.8rem;
                font-weight: 600;
                font-family: {theme['heading_font']};
            }}
            
            /* Markdown Content */
            .markdown-content {{
                line-height: 1.6;
            }}
            
            .markdown-content h1, 
            .markdown-content h2, 
            .markdown-content h3, 
            .markdown-content h4, 
            .markdown-content h5, 
            .markdown-content h6 {{
                color: var(--heading-color);
                font-family: {theme['heading_font']};
                margin-top: 1.5em;
                margin-bottom: 0.5em;
            }}
            
            .markdown-content a {{
                color: var(--link-color);
                text-decoration: none;
            }}
            
            .markdown-content a:hover {{
                text-decoration: underline;
            }}
            
            .markdown-content code {{
                background-color: #f6f8fa;
                padding: 0.2em 0.4em;
                border-radius: 3px;
                font-family: SFMono-Regular, Consolas, "Liberation Mono", Menlo, monospace;
                font-size: 85%;
            }}
            
            .markdown-content pre {{
                background-color: #f6f8fa;
                border-radius: 6px;
                padding: 16px;
                overflow: auto;
            }}
            
            .markdown-content pre code {{
                background-color: transparent;
                padding: 0;
            }}
            
            .markdown-content blockquote {{
                margin: 1em 0;
                border-left: 3px solid var(--border-color);
                padding-left: 1em;
                color: #6a737d;
            }}
            
            .markdown-content img {{
                max-width: 100%;
                border-radius: 6px;
            }}
            
            .markdown-content table {{
                border-collapse: collapse;
                width: 100%;
                margin: 1em 0;
            }}
            
            .markdown-content table th,
            .markdown-content table td {{
                border: 1px solid var(--border-color);
                padding: 8px 12px;
            }}
            
            .markdown-content table th {{
                background-color: var(--light-bg);
                font-weight: 600;
            }}
            
            /* Component Grid */
            .component-grid {{
                display: flex;
                flex-wrap: wrap;
                gap: 30px;
                margin-top: 20px;
            }}
            
            .component-type {{
                flex: 1 0 300px;
            }}
            
            .component-type h3 {{
                margin-top: 0;
                padding-bottom: 8px;
                border-bottom: 1px solid var(--border-color);
                color: var(--heading-color);
                font-weight: 600;
                font-size: 1.2rem;
                font-family: {theme['heading_font']};
            }}
            
            .component-list {{
                list-style: none;
                padding: 0;
                margin: 0;
            }}
            
            .component-item {{
                margin-bottom: 12px;
            }}
            
            .component-link {{
                display: block;
                padding: 12px;
                border-radius: 4px;
                border: 1px solid var(--border-color);
                color: inherit;
                text-decoration: none;
                transition: all 0.2s;
            }}
            
            .component-link:hover {{
                border-color: var(--primary-color);
                box-shadow: var(--card-shadow);
            }}
            
            .component-name {{
                display: block;
                font-weight: 600;
                color: var(--link-color);
                margin-bottom: 4px;
            }}
            
            .component-desc {{
                display: block;
                font-size: 14px;
                color: #6a737d;
            }}
            
            /* Links Grid */
            .links-grid {{
                display: grid;
                grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
                gap: 20px;
                margin-top: 20px;
            }}
            
            .link-card {{
                background-color: white;
                border-radius: 6px;
                border: 1px solid var(--border-color);
                padding: 20px;
                transition: all 0.2s;
            }}
            
            .link-card:hover {{
                border-color: var(--primary-color);
                box-shadow: var(--card-shadow);
            }}
            
            .link-icon {{
                margin-bottom: 15px;
                color: var(--primary-color);
                font-size: 24px;
            }}
            
            .link-title {{
                margin: 0 0 10px;
                font-size: 1.2rem;
            }}
            
            .link-title a {{
                color: var(--heading-color);
                text-decoration: none;
            }}
            
            .link-title a:hover {{
                color: var(--primary-color);
            }}
            
            .link-desc {{
                margin: 0;
                color: #6a737d;
                font-size: 14px;
            }}
            
            /* Footer */
            footer {{
                padding: 40px 0;
                text-align: center;
                background-color: var(--light-bg);
                color: #6a737d;
                font-size: 14px;
            }}
            
            /* Responsive */
            @media (max-width: 768px) {{
                header {{
                    padding: 30px 0;
                }}
                
                header h1 {{
                    font-size: 2rem;
                }}
                
                .search-container {{
                    padding: 20px;
                }}
                
                .landing-section {{
                    padding: 30px 0;
                }}
                
                .component-grid {{
                    display: block;
                }}
                
                .component-type {{
                    margin-bottom: 30px;
                }}
                
                .stat-item {{
                    margin: 10px 15px;
                }}
            }}
        </style>
    </head>
    <body>
        <header>
            <div class="container">
                <h1>{config.title}</h1>
                <p class="subtitle">{config.subtitle}</p>
            </div>
        </header>
        
        {nav_html}
        
        {quick_links_html}
        
        {search_html}
        
        {stats_html}
        
        <div class="container">
            {section_html}
        </div>
        
        <footer>
            <div class="container">
                {config.footer_text or f"© {config.title} Documentation"}
            </div>
        </footer>
    </body>
    </html>
    """

    return html


async def generate_default_landing_page(
    all_items: list[Any],
    title: str = "API Documentation",
    base_url: str = "/",
) -> str:
    """
    Generate a default landing page with standard sections.

    Args:
        all_items: Documentable items from the system
        title: Page title
        base_url: Base URL for links

    Returns:
        HTML for the landing page
    """
    # Create default configuration
    config = LandingPageConfig(
        title=title,
        subtitle="Explore the API and components",
        description="Welcome to the documentation. Browse the components below or use the search to find what you need.",
        include_stats=True,
        include_search=True,
        include_navigation=True,
        quick_links=[
            {
                "title": "APIs",
                "url": "#apis",
                "icon": "📡",
            },
            {
                "title": "Models",
                "url": "#models",
                "icon": "📊",
            },
            {
                "title": "Services",
                "url": "#services",
                "icon": "⚙️",
            },
            {
                "title": "Config",
                "url": "#config",
                "icon": "🔧",
            },
            {
                "title": "Search",
                "url": "/search",
                "icon": "🔍",
            },
            {
                "title": "Visualize",
                "url": "/relationships",
                "icon": "🔗",
            },
        ],
    )

    # Add an introduction section
    intro_section = LandingPageSection(
        title="Introduction",
        type="markdown",
        content="""
        Welcome to the documentation! This site provides comprehensive information about all components, APIs, and services.

        ## Getting Started

        - Browse components by type in the sections below
        - Use the search bar to find specific items
        - Explore the relationships between components with the visualization tool
        
        For API endpoints, you can use the interactive playground to test endpoints directly from the documentation.
        """,
        order=0,
    )
    config.sections.append(intro_section)

    # Add component sections for different types
    component_types = [
        (DocumentationType.API, "APIs", 10),
        (DocumentationType.MODEL, "Models", 20),
        (DocumentationType.SERVICE, "Services", 30),
        (DocumentationType.CONFIG, "Configuration", 40),
        (DocumentationType.CLI, "Command-Line Tools", 50),
    ]

    for doc_type, title, order in component_types:
        section = LandingPageSection(
            title=title,
            type="components",
            doc_types=[doc_type],
            order=order,
        )
        config.sections.append(section)

    # Add a links section
    links_section = LandingPageSection(
        title="Additional Resources",
        type="links",
        links=[
            {
                "title": "Relationships Visualization",
                "url": "/relationships",
                "description": "Visual graph of component relationships and dependencies",
                "icon": "🔗",
            },
            {
                "title": "Search Documentation",
                "url": "/search",
                "description": "Find specific components and documentation",
                "icon": "🔍",
            },
            {
                "title": "API Playground",
                "url": "#apis",
                "description": "Test API endpoints directly from the documentation",
                "icon": "🧪",
            },
        ],
        order=100,
    )
    config.sections.append(links_section)

    # Generate the landing page
    return await generate_landing_page(config, all_items, base_url)
