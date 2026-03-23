"""Shared logging utilities."""


def log_progress(prefix: str, msg: str):
    """Print a progress message with a module prefix."""
    print(f"[{prefix}] {msg}", flush=True)
