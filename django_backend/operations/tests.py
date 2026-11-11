from datetime import date, datetime, timedelta, timezone as dt_timezone
from secrets import token_urlsafe
from unittest.mock import patch

from django.core.exceptions import ValidationError
from django.db import IntegrityError, connection, transaction
from django.db.models.query import QuerySet
from django.db.models.signals import post_delete
from django.test import TestCase
from django.utils import timezone
from rest_framework.exceptions import ValidationError as APIValidationError

from accounts.models import AuthSession, User
from accounts.authentication import token_digest
from farms.models import CropSeason, Farm, Plot
from operations.models import Operation, Reminder


class MigrationModelTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create(full_name="Test", phone="+989123456789", password_hash="hash")
        cls.other_user = User.objects.create(full_name="Other", phone="+989123456788", password_hash="hash")
        cls.farm = Farm.objects.create(owner=cls.user, name="Farm")
        cls.plot = Plot.objects.create(farm=cls.farm, name="Plot", code="A", area_m2=10)
        cls.other_plot = Plot.objects.create(farm=cls.farm, name="Other", area_m2=20)
        cls.season = CropSeason.objects.create(plot=cls.plot, crop_name="Wheat", start_date=date(2026, 1, 1))

    def assert_database_rejects(self, create):
        with self.assertRaises(IntegrityError), transaction.atomic():
            create()

    def create_operation(self, **overrides):
        values = {"plot": self.plot, "created_by": self.user, "title": "Water", "operation_type": "irrigation", "scheduled_date": date(2026, 1, 2)}
        values.update(overrides)
        return Operation.objects.create(**values)

    def test_seven_tables_and_integer_ids(self):
        tables = set(connection.introspection.table_names())
        self.assertTrue({"users", "auth_sessions", "farms", "plots", "crop_seasons", "operations", "reminders"}.issubset(tables))
        self.assertIsInstance(self.user.id, int)
        session = AuthSession.objects.create(user=self.user, token_hash="a" * 64, expires_at=timezone.now() + timedelta(hours=24))
        operation = self.create_operation(crop_season=self.season)
        reminder = Reminder.objects.create(operation=operation, recipient=self.user, remind_at=timezone.now())
        self.assertEqual(session.user_id, self.user.id)
        self.assertEqual(reminder.operation.crop_season_id, self.season.id)
        self.assertEqual((self.farm.timezone, self.season.status, operation.status, reminder.channel, reminder.status), ("Asia/Tehran", "planned", "planned", "in_app", "pending"))

    def test_plot_uniqueness_and_positive_area(self):
        self.assert_database_rejects(lambda: Plot.objects.create(farm=self.farm, name="Plot", area_m2=1))
        self.assert_database_rejects(lambda: Plot.objects.create(farm=self.farm, name="New", code="A", area_m2=1))
        for area in (0, -1):
            with self.subTest(area=area):
                self.assert_database_rejects(lambda: Plot.objects.create(farm=self.farm, name="Invalid", area_m2=area))
        Plot.objects.create(farm=self.farm, name="Null code", code=None, area_m2=1)

    def test_database_rejects_invalid_statuses_and_completion(self):
        self.assert_database_rejects(lambda: CropSeason.objects.create(plot=self.plot, crop_name="X", start_date=date(2026, 1, 1), status="invalid"))
        self.assert_database_rejects(lambda: self.create_operation(status="invalid"))
        self.assert_database_rejects(lambda: self.create_operation(status="completed"))
        self.assert_database_rejects(lambda: self.create_operation(status="planned", completed_at=timezone.now()))
        operation = self.create_operation(status="completed", completed_at=timezone.now())
        self.assert_database_rejects(lambda: Reminder.objects.create(operation=operation, recipient=self.user, remind_at=timezone.now(), status="invalid"))
        self.assert_database_rejects(lambda: Reminder.objects.create(operation=operation, recipient=self.user, remind_at=timezone.now(), attempt_count=-1))

    def test_season_dates_and_plot_relation(self):
        self.assert_database_rejects(lambda: CropSeason.objects.create(plot=self.plot, crop_name="X", start_date=date(2026, 2, 1), expected_end_date=date(2026, 1, 1)))
        self.assert_database_rejects(lambda: CropSeason.objects.create(plot=self.plot, crop_name="X", start_date=date(2026, 1, 1), actual_end_date=date(2026, 2, 1)))
        operation = Operation(plot=self.other_plot, crop_season=self.season, created_by=self.user, title="Water", operation_type="irrigation", scheduled_date=date(2026, 1, 2))
        with self.assertRaises(ValidationError):
            operation.full_clean()
        with self.assertRaises(ValidationError):
            operation.save()
        operation.plot = self.plot
        operation.full_clean()

    def test_coordinates_time_zone_and_recipient(self):
        self.assert_database_rejects(lambda: Farm.objects.create(owner=self.user, name="Bad", latitude=30))
        farm = Farm(owner=self.user, name="Bad zone", timezone="Not/AZone")
        with self.assertRaises(ValidationError):
            farm.full_clean()
        operation = self.create_operation()
        reminder = Reminder(operation=operation, recipient=self.other_user, remind_at=timezone.now())
        with self.assertRaises(ValidationError):
            reminder.full_clean()
        with self.assertRaises(ValidationError):
            reminder.save()

    def test_sqlite_triggers_reject_invalid_bulk_changes(self):
        operation = self.create_operation(crop_season=self.season)
        reminder = Reminder.objects.create(operation=operation, recipient=self.user, remind_at=timezone.now())
        foreign_farm = Farm.objects.create(owner=self.other_user, name="Foreign")
        foreign_plot = Plot.objects.create(farm=foreign_farm, name="Foreign plot", area_m2=1)
        foreign_operation = self.create_operation(plot=foreign_plot, crop_season=None)

        invalid_operation = Operation(plot=self.other_plot, crop_season=self.season, created_by=self.user, title="Invalid", operation_type="irrigation", scheduled_date=date(2026, 1, 2))
        self.assert_database_rejects(lambda: Operation.objects.bulk_create([invalid_operation]))
        self.assert_database_rejects(lambda: Operation.objects.filter(pk=operation.pk).update(plot=self.other_plot))
        self.assert_database_rejects(lambda: CropSeason.objects.filter(pk=self.season.pk).update(plot=self.other_plot))
        invalid_reminder = Reminder(operation=operation, recipient=self.other_user, remind_at=timezone.now())
        self.assert_database_rejects(lambda: Reminder.objects.bulk_create([invalid_reminder]))
        self.assert_database_rejects(lambda: Reminder.objects.filter(pk=reminder.pk).update(recipient=self.other_user))
        self.assert_database_rejects(lambda: Reminder.objects.filter(pk=reminder.pk).update(operation=foreign_operation))
        self.assert_database_rejects(lambda: Operation.objects.filter(pk=operation.pk).update(plot=foreign_plot, crop_season=None))
        self.assert_database_rejects(lambda: Plot.objects.filter(pk=self.plot.pk).update(farm=foreign_farm))
        self.assert_database_rejects(lambda: Farm.objects.filter(pk=self.farm.pk).update(owner=self.other_user))

    def test_raw_sql_and_valid_season_move(self):
        operation = self.create_operation(crop_season=self.season)

        def invalid_sql():
            with connection.cursor() as cursor:
                cursor.execute("UPDATE operations SET plot_id = %s WHERE id = %s", [self.other_plot.pk, operation.pk])

        self.assert_database_rejects(invalid_sql)
        # Temporarily unlink the season before moving both records atomically.
        with transaction.atomic():
            Operation.objects.filter(pk=operation.pk).update(crop_season=None)
            CropSeason.objects.filter(pk=self.season.pk).update(plot=self.other_plot)
            Operation.objects.filter(pk=operation.pk).update(plot=self.other_plot, crop_season=self.season)
        operation.refresh_from_db()
        self.assertEqual(operation.plot_id, operation.crop_season.plot_id)

    def test_relationship_triggers_are_installed(self):
        with connection.cursor() as cursor:
            cursor.execute("SELECT name FROM sqlite_master WHERE type = 'trigger'")
            names = {row[0] for row in cursor.fetchall()}
        self.assertTrue({"ops_season_insert", "ops_season_update", "season_plot_update", "rem_owner_insert", "rem_owner_update", "ops_plot_rem_owner", "plot_farm_rem_owner", "farm_owner_rem_owner"}.issubset(names))


class OperationWriteAPITests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create(full_name="A", phone="+989123456789", password_hash="unused")
        cls.other_user = User.objects.create(full_name="B", phone="+989123456788", password_hash="unused")
        cls.farm = Farm.objects.create(owner=cls.user, name="Tehran", timezone="Asia/Tehran")
        cls.second_farm = Farm.objects.create(owner=cls.user, name="Los Angeles", timezone="America/Los_Angeles")
        cls.other_farm = Farm.objects.create(owner=cls.other_user, name="Other")
        cls.plot = Plot.objects.create(farm=cls.farm, name="Plot", area_m2=10)
        cls.second_plot = Plot.objects.create(farm=cls.second_farm, name="Second", area_m2=10)
        cls.other_plot = Plot.objects.create(farm=cls.other_farm, name="Foreign", area_m2=10)

    def setUp(self):
        self.token = self.make_token(self.user)
        self.other_token = self.make_token(self.other_user)

    def make_token(self, user):
        token = token_urlsafe(32)
        AuthSession.objects.create(user=user, token_hash=token_digest(token.encode("ascii")), expires_at=timezone.now() + timedelta(days=10))
        return token

    def request_json(self, method, url, data=None, token=None):
        headers = {"HTTP_AUTHORIZATION": f"Bearer {token}"} if token else {}
        return getattr(self.client, method)(url, data=data, content_type="application/json", **headers)

    def create(self, token=None, **changes):
        data = {"plot_id": self.plot.pk, "operation_type": "irrigation", "scheduled_date": "2026-01-01"}
        data.update(changes)
        return self.request_json("post", "/api/v1/operations", data, token or self.token)

    def change(self, pk, data, token=None):
        return self.request_json("patch", f"/api/v1/operations/{pk}", data, token or self.token)

    def test_create_output_default_title_and_normalization(self):
        response = self.create(scheduled_time="08:30", description="  text  ", title=" ")
        self.assertEqual(response.status_code, 201)
        data = response.json()
        self.assertEqual(data, {"id": data["id"], "title": "آبیاری", "operation_type": "irrigation", "description": "text", "scheduled_date": "2026-01-01", "scheduled_time": "08:30", "status": "planned", "completed_date": None, "farm": {"id": self.farm.pk, "name": "Tehran"}, "plot": {"id": self.plot.pk, "name": "Plot"}})
        self.assertEqual(Operation.objects.get(pk=data["id"]).created_by_id, self.user.pk)
        self.assertEqual(response["Cache-Control"], "no-store")
        for operation_type, label in [("planting", "کاشت"), ("fertilizing", "کوددهی"), ("spraying", "سم‌پاشی"), ("harvesting", "برداشت"), ("other", "سایر")]:
            with self.subTest(operation_type=operation_type):
                self.assertEqual(self.create(operation_type=operation_type).json()["title"], label)

    def test_completion_date_uses_farm_timezone_and_utc(self):
        fixed_now = datetime(2026, 1, 1, 23, 30, tzinfo=dt_timezone.utc)
        with patch("operations.views.timezone.now", return_value=fixed_now):
            today = self.create(status="completed", completed_date="2026-01-02")
            self.assertEqual(today.status_code, 201)
            self.assertEqual(today.json()["completed_date"], "2026-01-02")
            self.assertEqual(Operation.objects.get(pk=today.json()["id"]).completed_at, fixed_now)
            historical = self.create(status="completed", completed_date="2025-12-30")
            self.assertEqual(historical.json()["completed_date"], "2025-12-30")
            self.assertEqual(Operation.objects.get(pk=historical.json()["id"]).completed_at, datetime(2025, 12, 30, 8, 30, tzinfo=dt_timezone.utc))
            los_angeles = self.create(plot_id=self.second_plot.pk, status="completed", completed_date="2026-01-01")
            self.assertEqual(los_angeles.json()["completed_date"], "2026-01-01")
            self.assertEqual(Operation.objects.get(pk=los_angeles.json()["id"]).completed_at, fixed_now)

    def test_all_status_transitions_and_edit_completed_date(self):
        created = self.create()
        pk = created.json()["id"]
        for target in ("completed", "in_progress", "cancelled", "planned", "completed", "cancelled", "completed"):
            with self.subTest(target=target):
                response = self.change(pk, {"status": target})
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.json()["status"], target)
                operation = Operation.objects.get(pk=pk)
                self.assertEqual(operation.completed_at is not None, target == "completed")
        response = self.change(pk, {"scheduled_date": "2026-03-01", "completed_date": "2026-02-01"})
        self.assertEqual((response.status_code, response.json()["scheduled_date"], response.json()["completed_date"]), (200, "2026-03-01", "2026-02-01"))
        self.assertEqual(self.change(pk, {"status": "planned"}).json()["completed_date"], None)

    def test_every_pair_of_statuses_is_allowed(self):
        statuses = ("planned", "in_progress", "completed", "cancelled")
        for source in statuses:
            for target in statuses:
                with self.subTest(source=source, target=target):
                    created = self.create(status=source)
                    self.assertEqual(created.status_code, 201)
                    pk = created.json()["id"]
                    previous_time = Operation.objects.get(pk=pk).completed_at
                    updated = self.change(pk, {"status": target})
                    self.assertEqual(updated.status_code, 200)
                    self.assertEqual(updated.json()["status"], target)
                    current_time = Operation.objects.get(pk=pk).completed_at
                    self.assertEqual(current_time is not None, target == "completed")
                    if source == target == "completed":
                        self.assertEqual(current_time, previous_time)

    def test_completed_date_is_cleared_when_leaving_completed(self):
        pk = self.create(status="completed").json()["id"]
        response = self.change(pk, {"status": "planned", "completed_date": "2026-01-01"})
        self.assertEqual(response.status_code, 200)
        self.assertIsNone(response.json()["completed_date"])
        self.assertIsNone(Operation.objects.get(pk=pk).completed_at)

    def test_update_plot_and_optional_fields(self):
        pk = self.create(title="  My title  ", description="details", scheduled_time="09:45").json()["id"]
        response = self.change(pk, {"plot_id": self.second_plot.pk, "description": " ", "scheduled_time": None, "title": " Edited "})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["farm"], {"id": self.second_farm.pk, "name": "Los Angeles"})
        self.assertEqual(response.json()["plot"]["id"], self.second_plot.pk)
        self.assertEqual((response.json()["title"], response.json()["description"], response.json()["scheduled_time"]), ("Edited", None, None))

    def test_invalid_data_returns_422_without_writing(self):
        cases = [{"operation_type": "bad"}, {"scheduled_date": "2026-1-1"}, {"scheduled_date": "2026-02-30"}, {"scheduled_time": "8:30"}, {"scheduled_time": "24:00"}, {"status": "bad"}, {"completed_date": "2026-01-01"}, {"created_by": self.other_user.pk}]
        for case in cases:
            with self.subTest(case=case):
                self.assertEqual(self.create(**case).status_code, 422)
        self.assertEqual(Operation.objects.count(), 0)
        pk = self.create().json()["id"]
        for data in ({"status": "planned", "completed_date": "2026-01-01"}, {"title": " "}, {"scheduled_date": None}, {"plot_id": 0}, {"result_notes": "unexpected"}):
            with self.subTest(data=data):
                self.assertEqual(self.change(pk, data).status_code, 422)
        self.assertEqual(Operation.objects.get(pk=pk).status, "planned")

    def test_crop_details_create_linked_season(self):
        response = self.create(operation_type="planting", crop_name="Wheat", variety="Spring")
        self.assertEqual(response.status_code, 201)
        operation = Operation.objects.get(pk=response.json()["id"])
        self.assertEqual((operation.crop_season.crop_name, operation.crop_season.variety, operation.crop_season.status), ("Wheat", "Spring", "planned"))
        self.assertEqual(operation.crop_season.start_date, date(2026, 1, 1))

    def test_planting_complete_revert_cancel_and_reopen(self):
        pk = self.create(operation_type="planting", crop_name="Wheat").json()["id"]
        season = Operation.objects.get(pk=pk).crop_season
        completed = self.change(pk, {"status": "completed", "completed_date": "2026-02-10"})
        self.assertEqual(completed.status_code, 200)
        season.refresh_from_db()
        self.assertEqual((season.status, season.actual_start_date), ("active", date(2026, 2, 10)))
        self.assertEqual(self.change(pk, {"completed_date": "2026-02-11"}).status_code, 200)
        season.refresh_from_db()
        self.assertEqual(season.actual_start_date, date(2026, 2, 11))
        self.assertEqual(self.change(pk, {"status": "planned"}).status_code, 200)
        season.refresh_from_db()
        self.assertEqual((season.status, season.actual_start_date), ("planned", None))
        self.assertEqual(self.change(pk, {"status": "cancelled"}).status_code, 200)
        season.refresh_from_db()
        self.assertEqual(season.status, "cancelled")
        self.assertEqual(self.change(pk, {"status": "in_progress"}).status_code, 200)
        season.refresh_from_db()
        self.assertEqual(season.status, "planned")

    def test_create_completed_or_cancelled_planting_and_without_crop(self):
        done = self.create(operation_type="planting", crop_name="Rice", status="completed", completed_date="2026-02-10")
        self.assertEqual(done.status_code, 201)
        season = Operation.objects.get(pk=done.json()["id"]).crop_season
        self.assertEqual((season.status, season.actual_start_date), ("active", date(2026, 2, 10)))
        cancelled = self.create(operation_type="planting", crop_name="Corn", status="cancelled")
        self.assertEqual(Operation.objects.get(pk=cancelled.json()["id"]).crop_season.status, "cancelled")
        bare = self.create(operation_type="planting", variety="Unspecified")
        self.assertIsNone(Operation.objects.get(pk=bare.json()["id"]).crop_season_id)

    def test_harvest_completes_most_recent_active_season_and_reverts(self):
        older = CropSeason.objects.create(plot=self.plot, crop_name="Old", start_date=date(2026, 1, 1), actual_start_date=date(2026, 1, 1), status="active")
        newest = CropSeason.objects.create(plot=self.plot, crop_name="New", start_date=date(2026, 1, 1), actual_start_date=date(2026, 1, 5), status="active")
        harvest = self.create(operation_type="harvesting", status="completed", completed_date="2026-03-01")
        self.assertEqual(harvest.status_code, 201)
        operation = Operation.objects.get(pk=harvest.json()["id"])
        self.assertEqual(operation.crop_season_id, newest.pk)
        newest.refresh_from_db()
        older.refresh_from_db()
        self.assertEqual((newest.status, newest.actual_end_date, older.status), ("completed", date(2026, 3, 1), "active"))
        self.assertEqual(self.change(operation.pk, {"completed_date": "2026-03-02"}).status_code, 200)
        newest.refresh_from_db()
        self.assertEqual(newest.actual_end_date, date(2026, 3, 2))
        self.assertEqual(self.change(operation.pk, {"status": "planned"}).status_code, 200)
        newest.refresh_from_db()
        operation.refresh_from_db()
        self.assertEqual((newest.status, newest.actual_end_date, operation.crop_season_id), ("active", None, None))

    def test_planting_move_transfers_planned_season_and_keeps_link(self):
        operation = Operation.objects.get(pk=self.create(operation_type="planting", crop_name="Wheat").json()["id"])
        season = operation.crop_season
        response = self.change(operation.pk, {"plot_id": self.second_plot.pk})
        self.assertEqual(response.status_code, 200)
        operation.refresh_from_db()
        season.refresh_from_db()
        self.assertEqual((operation.plot_id, operation.crop_season_id, season.plot_id, season.status), (self.second_plot.pk, season.pk, self.second_plot.pk, "planned"))
        self.assertEqual(self.change(operation.pk, {"status": "completed", "completed_date": "2026-02-10"}).status_code, 200)
        season.refresh_from_db()
        self.assertEqual((season.status, season.actual_start_date), ("active", date(2026, 2, 10)))

    def test_move_with_other_season_references_does_not_lose_data(self):
        operation = Operation.objects.get(pk=self.create(operation_type="planting", crop_name="Wheat").json()["id"])
        season = operation.crop_season
        Operation.objects.create(plot=self.plot, crop_season=season, created_by=self.user, title="other", operation_type="other", scheduled_date=date(2026, 1, 1))
        self.assertEqual(self.change(operation.pk, {"plot_id": self.second_plot.pk}).status_code, 409)
        operation.refresh_from_db()
        season.refresh_from_db()
        self.assertEqual((operation.plot_id, operation.crop_season_id, season.plot_id), (self.plot.pk, season.pk, self.plot.pk))

    def test_failed_move_rolls_back_unlink_and_season_transfer(self):
        operation = Operation.objects.get(pk=self.create(operation_type="planting", crop_name="Wheat").json()["id"])
        season = operation.crop_season
        with patch("operations.models.Operation.save", side_effect=APIValidationError("Simulated failure")):
            self.assertEqual(self.change(operation.pk, {"plot_id": self.second_plot.pk}).status_code, 422)
        operation.refresh_from_db()
        season.refresh_from_db()
        self.assertEqual((operation.plot_id, operation.crop_season_id, season.plot_id), (self.plot.pk, season.pk, self.plot.pk))

    def test_change_from_planting_to_other_preserves_season(self):
        operation = Operation.objects.get(pk=self.create(operation_type="planting", crop_name="Wheat", status="completed", completed_date="2026-02-01").json()["id"])
        season = operation.crop_season
        self.assertEqual(self.change(operation.pk, {"operation_type": "other"}).status_code, 200)
        operation.refresh_from_db()
        season.refresh_from_db()
        self.assertEqual((operation.crop_season_id, season.status, season.actual_start_date), (None, "planned", None))

    def test_move_completed_harvest_reopens_old_and_completes_new_season(self):
        first = CropSeason.objects.create(plot=self.plot, crop_name="A", start_date=date(2026, 1, 1), actual_start_date=date(2026, 1, 1), status="active")
        second = CropSeason.objects.create(plot=self.second_plot, crop_name="B", start_date=date(2026, 1, 1), actual_start_date=date(2026, 1, 1), status="active")
        operation = Operation.objects.get(pk=self.create(operation_type="harvesting", status="completed", completed_date="2026-02-01").json()["id"])
        self.assertEqual(self.change(operation.pk, {"plot_id": self.second_plot.pk}).status_code, 200)
        first.refresh_from_db()
        second.refresh_from_db()
        operation.refresh_from_db()
        self.assertEqual((first.status, first.actual_end_date, second.status, operation.crop_season_id), ("active", None, "completed", second.pk))

    def test_delete_only_planned_planting_season_and_preserve_references(self):
        planned = Operation.objects.get(pk=self.create(operation_type="planting", crop_name="Wheat").json()["id"])
        planned_id = planned.crop_season_id
        self.assertEqual(self.request_json("delete", f"/api/v1/operations/{planned.pk}", token=self.token).status_code, 204)
        self.assertFalse(CropSeason.objects.filter(pk=planned_id).exists())
        active = Operation.objects.get(pk=self.create(operation_type="planting", crop_name="Rice", status="completed", completed_date="2026-02-01").json()["id"])
        active_id = active.crop_season_id
        self.assertEqual(self.request_json("delete", f"/api/v1/operations/{active.pk}", token=self.token).status_code, 204)
        self.assertTrue(CropSeason.objects.filter(pk=active_id, status="active").exists())
        linked = Operation.objects.get(pk=self.create(operation_type="planting", crop_name="Corn").json()["id"])
        Operation.objects.create(plot=self.plot, crop_season=linked.crop_season, created_by=self.user, title="other", operation_type="other", scheduled_date=date(2026, 1, 1))
        self.assertEqual(self.request_json("delete", f"/api/v1/operations/{linked.pk}", token=self.token).status_code, 409)
        self.assertTrue(Operation.objects.filter(pk=linked.pk).exists())
        self.assertTrue(CropSeason.objects.filter(pk=linked.crop_season_id).exists())

    def test_invalid_harvest_date_rolls_back_all_changes(self):
        season = CropSeason.objects.create(plot=self.plot, crop_name="Wheat", start_date=date(2026, 2, 1), actual_start_date=date(2026, 2, 1), status="active")
        before = Operation.objects.count()
        response = self.create(operation_type="harvesting", status="completed", completed_date="2026-01-01")
        self.assertEqual(response.status_code, 422)
        season.refresh_from_db()
        self.assertEqual((season.status, season.actual_end_date, Operation.objects.count()), ("active", None, before))

    def test_edit_planting_after_harvest_does_not_reopen_or_lose_dates(self):
        planting = Operation.objects.get(pk=self.create(operation_type="planting", crop_name="Wheat", status="completed", completed_date="2026-02-01").json()["id"])
        harvest = self.create(operation_type="harvesting", status="completed", completed_date="2026-03-01")
        self.assertEqual(harvest.status_code, 201)
        season = planting.crop_season
        self.assertEqual(self.change(planting.pk, {"completed_date": "2026-02-05"}).status_code, 200)
        season.refresh_from_db()
        self.assertEqual((season.status, season.actual_start_date, season.actual_end_date), ("completed", date(2026, 2, 5), date(2026, 3, 1)))
        self.assertEqual(self.change(planting.pk, {"completed_date": "2026-04-01"}).status_code, 422)
        season.refresh_from_db()
        self.assertEqual((season.actual_start_date, season.actual_end_date), (date(2026, 2, 5), date(2026, 3, 1)))
        self.assertEqual(self.change(planting.pk, {"status": "planned"}).status_code, 422)
        planting.refresh_from_db()
        season.refresh_from_db()
        self.assertEqual((planting.status, season.status, season.actual_end_date), ("completed", "completed", date(2026, 3, 1)))
        self.assertEqual(self.change(harvest.json()["id"], {"status": "planned"}).status_code, 200)
        self.assertEqual(self.change(planting.pk, {"status": "planned"}).status_code, 200)
        season.refresh_from_db()
        self.assertEqual((season.status, season.actual_start_date, season.actual_end_date), ("planned", None, None))

    def test_ownership_and_auth(self):
        payload = {"plot_id": self.plot.pk, "operation_type": "other", "scheduled_date": "2026-01-01"}
        self.assertEqual(self.request_json("post", "/api/v1/operations", payload).status_code, 401)
        self.assertEqual(self.create(plot_id=self.other_plot.pk).status_code, 404)
        own_pk = self.create().json()["id"]
        foreign_pk = self.create(token=self.other_token, plot_id=self.other_plot.pk).json()["id"]
        self.assertEqual(self.change(foreign_pk, {"status": "completed"}).status_code, 404)
        self.assertEqual(self.request_json("delete", f"/api/v1/operations/{foreign_pk}", token=self.token).status_code, 404)
        self.assertEqual(self.change(own_pk, {"plot_id": self.other_plot.pk}).status_code, 404)
        self.assertEqual(self.change(999999, {"title": "x"}).status_code, 404)
        self.assertEqual(Operation.objects.get(pk=own_pk).plot_id, self.plot.pk)

    def test_delete_also_removes_dependent_reminders(self):
        pk = self.create().json()["id"]
        operation = Operation.objects.get(pk=pk)
        Reminder.objects.create(operation=operation, recipient=self.user, remind_at=timezone.now())
        response = self.request_json("delete", f"/api/v1/operations/{pk}", token=self.token)
        self.assertEqual(response.status_code, 204)
        self.assertFalse(Operation.objects.filter(pk=pk).exists())
        self.assertFalse(Reminder.objects.filter(operation_id=pk).exists())


class OperationReminderTests(TestCase):
    setUpTestData = classmethod(OperationWriteAPITests.setUpTestData.__func__)
    setUp = OperationWriteAPITests.setUp
    make_token = OperationWriteAPITests.make_token
    request_json = OperationWriteAPITests.request_json
    create = OperationWriteAPITests.create
    change = OperationWriteAPITests.change

    def reminder(self, operation, status="pending", **changes):
        values = dict(operation=operation, recipient=self.user, remind_at=timezone.now(), status=status,
                      last_error="private delivery failure")
        values.update(changes)
        return Reminder.objects.create(**values)

    def test_date_change_completion_and_cancellation_cancel_only_unsent(self):
        for payload in ({"scheduled_date": "2026-02-01"}, {"status": "completed"}, {"status": "cancelled"}):
            with self.subTest(payload=payload):
                operation = Operation.objects.get(pk=self.create().json()["id"])
                reminders = [self.reminder(operation, status) for status in ("pending", "processing", "failed", "sent", "cancelled")]
                delivered = self.reminder(operation, "processing", sent_at=timezone.now())
                untouched = self.reminder(Operation.objects.get(pk=self.create().json()["id"]))
                old_time = timezone.now() - timedelta(days=1)
                Reminder.objects.filter(pk__in=[r.pk for r in reminders]).update(updated_at=old_time)
                response = self.change(operation.pk, payload)
                self.assertEqual(response.status_code, 200)
                for reminder, expected in zip(reminders, ("cancelled", "cancelled", "cancelled", "sent", "cancelled")):
                    reminder.refresh_from_db()
                    self.assertEqual(reminder.status, expected)
                self.assertGreater(reminders[0].updated_at, old_time)
                delivered.refresh_from_db()
                untouched.refresh_from_db()
                self.assertEqual((delivered.status, untouched.status), ("processing", "pending"))
                self.assertEqual(operation.reminders.count(), 6)  # No automatic replacement.

    def test_unrelated_edits_and_identical_date_preserve_reminders(self):
        operation = Operation.objects.get(pk=self.create().json()["id"])
        reminder = self.reminder(operation)
        for payload in ({}, {"title": "Edited"}, {"scheduled_date": "2026-01-01"},
                        {"scheduled_time": "09:00"}, {"status": "in_progress"}):
            self.assertEqual(self.change(operation.pk, payload).status_code, 200)
            reminder.refresh_from_db()
            self.assertEqual(reminder.status, "pending")

    def test_reopening_does_not_reactivate_or_replace_cancelled_reminders(self):
        operation = Operation.objects.get(pk=self.create().json()["id"])
        reminder = self.reminder(operation)
        self.assertEqual(self.change(operation.pk, {"status": "completed"}).status_code, 200)
        self.assertEqual(self.change(operation.pk, {"status": "planned"}).status_code, 200)
        reminder.refresh_from_db()
        self.assertEqual(reminder.status, "cancelled")
        self.assertEqual(operation.reminders.count(), 1)

    def test_reminder_failure_rolls_back_operation_season_and_reminders(self):
        operation = Operation.objects.get(pk=self.create(operation_type="planting", crop_name="Wheat").json()["id"])
        reminder = self.reminder(operation)
        real_update = QuerySet.update

        def fail_after_reminder_update(queryset, **values):
            result = real_update(queryset, **values)
            if queryset.model is Reminder:
                raise APIValidationError("Simulated persistence failure")
            return result

        with patch.object(QuerySet, "update", fail_after_reminder_update):
            response = self.change(operation.pk, {"status": "completed", "completed_date": "2026-02-01"})
        self.assertEqual(response.status_code, 422)
        operation.refresh_from_db()
        reminder.refresh_from_db()
        self.assertEqual((operation.status, operation.completed_at, reminder.status), ("planned", None, "pending"))
        self.assertEqual((operation.crop_season.status, operation.crop_season.actual_start_date), ("planned", None))

    def test_invalid_or_foreign_updates_leave_reminders_unchanged(self):
        operation = Operation.objects.get(pk=self.create().json()["id"])
        reminder = self.reminder(operation)
        self.assertEqual(self.change(operation.pk, {"scheduled_date": "invalid"}).status_code, 422)
        self.assertEqual(self.change(operation.pk, {"status": "completed"}, token=self.other_token).status_code, 404)
        self.assertEqual(self.request_json("delete", f"/api/v1/operations/{operation.pk}", token=self.other_token).status_code, 404)
        reminder.refresh_from_db()
        self.assertEqual(reminder.status, "pending")

    def test_delete_removes_all_reminders_and_rolls_back_on_failure(self):
        operation = Operation.objects.get(pk=self.create().json()["id"])
        for status, _ in Reminder.STATUSES:
            self.reminder(operation, status)

        def fail_delete(sender, instance, **kwargs):
            raise APIValidationError("Simulated delete failure")

        post_delete.connect(fail_delete, sender=Operation)
        try:
            response = self.request_json("delete", f"/api/v1/operations/{operation.pk}", token=self.token)
            self.assertEqual(response.status_code, 422)
        finally:
            post_delete.disconnect(fail_delete, sender=Operation)
        self.assertTrue(Operation.objects.filter(pk=operation.pk).exists())
        self.assertEqual(operation.reminders.count(), 5)
        response = self.request_json("delete", f"/api/v1/operations/{operation.pk}", token=self.token)
        self.assertEqual(response.status_code, 204)
        self.assertFalse(Reminder.objects.filter(operation_id=operation.pk).exists())

    def test_recipient_is_owner_and_private_delivery_errors_are_not_exposed(self):
        operation = Operation.objects.get(pk=self.create().json()["id"])
        with self.assertRaises(ValidationError):
            self.reminder(operation, recipient=self.other_user)
        self.reminder(operation)
        response = self.change(operation.pk, {"scheduled_date": "2026-02-01"})
        responses = [response] + [self.request_json("get", url, token=self.token) for url in (
            "/api/v1/operations", "/api/v1/operations/calendar?from=2026-02-01&to=2026-02-28",
            f"/api/v1/farms/{self.farm.pk}", f"/api/v1/plots/{self.plot.pk}")]
        for response in responses:
            self.assertEqual(response.status_code, 200)
            self.assertNotIn(b"last_error", response.content)
            self.assertNotIn(b"private delivery failure", response.content)


class OperationListAndCalendarAPITests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create(full_name="A", phone="+989123456789", password_hash="unused")
        cls.other_user = User.objects.create(full_name="B", phone="+989123456788", password_hash="unused")
        cls.farm = Farm.objects.create(owner=cls.user, name="Tehran", timezone="Asia/Tehran")
        cls.plot = Plot.objects.create(farm=cls.farm, name="Plot", area_m2=10)
        cls.other_farm = Farm.objects.create(owner=cls.other_user, name="Other")
        cls.other_plot = Plot.objects.create(farm=cls.other_farm, name="Foreign", area_m2=10)

    def setUp(self):
        self.token = token_urlsafe(32)
        AuthSession.objects.create(
            user=self.user,
            token_hash=token_digest(self.token.encode("ascii")),
            expires_at=timezone.now() + timedelta(days=10),
        )

    def get(self, url):
        return self.client.get(url, HTTP_AUTHORIZATION=f"Bearer {self.token}")

    def operation(self, scheduled_date, *, status="planned", completed_at=None, plot=None):
        return Operation.objects.create(
            plot=plot or self.plot,
            created_by=self.user,
            title="Operation",
            operation_type="irrigation",
            scheduled_date=scheduled_date,
            status=status,
            completed_at=completed_at,
        )

    def test_search_filters_paginates_and_keeps_overdue_operations_first(self):
        operations = [self.operation(date(2026, 1, day)) for day in range(1, 26)]
        self.operation(date(2026, 1, 1), plot=self.other_plot)

        first_page = self.get(
            f"/api/v1/operations?from=2026-01-01&to=2026-01-25&farm={self.farm.pk}"
            f"&plot={self.plot.pk}&status=planned,in_progress&sort=date&order=asc&limit=20"
        )
        self.assertEqual(first_page.status_code, 200)
        self.assertEqual([item["id"] for item in first_page.json()], [operation.pk for operation in operations[:20]])

        second_page = self.get(
            f"/api/v1/operations?farm={self.farm.pk}&plot={self.plot.pk}&status=planned"
            "&sort=date&order=asc&limit=20&offset=20"
        )
        self.assertEqual(second_page.status_code, 200)
        self.assertEqual([item["id"] for item in second_page.json()], [operation.pk for operation in operations[20:]])

    def test_calendar_uses_completion_date_and_includes_cancelled_operations(self):
        completed = self.operation(
            date(2026, 1, 4),
            status="completed",
            completed_at=datetime(2026, 1, 10, 8, 30, tzinfo=dt_timezone.utc),
        )
        cancelled = self.operation(date(2026, 1, 3), status="cancelled")
        outside = self.operation(date(2026, 1, 11))

        response = self.get("/api/v1/operations/calendar?from=2026-01-01&to=2026-01-10")
        self.assertEqual(response.status_code, 200)
        self.assertEqual([item["id"] for item in response.json()], [cancelled.pk, completed.pk])
        self.assertNotIn(outside.pk, [item["id"] for item in response.json()])

        self.assertEqual(self.get("/api/v1/operations/calendar?from=2026-01-01&to=2026-03-05").status_code, 422)
