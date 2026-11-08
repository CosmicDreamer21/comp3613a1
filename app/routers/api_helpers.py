"""Shared helpers for the REST API routers."""

from fastapi import HTTPException

from app.services.errors import ConflictError, NotFoundError


def api_error(exc: Exception) -> HTTPException:
    """Translate a domain error into the matching HTTP error."""
    if isinstance(exc, LookupError):  # includes NotFoundError
        return HTTPException(404, detail=str(exc.args[0]) if exc.args else "Not found")
    if isinstance(exc, ConflictError):
        return HTTPException(409, detail=str(exc))
    return HTTPException(422, detail=str(exc))


__all__ = ["api_error", "ConflictError", "NotFoundError"]
