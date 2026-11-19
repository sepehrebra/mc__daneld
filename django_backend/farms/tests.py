from datetime import date, datetime, timedelta, timezone as dt_timezone
from secrets import token_urlsafe
from unittest.mock import patch

from django.db import connection
from django.test import TestCase, override_settings
from django.test.utils import CaptureQueriesContext
from django.utils import timezone

from accounts.authentication import token_digest
from accounts.models import AuthSession, User
from farms.models import CropSeason, Farm, Plot
from operations.models import Operation


@override_settings(ALLOWED_HOSTS=["testserver"])
class FarmPlotAPITests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user_a = User.objects.create(full_name="A", phone="+989123456789", password_hash="unused")
        cls.user_b = User.objects.create(full_name="B", phone="+989123456788", password_hash="unused")
        cls.farm_a = Farm.objects.create(owner=cls.user_a, name="A farm")
        cls.farm_b = Farm.objects.create(owner=cls.user_b, name="B farm")
        cls.plot_a = Plot.objects.create(farm=cls.farm_a, name="A plot", code="A1", area_m2=10)
        cls.plot_b = Plot.objects.create(farm=cls.farm_b, name="B plot", code="B1", area_m2=20)

    def setUp(self):
        self.token_a = self.create_token(self.user_a)
        self.token_b = self.create_token(self.user_b)

    def create_token(self, user):
        token = token_urlsafe(32)
        AuthSession.objects.create(user=user, token_hash=token_digest(token.encode("ascii")), expires_at=timezone.now() + timedelta(hours=1))
        return token

    def call(self, method, path, data=None, token=None):
        headers = {"HTTP_AUTHORIZATION": f"Bearer {token}"} if token else {}
        return getattr(self.client, method)(path, data=data, content_type="application/json", **headers)

    def test_list_is_lightweight_sorted_and_owner_scoped(self):
        extra = Plot.objects.create(farm=self.farm_a, name="Second", area_m2=1)
        second_farm = Farm.objects.create(owner=self.user_a, name="Second farm")
        self.assertEqual(self.call("get", "/api/v1/farms").status_code, 401)
        response = self.call("get", "/api/v1/farms", token=self.token_a)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), [
            {"id": self.farm_a.pk, "name": "A farm", "plots": [{"id": self.plot_a.pk, "name": "A plot"}, {"id": extra.pk, "name": "Second"}]},
            {"id": second_farm.pk, "name": "Second farm", "plots": []},
        ])
        self.assertEqual(response["Cache-Control"], "no-store")
        self.assertEqual(self.call("get", "/api/v1/farms", token=self.token_b).json()[0]["id"], self.farm_b.pk)

    def test_create_farm_input_output_and_ownership(self):
        response = self.call("post", "/api/v1/farms", {"name": " New farm ", "address": "  ", "description": "  hello  "}, self.token_a)
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json()["name"], "New farm")
        self.assertIsNone(response.json()["address"])
        self.assertEqual(response.json()["description"], "hello")
        self.assertEqual(response.json()["timezone"], "Asia/Tehran")
        self.assertEqual(response.json()["plots"], [])
        self.assertEqual(Farm.objects.get(pk=response.json()["id"]).owner_id, self.user_a.pk)
        for payload in ({"name": "  "}, {"name": None}, {"name": "X" * 121}, {"name": "ok", "owner_id": self.user_b.pk}):
            with self.subTest(payload=payload):
                self.assertEqual(self.call("post", "/api/v1/farms", payload, self.token_a).status_code, 422)

    def test_farm_patch_coordinates_and_text(self):
        url = f"/api/v1/farms/{self.farm_a.pk}"
        for payload in ({"latitude": 30}, {"latitude": None}, {"latitude": 30, "longitude": None}, {"latitude": 91, "longitude": 50}, {"latitude": "NaN", "longitude": 50}, {"name": None}, {"name": " "}, {"timezone": "UTC"}):
            with self.subTest(payload=payload):
                self.assertEqual(self.call("patch", url, payload, self.token_a).status_code, 422)
        response = self.call("patch", url, {"latitude": 35.7, "longitude": 51.4, "city": "  تهران  ", "address": "   "}, self.token_a)
        self.assertEqual(response.status_code, 200)
        self.assertEqual((response.json()["latitude"], response.json()["longitude"], response.json()["city"], response.json()["address"]), (35.7, 51.4, "تهران", None))
        self.assertEqual(response.json()["plots"][0]["id"], self.plot_a.pk)
        response = self.call("patch", url, {"latitude": None, "longitude": None}, self.token_a)
        self.assertEqual(response.status_code, 200)
        self.assertIsNone(response.json()["latitude"])
        self.assertIsNone(response.json()["longitude"])

    def test_plot_create_update_conflicts_and_validation(self):
        collection = f"/api/v1/farms/{self.farm_a.pk}/plots"
        for payload in ({"name": "A plot", "area_m2": 1}, {"name": "New", "code": "A1", "area_m2": 1}):
            self.assertEqual(self.call("post", collection, payload, self.token_a).status_code, 409)
        for payload in ({"name": "New", "area_m2": 0}, {"name": "New", "area_m2": -1}, {"name": "New", "area_m2": "NaN"}, {"name": "New", "area_m2": True}, {"name": "", "area_m2": 1}):
            with self.subTest(payload=payload):
                self.assertEqual(self.call("post", collection, payload, self.token_a).status_code, 422)
        response = self.call("post", collection, {"name": " New ", "code": " ", "area_m2": 12, "soil_type": " loam "}, self.token_a)
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json(), {"id": response.json()["id"], "name": "New", "code": None, "area_m2": 12.0, "soil_type": "loam", "description": None})
        url = f"/api/v1/plots/{response.json()['id']}"
        self.assertEqual(self.call("patch", url, {"name": "A plot"}, self.token_a).status_code, 409)
        self.assertEqual(self.call("patch", url, {"code": "A1"}, self.token_a).status_code, 409)
        self.assertEqual(self.call("patch", url, {"area_m2": None}, self.token_a).status_code, 422)
        self.assertEqual(self.call("patch", url, {"name": None}, self.token_a).status_code, 422)
        updated = self.call("patch", url, {"code": " C2 ", "area_m2": 25, "soil_type": " "}, self.token_a)
        self.assertEqual((updated.status_code, updated.json()["code"], updated.json()["area_m2"], updated.json()["soil_type"]), (200, "C2", 25, None))
        other_farm = Farm.objects.create(owner=self.user_a, name="Other")
        self.assertEqual(self.call("post", f"/api/v1/farms/{other_farm.pk}/plots", {"name": "A plot", "code": "A1", "area_m2": 1}, self.token_a).status_code, 201)

    def test_other_users_resources_are_hidden(self):
        requests = [
            ("patch", f"/api/v1/farms/{self.farm_b.pk}", {"name": "stolen"}),
            ("post", f"/api/v1/farms/{self.farm_b.pk}/plots", {"name": "stolen", "area_m2": 1}),
            ("patch", f"/api/v1/plots/{self.plot_b.pk}", {"name": "stolen"}),
            ("patch", "/api/v1/farms/999999", {"name": "missing"}),
            ("patch", "/api/v1/plots/999999", {"name": "missing"}),
        ]
        for method, url, payload in requests:
            with self.subTest(url=url):
                self.assertEqual(self.call(method, url, payload, self.token_a).status_code, 404)
        self.farm_b.refresh_from_db()
        self.plot_b.refresh_from_db()
        self.assertEqual((self.farm_b.name, self.plot_b.name), ("B farm", "B plot"))

    def test_registration_login_and_farm_workflow(self):
        signup = self.call("post", "/api/v1/auth/register", {"full_name": "New User", "phone": "09123456787", "password": "safe-password"})
        self.assertEqual(signup.status_code, 201)
        login = self.call("post", "/api/v1/auth/login", {"phone": "09123456787", "password": "safe-password"})
        self.assertEqual(login.status_code, 200)
        token = login.json()["access_token"]
        farm = self.call("post", "/api/v1/farms", {"name": "New farm"}, token)
        self.assertEqual(farm.status_code, 201)
        plot = self.call("post", f"/api/v1/farms/{farm.json()['id']}/plots", {"name": "New plot", "area_m2": 25}, token)
        self.assertEqual(plot.status_code, 201)
        self.assertEqual(self.call("get", "/api/v1/farms", token=token).json(), [{"id": farm.json()["id"], "name": "New farm", "plots": [{"id": plot.json()["id"], "name": "New plot"}]}])
        self.assertEqual(self.call("post", "/api/v1/auth/logout", {}, token).status_code, 204)
        self.assertEqual(self.call("get", "/api/v1/farms", token=token).status_code, 401)


class FarmPlotDetailTests(TestCase):
    setUpTestData = classmethod(FarmPlotAPITests.setUpTestData.__func__)
    setUp = FarmPlotAPITests.setUp
    create_token = FarmPlotAPITests.create_token
    call = FarmPlotAPITests.call

    def operation(self, **changes):
        values = dict(plot=self.plot_a, created_by=self.user_a, title="Water", operation_type="irrigation",
                      scheduled_date=date(2026, 1, 2))
        values.update(changes)
        return Operation.objects.create(**values)

    def detail(self, kind="plots", pk=None):
        pk = pk or (self.plot_a.pk if kind == "plots" else self.farm_a.pk)
        response = self.call("get", f"/api/v1/{kind}/{pk}", token=self.token_a)
        self.assertEqual(response.status_code, 200, response.content)
        return response.json()

    def test_empty_details_match_contract(self):
        expected = dict(id=self.plot_a.pk, name="A plot", code="A1", area_m2=10.0,
                        soil_type=None, description=None, today_count=0, overdue_count=0, current_season=None)
        self.assertEqual(self.detail(), dict(expected, farm={"id": self.farm_a.pk, "name": "A farm"},
                         last_done={"irrigation": None, "fertilizing": None, "spraying": None},
                         next_operations=[], recent_operations=[]))
        farm = self.detail("farms")
        self.assertEqual(farm, dict(id=self.farm_a.pk, name="A farm", province=None, city=None,
                         address=None, latitude=None, longitude=None, timezone="Asia/Tehran", description=None,
                         plots=[dict(expected, next_operation=None, last_irrigation_at=None)]))

    def test_counts_use_farm_day_and_exclude_closed_operations(self):
        overdue = self.operation(scheduled_date=date(2026, 1, 1))
        self.operation(status="in_progress")
        self.operation(scheduled_date=date(2026, 1, 3))
        self.operation(status="cancelled")
        self.operation(status="completed", completed_at=datetime(2026, 1, 1, 20, tzinfo=dt_timezone.utc))
        self.operation(plot=self.plot_b)
        # UTC January 1 is already January 2 in Tehran, but January 1 in Los Angeles.
        with patch("django.utils.timezone.now", return_value=datetime(2026, 1, 1, 22, tzinfo=dt_timezone.utc)):
            for zone, counts in (("Asia/Tehran", (1, 1)), ("America/Los_Angeles", (1, 0))):
                self.farm_a.timezone = zone
                self.farm_a.save()
                plot = self.detail()
                summary = self.detail("farms")["plots"][0]
                for item in (plot, summary):
                    self.assertEqual((item["today_count"], item["overdue_count"]), counts)
                self.assertEqual(summary["next_operation"], dict(id=overdue.pk, title="Water",
                                 operation_type="irrigation", scheduled_date="2026-01-01", scheduled_time=None))
                self.assertEqual(plot["next_operations"][0]["id"], overdue.pk)

    def test_operation_limits_order_and_last_done(self):
        future = self.operation(scheduled_date=date(2026, 1, 3))
        late = self.operation(scheduled_time="09:00")
        early = self.operation(scheduled_time="08:00")
        tie = self.operation(scheduled_time="08:00")
        done = []
        for day, kind in ((1, "irrigation"), (2, "spraying"), (3, "fertilizing"), (4, "irrigation")):
            done.append(self.operation(operation_type=kind, status="completed",
                        completed_at=datetime(2026, 1, day, 8, tzinfo=dt_timezone.utc)))
        self.operation(operation_type="spraying", status="cancelled")
        data = self.detail()
        self.assertEqual([x["id"] for x in data["next_operations"]], [early.pk, tie.pk, late.pk])
        self.assertEqual([x["id"] for x in data["recent_operations"]], [done[3].pk, done[2].pk, done[1].pk])
        self.assertEqual(data["last_done"], dict(irrigation="2026-01-04T08:00:00Z",
                         fertilizing="2026-01-03T08:00:00Z", spraying="2026-01-02T08:00:00Z"))
        self.assertEqual(self.detail("farms")["plots"][0]["last_irrigation_at"], "2026-01-04T08:00:00Z")
        self.assertEqual(set(data["next_operations"][0]), {"id", "title", "operation_type", "description",
                         "scheduled_date", "scheduled_time", "status", "completed_date", "farm", "plot"})

    def test_current_season_prefers_active_then_newest_planned(self):
        active = CropSeason.objects.create(plot=self.plot_a, crop_name="Wheat", start_date=date(2026, 1, 1),
                                          actual_start_date=date(2026, 1, 2), status="active")
        planned = CropSeason.objects.create(plot=self.plot_a, crop_name="Rice", start_date=date(2026, 5, 1))
        newest = CropSeason.objects.create(plot=self.plot_a, crop_name="Corn", start_date=date(2026, 4, 1))
        for kind in ("plots", "farms"):
            data = self.detail(kind)
            item = data if kind == "plots" else data["plots"][0]
            self.assertEqual(item["current_season"], dict(crop_name="Wheat", variety=None,
                             start_date="2026-01-01", actual_start_date="2026-01-02", status="active"))
        active.status = "completed"
        active.save()
        # Imported planned rows may retain a historical actual start; creation still wins.
        planned.actual_start_date = date(2026, 2, 1)
        planned.save()
        self.assertEqual(self.detail()["current_season"]["crop_name"], "Corn")
        CropSeason.objects.filter(pk__in=[planned.pk, newest.pk]).update(status="cancelled")
        self.assertIsNone(self.detail()["current_season"])

    def test_details_require_auth_and_hide_foreign_and_missing_resources(self):
        for kind, own, foreign in (("farms", self.farm_a.pk, self.farm_b.pk), ("plots", self.plot_a.pk, self.plot_b.pk)):
            self.assertEqual(self.call("get", f"/api/v1/{kind}/{own}").status_code, 401)
            for pk in (foreign, 999999):
                self.assertEqual(self.call("get", f"/api/v1/{kind}/{pk}", token=self.token_a).status_code, 404)

    def test_farm_query_count_does_not_grow_per_plot(self):
        self.operation()
        CropSeason.objects.create(plot=self.plot_a, crop_name="Wheat", start_date=date(2026, 1, 1))
        with CaptureQueriesContext(connection) as small:
            self.detail("farms")
        ids = [self.plot_a.pk]
        for index in range(8):
            plot = Plot.objects.create(farm=self.farm_a, name=f"Extra {index}", area_m2=1)
            ids.append(plot.pk)
            self.operation(plot=plot)
            CropSeason.objects.create(plot=plot, crop_name="Rice", start_date=date(2026, 1, 1))
        with CaptureQueriesContext(connection) as large:
            data = self.detail("farms")
        self.assertEqual([plot["id"] for plot in data["plots"]], ids)
        self.assertEqual(len(large), len(small))
        self.assertLessEqual(len(large), 6)
