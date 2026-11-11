from datetime import timedelta
from secrets import token_urlsafe

from django.test import TestCase, override_settings
from django.utils import timezone

from accounts.authentication import token_digest
from accounts.models import AuthSession, User
from farms.models import Farm, Plot


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
