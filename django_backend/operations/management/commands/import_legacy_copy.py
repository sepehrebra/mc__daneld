import os
import sqlite3
from contextlib import closing
from datetime import datetime, timezone
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.db import IntegrityError, connection, models, transaction

from accounts.models import AuthSession, User
from farms.models import CropSeason, Farm, Plot
from operations.models import Operation, Reminder


# Foreign keys point to an earlier table in this list. Sessions are not migrated.
IMPORT_ORDER = (User, Farm, Plot, CropSeason, Operation, Reminder)


class Command(BaseCommand):
    help = "Rehearse the FastAPI data transfer from a SQLite copy into an empty Django database."

    def add_arguments(self, parser):
        parser.add_argument("--source-copy", required=True, type=Path)

    def handle(self, *args, source_copy, **options):
        if not os.environ.get("DJANGO_DATABASE_PATH"):
            raise CommandError("Set DJANGO_DATABASE_PATH to an empty, migrated rehearsal database.")
        source = source_copy.resolve()
        target = Path(connection.settings_dict["NAME"]).resolve()
        original = (Path(__file__).resolve().parents[4] / "data" / "farm.db").resolve()
        if source in (target, original) or target == original or not source.is_file():
            raise CommandError("Use a separate copy of the legacy database and a separate Django target.")

        try:
            with closing(sqlite3.connect(source.as_uri() + "?mode=ro", uri=True)) as legacy, transaction.atomic():
                legacy.row_factory = sqlite3.Row
                if any(model.objects.exists() for model in (*IMPORT_ORDER, AuthSession)):
                    raise CommandError("The Django target must be empty.")
                id_maps = {}
                for model in IMPORT_ORDER:
                    self.copy_table(legacy, model, id_maps)
                connection.check_constraints()
        except (IntegrityError, sqlite3.Error, KeyError, ValueError, IndexError) as exc:
            raise CommandError("Legacy data could not be imported. Check schema and data constraints on the copy.") from exc

        counts = ", ".join(f"{model._meta.db_table}={len(id_maps[model])}" for model in IMPORT_ORDER)
        self.stdout.write(self.style.SUCCESS(f"Imported {counts}. Existing sessions require a fresh login."))

    def copy_table(self, legacy, model, id_maps):
        table = model._meta.db_table
        fields = model._meta.concrete_fields
        columns = ", ".join(connection.ops.quote_name(field.column) for field in fields)
        source_columns = [
            f'legacy."{field.column}"' if model is not Operation or field.name != "created_by"
            else 'legacy."created_by" AS "created_by_id"'
            for field in fields
        ]
        rows = legacy.execute(f'SELECT {", ".join(source_columns)} FROM "{table}" AS legacy ORDER BY id').fetchall()
        id_maps[model] = {row["id"]: index for index, row in enumerate(rows, start=1)}
        values = [tuple(self.convert(field, row[field.column], model, id_maps) for field in fields) for row in rows]
        if values:
            placeholders = ", ".join(["%s"] * len(fields))
            with connection.cursor() as cursor:
                cursor.executemany(f'INSERT INTO "{table}" ({columns}) VALUES ({placeholders})', values)

    def convert(self, field, value, model, id_maps):
        if value is None:
            return None
        if field.primary_key:
            return id_maps[model][value]
        if field.many_to_one:
            return id_maps[field.related_model][value]
        if isinstance(field, models.DateTimeField):
            instant = datetime.fromisoformat(value)
            if instant.tzinfo is None:
                instant = instant.replace(tzinfo=timezone.utc)
            return connection.ops.adapt_datetimefield_value(instant)
        if model is User and field.name == "password_hash":
            if value.startswith("$argon2"):
                return "argon2" + value
            if not value.startswith("argon2$"):
                raise ValueError("Unsupported legacy password hash")
        return value
