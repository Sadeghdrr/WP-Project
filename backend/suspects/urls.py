"""
Suspects app URL configuration.

All routes are registered under the ``/api/suspects/`` prefix
(included from ``backend.urls``).

Route Hierarchy
---------------
  ── Suspect CRUD + Workflow Actions ─────────────────────────────
  GET    /api/suspects/                                → list suspects
  POST   /api/suspects/                                → create (identify) suspect
  GET    /api/suspects/{id}/                           → retrieve suspect detail
  PATCH  /api/suspects/{id}/                           → update suspect profile

  ── Suspect Workflow @actions ───────────────────────────────────
  GET    /api/suspects/most-wanted/                    → Most Wanted listing
  POST   /api/suspects/{id}/approve/                   → Sergeant approve/reject
  POST   /api/suspects/{id}/arrest/                    → execute arrest
  POST   /api/suspects/{id}/transition-status/         → generic status transition

  ── Nested: Interrogations ──────────────────────────────────────
  GET    /api/suspects/{suspect_pk}/interrogations/       → list interrogations
  POST   /api/suspects/{suspect_pk}/interrogations/       → create interrogation
  GET    /api/suspects/{suspect_pk}/interrogations/{id}/  → retrieve interrogation
 POST    /api/suspects/{id}/captain-verdict/
 POST    /api/suspects/{id}/chief-approval/

  ── Nested: Trials ──────────────────────────────────────────────
  GET    /api/suspects/{suspect_pk}/trials/                → list trials
  POST   /api/suspects/{suspect_pk}/trials/                → create trial
  GET    /api/suspects/{suspect_pk}/trials/{id}/           → retrieve trial

  ── Nested: Bails ───────────────────────────────────────────────
  GET    /api/suspects/{suspect_pk}/bails/                 → list bails
  POST   /api/suspects/{suspect_pk}/bails/                 → create bail
  GET    /api/suspects/{suspect_pk}/bails/{id}/            → retrieve bail
  POST   /api/suspects/{suspect_pk}/bails/{id}/pay/        → process payment

  ── Bounty Tips (top-level) ─────────────────────────────────────
  GET    /api/bounty-tips/                                 → list bounty tips
  POST   /api/bounty-tips/                                 → submit bounty tip
  GET    /api/bounty-tips/{id}/                            → retrieve tip detail
  POST   /api/bounty-tips/{id}/review/                     → officer review
  POST   /api/bounty-tips/{id}/verify/                     → detective verify
  POST   /api/bounty-tips/lookup-reward/                   → reward lookup
"""

from django.urls import include, path
from rest_framework.routers import DefaultRouter
from rest_framework_nested.routers import NestedDefaultRouter

from .views import (
    BailViewSet,
    BountyTipViewSet,
    InterrogationViewSet,
    SuspectViewSet,
    TrialViewSet,
)

# ── Primary Router ──────────────────────────────────────────────────
router = DefaultRouter()
router.register(
    prefix=r"suspects",
    viewset=SuspectViewSet,
    basename="suspect",
)
router.register(
    prefix=r"bounty-tips",
    viewset=BountyTipViewSet,
    basename="bounty-tip",
)

# ── Nested Routers (under /suspects/{suspect_pk}/) ──────────────────
suspects_router = NestedDefaultRouter(
    parent_router=router,
    parent_prefix=r"suspects",
    lookup="suspect",
)
suspects_router.register(
    prefix=r"interrogations",
    viewset=InterrogationViewSet,
    basename="suspect-interrogation",
)
suspects_router.register(
    prefix=r"trials",
    viewset=TrialViewSet,
    basename="suspect-trial",
)
suspects_router.register(
    prefix=r"bails",
    viewset=BailViewSet,
    basename="suspect-bail",
)

urlpatterns = [
    path("", include(router.urls)),
    path("", include(suspects_router.urls)),
]
