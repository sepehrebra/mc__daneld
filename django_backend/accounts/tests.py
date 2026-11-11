from datetime import timedelta

from django.contrib.auth.hashers import check_password
from django.core.cache import cache
from django.test import TestCase, override_settings
from django.utils import timezone

from accounts.authentication import token_digest
from accounts.models import AuthSession, User


@override_settings(ALLOWED_HOSTS=["testserver"])
class AuthenticationTests(TestCase):
    def setUp(self):
        cache.clear()

    def tearDown(self):
        cache.clear()

    def post_json(self, url, payload, **headers):
        return self.client.post(url, payload, content_type="application/json", **headers)

    def register(self, **fields):
        payload = {"full_name": "  Test User  ", "phone": "۰۹۱۲۳۴۵۶۷۸۹", "password": "secure-password"}
        payload.update(fields)
        return self.post_json("/api/v1/auth/register", payload)

    def login(self, **fields):
        payload = {"phone": "+989123456789", "password": "secure-password"}
        payload.update(fields)
        return self.post_json("/api/v1/auth/login", payload)

    def test_registration_normalizes_and_hides_secrets(self):
        response = self.register(email=" User@Example.com ")
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json(), {"id": User.objects.get().pk, "full_name": "Test User", "phone": "+989123456789", "email": "user@example.com"})
        self.assertEqual(response["Cache-Control"], "no-store")
        user = User.objects.get()
        self.assertTrue(user.password_hash.startswith("argon2$"))
        self.assertTrue(check_password("secure-password", user.password_hash))
        self.assertEqual(self.register().status_code, 409)
        self.assertEqual(self.register(phone="09123456788", email="USER@example.com").status_code, 409)

    def test_bad_registration_is_422(self):
        for fields in ({"phone": "123"}, {"phone": "+14155552671"}, {"password": "short"}, {"password": "x" * 129}, {"full_name": "   "}, {"email": "invalid"}):
            with self.subTest(fields=fields):
                self.assertEqual(self.register(**fields).status_code, 422)
        self.assertEqual(User.objects.count(), 0)

    @override_settings(SESSION_TTL_HOURS=2)
    def test_login_session_hash_me_and_logout(self):
        self.register()
        before = timezone.now()
        response = self.login()
        self.assertEqual(response.status_code, 200)
        token = response.json()["access_token"]
        self.assertEqual(response.json()["token_type"], "bearer")
        self.assertTrue(response.json()["expires_at"].endswith("Z"))
        session = AuthSession.objects.get()
        self.assertEqual(session.token_hash, token_digest(token.encode("ascii")))
        self.assertNotEqual(session.token_hash, token)
        self.assertGreaterEqual(session.expires_at, before + timedelta(hours=2))
        headers = {"HTTP_AUTHORIZATION": f"Bearer {token}"}
        me = self.client.get("/api/v1/auth/me", **headers)
        self.assertEqual(me.status_code, 200)
        self.assertEqual(set(me.json()), {"id", "full_name", "phone", "email"})
        self.assertEqual(self.post_json("/api/v1/auth/logout", {}, **headers).status_code, 204)
        session.refresh_from_db()
        self.assertIsNotNone(session.revoked_at)
        self.assertEqual(self.client.get("/api/v1/auth/me", **headers).status_code, 401)

    def test_invalid_expired_and_inactive_sessions(self):
        self.register()
        for header in (None, "Bearer invalid", "Basic invalid", "Bearer", "Bearer " + "x" * 1025):
            headers = {"HTTP_AUTHORIZATION": header} if header else {}
            self.assertEqual(self.client.get("/api/v1/auth/me", **headers).status_code, 401)
        token = self.login().json()["access_token"]
        headers = {"HTTP_AUTHORIZATION": f"Bearer {token}"}
        AuthSession.objects.update(expires_at=timezone.now() - timedelta(seconds=1))
        self.assertEqual(self.client.get("/api/v1/auth/me", **headers).status_code, 401)
        AuthSession.objects.update(expires_at=timezone.now() + timedelta(hours=1))
        User.objects.update(is_active=False)
        self.assertEqual(self.client.get("/api/v1/auth/me", **headers).status_code, 401)
        self.assertEqual(self.login().status_code, 401)

    def test_wrong_password_and_unknown_phone_match(self):
        self.register()
        wrong = self.login(password="wrong-password")
        unknown = self.login(phone="09123456788", password="wrong-password")
        self.assertEqual((wrong.status_code, unknown.status_code), (401, 401))
        self.assertEqual(wrong.json(), unknown.json())

    def test_logout_revokes_only_current_session(self):
        self.assertEqual(self.register(email="").status_code, 201)
        first = self.login(phone="٠٩١٢٣٤٥٦٧٨٩").json()["access_token"]
        second = self.login().json()["access_token"]
        self.assertNotEqual(first, second)
        self.assertEqual(self.post_json("/api/v1/auth/logout", {}, HTTP_AUTHORIZATION=f"Bearer {first}").status_code, 204)
        self.assertEqual(self.client.get("/api/v1/auth/me", HTTP_AUTHORIZATION=f"Bearer {first}").status_code, 401)
        self.assertEqual(self.client.get("/api/v1/auth/me", HTTP_AUTHORIZATION=f"Bearer {second}").status_code, 200)

    def test_login_throttle(self):
        for _ in range(10):
            self.assertEqual(self.login(phone="bad").status_code, 422)
        response = self.login(phone="bad")
        self.assertEqual(response.status_code, 429)
        self.assertIn("Retry-After", response)
