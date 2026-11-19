from datetime import date, timedelta
from secrets import token_urlsafe
from zoneinfo import ZoneInfo

from django.core.cache import cache
from django.test import TestCase
from django.utils import timezone

from accounts.authentication import token_digest
from accounts.models import AuthSession, User
from farms.models import Farm, Plot
from operations.models import Operation, Reminder


class AcceptanceTests(TestCase):
    """The eleven scenarios in section 12 of the backend contract."""

    @classmethod
    def setUpTestData(cls):
        cls.owner = User.objects.create(full_name="Owner", phone="+989123456781", password_hash="unused")
        cls.other = User.objects.create(full_name="Other", phone="+989123456782", password_hash="unused")
        cls.farm = Farm.objects.create(owner=cls.owner, name="Farm")
        cls.plot = Plot.objects.create(farm=cls.farm, name="Plot", code="A", area_m2=20)

    def setUp(self):
        self.token = self.issue_token(self.owner)

    def issue_token(self, user):
        token = token_urlsafe(32)
        AuthSession.objects.create(user=user, token_hash=token_digest(token.encode("ascii")),
                                   expires_at=timezone.now() + timedelta(hours=1))
        return token

    def request(self, method, path, expected, body=None, *, token=None):
        response = getattr(self.client, method)("/api/v1" + path, data=body, content_type="application/json",
                                               HTTP_AUTHORIZATION=f"Bearer {token or self.token}")
        self.assertEqual(response.status_code, expected, response.content)
        return response.json() if response.content else None

    def add_operation(self, **changes):
        payload = dict(plot_id=self.plot.pk, operation_type="irrigation", scheduled_date="2026-03-24")
        return self.request("post", "/operations", 201, payload | changes)

    def test_01_duplicate_login_and_revoked_session(self):
        cache.clear()
        self.addCleanup(cache.clear)
        credentials = dict(phone="09123456783", password="acceptance-password")
        signup = credentials | {"full_name": "New user"}
        self.request("post", "/auth/register", 201, signup)
        self.request("post", "/auth/register", 409, signup)
        self.request("post", "/auth/login", 401, credentials | {"password": "wrong-password"})
        token = self.request("post", "/auth/login", 200, credentials)["access_token"]
        self.request("post", "/auth/logout", 204, token=token)
        self.request("get", "/auth/me", 401, token=token)

    def test_02_foreign_resources_are_hidden(self):
        operation = self.add_operation()
        other_token = self.issue_token(self.other)
        self.request("get", f"/farms/{self.farm.pk}", 404, token=other_token)
        self.request("get", f"/plots/{self.plot.pk}", 404, token=other_token)
        self.request("patch", f"/operations/{operation['id']}", 404, {"status": "cancelled"}, token=other_token)

    def test_03_plot_duplicates_and_nonpositive_area(self):
        url = f"/farms/{self.farm.pk}/plots"
        for fields in ({"name": "Plot", "area_m2": 1}, {"name": "New", "code": "A", "area_m2": 1}):
            self.request("post", url, 409, fields)
        for area in (0, -1):
            self.request("post", url, 422, {"name": "New", "area_m2": area})

    def test_04_cannot_create_operation_on_foreign_plot(self):
        other_token = self.issue_token(self.other)
        self.request("post", "/operations", 404, {
            "plot_id": self.plot.pk, "operation_type": "other", "scheduled_date": "2026-03-24",
        }, token=other_token)
        self.assertFalse(Operation.objects.exists())

    def assert_counts(self, today, overdue):
        plot = self.request("get", f"/plots/{self.plot.pk}", 200)
        farm_plot = self.request("get", f"/farms/{self.farm.pk}", 200)["plots"][0]
        for item in (plot, farm_plot):
            self.assertEqual((item["today_count"], item["overdue_count"]), (today, overdue))
        return farm_plot["next_operation"]

    def test_05_overdue_disappears_from_counters_when_completed(self):
        today = timezone.localdate(timezone=ZoneInfo(self.farm.timezone))
        operation = self.add_operation(scheduled_date=(today - timedelta(days=1)).isoformat())
        self.assertEqual(self.assert_counts(0, 1)["id"], operation["id"])
        upcoming = self.request("get", "/operations?status=planned,in_progress&order=asc&limit=3", 200)
        self.assertEqual(upcoming[0]["id"], operation["id"])
        updated = self.request("patch", f"/operations/{operation['id']}", 200, {"status": "completed"})
        self.assertEqual(updated["completed_date"], today.isoformat())
        self.assertIsNone(self.assert_counts(0, 0))

    def calendar(self, day):
        return self.request("get", f"/operations/calendar?from={day}&to={day}", 200)

    def test_06_calendar_follows_completion_and_reopening(self):
        operation = self.add_operation()
        path = f"/operations/{operation['id']}"
        self.request("patch", path, 200, {"status": "completed", "completed_date": "2026-03-30"})
        self.assertEqual(self.calendar("2026-03-24"), [])
        self.assertEqual(self.calendar("2026-03-30")[0]["id"], operation["id"])
        self.assertIsNone(self.request("patch", path, 200, {"status": "planned"})["completed_date"])
        self.assertEqual(self.calendar("2026-03-30"), [])
        self.assertEqual(self.calendar("2026-03-24")[0]["id"], operation["id"])

    def test_07_cancelled_remains_in_calendar_but_is_not_open(self):
        today = timezone.localdate(timezone=ZoneInfo(self.farm.timezone))
        operation = self.add_operation(scheduled_date=today.isoformat(), status="cancelled")
        self.assertEqual(self.calendar(today)[0]["id"], operation["id"])
        self.assertIsNone(self.assert_counts(0, 0))
        self.assertEqual(self.request("get", "/operations?status=planned,in_progress&order=asc&limit=3", 200), [])

    def test_08_completed_planting_sets_current_season(self):
        operation = self.add_operation(operation_type="planting", crop_name="Wheat")
        self.request("patch", f"/operations/{operation['id']}", 200,
                     {"status": "completed", "completed_date": "2026-03-25"})
        season = self.request("get", f"/plots/{self.plot.pk}", 200)["current_season"]
        self.assertEqual((season["crop_name"], season["status"], season["actual_start_date"]),
                         ("Wheat", "active", "2026-03-25"))

    def test_09_search_filters_before_paginating(self):
        target = [self.add_operation(scheduled_date=f"2026-03-{day:02}")["id"] for day in range(1, 26)]
        farm = Farm.objects.create(owner=self.owner, name="Other farm")
        plot = Plot.objects.create(farm=farm, name="Other plot", area_m2=2)
        second_plot = Plot.objects.create(farm=self.farm, name="Same farm", area_m2=2)
        self.add_operation(plot_id=plot.pk)
        self.add_operation(plot_id=second_plot.pk)
        self.add_operation(status="cancelled")
        self.add_operation(scheduled_date="2026-02-28")
        self.add_operation(scheduled_date="2026-03-26")
        query = "/operations?from=2026-03-01&to=2026-03-25&status=planned&order=asc"
        self.assertEqual(len(self.request("get", query + f"&farm={self.farm.pk}&offset=20", 200)), 6)
        query += f"&farm={self.farm.pk}&plot={self.plot.pk}"
        self.assertEqual([item["id"] for item in self.request("get", query, 200)], target[:20])
        self.assertEqual([item["id"] for item in self.request("get", query + "&offset=20", 200)], target[20:])

    def test_10_coordinates_update_as_a_pair(self):
        path = f"/farms/{self.farm.pk}"
        self.request("patch", path, 422, {"latitude": 35})
        self.request("patch", path, 200, {"latitude": 35, "longitude": 51})
        data = self.request("patch", path, 200, {"latitude": None, "longitude": None})
        self.assertEqual((data["latitude"], data["longitude"]), (None, None))

    def test_11_operations_cancel_or_delete_pending_reminders(self):
        for change in ({"scheduled_date": "2026-03-25"}, {"status": "completed"}, {"status": "cancelled"}, None):
            with self.subTest(change=change):
                operation = self.add_operation()
                reminder = Reminder.objects.create(operation_id=operation["id"], recipient=self.owner,
                                                   remind_at=timezone.now())
                path = f"/operations/{operation['id']}"
                if change is None:
                    self.request("delete", path, 204)
                    self.assertFalse(Reminder.objects.filter(pk=reminder.pk).exists())
                else:
                    self.request("patch", path, 200, change)
                    reminder.refresh_from_db()
                    self.assertEqual(reminder.status, "cancelled")
