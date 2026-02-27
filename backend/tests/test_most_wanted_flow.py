"""
Integration tests — Most Wanted flow scenario 9.1 (shared file for 9.1–9.2).

Source of truth:
- md-files/project-doc.md §4.7 (Most Wanted rules and formulas)
- md-files/24-swagger_documentation_report.md §3.3 (Most Wanted endpoint)
"""

from __future__ import annotations

from datetime import timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from accounts.models import Role
from cases.models import Case, CaseCreationType, CaseStatus
from suspects.models import Suspect, SuspectStatus

User = get_user_model()


class TestMostWantedFlow(TestCase):
    @classmethod
    def setUpTestData(cls):
        # Authenticated police actor for Most Wanted endpoint access.
        cls.detective_role, _ = Role.objects.get_or_create(
            name="Detective",
            defaults={
                "description": "Detective role for Most Wanted tests.",
                "hierarchy_level": 7,
            },
        )
        cls.detective_password = "MostWanted!Pass901"
        cls.detective_user = User.objects.create_user(
            username="most_wanted_detective",
            password=cls.detective_password,
            email="most_wanted_detective@lapd.test",
            phone_number="09152000001",
            national_id="5200000001",
            first_name="Mason",
            last_name="Detective",
            role=cls.detective_role,
        )

    def setUp(self):
        self.client = APIClient()

    def login(self, user: User) -> str:
        response = self.client.post(
            reverse("accounts:login"),
            {"identifier": user.username, "password": self.detective_password},
            format="json",
        )
        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
            msg=f"Login failed for {user.username}: {response.data}",
        )
        return response.data["access"]

    def auth(self, token: str) -> None:
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")

    def create_case(
        self,
        *,
        title: str,
        status_value: str = CaseStatus.OPEN,
        crime_level: int = 2,
    ) -> Case:
        return Case.objects.create(
            title=title,
            description="Scenario 9.1 case fixture.",
            crime_level=crime_level,
            creation_type=CaseCreationType.CRIME_SCENE,
            status=status_value,
            created_by=self.detective_user,
            assigned_detective=self.detective_user,
        )

    def create_suspect(
        self,
        *,
        case: Case,
        full_name: str,
        national_id: str,
        wanted_days: int,
        status_value: str = SuspectStatus.WANTED,
    ) -> Suspect:
        suspect = Suspect.objects.create(
            case=case,
            full_name=full_name,
            national_id=national_id,
            status=status_value,
            identified_by=self.detective_user,
            sergeant_approval_status="approved",
            description="Scenario 9.1 suspect fixture.",
        )
        suspect.wanted_since = timezone.now() - timedelta(days=wanted_days)
        suspect.save(update_fields=["wanted_since"])
        return suspect

    def _extract_items(self, payload):
        if isinstance(payload, list):
            return payload
        if isinstance(payload, dict) and "results" in payload:
            return payload["results"]
        self.fail(f"Unexpected Most Wanted payload shape: {payload!r}")

    def test_only_suspects_wanted_over_30_days_on_open_cases_appear(self):
        """
        project-doc §4.7 rules:
        - suspect status must be "wanted"
        - wanted_since must be strictly over 30 days
        - suspect's case must be open (not closed/voided)
        """
        token = self.login(self.detective_user)
        self.auth(token)

        case_open = self.create_case(
            title="Most Wanted Open Case",
            status_value=CaseStatus.OPEN,
            crime_level=2,
        )
        old_suspect = self.create_suspect(
            case=case_open,
            full_name="Old Wanted",
            national_id="9000000001",
            wanted_days=31,
            status_value=SuspectStatus.WANTED,
        )
        self.create_suspect(
            case=case_open,
            full_name="New Wanted",
            national_id="9000000002",
            wanted_days=10,
            status_value=SuspectStatus.WANTED,
        )
        self.create_suspect(
            case=case_open,
            full_name="Old Arrested",
            national_id="9000000003",
            wanted_days=45,
            status_value=SuspectStatus.ARRESTED,
        )

        case_closed = self.create_case(
            title="Most Wanted Closed Case",
            status_value=CaseStatus.CLOSED,
            crime_level=3,
        )
        self.create_suspect(
            case=case_closed,
            full_name="Old Wanted Closed Case",
            national_id="9000000004",
            wanted_days=40,
            status_value=SuspectStatus.WANTED,
        )

        response = self.client.get(reverse("suspect-most-wanted"), format="json")
        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
            msg=f"Most Wanted request failed: {response.data}",
        )

        items = self._extract_items(response.data)
        ids = {item["national_id"] for item in items}

        self.assertIn(old_suspect.national_id, ids)
        self.assertNotIn("9000000002", ids)  # <= 30 days
        self.assertNotIn("9000000003", ids)  # status != wanted
        self.assertNotIn("9000000004", ids)  # case is closed

    def test_most_wanted_score_and_reward_follow_formula(self):
        """
        project-doc §4.7 Note 1/2:
        score = days_wanted * crime_level
        reward = score * 20,000,000 (Rials)
        """
        token = self.login(self.detective_user)
        self.auth(token)

        case_open = self.create_case(
            title="Most Wanted Formula Case",
            status_value=CaseStatus.OPEN,
            crime_level=2,
        )
        self.create_suspect(
            case=case_open,
            full_name="Formula Target",
            national_id="9000000010",
            wanted_days=31,
            status_value=SuspectStatus.WANTED,
        )

        response = self.client.get(reverse("suspect-most-wanted"), format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        items = self._extract_items(response.data)

        target = next(
            (item for item in items if item["national_id"] == "9000000010"),
            None,
        )
        self.assertIsNotNone(target, msg=f"Target suspect not found: {items}")

        days_wanted = int(target["days_wanted"])
        self.assertGreaterEqual(days_wanted, 31)
        self.assertLessEqual(days_wanted, 32)

        expected_score = days_wanted * case_open.crime_level
        expected_reward = expected_score * 20_000_000

        self.assertEqual(target["most_wanted_score"], expected_score)
        self.assertEqual(target["reward_amount"], expected_reward)
        if "calculated_reward" in target:
            self.assertEqual(target["calculated_reward"], expected_reward)

    def test_most_wanted_aggregates_same_national_id_by_max_days_and_max_crime_level(self):
        """
        Scenario 9.2:
        project-doc §4.7 requires person-level aggregation by national_id:
        score = max(days_wanted across open Lj) * max(crime_level across Di)
        """
        token = self.login(self.detective_user)
        self.auth(token)

        shared_national_id = "5555555555"
        low_level = 1
        high_level = 3
        long_days = 60
        short_days = 35

        case_low = self.create_case(
            title="Aggregation Low Crime Case",
            status_value=CaseStatus.OPEN,
            crime_level=low_level,
        )
        case_high = self.create_case(
            title="Aggregation High Crime Case",
            status_value=CaseStatus.OPEN,
            crime_level=high_level,
        )

        self.create_suspect(
            case=case_low,
            full_name="Aggregation Suspect Low",
            national_id=shared_national_id,
            wanted_days=long_days,
            status_value=SuspectStatus.WANTED,
        )
        self.create_suspect(
            case=case_high,
            full_name="Aggregation Suspect High",
            national_id=shared_national_id,
            wanted_days=short_days,
            status_value=SuspectStatus.WANTED,
        )

        response = self.client.get(reverse("suspect-most-wanted"), format="json")
        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
            msg=f"Most Wanted request failed: {response.data}",
        )
        items = self._extract_items(response.data)
        same_person_entries = [
            item for item in items if item.get("national_id") == shared_national_id
        ]

        expected_max_days = max(long_days, short_days)
        expected_max_crime = max(low_level, high_level)
        expected_score = expected_max_days * expected_max_crime
        expected_reward = expected_score * 20_000_000

        if len(same_person_entries) != 1:
            returned_scores = {
                item.get("most_wanted_score", item.get("computed_score"))
                for item in same_person_entries
            }
            if returned_scores == {long_days * low_level, short_days * high_level}:
                self.fail(
                    "API appears to compute per-row score (days_wanted*crime_level) "
                    "instead of aggregated max-days * max-crime-level."
                )
            self.fail(
                "API returned multiple Most Wanted entries for the same national_id; "
                "project-doc.md requires aggregation by national_id using "
                "score=max(days_wanted)*max(crime_level)."
            )

        entry = same_person_entries[0]
        score = entry.get("most_wanted_score", entry.get("computed_score"))
        reward = entry.get("reward_amount", entry.get("reward"))
        if reward is None:
            reward = entry.get("calculated_reward")

        self.assertIsNotNone(
            score,
            msg=f"Most Wanted entry must expose score field: {entry}",
        )
        self.assertEqual(score, expected_score)

        if reward is not None:
            self.assertEqual(reward, expected_reward)

        if "days_wanted" in entry:
            # days_wanted should represent the aggregated max-days term.
            self.assertGreaterEqual(int(entry["days_wanted"]), expected_max_days)
