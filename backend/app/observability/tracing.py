"""LangSmith @traceable — real when installed, no-op fallback otherwise.

Tracing activation itself is env-var driven (LANGSMITH_TRACING=true) and handled
by langsmith/langchain internals — this module only guards against langsmith
not being installed, so custom (non-LangChain) functions can always use the
same decorator.
"""
from collections.abc import Callable
from typing import Any

try:
    from langsmith import traceable as traceable  # noqa: F401
except ImportError:
    def traceable(*dargs: Any, **dkwargs: Any) -> Callable:
        if dargs and callable(dargs[0]) and not dkwargs:
            return dargs[0]

        def decorator(fn: Callable) -> Callable:
            return fn

        return decorator
