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
  5.2  Biological evidence + file upload + chain-of-custody + Coroner verify (approve/reject)
  5.3  Vehicle evidence XOR constraint (license_plate ⊕ serial_number)
  5.4 – 5.6  (appended by subsequent prompts)
"""

from __future__ import annotations

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from accounts.models import Role
from cases.models import Case, CaseCreationType, CaseStatus, CrimeLevel
from evidence.models import BiologicalEvidence, EvidenceType, TestimonyEvidence, VehicleEvidence

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
        # Coroner — can verify biological evidence (CAN_VERIFY_EVIDENCE)
        cls.coroner_role = _make_role("Coroner", hierarchy_level=3)

        # Grant Detective permissions for all scenarios (testimony + biological
        # creation, file uploads, custody log reads).
        # Reference: setup_rbac.py  "Detective" entry
        for codename in (
            "add_evidence",
            "view_evidence",
            "add_testimonyevidence",
            "view_testimonyevidence",
            "add_biologicalevidence",
            "view_biologicalevidence",
            "add_evidencefile",
            "view_evidencefile",
            "add_vehicleevidence",
            "view_vehicleevidence",
        ):
            _grant(cls.detective_role, codename, app_label="evidence")

        # Detective also needs view_case so the scoped queryset doesn't hide
        # the case from the user (evidence detail fetch filters by assigned_detective).
        _grant(cls.detective_role, "view_case", app_label="cases")

        # Cadet has no evidence permissions (intentionally left empty).

        # Grant Coroner the permissions required to verify biological evidence
        # and read chain-of-custody.
        # Reference: setup_rbac.py  "Coroner" entry
        for codename in (
            "view_evidence",
            "view_biologicalevidence",
            "change_biologicalevidence",
            "view_evidencefile",
            "can_verify_evidence",
        ):
            _grant(cls.coroner_role, codename, app_label="evidence")
        _grant(cls.coroner_role, "view_case", app_label="cases")

        # ── Users ─────────────────────────────────────────────────────────
        cls.detective_password = "D3tective!Pass"
        cls.cadet_password = "C@det!Pass9999"
        cls.coroner_password = "C0r0ner!Pass99"

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
        cls.coroner_user = User.objects.create_user(
            username="ev_coroner",
            password=cls.coroner_password,
            email="coroner@lapd.test",
            phone_number="09130001003",
            national_id="2000000003",
            first_name="Stefan",
            last_name="Bekowsky",
            role=cls.coroner_role,
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

    # ════════════════════════════════════════════════════════════════════════
    #  Scenario 5.2 — Biological Evidence + File Upload + Coroner Verify
    # ════════════════════════════════════════════════════════════════════════

    # ── Payload helper ───────────────────────────────────────────────────

    def _biological_payload(self, **overrides) -> dict:
        """
        Return a valid biological-evidence creation payload.

        Fields come from BiologicalEvidenceCreateSerializer:
            evidence/serializers.py  BiologicalEvidenceCreateSerializer
            → required: evidence_type (discriminator), case, title
            → optional: description
            NOTE: forensic_result must NOT be included on creation —
                  the service validates it must be empty at creation time.

        Reference:
            evidence/services.py  EvidenceProcessingService._validate_biological
        """
        base = {
            "evidence_type": "biological",
            "case": self.case.pk,
            "title": "Blood Sample — Downtown Homicide",
            "description": "Blood stain found on the pavement near the victim.",
        }
        base.update(overrides)
        return base

    # ── Internal helper: create biological evidence via API as detective ──

    def _create_biological_evidence(self, title: str | None = None) -> int:
        """
        POST a biological evidence payload as the detective and return the
        created evidence PK.  Asserts HTTP 201 and leaves the client
        authenticated as the detective.
        """
        self._login_as(self.detective_user.username, self.detective_password)
        payload = self._biological_payload()
        if title is not None:
            payload["title"] = title
        resp = self.client.post(reverse("evidence-list"), payload, format="json")
        self.assertEqual(
            resp.status_code,
            status.HTTP_201_CREATED,
            msg=f"Biological evidence creation failed: {resp.data}",
        )
        return resp.data["id"]

    # ── Test B: Create biological evidence ───────────────────────────────

    def test_create_biological_evidence_returns_201(self) -> None:
        """
        Scenario 5.2 — Test B: Detective creates biological evidence.

        Asserts:
        - HTTP 201
        - evidence_type == "biological"
        - case PK matches
        - forensic_result present and empty (pending Coroner examination)
        - is_verified == False
        - verified_by is None
        - Testimony/vehicle/identity-specific fields are absent

        Reference:
            swagger_documentation_report.md §3.4 — EvidenceViewSet.create
            evidence/serializers.py  BiologicalEvidenceDetailSerializer
        """
        self._login_as(self.detective_user.username, self.detective_password)
        url = reverse("evidence-list")
        response = self.client.post(url, self._biological_payload(), format="json")

        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED,
            msg=f"Expected 201, got {response.status_code}: {response.data}",
        )
        data = response.data

        # Required schema fields
        for field in ("id", "evidence_type", "case", "title", "description",
                      "forensic_result", "is_verified", "verified_by",
                      "registered_by", "created_at"):
            self.assertIn(field, data, msg=f"Field '{field}' missing from biological response")

        self.assertEqual(data["evidence_type"], EvidenceType.BIOLOGICAL)
        self.assertEqual(data["case"], self.case.pk)
        # forensic_result must be empty on creation (service validation rule)
        self.assertEqual(data["forensic_result"], "")
        self.assertFalse(data["is_verified"])
        self.assertIsNone(data["verified_by"])
        self.assertEqual(data["registered_by"], self.detective_user.pk)

        # Fields specific to OTHER types must not appear
        self.assertNotIn("statement_text", data)
        self.assertNotIn("vehicle_model", data)
        self.assertNotIn("owner_full_name", data)

    # ── Test C: Upload a file to biological evidence ─────────────────────

    def test_upload_file_to_biological_evidence_returns_201(self) -> None:
        """
        Scenario 5.2 — Test C: Detective uploads an image file to existing
        biological evidence via POST /api/evidence/{id}/files/.

        The upload uses multipart/form-data with a SimpleUploadedFile.
        EvidenceFileService.upload_file() creates a CHECKED_IN custody log
        entry alongside the EvidenceFile row.

        Asserts:
        - HTTP 201
        - Response includes: id, file, file_type, caption, created_at
        - file_type == "image", caption is echoed back
        - Subsequent GET /api/evidence/{id}/files/ lists the uploaded file id

        Reference:
            swagger_documentation_report.md §3.4 — EvidenceViewSet.files
            evidence/services.py  EvidenceFileService.upload_file
                → creates CustodyAction.CHECKED_IN log entry
        """
        evid_id = self._create_biological_evidence(
            title="Bio Evidence — File Upload Test"
        )

        fake_image = SimpleUploadedFile(
            name="crime_scene_blood.jpg",
            content=b"\xff\xd8\xff\xe0" + b"0" * 100,  # minimal fake JPEG bytes
            content_type="image/jpeg",
        )

        upload_url = reverse("evidence-files", kwargs={"pk": evid_id})
        upload_resp = self.client.post(
            upload_url,
            data={"file": fake_image, "file_type": "image", "caption": "Crime scene photo"},
            format="multipart",
        )
        self.assertEqual(
            upload_resp.status_code,
            status.HTTP_201_CREATED,
            msg=f"File upload returned {upload_resp.status_code}: {upload_resp.data}",
        )

        upload_data = upload_resp.data
        # Response schema — EvidenceFileReadSerializer
        for field in ("id", "file", "file_type", "caption", "created_at"):
            self.assertIn(field, upload_data, msg=f"Field '{field}' missing from file upload response")
        self.assertEqual(upload_data["file_type"], "image")
        self.assertEqual(upload_data["caption"], "Crime scene photo")

        # The uploaded file must appear in GET /evidence/{id}/files/
        list_resp = self.client.get(upload_url)
        self.assertEqual(list_resp.status_code, status.HTTP_200_OK)
        file_ids = [f["id"] for f in list_resp.data]
        self.assertIn(
            upload_data["id"],
            file_ids,
            msg="Uploaded file id not found in GET /evidence/{id}/files/ response",
        )

    # ── Test D: Chain of custody contains CHECKED_IN after file upload ───

    def test_chain_of_custody_contains_checked_in_after_upload(self) -> None:
        """
        Scenario 5.2 — Test D: After uploading a file, the chain-of-custody
        log (GET /api/evidence/{id}/chain-of-custody/) must contain at least
        one entry with action == "Checked In" (CustodyAction.CHECKED_IN).

        EvidenceFileService.upload_file() creates:
            EvidenceCustodyLog(action_type=CustodyAction.CHECKED_IN, ...)

        Response fields per ChainOfCustodyEntrySerializer:
            id, timestamp, action (display label), performed_by (PK),
            performer_name, details

        Reference:
            evidence/services.py  EvidenceFileService.upload_file
            evidence/services.py  ChainOfCustodyService.get_chain_of_custody
            swagger_documentation_report.md §3.4 — EvidenceViewSet.chain_of_custody
        """
        evid_id = self._create_biological_evidence(
            title="Bio Evidence — Custody Log Test"
        )

        # Upload a file to trigger the CHECKED_IN custody log entry
        fake_image = SimpleUploadedFile(
            name="lab_sample.jpg",
            content=b"\xff\xd8\xff\xe0" + b"1" * 80,
            content_type="image/jpeg",
        )
        upload_url = reverse("evidence-files", kwargs={"pk": evid_id})
        up_resp = self.client.post(
            upload_url,
            data={"file": fake_image, "file_type": "image", "caption": "Lab specimen"},
            format="multipart",
        )
        self.assertEqual(up_resp.status_code, status.HTTP_201_CREATED)

        # Fetch chain of custody (detective has view_evidence)
        custody_url = reverse("evidence-chain-of-custody", kwargs={"pk": evid_id})
        custody_resp = self.client.get(custody_url)
        self.assertEqual(
            custody_resp.status_code,
            status.HTTP_200_OK,
            msg=f"Chain-of-custody GET failed: {custody_resp.data}",
        )

        entries = custody_resp.data
        self.assertGreater(
            len(entries), 0,
            msg="Chain-of-custody log must not be empty after file upload",
        )

        # Verify entry schema
        for field in ("id", "timestamp", "action", "performed_by", "performer_name", "details"):
            self.assertIn(field, entries[0], msg=f"Custody entry missing field '{field}'")

        # At least one "Checked In" entry must exist (from the file upload)
        actions = [e["action"] for e in entries]
        self.assertIn(
            "Checked In",
            actions,
            msg=(
                "Expected a 'Checked In' custody entry after file upload. "
                f"Actual actions: {actions}"
            ),
        )

        # The actor on the CHECKED_IN entry must be the detective who uploaded
        checked_in = [e for e in entries if e["action"] == "Checked In"]
        self.assertEqual(
            checked_in[0]["performed_by"],
            self.detective_user.pk,
            msg="performed_by on the CHECKED_IN entry must be the detective who uploaded the file",
        )

    # ── Test E: Coroner approves biological evidence ──────────────────────

    def test_coroner_approve_biological_evidence(self) -> None:
        """
        Scenario 5.2 — Test E: Coroner approves biological evidence.

        Flow:
          1. Detective creates biological evidence via API.
          2. Coroner POSTs to /api/evidence/{id}/verify/ with
             decision="approve" and forensic_result (required).
          3. Asserts HTTP 200, is_verified=True, forensic_result matches,
             verified_by == coroner PK.
          4. DB row is updated accordingly.
          5. GET chain-of-custody must contain an "Analysed" entry
             (CustodyAction.ANALYSED created by the service on verification).

        Reference:
            evidence/services.py  MedicalExaminerService.verify_biological_evidence
                → decision=approve:
                      bio_evidence.is_verified = True
                      bio_evidence.forensic_result = forensic_result
                      bio_evidence.verified_by = examiner_user
                → creates CustodyAction.ANALYSED log entry
            swagger_documentation_report.md §3.4 — EvidenceViewSet.verify
        """
        evid_id = self._create_biological_evidence(
            title="Bio Evidence — Coroner Approval Test"
        )

        # Switch to Coroner credentials
        self._login_as(self.coroner_user.username, self.coroner_password)

        verify_url = reverse("evidence-verify", kwargs={"pk": evid_id})
        forensic_text = "Blood type O+. DNA profile matches suspect on file."
        resp = self.client.post(
            verify_url,
            {"decision": "approve", "forensic_result": forensic_text},
            format="json",
        )
        self.assertEqual(
            resp.status_code,
            status.HTTP_200_OK,
            msg=f"Coroner approve returned {resp.status_code}: {resp.data}",
        )

        data = resp.data
        self.assertTrue(data["is_verified"], msg="is_verified must be True after approval")
        self.assertEqual(
            data["forensic_result"],
            forensic_text,
            msg="forensic_result must match the submitted value after approval",
        )
        self.assertEqual(
            data["verified_by"],
            self.coroner_user.pk,
            msg="verified_by must be the Coroner's PK",
        )

        # DB must reflect the approval
        db_bio = BiologicalEvidence.objects.get(pk=evid_id)
        self.assertTrue(db_bio.is_verified)
        self.assertEqual(db_bio.forensic_result, forensic_text)
        self.assertEqual(db_bio.verified_by_id, self.coroner_user.pk)

        # Chain of custody must include an "Analysed" entry
        custody_resp = self.client.get(
            reverse("evidence-chain-of-custody", kwargs={"pk": evid_id})
        )
        self.assertEqual(custody_resp.status_code, status.HTTP_200_OK)
        actions = [e["action"] for e in custody_resp.data]
        self.assertIn(
            "Analysed",
            actions,
            msg=f"Expected 'Analysed' custody entry after Coroner approval. Got: {actions}",
        )

    # ── Test F: Coroner rejects biological evidence ───────────────────────

    def test_coroner_reject_biological_evidence(self) -> None:
        """
        Scenario 5.2 — Test F: Coroner rejects biological evidence.

        Flow:
          1. Detective creates a fresh biological evidence record.
          2. Coroner POSTs with decision="reject" and notes (required).
          3. Asserts:
             - HTTP 200
             - is_verified == False  (rejection does NOT set verified)
             - forensic_result == "REJECTED: <notes>"  (service rule from
               evidence/services.py line: bio_evidence.forensic_result = f"REJECTED: {notes}")
             - verified_by == coroner PK  (tracks who acted even on rejection)
          4. DB row reflects the rejection.

        Reference:
            evidence/services.py  MedicalExaminerService.verify_biological_evidence
                → decision=reject:
                      bio_evidence.is_verified = False
                      bio_evidence.forensic_result = f"REJECTED: {notes}"
                      bio_evidence.verified_by = examiner_user
        """
        evid_id = self._create_biological_evidence(
            title="Bio Evidence — Coroner Rejection Test"
        )

        self._login_as(self.coroner_user.username, self.coroner_password)

        rejection_notes = "Sample contaminated — collection process compromised."
        verify_url = reverse("evidence-verify", kwargs={"pk": evid_id})
        resp = self.client.post(
            verify_url,
            {"decision": "reject", "notes": rejection_notes},
            format="json",
        )
        self.assertEqual(
            resp.status_code,
            status.HTTP_200_OK,
            msg=f"Coroner reject returned {resp.status_code}: {resp.data}",
        )

        data = resp.data
        # Rejection must NOT set is_verified to True
        self.assertFalse(
            data["is_verified"],
            msg="is_verified must remain False after rejection",
        )
        # forensic_result is stored as "REJECTED: <notes>" per service rule
        self.assertEqual(
            data["forensic_result"],
            f"REJECTED: {rejection_notes}",
            msg=(
                "forensic_result must be prefixed 'REJECTED: ' containing the "
                "rejection notes (see evidence/services.py line: "
                "bio_evidence.forensic_result = f'REJECTED: {notes}')"
            ),
        )
        # verified_by tracks the acting Coroner even on rejection
        self.assertEqual(
            data["verified_by"],
            self.coroner_user.pk,
            msg="verified_by must be set to the Coroner's PK even on rejection",
        )

        # DB verification
        db_bio = BiologicalEvidence.objects.get(pk=evid_id)
        self.assertFalse(db_bio.is_verified)
        self.assertEqual(db_bio.forensic_result, f"REJECTED: {rejection_notes}")
        self.assertEqual(db_bio.verified_by_id, self.coroner_user.pk)

    # ── Test G: Approve is irreversible ──────────────────────────────────

    def test_approve_biological_evidence_is_irreversible(self) -> None:
        """
        Scenario 5.2 — Test G: Once biological evidence is approved, any
        subsequent call to the verify endpoint (approve or reject) must
        return HTTP 400.

        Business rule from the service layer:
            if bio_evidence.is_verified:
                raise DomainError(
                    "This evidence has already been verified. "
                    "Verification is irreversible."
                )

        DomainError → HTTP 400 via the custom domain_exception_handler
        (core/domain/exception_handler.py).

        Reference:
            evidence/services.py  MedicalExaminerService.verify_biological_evidence
        """
        evid_id = self._create_biological_evidence(
            title="Bio Evidence — Irreversibility Test"
        )

        # First approval → must succeed
        self._login_as(self.coroner_user.username, self.coroner_password)
        verify_url = reverse("evidence-verify", kwargs={"pk": evid_id})
        first_resp = self.client.post(
            verify_url,
            {"decision": "approve", "forensic_result": "Initial report — conclusive."},
            format="json",
        )
        self.assertEqual(
            first_resp.status_code,
            status.HTTP_200_OK,
            msg=f"First approval failed unexpectedly: {first_resp.data}",
        )
        self.assertTrue(first_resp.data["is_verified"])

        # Second approve attempt → must fail (irreversibility invariant)
        second_resp = self.client.post(
            verify_url,
            {"decision": "approve", "forensic_result": "Trying to overwrite."},
            format="json",
        )
        self.assertEqual(
            second_resp.status_code,
            status.HTTP_400_BAD_REQUEST,
            msg=(
                f"Expected 400 on second approve attempt (irreversible), "
                f"got {second_resp.status_code}: {second_resp.data}"
            ),
        )
        error_str = str(second_resp.data).lower()
        self.assertIn(
            "irreversible",
            error_str,
            msg=f"Error message should mention 'irreversible'. Got: {second_resp.data}",
        )

        # Reject attempt on already-approved evidence must also fail
        reject_resp = self.client.post(
            verify_url,
            {"decision": "reject", "notes": "Trying to reverse the approval."},
            format="json",
        )
        self.assertEqual(
            reject_resp.status_code,
            status.HTTP_400_BAD_REQUEST,
            msg=(
                f"Expected 400 when rejecting already-approved evidence, "
                f"got {reject_resp.status_code}: {reject_resp.data}"
            ),
        )

    # ── Test H1: Non-Coroner cannot verify → 403 ─────────────────────────

    def test_non_coroner_verify_returns_403(self) -> None:
        """
        Scenario 5.2 — Test H1: A Detective (lacks can_verify_evidence)
        attempting POST /api/evidence/{id}/verify/ receives HTTP 403.

        Reference:
            evidence/services.py  MedicalExaminerService.verify_biological_evidence
                → if not examiner_user.has_perm("evidence.can_verify_evidence"):
                      raise PermissionDenied("Only the Coroner can verify...")
        """
        evid_id = self._create_biological_evidence(
            title="Bio Evidence — Non-Coroner Verify 403 Test"
        )
        # _create_biological_evidence leaves the client logged in as detective
        verify_url = reverse("evidence-verify", kwargs={"pk": evid_id})
        resp = self.client.post(
            verify_url,
            {"decision": "approve", "forensic_result": "Unauthorised forensic report."},
            format="json",
        )
        self.assertEqual(
            resp.status_code,
            status.HTTP_403_FORBIDDEN,
            msg=(
                f"Expected 403 for Detective (no can_verify_evidence), "
                f"got {resp.status_code}: {resp.data}"
            ),
        )

    # ── Test H2: Approve without forensic_result → 400 ───────────────────

    def test_approve_without_forensic_result_returns_400(self) -> None:
        """
        Scenario 5.2 — Test H2: Coroner sends decision="approve" with an
        empty forensic_result.  Must receive HTTP 400.

        Validation fires in VerifyBiologicalEvidenceSerializer.validate():
            if decision == "approve" and not forensic_result.strip():
                raise ValidationError({"forensic_result": "..."})

        Reference:
            evidence/serializers.py  VerifyBiologicalEvidenceSerializer.validate
        """
        evid_id = self._create_biological_evidence(
            title="Bio Evidence — Missing forensic_result 400 Test"
        )
        self._login_as(self.coroner_user.username, self.coroner_password)

        verify_url = reverse("evidence-verify", kwargs={"pk": evid_id})
        resp = self.client.post(
            verify_url,
            {"decision": "approve", "forensic_result": ""},
            format="json",
        )
        self.assertEqual(
            resp.status_code,
            status.HTTP_400_BAD_REQUEST,
            msg=(
                f"Expected 400 when approving without forensic_result, "
                f"got {resp.status_code}: {resp.data}"
            ),
        )

    # ── Test H3: Reject without notes → 400 ─────────────────────────────

    def test_reject_without_notes_returns_400(self) -> None:
        """
        Scenario 5.2 — Test H3: Coroner sends decision="reject" with empty
        notes.  Must receive HTTP 400.

        Validation fires in VerifyBiologicalEvidenceSerializer.validate():
            if decision == "reject" and not notes.strip():
                raise ValidationError({"notes": "A rejection reason is required."})

        Reference:
            evidence/serializers.py  VerifyBiologicalEvidenceSerializer.validate
        """
        evid_id = self._create_biological_evidence(
            title="Bio Evidence — Missing notes 400 Test"
        )
        self._login_as(self.coroner_user.username, self.coroner_password)

        verify_url = reverse("evidence-verify", kwargs={"pk": evid_id})
        resp = self.client.post(
            verify_url,
            {"decision": "reject", "notes": ""},
            format="json",
        )
        self.assertEqual(
            resp.status_code,
            status.HTTP_400_BAD_REQUEST,
            msg=(
                f"Expected 400 when rejecting without notes, "
                f"got {resp.status_code}: {resp.data}"
            ),
        )

    # ════════════════════════════════════════════════════════════════════════
    #  Scenario 5.3 — Vehicle Evidence XOR Constraint
    #  (license_plate ⊕ serial_number — exactly one must be provided)
    # ════════════════════════════════════════════════════════════════════════

    # ── Payload helper ───────────────────────────────────────────────────

    def _vehicle_payload(self, **overrides) -> dict:
        """
        Return a valid vehicle-evidence creation payload with license_plate
        set and serial_number absent (the most common valid case).

        Fields come from VehicleEvidenceCreateSerializer:
            evidence/serializers.py  VehicleEvidenceCreateSerializer
            → required: evidence_type, case, title, vehicle_model, color
            → optional (mutually exclusive): license_plate, serial_number

        XOR enforcement layers (project-doc §4.3.3):
            1. Serializer: VehicleEvidenceCreateSerializer.validate()
               → raises serializers.ValidationError → HTTP 400
                   non_field_errors: "Provide either a license plate or a
                   serial number, not both." / "Either a license plate or a
                   serial number must be provided."
            2. Service: EvidenceProcessingService._validate_vehicle()
               → raises DomainError → HTTP 400
            3. DB: VehicleEvidence.Meta.constraints  vehicle_plate_xor_serial
        """
        base = {
            "evidence_type": "vehicle",
            "case": self.case.pk,
            "title": "Blue Sedan — Vehicle Evidence Test",
            "description": "Suspicious vehicle spotted near the alley at midnight.",
            "vehicle_model": "Ford Sedan 1947",
            "color": "Midnight Blue",
            "license_plate": "LA-4521",
        }
        base.update(overrides)
        return base

    # ── Test A: license_plate provided, serial_number absent → 201 ───────

    def test_create_vehicle_evidence_with_license_plate_returns_201(self) -> None:
        """
        Scenario 5.3 — Test A: Detective creates vehicle evidence with only
        license_plate provided (serial_number omitted).

        XOR constraint satisfied: exactly one identifier present.

        Asserts:
        - HTTP 201
        - evidence_type == "vehicle"
        - case PK matches
        - license_plate is echoed back
        - serial_number is present in response and is empty string
        - Vehicle-specific fields (vehicle_model, color) are present
        - Non-vehicle fields (statement_text, forensic_result,
          owner_full_name) are absent

        Reference:
            evidence/serializers.py  VehicleEvidenceCreateSerializer
            evidence/serializers.py  VehicleEvidenceDetailSerializer (response)
            project-doc.md §4.3.3
        """
        self._login_as(self.detective_user.username, self.detective_password)

        payload = self._vehicle_payload(
            title="Vehicle Evidence — License Plate Only",
            license_plate="LA-4521",
            # serial_number intentionally omitted → defaults to ""
        )

        url = reverse("evidence-list")
        response = self.client.post(url, payload, format="json")

        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED,
            msg=(
                f"Expected 201 for vehicle evidence with license_plate only, "
                f"got {response.status_code}: {response.data}"
            ),
        )

        data = response.data

        # Required schema fields must be present
        for field in ("id", "evidence_type", "case", "title", "description",
                      "vehicle_model", "color", "license_plate", "serial_number",
                      "registered_by", "created_at"):
            self.assertIn(field, data, msg=f"Field '{field}' missing from vehicle response")

        self.assertEqual(data["evidence_type"], EvidenceType.VEHICLE)
        self.assertEqual(data["case"], self.case.pk)
        self.assertEqual(data["license_plate"], "LA-4521")
        self.assertEqual(data["serial_number"], "", msg="serial_number must be empty when not supplied")
        self.assertEqual(data["vehicle_model"], "Ford Sedan 1947")
        self.assertEqual(data["color"], "Midnight Blue")
        self.assertEqual(data["registered_by"], self.detective_user.pk)

        # Fields belonging to other evidence types must not appear
        self.assertNotIn("statement_text", data)
        self.assertNotIn("forensic_result", data)
        self.assertNotIn("owner_full_name", data)

        # DB: VehicleEvidence child row must exist
        self.assertTrue(
            VehicleEvidence.objects.filter(pk=data["id"]).exists(),
            msg="VehicleEvidence DB row not found after creation.",
        )
        db_obj = VehicleEvidence.objects.get(pk=data["id"])
        self.assertEqual(db_obj.license_plate, "LA-4521")
        self.assertEqual(db_obj.serial_number, "")

    # ── Test B: serial_number provided, license_plate absent → 201 ───────

    def test_create_vehicle_evidence_with_serial_number_returns_201(self) -> None:
        """
        Scenario 5.3 — Test B: Detective creates vehicle evidence with only
        serial_number provided (license_plate omitted / empty).

        This covers the case where a vehicle has no visible license plate
        (e.g., stolen plates, burnt vehicle) — project-doc §4.3.3:
        "If a vehicle lacks a license plate, its serial number must be entered."

        Asserts:
        - HTTP 201
        - serial_number is echoed back with the submitted value
        - license_plate is present in response and is empty string

        Reference:
            project-doc.md §4.3.3
            evidence/serializers.py  VehicleEvidenceCreateSerializer
        """
        self._login_as(self.detective_user.username, self.detective_password)

        payload = self._vehicle_payload(
            title="Vehicle Evidence — Serial Number Only",
            license_plate="",          # explicitly empty
            serial_number="CHV-19470812-0042",
        )

        url = reverse("evidence-list")
        response = self.client.post(url, payload, format="json")

        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED,
            msg=(
                f"Expected 201 for vehicle evidence with serial_number only, "
                f"got {response.status_code}: {response.data}"
            ),
        )

        data = response.data
        self.assertEqual(data["evidence_type"], EvidenceType.VEHICLE)
        self.assertEqual(data["serial_number"], "CHV-19470812-0042")
        self.assertEqual(
            data["license_plate"], "",
            msg="license_plate must be empty when serial_number is the identifier",
        )

        # DB verification
        db_obj = VehicleEvidence.objects.get(pk=data["id"])
        self.assertEqual(db_obj.serial_number, "CHV-19470812-0042")
        self.assertEqual(db_obj.license_plate, "")

    # ── Test C: Both license_plate AND serial_number → 400 ───────────────

    def test_create_vehicle_evidence_both_identifiers_returns_400(self) -> None:
        """
        Scenario 5.3 — Test C: Providing both license_plate and serial_number
        simultaneously violates the XOR constraint.

        The serializer's validate() rejects the payload before it reaches
        the service layer:
            VehicleEvidenceCreateSerializer.validate()
            → "Provide either a license plate or a serial number, not both."
            → serializers.ValidationError → HTTP 400

        The error is keyed to non_field_errors because validate() raises
        a plain ValidationError (not a field-level one).

        Asserts:
        - HTTP 400
        - Response body contains non_field_errors or detail key
        - The error text mentions the XOR violation
          ("not both" in the message)

        Reference:
            evidence/serializers.py  VehicleEvidenceCreateSerializer.validate
            evidence/services.py  EvidenceProcessingService._validate_vehicle
            project-doc.md §4.3.3 — "cannot both have a value at the same time"
        """
        self._login_as(self.detective_user.username, self.detective_password)

        payload = self._vehicle_payload(
            title="Vehicle Evidence — Both Identifiers (invalid)",
            license_plate="LA-4521",
            serial_number="CHV-19470812-0042",  # BOTH provided → XOR violation
        )

        url = reverse("evidence-list")
        response = self.client.post(url, payload, format="json")

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
            msg=(
                f"Expected 400 when both license_plate and serial_number are provided, "
                f"got {response.status_code}: {response.data}"
            ),
        )

        # The error body must reference the XOR violation
        error_str = str(response.data).lower()
        self.assertIn(
            "not both",
            error_str,
            msg=(
                "Error response should contain 'not both' (from the XOR message "
                "'Provide either a license plate or a serial number, not both.'). "
                f"Got: {response.data}"
            ),
        )

        # non_field_errors is the expected key when validate() raises
        # a plain ValidationError (not tied to a specific field)
        self.assertIn(
            "non_field_errors",
            response.data,
            msg=(
                "XOR validation error must be reported under 'non_field_errors'. "
                f"Got keys: {list(response.data.keys())}"
            ),
        )

    # ── Test D: Neither license_plate NOR serial_number → 400 ────────────

    def test_create_vehicle_evidence_no_identifier_returns_400(self) -> None:
        """
        Scenario 5.3 — Test D: Providing neither license_plate nor
        serial_number violates the XOR constraint (the other direction).

        The serializer's validate() rejects the payload:
            VehicleEvidenceCreateSerializer.validate()
            → "Either a license plate or a serial number must be provided."
            → serializers.ValidationError → HTTP 400

        All other fields (vehicle_model, color, title, description) must be
        valid so that only the missing identifier triggers the error.

        Asserts:
        - HTTP 400
        - Error text references the missing identifier requirement

        Reference:
            evidence/serializers.py  VehicleEvidenceCreateSerializer.validate
            project-doc.md §4.3.3 — "license plate … serial number must be entered"
        """
        self._login_as(self.detective_user.username, self.detective_password)

        payload = self._vehicle_payload(
            title="Vehicle Evidence — No Identifier (invalid)",
            license_plate="",   # explicitly empty
            serial_number="",   # explicitly empty → NEITHER provided
        )

        url = reverse("evidence-list")
        response = self.client.post(url, payload, format="json")

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
            msg=(
                f"Expected 400 when neither license_plate nor serial_number is provided, "
                f"got {response.status_code}: {response.data}"
            ),
        )

        # The error body must reference the requirement to provide an identifier
        error_str = str(response.data).lower()
        self.assertIn(
            "serial number",
            error_str,
            msg=(
                "Error response should mention 'serial number' (from 'Either a license "
                "plate or a serial number must be provided.'). "
                f"Got: {response.data}"
            ),
        )
        self.assertIn(
            "non_field_errors",
            response.data,
            msg=(
                "XOR validation error must be reported under 'non_field_errors'. "
                f"Got keys: {list(response.data.keys())}"
            ),
        )
