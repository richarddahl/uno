import sys
from contextlib import contextmanager
from io import StringIO


@contextmanager
def suppress_stdout_stderr():
    """
    Context manager to suppress all output to stdout and stderr.
    Use in tests to silence print/log/plugin output for a code block.
    """
    original_stdout = sys.stdout
    original_stderr = sys.stderr
    sys.stdout = StringIO()
    sys.stderr = StringIO()
    try:
        yield
    finally:
        sys.stdout = original_stdout
        sys.stderr = original_stderr
