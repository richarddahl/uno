# SPDX-FileCopyrightText: 2025-present Richard Dahl <richard@dahl.us>
# SPDX-License-Identifier: MIT
"""
Uno Integrated Example App Entrypoint

Starts the FastAPI demo app for the InventoryItem vertical slice.
Extend this to add more aggregates, endpoints, and demo logic.
"""

import asyncio
import uvicorn

from examples.app.api.api import app_factory


async def create_app():
    """Create and configure the FastAPI application."""
    return await app_factory()


if __name__ == "__main__":
    # Get the app using asyncio.run to handle the async factory
    app = asyncio.run(create_app())

    # Run the app with uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
