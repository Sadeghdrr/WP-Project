"""
core.domain.exceptions — Domain-specific exception hierarchy.

These exceptions represent business-rule violations inside service layers.
They are deliberately **not** DRF exceptions so that the domain layer stays
framework-agnostic.  A global DRF exception handler (or per-view try/except)
maps them to the appropriate ``rest_framework.exceptions.APIException``
subclass.

Mapping cheatsheet
------------------
┌─────────────────────┬──────────────────────────────┬──────┐
│ Domain Exception    │ DRF / HTTP equivalent        │ Code │
├─────────────────────┼──────────────────────────────┼──────┤
│ DomainError         │ ValidationError / 400        │ 400  │
│ PermissionDenied    │ PermissionDenied / 403       │ 403  │
│ NotFound            │ NotFound / 404               │ 404  │
│ Conflict            │ APIException / 409           │ 409  │
│ InvalidTransition   │ APIException / 409           │ 409  │
└─────────────────────┴──────────────────────────────┴──────┘

Recommended usage inside a service::

    from core.domain.exceptions import InvalidTransition

    if new_status not in ALLOWED_TRANSITIONS[current_status]:
        raise InvalidTransition(
            f"Cannot move from {current_status} to {new_status}."
        )

Global exception handler (register in settings or a middleware)::

    from rest_framework.views import exception_handler as drf_handler
    from rest_framework.exceptions import (
        ValidationError, PermissionDenied as DRFPermissionDenied,
        NotFound as DRFNotFound,
    )
    from rest_framework.response import Response
    from core.domain.exceptions import (
        DomainError, PermissionDenied, NotFound, Conflict, InvalidTransition,
    )

    _MAPPING = {
        DomainError:       (ValidationError, 400),
        PermissionDenied:  (DRFPermissionDenied, 403),
        NotFound:          (DRFNotFound, 404),
        Conflict:          (None, 409),
        InvalidTransition: (None, 409),
    }

    def domain_exception_handler(exc, context):
        # Let DRF handle its own exceptions first
        response = drf_handler(exc, context)
        if response is not None:
            return response

        for domain_cls, (_, status) in _MAPPING.items():
            if isinstance(exc, domain_cls):
                return Response(
                    {"detail": str(exc)},
                    status=status,
                )
        return None
"""

from __future__ import annotations


class DomainError(Exception):
    """
    Base class for all domain / business-rule errors.

    Catch this at the view boundary and convert to a 400 Bad Request.
    """

    def __init__(self, message: str = "A business rule was violated.") -> None:
        self.message = message
        super().__init__(self.message)


class PermissionDenied(DomainError):
    """
    The authenticated user does not have the required role or permission
    for this operation.

    Maps to HTTP 403.
    """

    def __init__(self, message: str = "You do not have permission to perform this action.") -> None:
        super().__init__(message)


class NotFound(DomainError):
    """
    The requested resource does not exist (or is not visible to the
    requesting user given their role scope).

    Maps to HTTP 404.
    """

    def __init__(self, message: str = "The requested resource was not found.") -> None:
        super().__init__(message)


class Conflict(DomainError):
    """
    The operation conflicts with the current state of the resource.

    Typical usage: duplicate creation attempt, optimistic-lock failure.
    Maps to HTTP 409.
    """

    def __init__(self, message: str = "The operation conflicts with the current state.") -> None:
        super().__init__(message)


class InvalidTransition(Conflict):
    """
    A state-machine transition that is not allowed from the current status.

    Inherits from ``Conflict`` because an invalid transition IS a conflict
    with the resource's current state.  Maps to HTTP 409.

    Example::

        raise InvalidTransition(
            current="pending_review",
            target="closed",
            reason="Case must be approved before closing.",
        )
    """

    def __init__(
        self,
        message: str | None = None,
        *,
        current: str | None = None,
        target: str | None = None,
        reason: str | None = None,
    ) -> None:
        if message is None:
            parts = ["Invalid state transition"]
            if current and target:
                parts.append(f"from '{current}' to '{target}'")
            if reason:
                parts.append(f"— {reason}")
            message = " ".join(parts) + "."
        super().__init__(message)
        self.current = current
        self.target = target
        self.reason = reason
