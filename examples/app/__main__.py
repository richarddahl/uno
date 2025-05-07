# SPDX-FileCopyrightText: 2025-present Richard Dahl <richard@dahl.us>
# SPDX-License-Identifier: MIT
"""
Uno Integrated Example App Entrypoint

Starts the FastAPI demo app for the InventoryItem vertical slice.
Extend this to add more aggregates, endpoints, and demo logic.
"""

import uvicorn

from examples.app.api.api import app_factory
import asyncio

async def create_app():
    return await app_factory()

if __name__ == "__main__":
    app = asyncio.run(create_app())
    uvicorn.run(app, host="0.0.0.0", port=8000)
    uvicorn.run(app, host="127.0.0.1", port=8000)
