"""Domain errors shared by services and the REST API.

Both subclass ValueError (and NotFoundError also LookupError) so the original
HTML routes, which catch ValueError / LookupError, keep working unchanged.
"""


class ConflictError(ValueError):
    """A request that is valid but clashes with current state (HTTP 409)."""


class NotFoundError(LookupError, ValueError):
    """A referenced resource does not exist or is not visible (HTTP 404)."""
