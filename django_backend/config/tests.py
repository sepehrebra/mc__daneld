from django.test import SimpleTestCase, TestCase, override_settings
from rest_framework.exceptions import AuthenticationFailed, NotAuthenticated, NotFound, ValidationError
from config.errors import Conflict, exception_handler


@override_settings(ALLOWED_HOSTS=["testserver"], DEBUG=False)
class StartupTests(TestCase):
    def test_api_health_connects_to_test_database(self):
        response = self.client.get("/api/v1/health")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"status": "ok", "database": "connected"})

    def test_unknown_route_returns_json_404(self):
        response = self.client.get("/api/v1/does-not-exist")
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json(), {"detail": "Not found."})

    def test_cors_preflight(self):
        response = self.client.options("/api/v1/health", HTTP_ORIGIN="http://localhost:5173", HTTP_ACCESS_CONTROL_REQUEST_METHOD="PATCH", HTTP_ACCESS_CONTROL_REQUEST_HEADERS="authorization,content-type")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["access-control-allow-origin"], "http://localhost:5173")
        self.assertIn("PATCH", response["access-control-allow-methods"])


class ErrorTests(SimpleTestCase):
    def test_exception_statuses(self):
        for error, expected in [(ValidationError("invalid"), 422), (NotAuthenticated(), 401), (AuthenticationFailed(), 401), (NotFound(), 404), (Conflict(), 409)]:
            with self.subTest(expected=expected):
                self.assertEqual(exception_handler(error, {}).status_code, expected)
