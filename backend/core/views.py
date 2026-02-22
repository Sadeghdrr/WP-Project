"""
Core app views — **Thin Views**.

Each view delegates all business logic to the corresponding service in
``core.services``.  Views are responsible only for:

1. Extracting and validating query parameters from the request.
2. Calling the service with the authenticated user and parameters.
3. Serialising the result and returning an HTTP ``Response``.

No model imports, no aggregation logic, no cross-app queries.
"""

from __future__ import annotations

from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from .serializers import (
    DashboardStatsSerializer,
    GlobalSearchResponseSerializer,
    SystemConstantsSerializer,
)
from .services import (
    DashboardAggregationService,
    GlobalSearchService,
    SystemConstantsService,
)


class DashboardStatsView(APIView):
    """
    **GET /api/core/dashboard/**

    Return aggregated dashboard statistics for the authenticated user.

    The response payload is **role-aware** — a Captain or Police Chief
    sees department-wide metrics, while a Detective sees only the stats
    of their assigned cases.  See ``DashboardAggregationService`` for
    the full scoping logic.

    **Authentication**: Required (``IsAuthenticated``).

    **Query Parameters**: None.

    **Response** (``200 OK``):
        Serialised by ``DashboardStatsSerializer``.

    **Error Responses**:
        - ``401 Unauthorized``: Missing or invalid credentials.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request: Request) -> Response:
        """
        Handle GET request — delegate to
        ``DashboardAggregationService``.

        Args:
            request: The incoming DRF request with an authenticated
                     user.

        Returns:
            A ``Response`` containing the serialised dashboard stats.

        Raises:
            NotImplementedError: Propagated from the service layer
                                 (structural draft).
        """
        service = DashboardAggregationService(user=request.user)
        data = service.get_stats()
        serializer = DashboardStatsSerializer(data)
        return Response(serializer.data, status=status.HTTP_200_OK)


class GlobalSearchView(APIView):
    """
    **GET /api/core/search/?q=<term>[&category=<cat>][&limit=<n>]**

    Perform a unified search across Cases, Suspects, and Evidence,
    returning categorised results in a single response.

    **Authentication**: Required (``IsAuthenticated``).

    **Query Parameters**:
        - ``q`` (str, **required**): The search term.
          Minimum 2 characters.
        - ``category`` (str, optional): Restrict search to one of
          ``cases``, ``suspects``, ``evidence``.  Omit to search all.
        - ``limit`` (int, optional): Max results per category.
          Default ``10``, maximum ``50``.

    **Response** (``200 OK``):
        Serialised by ``GlobalSearchResponseSerializer``.

    **Error Responses**:
        - ``400 Bad Request``: Missing or too-short ``q`` parameter.
        - ``401 Unauthorized``: Missing or invalid credentials.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request: Request) -> Response:
        """
        Handle GET request — validate parameters and delegate to
        ``GlobalSearchService``.

        Args:
            request: The incoming DRF request.

        Returns:
            A ``Response`` containing categorised search results.
        """
        query = request.query_params.get("q", "").strip()
        if len(query) < GlobalSearchService.MIN_QUERY_LENGTH:
            return Response(
                {
                    "detail": (
                        f"Search query must be at least "
                        f"{GlobalSearchService.MIN_QUERY_LENGTH} characters."
                    ),
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        category = request.query_params.get("category", None)
        valid_categories = {"cases", "suspects", "evidence"}
        if category is not None and category not in valid_categories:
            return Response(
                {
                    "detail": (
                        f"Invalid category '{category}'. "
                        f"Must be one of: {', '.join(sorted(valid_categories))}."
                    ),
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            limit = int(request.query_params.get("limit", GlobalSearchService.DEFAULT_LIMIT))
        except (TypeError, ValueError):
            limit = GlobalSearchService.DEFAULT_LIMIT

        service = GlobalSearchService(
            query=query,
            user=request.user,
            category=category,
            limit=limit,
        )
        data = service.search()
        serializer = GlobalSearchResponseSerializer(data)
        return Response(serializer.data, status=status.HTTP_200_OK)


class SystemConstantsView(APIView):
    """
    **GET /api/core/constants/**

    Return all system-wide choice enumerations and the role hierarchy
    so the frontend can dynamically build dropdowns, filters, and
    labels without hardcoding values.

    **Authentication**: Not required (``AllowAny``).
    These constants are public configuration data.

    **Query Parameters**: None.

    **Response** (``200 OK``):
        Serialised by ``SystemConstantsSerializer``.
    """

    permission_classes = [AllowAny]

    def get(self, request: Request) -> Response:
        """
        Handle GET request — delegate to ``SystemConstantsService``.

        Args:
            request: The incoming DRF request.

        Returns:
            A ``Response`` containing all system constants.
        """
        data = SystemConstantsService.get_constants()
        serializer = SystemConstantsSerializer(data)
        return Response(serializer.data, status=status.HTTP_200_OK)
