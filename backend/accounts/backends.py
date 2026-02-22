"""
Custom authentication backend for multi-field login.

Allows users to authenticate using any one of:
``username``, ``national_id``, ``phone_number``, or ``email``
together with their ``password``.

This backend is registered in ``settings.AUTHENTICATION_BACKENDS``
so that Django's ``authenticate()`` call dispatches to it.
"""

from __future__ import annotations

from django.contrib.auth import get_user_model
from django.contrib.auth.backends import ModelBackend
from django.db.models import Q

User = get_user_model()


class MultiFieldAuthBackend(ModelBackend):
    """
    Authenticate against username, national_id, phone_number, or email.

    When ``django.contrib.auth.authenticate(identifier=..., password=...)``
    is called, this backend resolves the user from the ``identifier``
    keyword argument by checking all four unique fields.
    """

    def authenticate(self, request, identifier=None, password=None, **kwargs):
        """
        Resolve the user by *identifier* and verify *password*.

        Parameters
        ----------
        request : HttpRequest | None
        identifier : str
            The value supplied in the login form.  May be a username,
            national ID, phone number, or email address.
        password : str
            The raw password to verify.

        Returns
        -------
        User | None
            The authenticated user, or ``None`` on failure.
        """
        if identifier is None or password is None:
            return None

        try:
            user = User.objects.get(
                Q(username=identifier)
                | Q(national_id=identifier)
                | Q(phone_number=identifier)
                | Q(email=identifier)
            )
        except User.DoesNotExist:
            # Run the default password hasher to mitigate timing attacks
            User().set_password(password)
            return None
        except User.MultipleObjectsReturned:
            # Should not happen given unique constraints, but guard anyway
            return None

        if user.check_password(password) and self.user_can_authenticate(user):
            return user
        return None
