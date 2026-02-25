"""
Integration tests — Evidence Registration Flows (Scenarios 5.1 – 5.6).

All scenarios share a single TestCase class so the database fixtures
(users, roles, case) are created only once via setUpTestData.

To run this file inside Docker:
    docker compose exec backend python manage.py test tests.test_evidence_flows

Business-flow reference : md-files/project-doc.md §4.3
API reference           : md-files/swagger_documentation_report.md §3.4
Service reference       : evidence/services.py   EvidenceProcessingService
Model reference         : evidence/models.py

Test map
--------
  5.1  Create Testimony evidence → 201 + DB persistence + negative tests
  5.2 – 5.6  (appended by subsequent prompts)
"""

from __future__ import annotations

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from accounts.models import Role
from cases.models import Case, CaseCreationType, CaseStatus, CrimeLevel
from evidence.models import EvidenceType, TestimonyEvidence

User = get_user_model()


# ─────────────────────────────────────────────────────────────────────────────
#  Module-level helpers (follow the same pattern as test_cases_crime_scene_flow)
# ─────────────────────────────────────────────────────────────────────────────

def _make_role(name: str, hierarchy_level: int) -> Role:
    """Get or create a Role by name (idempotent within a test-DB transaction)."""
    role, _ = Role.objects.get_or_create(
        name=name,
        defaults={
            "description": f"Test role: {name}",
            "hierarchy_level": hierarchy_level,
        },
    )
    return role


def _grant(role: Role, codename: str, app_label: str) -> None:
    """Attach a single Django Permission to a Role (no-op if already attached)."""
    perm = Permission.objects.get(
        codename=codename,
        content_type__app_label=app_label,
    )
    role.permissions.add(perm)


# ─────────────────────────────────────────────────────────────────────────────
#  Shared TestCase — all 5.x scenarios live in this class
# ─────────────────────────────────────────────────────────────────────────────

class TestEvidenceFlows(TestCase):
    """
    End-to-end integration tests for Evidence Registration (project-doc §4.3).

    Database fixtures (roles, users, case) are seeded once per class via
    setUpTestData.  Every evidence **action** is performed through the real
    HTTP endpoints via APIClient.

    Scenario map
    ------------
      5.1  Testimony evidence — create (happy path + DB persistence + negative)
      5.2 – 5.6  (added in subsequent prompts inside this same file)
    """

    # ────────────────────────────────────────────────────────────────────────
    #  Class-level fixtures — created once, shared across all tests
    # ────────────────────────────────────────────────────────────────────────

    @classmethod
    def setUpTestData(cls) -> None:
        """
        Seed roles, users, and a ready-to-receive-evidence Case.

        DB/model creation is permitted here (test constraints allow it for
        setup stability).  All evidence actions must go through the API.

        Role permissions follow the mapping in:
            accounts/management/commands/setup_rbac.py

        Evidence creation check (service layer):
            evidence/services.py  →  EvidenceProcessingService.process_new_evidence
            checks:  requesting_user.has_perm("evidence.add_evidence")
        """

        # ── Roles ─────────────────────────────────────────────────────────
        # Detective — allowed to create all evidence types (ADD_EVIDENCE)
        cls.detective_role = _make_role("Detective", hierarchy_level=7)
        # Cadet — no evidence permissions → used for 403 negative tests
        cls.cadet_role = _make_role("Cadet", hierarchy_level=1)

        # Grant Detective the minimum permissions required to create evidence
        # and read the detail record afterward.
        # Reference: setup_rbac.py  "Detective" entry
        for codename in (
            "add_evidence",
            "view_evidence",
            "add_testimonyevidence",
            "view_testimonyevidence",
        ):
            _grant(cls.detective_role, codename, app_label="evidence")

        # Detective also needs view_case so the scoped queryset doesn't hide
        # the case from the user (evidence detail fetch filters by assigned_detective).
        _grant(cls.detective_role, "view_case", app_label="cases")

        # Cadet has no evidence permissions (intentionally left empty).

        # ── Users ─────────────────────────────────────────────────────────
        cls.detective_password = "D3tective!Pass"
        cls.cadet_password = "C@det!Pass9999"

        cls.detective_user = User.objects.create_user(
            username="ev_detective",
            password=cls.detective_password,
            email="detective@lapd.test",
            phone_number="09130001001",
            national_id="2000000001",
            first_name="Cole",
            last_name="Phelps",
            role=cls.detective_role,
        )
        cls.cadet_user = User.objects.create_user(
            username="ev_cadet",
            password=cls.cadet_password,
            email="cadet@lapd.test",
            phone_number="09130001002",
            national_id="2000000002",
            first_name="John",
            last_name="Recruit",
            role=cls.cadet_role,
        )

        # ── Case ──────────────────────────────────────────────────────────
        # Created via the DB layer (permitted for setup).
        # Status OPEN is a safe, valid state for evidence attachment.
        # The service layer does NOT validate case status before creating evidence.
        # Reference: evidence/services.py  process_new_evidence — only checks
        #            has_perm("evidence.add_evidence"), not case.status
        cls.case = Case.objects.create(
            title="Downtown Homicide — Test Case",
            description="Victim found at 3rd & Broadway. Test fixture.",
            crime_level=CrimeLevel.LEVEL_1,
            creation_type=CaseCreationType.CRIME_SCENE,
            status=CaseStatus.OPEN,
            created_by=cls.detective_user,
            assigned_detective=cls.detective_user,
        )

    # ────────────────────────────────────────────────────────────────────────
    #  Per-test setup
    # ────────────────────────────────────────────────────────────────────────

    def setUp(self) -> None:
        """Instantiate a fresh APIClient before every test method."""
        self.client = APIClient()

    # ────────────────────────────────────────────────────────────────────────
    #  Shared helpers
    # ────────────────────────────────────────────────────────────────────────

    def _login(self, username: str, password: str) -> str:
        """
        Authenticate via POST /api/accounts/auth/login/ and return the JWT
        access token.

        Endpoint: accounts:login  (POST /api/accounts/auth/login/)
        Payload:  {"identifier": <username|national_id|phone|email>, "password": str}
        Response: {"access": str, "refresh": str, …}
        Reference: swagger_documentation_report.md §3.1 — LoginView.post
        """
        url = reverse("accounts:login")
        response = self.client.post(
            url,
            {"identifier": username, "password": password},
            format="json",
        )
        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
            msg=f"Login failed for '{username}': {getattr(response, 'data', response.content)}",
        )
        return response.data["access"]

    def _set_auth(self, token: str) -> None:
        """
        Attach the Bearer token to every subsequent request on self.client.

        Scheme: Authorization: Bearer <token>
        Reference: swagger_documentation_report.md §3.1 — SimpleJWT
        """
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")

    def _login_as(self, username: str, password: str) -> None:
        """Convenience wrapper: login then immediately set auth credentials."""
        self._set_auth(self._login(username, password))

    # ────────────────────────────────────────────────────────────────────────
    #  Testimony evidence helpers
    # ────────────────────────────────────────────────────────────────────────

    def _testimony_payload(self, **overrides) -> dict:
        """
        Return a valid testimony-evidence creation payload.

        Fields come from TestimonyEvidenceCreateSerializer:
            evidence/serializers.py  TestimonyEvidenceCreateSerializer
            → required: evidence_type (discriminator), case, title
            → optional: description, statement_text

        Service-level validation (evidence/services.py):
            _validate_testimony():  statement_text must be non-empty.
        """
        base = {
            "evidence_type": "testimony",
            "case": self.case.pk,
            "title": "Witness Statement — Downtown Homicide",
            "description": "Local resident witnessed the incident at midnight.",
            "statement_text": (
                "I heard a loud argument and then a single gunshot around midnight. "
                "I saw two men in dark coats running toward 4th Street."
            ),
        }
        base.update(overrides)
        return base

    # ════════════════════════════════════════════════════════════════════════
    #  Scenario 5.1 — Evidence Type = Testimony
    # ════════════════════════════════════════════════════════════════════════

    # ── Happy path: successful creation ─────────────────────────────────────

    def test_create_testimony_evidence_returns_201(self) -> None:
        """
        Scenario 5.1 (happy path — HTTP 201):
        A Detective POSTs a valid testimony payload to POST /api/evidence/
        and receives HTTP 201 Created.

        Asserts:
        - HTTP 201
        - Response body contains: id, evidence_type, case, title,
          statement_text, registered_by, created_at
        - evidence_type == "testimony"
        - case PK matches the seeded case
        - statement_text is correctly echoed back
        - Fields irrelevant to testimony (forensic_result, vehicle_model,
          owner_full_name) are absent from the response

        Reference:
            swagger_documentation_report.md §3.4 — EvidenceViewSet.create
            evidence/serializers.py  TestimonyEvidenceDetailSerializer (response)
        """
        self._login_as(self.detective_user.username, self.detective_password)

        url = reverse("evidence-list")  # POST /api/evidence/
        response = self.client.post(url, self._testimony_payload(), format="json")

        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED,
            msg=f"Expected 201, got {response.status_code}: {response.data}",
        )

        data = response.data

        # ── Required schema fields are present ──────────────────────
        for field in ("id", "evidence_type", "case", "title", "statement_text",
                      "registered_by", "created_at", "description"):
            self.assertIn(field, data, msg=f"Field '{field}' missing from response")

        # ── Field values are correct ─────────────────────────────────
        self.assertEqual(data["evidence_type"], EvidenceType.TESTIMONY)
        self.assertEqual(data["case"], self.case.pk)
        self.assertEqual(data["title"], "Witness Statement — Downtown Homicide")
        self.assertEqual(
            data["statement_text"],
            (
                "I heard a loud argument and then a single gunshot around midnight. "
                "I saw two men in dark coats running toward 4th Street."
            ),
        )
        # registered_by must point to the authenticated detective
        self.assertEqual(data["registered_by"], self.detective_user.pk)

        # ── Fields belonging to OTHER evidence types are absent ──────
        # (ensures the polymorphic serializer returns the correct subtype)
        self.assertNotIn(
            "forensic_result", data,
            msg="Biological-only field 'forensic_result' must not appear in testimony response",
        )
        self.assertNotIn(
            "vehicle_model", data,
            msg="Vehicle-only field 'vehicle_model' must not appear in testimony response",
        )
        self.assertNotIn(
            "owner_full_name", data,
            msg="Identity-only field 'owner_full_name' must not appear in testimony response",
        )
        # password must never be exposed
        self.assertNotIn("password", data)

    # ── Happy path: DB persistence ────────────────────────────────────────

    def test_create_testimony_evidence_is_persisted_in_db(self) -> None:
        """
        Scenario 5.1 (DB persistence):
        After a successful POST, the evidence record is:
          1. Retrievable via GET /api/evidence/{id}/ with matching fields.
          2. Present in the database (TestimonyEvidence ORM query).

        Reference:
            swagger_documentation_report.md §3.4 — EvidenceViewSet.retrieve
        """
        self._login_as(self.detective_user.username, self.detective_password)
        payload = self._testimony_payload()

        # ── Step 1: create via POST ──────────────────────────────────
        create_url = reverse("evidence-list")
        create_resp = self.client.post(create_url, payload, format="json")
        self.assertEqual(
            create_resp.status_code,
            status.HTTP_201_CREATED,
            msg=f"Creation failed: {create_resp.data}",
        )
        evidence_id = create_resp.data["id"]

        # ── Step 2: fetch via GET /api/evidence/{id}/ ────────────────
        detail_url = reverse("evidence-detail", kwargs={"pk": evidence_id})
        get_resp = self.client.get(detail_url)
        self.assertEqual(
            get_resp.status_code,
            status.HTTP_200_OK,
            msg=f"GET returned {get_resp.status_code}: {get_resp.data}",
        )

        detail = get_resp.data

        # Fields must match what was submitted
        self.assertEqual(detail["id"], evidence_id)
        self.assertEqual(detail["evidence_type"], EvidenceType.TESTIMONY)
        self.assertEqual(detail["case"], self.case.pk)
        self.assertEqual(detail["title"], payload["title"])
        self.assertEqual(detail["description"], payload["description"])
        self.assertEqual(detail["statement_text"], payload["statement_text"])

        # ── Step 3: direct DB verification ──────────────────────────
        # The TestimonyEvidence child-table row must exist.
        self.assertTrue(
            TestimonyEvidence.objects.filter(pk=evidence_id).exists(),
            msg="No TestimonyEvidence row found in the database after creation.",
        )
        db_obj = TestimonyEvidence.objects.get(pk=evidence_id)
        self.assertEqual(db_obj.evidence_type, EvidenceType.TESTIMONY)
        self.assertEqual(db_obj.case_id, self.case.pk)
        self.assertEqual(db_obj.title, payload["title"])
        self.assertEqual(db_obj.statement_text, payload["statement_text"])
        self.assertEqual(
            db_obj.registered_by_id,
            self.detective_user.pk,
            msg="registered_by must be the authenticated detective.",
        )

    # ── Negative test 1: unauthenticated request ─────────────────────────

    def test_create_testimony_evidence_unauthenticated_returns_401(self) -> None:
        """
        Scenario 5.1 (negative — no token):
        An unauthenticated POST to POST /api/evidence/ must return HTTP 401.

        Reference:
            evidence/views.py  →  permission_classes = [IsAuthenticated]
        """
        # Ensure no credentials are set (client starts clean, but be explicit)
        self.client.credentials()

        url = reverse("evidence-list")
        response = self.client.post(url, self._testimony_payload(), format="json")

        self.assertEqual(
            response.status_code,
            status.HTTP_401_UNAUTHORIZED,
            msg=(
                f"Expected 401 for an unauthenticated request, "
                f"got {response.status_code}: {response.data}"
            ),
        )

    # ── Negative test 2: role without ADD_EVIDENCE permission ────────────

    def test_create_testimony_evidence_cadet_returns_403(self) -> None:
        """
        Scenario 5.1 (negative — insufficient role):
        A Cadet who lacks the ``evidence.add_evidence`` permission must
        receive HTTP 403 Forbidden when attempting to create evidence.

        The service layer raises core.domain.exceptions.PermissionDenied,
        which is translated to HTTP 403 by the custom exception handler:
            core/domain/exception_handler.py  →  domain_exception_handler

        Reference:
            evidence/services.py  EvidenceProcessingService.process_new_evidence
                → if not requesting_user.has_perm("evidence.add_evidence"):
                      raise PermissionDenied(...)
        """
        self._login_as(self.cadet_user.username, self.cadet_password)

        url = reverse("evidence-list")
        response = self.client.post(url, self._testimony_payload(), format="json")

        self.assertEqual(
            response.status_code,
            status.HTTP_403_FORBIDDEN,
            msg=(
                f"Expected 403 for Cadet (no add_evidence permission), "
                f"got {response.status_code}: {response.data}"
            ),
        )
