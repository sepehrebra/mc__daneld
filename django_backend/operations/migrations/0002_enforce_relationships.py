from django.db import migrations


# SQLite CHECK constraints cannot reference another table. These triggers protect
# relationships even when callers use bulk updates or issue SQL directly.
# SQLite table rebuilds in later migrations can remove triggers. Keep the
# trigger-presence test passing and recreate them in such migrations if needed.
TRIGGERS = {
    "ops_season_insert": """
        CREATE TRIGGER ops_season_insert BEFORE INSERT ON operations
        WHEN NEW.crop_season_id IS NOT NULL AND EXISTS (
            SELECT 1 FROM crop_seasons s
            WHERE s.id = NEW.crop_season_id AND s.plot_id != NEW.plot_id
        ) BEGIN SELECT RAISE(ABORT, 'crop season must belong to operation plot'); END
    """,
    "ops_season_update": """
        CREATE TRIGGER ops_season_update BEFORE UPDATE OF plot_id, crop_season_id ON operations
        WHEN NEW.crop_season_id IS NOT NULL AND EXISTS (
            SELECT 1 FROM crop_seasons s
            WHERE s.id = NEW.crop_season_id AND s.plot_id != NEW.plot_id
        ) BEGIN SELECT RAISE(ABORT, 'crop season must belong to operation plot'); END
    """,
    "season_plot_update": """
        CREATE TRIGGER season_plot_update BEFORE UPDATE OF plot_id ON crop_seasons
        WHEN EXISTS (
            SELECT 1 FROM operations o
            WHERE o.crop_season_id = NEW.id AND o.plot_id != NEW.plot_id
        ) BEGIN SELECT RAISE(ABORT, 'crop season must belong to operation plot'); END
    """,
    "rem_owner_insert": """
        CREATE TRIGGER rem_owner_insert BEFORE INSERT ON reminders
        WHEN EXISTS (
            SELECT 1 FROM operations o JOIN plots p ON p.id = o.plot_id
            JOIN farms f ON f.id = p.farm_id
            WHERE o.id = NEW.operation_id AND f.owner_id != NEW.recipient_id
        ) BEGIN SELECT RAISE(ABORT, 'reminder recipient must own farm'); END
    """,
    "rem_owner_update": """
        CREATE TRIGGER rem_owner_update BEFORE UPDATE OF operation_id, recipient_id ON reminders
        WHEN EXISTS (
            SELECT 1 FROM operations o JOIN plots p ON p.id = o.plot_id
            JOIN farms f ON f.id = p.farm_id
            WHERE o.id = NEW.operation_id AND f.owner_id != NEW.recipient_id
        ) BEGIN SELECT RAISE(ABORT, 'reminder recipient must own farm'); END
    """,
    "ops_plot_rem_owner": """
        CREATE TRIGGER ops_plot_rem_owner BEFORE UPDATE OF plot_id ON operations
        WHEN EXISTS (
            SELECT 1 FROM reminders r JOIN plots p ON p.id = NEW.plot_id
            JOIN farms f ON f.id = p.farm_id
            WHERE r.operation_id = NEW.id AND r.recipient_id != f.owner_id
        ) BEGIN SELECT RAISE(ABORT, 'reminder recipient must own farm'); END
    """,
    "plot_farm_rem_owner": """
        CREATE TRIGGER plot_farm_rem_owner BEFORE UPDATE OF farm_id ON plots
        WHEN EXISTS (
            SELECT 1 FROM operations o JOIN reminders r ON r.operation_id = o.id
            JOIN farms f ON f.id = NEW.farm_id
            WHERE o.plot_id = NEW.id AND r.recipient_id != f.owner_id
        ) BEGIN SELECT RAISE(ABORT, 'reminder recipient must own farm'); END
    """,
    "farm_owner_rem_owner": """
        CREATE TRIGGER farm_owner_rem_owner BEFORE UPDATE OF owner_id ON farms
        WHEN EXISTS (
            SELECT 1 FROM plots p JOIN operations o ON o.plot_id = p.id
            JOIN reminders r ON r.operation_id = o.id
            WHERE p.farm_id = NEW.id AND r.recipient_id != NEW.owner_id
        ) BEGIN SELECT RAISE(ABORT, 'reminder recipient must own farm'); END
    """,
}


def create_triggers(apps, schema_editor):
    if schema_editor.connection.vendor != "sqlite":
        raise RuntimeError("Relationship protection requires SQLite.")
    for statement in TRIGGERS.values():
        schema_editor.execute(statement)


def drop_triggers(apps, schema_editor):
    for name in TRIGGERS:
        schema_editor.execute(f'DROP TRIGGER IF EXISTS "{name}"')


class Migration(migrations.Migration):
    dependencies = [("operations", "0001_initial")]
    operations = [migrations.RunPython(create_triggers, drop_triggers)]
