# src/memotic/decorators.py
from __future__ import annotations
from functools import wraps
from typing import Callable, Any


def on_any() -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """
    Mark a method to run for any matching event.
    In a richer system, you'd have on_create/on_update, etc.
    """

    def deco(fn: Callable[..., Any]) -> Callable[..., Any]:
        setattr(fn, "_memotic_trigger", "any")

        @wraps(fn)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            return fn(*args, **kwargs)

        return wrapper

    return deco
