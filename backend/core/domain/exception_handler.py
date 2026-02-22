"""
core.domain.exception_handler — DRF-compatible global exception handler.

Maps domain exceptions from ``core.domain.exceptions`` to proper
DRF ``Response`` objects so that views don't need per-endpoint
try/except boilerplate.

Register in ``settings.py``::

    REST_FRAMEWORK = {
        ...
        'EXCEPTION_HANDLER': 'core.domain.exception_handler.domain_exception_handler',
    }
"""

from __future__ import annotations

import logging

from rest_framework.response import Response
from rest_framework.views import exception_handler as drf_default_handler

from core.domain.exceptions import (
    Conflict,
    DomainError,
    InvalidTransition,
    NotFound,
    PermissionDenied,
)

logger = logging.getLogger(__name__)

# Domain exception → HTTP status code
_STATUS_MAP: dict[type, int] = {
    PermissionDenied:  403,
    NotFound:          404,
    InvalidTransition: 409,
    Conflict:          409,
    DomainError:       400,  # catch-all base class last
}


def domain_exception_handler(exc: Exception, context: dict) -> Response | None:
    """
    DRF exception handler that also handles ``core.domain.exceptions``.

    The default DRF handler is called first.  If it returns ``None``
    (meaning DRF doesn't recognise the exception), we check whether
    it's one of our domain exceptions and return an appropriate response.
    """
    # Let DRF handle its own exceptions (ValidationError, AuthN, etc.)
    response = drf_default_handler(exc, context)
    if response is not None:
        return response

    # Check domain exceptions (order matters — most specific first)
    for exc_class, status_code in _STATUS_MAP.items():
        if isinstance(exc, exc_class):
            logger.warning(
                "Domain exception [%s] in %s: %s",
                exc_class.__name__,
                context.get("view", "unknown"),
                exc,
            )
            return Response(
                {"detail": str(exc)},
                status=status_code,
            )

    # Not our exception — let it propagate
    return None
