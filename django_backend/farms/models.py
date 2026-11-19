from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import F, Q


class Farm(models.Model):
    owner = models.ForeignKey("accounts.User", on_delete=models.PROTECT, related_name="farms")
    name = models.CharField(max_length=120)
    province = models.TextField(null=True, blank=True)
    city = models.TextField(null=True, blank=True)
    address = models.CharField(max_length=500, null=True, blank=True)
    latitude = models.FloatField(null=True, blank=True)
    longitude = models.FloatField(null=True, blank=True)
    timezone = models.CharField(max_length=64, default="Asia/Tehran", db_default="Asia/Tehran")
    description = models.CharField(max_length=2000, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def clean(self):
        super().clean()
        try:
            ZoneInfo(self.timezone)
        except (ZoneInfoNotFoundError, ValueError, TypeError):
            raise ValidationError({"timezone": "Invalid IANA time zone."})

    class Meta:
        db_table = "farms"
        constraints = [
            models.CheckConstraint(condition=Q(latitude__isnull=True, longitude__isnull=True) | Q(latitude__isnull=False, longitude__isnull=False), name="ck_farms_coordinates_pair"),
            models.CheckConstraint(condition=Q(latitude__isnull=True) | Q(latitude__gte=-90, latitude__lte=90), name="ck_farms_latitude"),
            models.CheckConstraint(condition=Q(longitude__isnull=True) | Q(longitude__gte=-180, longitude__lte=180), name="ck_farms_longitude"),
        ]


class Plot(models.Model):
    farm = models.ForeignKey(Farm, on_delete=models.PROTECT, related_name="plots")
    name = models.CharField(max_length=120)
    code = models.CharField(max_length=30, null=True, blank=True)
    area_m2 = models.FloatField()
    soil_type = models.CharField(max_length=60, null=True, blank=True)
    description = models.CharField(max_length=2000, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "plots"
        constraints = [
            models.UniqueConstraint(fields=["farm", "name"], name="uq_plots_farm_name"),
            models.UniqueConstraint(fields=["farm", "code"], name="uq_plots_farm_code"),
            models.CheckConstraint(condition=Q(area_m2__gt=0), name="ck_plots_area_positive"),
        ]


class CropSeason(models.Model):
    STATUSES = [(value, value) for value in ("planned", "active", "completed", "cancelled")]
    plot = models.ForeignKey(Plot, on_delete=models.PROTECT, related_name="crop_seasons")
    crop_name = models.TextField()
    variety = models.TextField(null=True, blank=True)
    start_date = models.DateField()
    actual_start_date = models.DateField(null=True, blank=True)
    expected_end_date = models.DateField(null=True, blank=True)
    actual_end_date = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=10, choices=STATUSES, default="planned", db_default="planned")
    notes = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "crop_seasons"
        constraints = [
            models.CheckConstraint(condition=Q(status__in=["planned", "active", "completed", "cancelled"]), name="ck_seasons_status"),
            models.CheckConstraint(condition=Q(expected_end_date__isnull=True) | Q(expected_end_date__gte=F("start_date")), name="ck_seasons_expected_dates"),
            models.CheckConstraint(condition=Q(actual_end_date__isnull=True) | (Q(actual_start_date__isnull=False) & Q(actual_end_date__gte=F("actual_start_date"))), name="ck_seasons_actual_dates"),
        ]
