from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q


class Operation(models.Model):
    TYPES = [(value, value) for value in ("planting", "irrigation", "fertilizing", "spraying", "harvesting", "other")]
    STATUSES = [(value, value) for value in ("planned", "in_progress", "completed", "cancelled")]
    plot = models.ForeignKey("farms.Plot", on_delete=models.PROTECT, related_name="operations")
    crop_season = models.ForeignKey("farms.CropSeason", on_delete=models.PROTECT, null=True, blank=True, related_name="operations")
    created_by = models.ForeignKey("accounts.User", on_delete=models.PROTECT, related_name="operations")
    title = models.CharField(max_length=120)
    operation_type = models.CharField(max_length=12, choices=TYPES)
    description = models.CharField(max_length=2000, null=True, blank=True)
    scheduled_date = models.DateField()
    scheduled_time = models.TimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=11, choices=STATUSES, default="planned", db_default="planned")
    result_notes = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def clean(self):
        super().clean()
        if self.crop_season_id and self.plot_id:
            from farms.models import CropSeason
            season_plot_id = CropSeason.objects.filter(pk=self.crop_season_id).values_list("plot_id", flat=True).first()
            if season_plot_id is not None and season_plot_id != self.plot_id:
                raise ValidationError({"crop_season": "Crop season must belong to the same plot."})

    def save(self, *args, **kwargs):
        self.clean()
        return super().save(*args, **kwargs)

    class Meta:
        db_table = "operations"
        indexes = [
            models.Index(fields=["plot", "status", "scheduled_date"], name="ix_ops_plot_status_date"),
            models.Index(fields=["created_at"], name="ix_ops_created_at"),
        ]
        constraints = [
            models.CheckConstraint(condition=Q(operation_type__in=["planting", "irrigation", "fertilizing", "spraying", "harvesting", "other"]), name="ck_operations_type"),
            models.CheckConstraint(condition=Q(status__in=["planned", "in_progress", "completed", "cancelled"]), name="ck_operations_status"),
            models.CheckConstraint(condition=Q(status="completed", completed_at__isnull=False) | (~Q(status="completed") & Q(completed_at__isnull=True)), name="ck_operations_completion_time"),
        ]


class Reminder(models.Model):
    STATUSES = [(value, value) for value in ("pending", "processing", "sent", "failed", "cancelled")]
    operation = models.ForeignKey(Operation, on_delete=models.CASCADE, related_name="reminders")
    recipient = models.ForeignKey("accounts.User", on_delete=models.PROTECT, related_name="reminders")
    remind_at = models.DateTimeField()
    channel = models.CharField(max_length=6, default="in_app", db_default="in_app")
    status = models.CharField(max_length=10, choices=STATUSES, default="pending", db_default="pending")
    sent_at = models.DateTimeField(null=True, blank=True)
    read_at = models.DateTimeField(null=True, blank=True)
    attempt_count = models.IntegerField(default=0, db_default=0)
    last_error = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def clean(self):
        super().clean()
        if self.operation_id and self.recipient_id:
            owner_id = Operation.objects.filter(pk=self.operation_id).values_list("plot__farm__owner_id", flat=True).first()
            if owner_id is not None and owner_id != self.recipient_id:
                raise ValidationError({"recipient": "Recipient must own the operation's farm."})

    def save(self, *args, **kwargs):
        self.clean()
        return super().save(*args, **kwargs)

    class Meta:
        db_table = "reminders"
        indexes = [models.Index(fields=["recipient", "status", "remind_at"], name="ix_rem_recipient_due")]
        constraints = [
            models.CheckConstraint(condition=Q(channel="in_app"), name="ck_reminders_channel"),
            models.CheckConstraint(condition=Q(status__in=["pending", "processing", "sent", "failed", "cancelled"]), name="ck_reminders_status"),
            models.CheckConstraint(condition=Q(attempt_count__gte=0), name="ck_reminders_attempt_count"),
        ]
