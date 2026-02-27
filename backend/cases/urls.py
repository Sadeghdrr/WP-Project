"""
Cases app URL configuration.

All routes are registered under the ``/api/cases/`` prefix.

Route Hierarchy
---------------
  /api/cases/                             → list / create
  /api/cases/{id}/                        → retrieve / partial_update / destroy

  ── Workflow @actions (resource-level RPC) ──────────────────────
  POST /api/cases/{id}/submit/             → complainant submits draft
  POST /api/cases/{id}/resubmit/           → complainant edits & re-submits
  POST /api/cases/{id}/cadet-review/       → cadet approve/reject
  POST /api/cases/{id}/officer-review/     → officer approve/reject
  POST /api/cases/{id}/approve-crime-scene/→ superior approves crime-scene case
  POST /api/cases/{id}/transition/        → generic centralized transition

  ── Assignment @actions ─────────────────────────────────────────
  POST   /api/cases/{id}/assign-detective/
  DELETE /api/cases/{id}/unassign-detective/
  POST   /api/cases/{id}/assign-sergeant/
  POST   /api/cases/{id}/assign-captain/
  POST   /api/cases/{id}/assign-judge/

  ── Sub-resource @actions ───────────────────────────────────────
  GET  /api/cases/{id}/complainants/
  POST /api/cases/{id}/complainants/
  POST /api/cases/{id}/complainants/{complainant_pk}/review/

  GET  /api/cases/{id}/witnesses/
  POST /api/cases/{id}/witnesses/

  GET  /api/cases/{id}/status-log/
  GET  /api/cases/{id}/calculations/
"""

from rest_framework.routers import DefaultRouter

from .views import CaseViewSet

router = DefaultRouter()
router.register(
    prefix=r"cases",
    viewset=CaseViewSet,
    basename="case",
)

urlpatterns = router.urls
