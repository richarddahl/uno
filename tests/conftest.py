# SPDX-FileCopyrightText: 2024-present Richard Dahl <richard@dahl.us>
# SPDX-License-Identifier: MIT
# uno framework
import sys
from pathlib import Path

# Ensure the src directory is on sys.path so local uno package is imported
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
