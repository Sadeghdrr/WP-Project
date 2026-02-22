"""
core.domain.transactions — Helpers for safe state transitions.

Provides utilities that wrap ``transaction.atomic`` and
``select_for_update`` into reusable patterns so that every app's
service layer follows the same concurrency-safe approach.

Design goals
------------
* Eliminate boilerplate around ``with transaction.atomic(): ...``
  inside service methods.
* Ensure that state-transition reads always lock the row first
  (``select_for_update``) to prevent race conditions.
* Keep the helpers **generic** — they accept any Django ``Model``
  instance and a field name.

Usage::

    from core.domain.transactions import atomic_transition

    updated_case = atomic_transition(
        instance=case,
        status_field="status",
        target_status="under_investigation",
        allowed_sources={"pending_review", "returned_for_revision"},
    )

    # For arbitrary atomic blocks:
    from core.domain.transactions import run_in_atomic

    result = run_in_atomic(my_service_function, arg1, arg2, kwarg=val)
"""

from __future__ import annotations

import functools
from typing import Any, Callable, Iterable, TypeVar

from django.db import models, transaction

from core.domain.exceptions import InvalidTransition, NotFound

T = TypeVar("T")
M = TypeVar("M", bound=models.Model)


def atomic_transition(
    *,
    instance: M,
    status_field: str = "status",
    target_status: str,
    allowed_sources: Iterable[str] | None = None,
    save_fields: Iterable[str] | None = None,
) -> M:
    """
    Atomically transition a model instance from one status to another.

    Steps performed inside ``transaction.atomic()``:
        1. Re-fetch the instance with ``select_for_update()`` to acquire
           a row-level lock.
        2. Read the current value of ``status_field``.
        3. If ``allowed_sources`` is provided, verify the current value
           is among them; raise ``InvalidTransition`` otherwise.
        4. Set ``status_field`` to ``target_status`` and save.
        5. Return the refreshed instance.

    Args:
        instance:        The model instance to transition.
        status_field:    Name of the status CharField/IntegerField on
                         the model.  Defaults to ``"status"``.
        target_status:   The desired new value.
        allowed_sources: Optional set/list of status values from which
                         the transition is permitted.  ``None`` means
                         any current value is accepted (use with care).
        save_fields:     Extra fields to include in the ``save(update_fields=...)``
                         call.  ``status_field`` is always included.

    Returns:
        The same instance with the updated field value persisted.

    Raises:
        NotFound:          If the instance no longer exists in the DB.
        InvalidTransition: If the current status is not in ``allowed_sources``.
    """
    model_class = type(instance)

    with transaction.atomic():
        try:
            locked = (
                model_class.objects
                .select_for_update()
                .get(pk=instance.pk)
            )
        except model_class.DoesNotExist:
            raise NotFound(
                f"{model_class.__name__} with pk={instance.pk} no longer exists."
            )

        current = getattr(locked, status_field)

        if allowed_sources is not None and current not in allowed_sources:
            raise InvalidTransition(
                current=str(current),
                target=target_status,
                reason=(
                    f"Allowed source states: "
                    f"{', '.join(str(s) for s in allowed_sources)}"
                ),
            )

        setattr(locked, status_field, target_status)

        update_fields = {status_field, "updated_at"}
        if save_fields:
            update_fields.update(save_fields)

        locked.save(update_fields=list(update_fields))

    # Refresh caller's reference
    instance.refresh_from_db()
    return instance


def run_in_atomic(fn: Callable[..., T], *args: Any, **kwargs: Any) -> T:
    """
    Execute ``fn(*args, **kwargs)`` inside ``transaction.atomic()``.

    Convenient when a service function should be fully atomic but you
    don't want to decorate the function itself (e.g. because it's a
    method and you want the caller to decide on atomicity).

    Args:
        fn:      Callable to run.
        *args:   Positional arguments forwarded to ``fn``.
        **kwargs: Keyword arguments forwarded to ``fn``.

    Returns:
        Whatever ``fn`` returns.

    Raises:
        Any exception raised by ``fn`` — the transaction is rolled back.
    """
    with transaction.atomic():
        return fn(*args, **kwargs)


def lock_for_update(model_class: type[M], pk: Any) -> M:
    """
    Acquire a row-level lock on the given model instance.

    Convenience wrapper around ``select_for_update().get(pk=pk)``
    that must be called inside an ``atomic()`` block.

    Args:
        model_class: The Django model class.
        pk:          Primary key value.

    Returns:
        The locked model instance.

    Raises:
        NotFound: If no row with that PK exists.
    """
    try:
        return model_class.objects.select_for_update().get(pk=pk)
    except model_class.DoesNotExist:
        raise NotFound(f"{model_class.__name__} with pk={pk} does not exist.")
