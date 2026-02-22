"""
Evidence app URL configuration.

All routes are registered under the ``/api/evidence/`` prefix
(included from ``backend.urls``).

Route Hierarchy
---------------
  /api/evidence/                                → list / create (polymorphic)
  /api/evidence/{id}/                           → retrieve / partial_update / destroy

  ── Workflow @actions (resource-level RPC) ──────────────────────
  POST /api/evidence/{id}/verify/               → Coroner verifies biological evidence
  POST /api/evidence/{id}/link-case/            → link evidence to a case
  POST /api/evidence/{id}/unlink-case/          → unlink evidence from a case

  ── File management @actions ────────────────────────────────────
  GET  /api/evidence/{id}/files/                → list attached files
  POST /api/evidence/{id}/files/                → upload a new file

  ── Audit / history @actions ────────────────────────────────────
  GET  /api/evidence/{id}/chain-of-custody/     → read-only custody audit trail
"""

from rest_framework.routers import DefaultRouter

from .views import EvidenceViewSet

router = DefaultRouter()
router.register(
    prefix=r"evidence",
    viewset=EvidenceViewSet,
    basename="evidence",
)

urlpatterns = router.urls
