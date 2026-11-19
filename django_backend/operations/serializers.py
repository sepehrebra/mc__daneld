import re
from zoneinfo import ZoneInfo

from django.utils import timezone
from rest_framework import serializers

from farms.serializers import OptionalTextField, StrictSerializer
from operations.models import Operation


class ISODateField(serializers.DateField):
    def to_internal_value(self, value):
        if not isinstance(value, str) or not re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}", value):
            raise serializers.ValidationError("Use YYYY-MM-DD.")
        return super().to_internal_value(value)


class ScheduledTimeField(serializers.TimeField):
    def __init__(self, **kwargs):
        super().__init__(format="%H:%M", input_formats=["%H:%M"], **kwargs)

    def to_internal_value(self, value):
        if not isinstance(value, str) or not re.fullmatch(r"[0-9]{2}:[0-9]{2}", value):
            raise serializers.ValidationError("Use HH:mm.")
        return super().to_internal_value(value)


class OperationCreateSerializer(StrictSerializer):
    plot_id = serializers.IntegerField(min_value=1)
    operation_type = serializers.ChoiceField(choices=Operation.TYPES)
    title = OptionalTextField(max_length=120)
    scheduled_date = ISODateField()
    scheduled_time = ScheduledTimeField(required=False, allow_null=True)
    description = OptionalTextField(max_length=2000)
    status = serializers.ChoiceField(choices=Operation.STATUSES, required=False)
    completed_date = ISODateField(required=False)
    crop_name = OptionalTextField()
    variety = OptionalTextField()


class OperationUpdateSerializer(StrictSerializer):
    plot_id = serializers.IntegerField(min_value=1, required=False)
    operation_type = serializers.ChoiceField(choices=Operation.TYPES, required=False)
    title = serializers.CharField(max_length=120, required=False)
    scheduled_date = ISODateField(required=False)
    scheduled_time = ScheduledTimeField(required=False, allow_null=True)
    description = OptionalTextField(max_length=2000)
    status = serializers.ChoiceField(choices=Operation.STATUSES, required=False)
    completed_date = ISODateField(required=False)


class OperationListQuerySerializer(serializers.Serializer):
    from_date = ISODateField(required=False, source="from")
    to_date = ISODateField(required=False, source="to")
    farm = serializers.IntegerField(min_value=1, required=False)
    plot = serializers.IntegerField(min_value=1, required=False)
    status = serializers.CharField(required=False)
    sort = serializers.ChoiceField(choices=("date", "created"), required=False, default="date")
    order = serializers.ChoiceField(choices=("asc", "desc"), required=False, default="desc")
    limit = serializers.IntegerField(min_value=1, max_value=100, required=False, default=20)
    offset = serializers.IntegerField(min_value=0, required=False, default=0)

    def validate_status(self, value):
        values = value.split(",")
        if not values or any(item not in dict(Operation.STATUSES) for item in values):
            raise serializers.ValidationError("Use comma-separated operation statuses.")
        return values

    def validate(self, attrs):
        if attrs.get("from") and attrs.get("to") and attrs["from"] > attrs["to"]:
            raise serializers.ValidationError({"to": "Must not be before from."})
        return attrs


class OperationCalendarQuerySerializer(serializers.Serializer):
    from_date = ISODateField(source="from")
    to_date = ISODateField(source="to")

    def validate(self, attrs):
        if attrs["to"] < attrs["from"]:
            raise serializers.ValidationError({"to": "Must not be before from."})
        if (attrs["to"] - attrs["from"]).days + 1 > 62:
            raise serializers.ValidationError({"to": "Calendar range cannot exceed 62 days."})
        return attrs


class OperationResponseSerializer(serializers.Serializer):
    id = serializers.IntegerField(read_only=True)
    title = serializers.CharField(read_only=True)
    operation_type = serializers.CharField(read_only=True)
    description = serializers.CharField(read_only=True, allow_null=True)
    scheduled_date = serializers.DateField(read_only=True, format="%Y-%m-%d")
    scheduled_time = serializers.TimeField(read_only=True, format="%H:%M", allow_null=True)
    status = serializers.CharField(read_only=True)
    completed_date = serializers.SerializerMethodField()
    farm = serializers.SerializerMethodField()
    plot = serializers.SerializerMethodField()

    def get_completed_date(self, operation):
        if operation.completed_at is None:
            return None
        return timezone.localtime(operation.completed_at, ZoneInfo(operation.plot.farm.timezone)).date().isoformat()

    def get_farm(self, operation):
        farm = operation.plot.farm
        return {"id": farm.pk, "name": farm.name}

    def get_plot(self, operation):
        return {"id": operation.plot_id, "name": operation.plot.name}
