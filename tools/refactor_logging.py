#!/usr/bin/env python3
"""
Automated refactor script to update codebase to use the central logger abstraction.
- Replaces `logging.getLogger(...)` with `get_logger(...)` from uno.core.logging.logger
- Adds import for get_logger if missing
- Optionally warns on direct use of logging.basicConfig

Usage:
    python tools/refactor_logging.py [--dry-run]

Set --dry-run to preview changes without modifying files.
"""
import os
import re
import sys
import argparse
from pathlib import Path

SRC_ROOT = Path(__file__).resolve().parent.parent / "src"
LOGGER_IMPORT = "from uno.core.logging.logger import get_logger"

GETLOGGER_PATTERN = re.compile(r"logging\.getLogger\(([^)]*)\)")
BASICCONFIG_PATTERN = re.compile(r"logging\.basicConfig\(")


def refactor_file(path: Path, dry_run: bool = False) -> bool:
    """Refactor a single Python file. Returns True if file was changed."""
    with open(path, "r", encoding="utf-8") as f:
        lines = f.readlines()
    changed = False
    new_lines = []
    has_logger_import = any(LOGGER_IMPORT in l for l in lines)
    for line in lines:
        # Replace logging.getLogger(...) with get_logger(...)
        m = GETLOGGER_PATTERN.search(line)
        if m:
            # Preserve the argument (e.g., __name__)
            arg = m.group(1).strip()
            new_line = GETLOGGER_PATTERN.sub(f"get_logger({arg})", line)
            new_lines.append(new_line)
            changed = True
            continue
        # Warn on logging.basicConfig
        if BASICCONFIG_PATTERN.search(line):
            print(f"[WARN] {path}: direct use of logging.basicConfig")
        new_lines.append(line)
    # Add import if needed
    if changed and not has_logger_import:
        # Find first import line
        for i, l in enumerate(new_lines):
            if l.startswith("import") or l.startswith("from"):
                new_lines.insert(i, LOGGER_IMPORT + "\n")
                break
        else:
            new_lines.insert(0, LOGGER_IMPORT + "\n")
    if changed and not dry_run:
        # Backup original
        path.with_suffix(path.suffix + ".bak").write_text("".join(lines), encoding="utf-8")
        # Write modified
        with open(path, "w", encoding="utf-8") as f:
            f.writelines(new_lines)
    return changed


def main():
    parser = argparse.ArgumentParser(description="Refactor logging to use central logger.")
    parser.add_argument("--dry-run", action="store_true", help="Show what would change, don't modify files.")
    args = parser.parse_args()
    
    for root, dirs, files in os.walk(SRC_ROOT):
        for fname in files:
            if fname.endswith(".py"):
                fpath = Path(root) / fname
                changed = refactor_file(fpath, dry_run=args.dry_run)
                if changed:
                    print(f"[UPDATED] {fpath}")

if __name__ == "__main__":
    main()
