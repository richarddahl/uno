#!/bin/bash
# SPDX-FileCopyrightText: 2024-present Richard Dahl <richard@dahl.us>
# SPDX-License-Identifier: MIT

# This script adds an SPDX copyright and license header to all Python files
# in the repo that do not already contain one.

HEADER="# SPDX-FileCopyrightText: 2024-present Richard Dahl <richard@dahl.us>\n# SPDX-License-Identifier: MIT\n# uno framework"

find . -type f -name '*.py' | while read -r file; do
    # Check if the file already contains the SPDX header (in first 5 lines)
    if ! head -n 5 "$file" | grep -q 'SPDX-FileCopyrightText'; then
        echo "Adding SPDX header to $file"
        # Insert the header after a shebang if present, otherwise at the top
        if head -n 1 "$file" | grep -q '^#!'; then
            # Preserve shebang, then insert header
            (head -n 1 "$file"; echo -e "$HEADER"; tail -n +2 "$file") > "$file.tmp" && mv "$file.tmp" "$file"
        else
            # No shebang, insert header at the top
            (echo -e "$HEADER"; cat "$file") > "$file.tmp" && mv "$file.tmp" "$file"
        fi
    fi
done

echo "SPDX headers added where missing."
