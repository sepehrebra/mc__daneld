from django.core.exceptions import ValidationError as DjangoValidationError
from django.db.models import F
from django.utils import timezone
from rest_framework import serializers
from zoneinfo import ZoneInfo

from farms.models import CropSeason


def operation_completed_date(operation):
    return timezone.localtime(operation.completed_at, ZoneInfo(operation.plot.farm.timezone)).date()


def save_season(season):
    try:
        season.full_clean()
    except DjangoValidationError as exc:
        raise serializers.ValidationError({"crop_season": exc.message_dict}) from exc
    season.save()


def sync_planting(season, old_status, operation, completion_changed=False):
    new_status = operation.status
    if new_status == "completed":
        if old_status != "completed" or completion_changed:
            season.actual_start_date = operation_completed_date(operation)
            # Editing a completed planting must not reopen a harvested season.
            if old_status != "completed":
                season.status = "active"
            save_season(season)
    elif old_status == "completed":
        season.actual_start_date = None
        season.status = "cancelled" if new_status == "cancelled" else "planned"
        save_season(season)
    elif new_status == "cancelled" and season.status == "planned":
        season.status = "cancelled"
        save_season(season)
    elif old_status == "cancelled" and season.status == "cancelled":
        season.status = "planned"
        save_season(season)


def select_active_season(plot_id):
    # Overlapping active seasons are allowed; select the most recent start,
    # breaking ties by ID. NULL actual dates are ordered last.
    return (CropSeason.objects.select_for_update().filter(plot_id=plot_id, status="active")
            .order_by(F("actual_start_date").desc(nulls_last=True), "-id").first())


def complete_harvest(operation):
    season = select_active_season(operation.plot_id)
    if season is None:
        operation.crop_season = None
        return
    season.status = "completed"
    season.actual_end_date = operation_completed_date(operation)
    save_season(season)
    operation.crop_season = season


def revert_harvest(season):
    if season and season.status == "completed":
        season.status = "active"
        season.actual_end_date = None
        save_season(season)
