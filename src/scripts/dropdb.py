# SPDX-FileCopyrightText: 2024-present Richard Dahl <richard@dahl.us>
#
# SPDX-License-Identifier: MIT

# SPDX-FileCopyrightText: 2024-present Richard Dahl <richard@dahl.us>
# SPDX-License-Identifier: MIT

import asyncio

from uno.infrastructure.database.manager import DBManager


if __name__ == "__main__":
    db_manager = DBManager()
    db_manager.drop_db()
