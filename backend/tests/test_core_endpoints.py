"""
Integration tests for core endpoints (scenario 12.1).

Scope in this file:
- GET /api/core/constants/
"""

from django.test import TestCase
from django.urls import reverse
from django.contrib.auth.models import Permission
from rest_framework import status
from rest_framework.test import APIClient

from accounts.models import Role, User
from cases.models import Case, CaseCreationType, CaseStatus, CrimeLevel
from evidence.models import Evidence, EvidenceType
from suspects.models import Suspect


def _grant(role: Role, codename: str, app_label: str) -> None:
    perm = Permission.objects.get(codename=codename, content_type__app_label=app_label)
    role.permissions.add(perm)


class TestCoreEndpoints(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.role_specs = [
            ("Police Chief", 10),
            ("Captain", 9),
            ("Sergeant", 8),
            ("Detective", 7),
            ("Cadet", 4),
            ("Base User", 0),
        ]
        cls.roles_by_name = {}
        for name, level in cls.role_specs:
            role, _ = Role.objects.get_or_create(
                name=name,
                defaults={"hierarchy_level": level, "description": f"{name} role"},
            )
            if role.hierarchy_level != level:
                role.hierarchy_level = level
                role.save(update_fields=["hierarchy_level"])
            cls.roles_by_name[name] = role

        # ── Scope & dashboard permissions (permission-based RBAC) ────
        _grant(cls.roles_by_name["Detective"], "can_scope_assigned_cases", "cases")
        _grant(cls.roles_by_name["Captain"], "can_scope_all_cases", "cases")
        _grant(cls.roles_by_name["Captain"], "can_view_full_dashboard", "core")
        _grant(cls.roles_by_name["Captain"], "can_search_all", "core")
        _grant(cls.roles_by_name["Police Chief"], "can_scope_all_cases", "cases")
        _grant(cls.roles_by_name["Police Chief"], "can_view_full_dashboard", "core")
        _grant(cls.roles_by_name["Police Chief"], "can_search_all", "core")

        cls.user_password = "CoreEndpointsP@ss123"
        cls.user = User.objects.create_user(
            username="core_test_user",
            password=cls.user_password,
            email="core_test_user@example.com",
            first_name="Core",
            last_name="Tester",
            national_id="9000000001",
            phone_number="09120000001",
            role=cls.roles_by_name["Detective"],
        )

        cls.detective_a = User.objects.create_user(
            username="dashboard_det_a",
            password=cls.user_password,
            email="dashboard_det_a@example.com",
            first_name="Dash",
            last_name="DetectiveA",
            national_id="9000000002",
            phone_number="09120000002",
            role=cls.roles_by_name["Detective"],
        )
        cls.detective_b = User.objects.create_user(
            username="dashboard_det_b",
            password=cls.user_password,
            email="dashboard_det_b@example.com",
            first_name="Dash",
            last_name="DetectiveB",
            national_id="9000000003",
            phone_number="09120000003",
            role=cls.roles_by_name["Detective"],
        )
        cls.captain_user = User.objects.create_user(
            username="dashboard_captain",
            password=cls.user_password,
            email="dashboard_captain@example.com",
            first_name="Dash",
            last_name="Captain",
            national_id="9000000004",
            phone_number="09120000004",
            role=cls.roles_by_name["Captain"],
        )
        cls.chief_user = User.objects.create_user(
            username="dashboard_chief",
            password=cls.user_password,
            email="dashboard_chief@example.com",
            first_name="Dash",
            last_name="Chief",
            national_id="9000000005",
            phone_number="09120000005",
            role=cls.roles_by_name["Police Chief"],
        )
        cls.base_user = User.objects.create_user(
            username="dashboard_base_user",
            password=cls.user_password,
            email="dashboard_base_user@example.com",
            first_name="Dash",
            last_name="Base",
            national_id="9000000006",
            phone_number="09120000006",
            role=cls.roles_by_name["Base User"],
        )

        # Dashboard scoping tests only need deterministic case ownership.
        # We set assignments directly in fixtures because assignment endpoints
        # require additional workflow/RBAC setup unrelated to this scenario.
        cls.case_for_detective_a = Case.objects.create(
            title="Dashboard Scope A",
            description="Case assigned to detective A.",
            crime_level=CrimeLevel.LEVEL_2,
            status=CaseStatus.OPEN,
            creation_type=CaseCreationType.CRIME_SCENE,
            created_by=cls.captain_user,
            assigned_detective=cls.detective_a,
            assigned_captain=cls.captain_user,
        )
        cls.case_for_detective_b = Case.objects.create(
            title="Dashboard Scope B",
            description="Case assigned to detective B.",
            crime_level=CrimeLevel.LEVEL_1,
            status=CaseStatus.INVESTIGATION,
            creation_type=CaseCreationType.CRIME_SCENE,
            created_by=cls.captain_user,
            assigned_detective=cls.detective_b,
            assigned_captain=cls.captain_user,
        )
        cls.closed_unassigned_case = Case.objects.create(
            title="Dashboard Closed Case",
            description="Closed case not assigned to a detective.",
            crime_level=CrimeLevel.LEVEL_3,
            status=CaseStatus.CLOSED,
            creation_type=CaseCreationType.COMPLAINT,
            created_by=cls.captain_user,
            assigned_captain=cls.captain_user,
        )

    def setUp(self):
        self.client = APIClient()
        self.login_url = reverse("accounts:login")
        self.constants_url = reverse("core:system-constants")
        self.dashboard_url = reverse("core:dashboard-stats")
        self.search_url = reverse("core:global-search")

    def login(self, user: User) -> str:
        response = self.client.post(
            self.login_url,
            {"identifier": user.username, "password": self.user_password},
            format="json",
        )
        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
            msg=f"Login failed in test setup: {response.data}",
        )
        return response.data["access"]

    def auth(self, token: str) -> None:
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")

    def _assert_choice_list(self, payload: dict, key: str) -> None:
        self.assertIn(key, payload, msg=f"Missing top-level key: {key}")
        items = payload[key]
        self.assertIsInstance(items, list, msg=f"{key} must be a list.")
        self.assertTrue(items, msg=f"{key} must not be empty.")

        for item in items:
            self.assertIsInstance(item, dict, msg=f"Each item in {key} must be an object.")
            self.assertIn("value", item, msg=f"Items in {key} must include 'value'.")
            self.assertIn("label", item, msg=f"Items in {key} must include 'label'.")
            self.assertIsInstance(item["value"], str, msg=f"{key}.value must be string.")
            self.assertIsInstance(item["label"], str, msg=f"{key}.label must be string.")
            self.assertTrue(item["value"], msg=f"{key}.value must not be empty.")
            self.assertTrue(item["label"], msg=f"{key}.label must not be empty.")

    def _status_counts(self, payload: dict) -> dict[str, int]:
        return {
            item["status"]: item["count"]
            for item in payload["cases_by_status"]
        }

    def _create_case_for_search(
        self,
        *,
        title: str,
        description: str,
        assigned_detective: User | None,
        status_value: str = CaseStatus.OPEN,
    ) -> Case:
        return Case.objects.create(
            title=title,
            description=description,
            crime_level=CrimeLevel.LEVEL_2,
            status=status_value,
            creation_type=CaseCreationType.CRIME_SCENE,
            created_by=self.captain_user,
            assigned_detective=assigned_detective,
            assigned_captain=self.captain_user,
        )

    def test_get_constants_success_returns_required_enums_and_maps(self):
        response = self.client.get(self.constants_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK, msg=response.data)

        data = response.data
        self.assertIsInstance(data, dict)

        required_keys = [
            "crime_levels",
            "case_statuses",
            "case_creation_types",
            "evidence_types",
            "evidence_file_types",
            "suspect_statuses",
            "verdict_choices",
            "bounty_tip_statuses",
            "complainant_statuses",
            "role_hierarchy",
        ]
        for key in required_keys:
            self.assertIn(key, data, msg=f"Missing required key '{key}'.")

        for key in required_keys[:-1]:
            self._assert_choice_list(data, key)

        self.assertIsInstance(data["role_hierarchy"], list)
        self.assertTrue(data["role_hierarchy"], msg="role_hierarchy must not be empty.")
        for role in data["role_hierarchy"]:
            self.assertIsInstance(role, dict)
            self.assertIn("id", role)
            self.assertIn("name", role)
            self.assertIn("hierarchy_level", role)
            self.assertIsInstance(role["id"], int)
            self.assertIsInstance(role["name"], str)
            self.assertIsInstance(role["hierarchy_level"], int)
            self.assertTrue(role["name"])

        case_status_values = {item["value"] for item in data["case_statuses"]}
        self.assertIn("open", case_status_values)

        case_creation_values = {item["value"] for item in data["case_creation_types"]}
        self.assertIn("complaint", case_creation_values)
        self.assertIn("crime_scene", case_creation_values)

        crime_levels = {item["value"]: item["label"] for item in data["crime_levels"]}
        self.assertIn("4", crime_levels)
        self.assertIn("critical", crime_levels["4"].lower())

        evidence_type_values = {item["value"] for item in data["evidence_types"]}
        self.assertTrue(
            {"testimony", "biological", "vehicle", "identity", "other"}.issubset(
                evidence_type_values
            )
        )

        suspect_status_values = {item["value"] for item in data["suspect_statuses"]}
        self.assertIn("wanted", suspect_status_values)

        role_names = {role["name"].lower() for role in data["role_hierarchy"]}
        self.assertIn("detective", role_names)
        self.assertIn("sergeant", role_names)
        self.assertIn("captain", role_names)

        levels = [role["hierarchy_level"] for role in data["role_hierarchy"]]
        self.assertEqual(levels, sorted(levels, reverse=True))

    def test_dashboard_detective_scope_shows_only_assigned_cases(self):
        token = self.login(self.detective_a)
        self.auth(token)

        response = self.client.get(self.dashboard_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK, msg=response.data)
        data = response.data

        self.assertEqual(data["total_cases"], 1)
        self.assertEqual(data["active_cases"], 1)
        self.assertEqual(data["closed_cases"], 0)

        status_counts = self._status_counts(data)
        self.assertEqual(status_counts.get(CaseStatus.OPEN), 1)
        self.assertNotIn(CaseStatus.INVESTIGATION, status_counts)
        self.assertNotIn(CaseStatus.CLOSED, status_counts)

        self.assertEqual(
            sum(item["count"] for item in data["cases_by_crime_level"]),
            1,
        )

    def test_dashboard_captain_scope_includes_broader_case_set(self):
        token = self.login(self.captain_user)
        self.auth(token)

        response = self.client.get(self.dashboard_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK, msg=response.data)
        data = response.data

        self.assertEqual(data["total_cases"], 3)
        self.assertEqual(data["active_cases"], 2)
        self.assertEqual(data["closed_cases"], 1)

        status_counts = self._status_counts(data)
        self.assertEqual(status_counts.get(CaseStatus.OPEN), 1)
        self.assertEqual(status_counts.get(CaseStatus.INVESTIGATION), 1)
        self.assertEqual(status_counts.get(CaseStatus.CLOSED), 1)

        self.assertEqual(
            sum(item["count"] for item in data["cases_by_crime_level"]),
            3,
        )

    def test_dashboard_chief_scope_includes_broader_case_set(self):
        token = self.login(self.chief_user)
        self.auth(token)

        response = self.client.get(self.dashboard_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK, msg=response.data)
        data = response.data

        self.assertEqual(data["total_cases"], 3)
        self.assertEqual(data["active_cases"], 2)
        self.assertEqual(data["closed_cases"], 1)

        status_counts = self._status_counts(data)
        self.assertEqual(status_counts.get(CaseStatus.OPEN), 1)
        self.assertEqual(status_counts.get(CaseStatus.INVESTIGATION), 1)
        self.assertEqual(status_counts.get(CaseStatus.CLOSED), 1)

    def test_dashboard_requires_authentication(self):
        response = self.client.get(self.dashboard_url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_search_returns_relevant_case_suspect_and_evidence_hits(self):
        alpha_case = self._create_case_for_search(
            title="Case ALPHA Search",
            description="Contains ALPHA keyword for search.",
            assigned_detective=self.detective_a,
        )
        alpha_suspect = Suspect.objects.create(
            case=alpha_case,
            full_name="ALPHA Suspect Person",
            description="Suspect linked to ALPHA case.",
            identified_by=self.detective_a,
        )
        alpha_evidence = Evidence.objects.create(
            case=alpha_case,
            evidence_type=EvidenceType.OTHER,
            title="ALPHA Evidence Item",
            description="Evidence text for ALPHA.",
            registered_by=self.detective_a,
        )

        token = self.login(self.captain_user)
        self.auth(token)
        response = self.client.get(
            self.search_url,
            {"q": "ALPHA", "limit": 5},
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK, msg=response.data)

        data = response.data
        self.assertIn("query", data)
        self.assertIn("total_results", data)
        self.assertIn("cases", data)
        self.assertIn("suspects", data)
        self.assertIn("evidence", data)

        case_ids = {item["id"] for item in data["cases"]}
        suspect_ids = {item["id"] for item in data["suspects"]}
        evidence_ids = {item["id"] for item in data["evidence"]}

        self.assertIn(alpha_case.id, case_ids)
        self.assertIn(alpha_suspect.id, suspect_ids)
        self.assertIn(alpha_evidence.id, evidence_ids)

    def test_search_limit_is_respected_for_cases(self):
        for idx in range(7):
            self._create_case_for_search(
                title=f"ALPHA-LIMIT Case {idx}",
                description="Limit behavior fixture.",
                assigned_detective=self.detective_a,
            )

        token = self.login(self.captain_user)
        self.auth(token)
        response = self.client.get(
            self.search_url,
            {"q": "ALPHA-LIMIT", "category": "cases", "limit": 5},
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK, msg=response.data)

        data = response.data
        self.assertLessEqual(len(data["cases"]), 5)
        self.assertEqual(len(data["cases"]), 5)
        self.assertEqual(data["total_results"], len(data["cases"]))
        self.assertEqual(len(data["suspects"]), 0)
        self.assertEqual(len(data["evidence"]), 0)
        self.assertTrue(all("ALPHA-LIMIT" in item["title"] for item in data["cases"]))

    def test_search_detective_scope_hides_other_detective_objects(self):
        hidden_case = self._create_case_for_search(
            title="Case2_BETA Hidden",
            description="Only detective B should see this BETA case.",
            assigned_detective=self.detective_b,
        )
        hidden_suspect = Suspect.objects.create(
            case=hidden_case,
            full_name="BETA Hidden Suspect",
            description="Hidden BETA suspect.",
            identified_by=self.detective_b,
        )
        hidden_evidence = Evidence.objects.create(
            case=hidden_case,
            evidence_type=EvidenceType.OTHER,
            title="BETA Hidden Evidence",
            description="Hidden BETA evidence.",
            registered_by=self.detective_b,
        )

        token = self.login(self.detective_a)
        self.auth(token)
        response = self.client.get(
            self.search_url,
            {"q": "BETA", "limit": 5},
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK, msg=response.data)
        data = response.data

        case_ids = {item["id"] for item in data["cases"]}
        suspect_ids = {item["id"] for item in data["suspects"]}
        evidence_ids = {item["id"] for item in data["evidence"]}

        self.assertNotIn(hidden_case.id, case_ids)
        self.assertNotIn(hidden_suspect.id, suspect_ids)
        self.assertNotIn(hidden_evidence.id, evidence_ids)
        self.assertEqual(data["total_results"], 0)

    def test_search_missing_q_returns_400(self):
        token = self.login(self.captain_user)
        self.auth(token)

        response = self.client.get(self.search_url)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("detail", response.data)

    def test_search_requires_authentication(self):
        response = self.client.get(self.search_url, {"q": "ALPHA", "limit": 5})
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
