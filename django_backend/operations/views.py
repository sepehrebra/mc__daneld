from datetime import datetime, time, timezone as dt_timezone
from zoneinfo import ZoneInfo

from django.db import transaction
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import serializers, status
from rest_framework.response import Response

from config.errors import Conflict
from farms.views import PrivateView, owned_plot
from operations.models import Operation
from operations.serializers import (
    OperationCalendarQuerySerializer,
    OperationCreateSerializer,
    OperationListQuerySerializer,
    OperationResponseSerializer,
    OperationUpdateSerializer,
)
from operations.seasons import complete_harvest, operation_completed_date, revert_harvest, save_season, sync_planting
from farms.models import CropSeason


TYPE_LABELS = {"planting": "کاشت", "irrigation": "آبیاری", "fertilizing": "کوددهی", "spraying": "سم‌پاشی", "harvesting": "برداشت", "other": "سایر"}


def completion_time(date_value, farm_timezone):
    now = timezone.now()
    zone = ZoneInfo(farm_timezone)
    if date_value is None or date_value == timezone.localtime(now, zone).date():
        return now
    return datetime.combine(date_value, time(hour=12), tzinfo=zone).astimezone(dt_timezone.utc)


def owned_operation(user, operation_id):
    return get_object_or_404(Operation.objects.select_for_update().select_related("plot__farm"), pk=operation_id, plot__farm__owner_id=user.pk)


def operation_queryset(user):
    return Operation.objects.filter(plot__farm__owner_id=user.pk).select_related("plot__farm")


def effective_date(operation):
    if operation.status == "completed":
        return timezone.localtime(operation.completed_at, ZoneInfo(operation.plot.farm.timezone)).date()
    return operation.scheduled_date


def query_data(query_params):
    data = query_params.copy()
    for external, internal in (("from", "from_date"), ("to", "to_date")):
        if external in data:
            data.setlist(internal, data.pop(external))
    return data


class OperationCollectionView(PrivateView):
    def get(self, request):
        serializer = OperationListQuerySerializer(data=query_data(request.query_params))
        serializer.is_valid(raise_exception=True)
        values = serializer.validated_data
        operations = operation_queryset(request.user)
        if "from" in values:
            operations = operations.filter(scheduled_date__gte=values["from"])
        if "to" in values:
            operations = operations.filter(scheduled_date__lte=values["to"])
        if "farm" in values:
            operations = operations.filter(plot__farm_id=values["farm"])
        if "plot" in values:
            operations = operations.filter(plot_id=values["plot"])
        if "status" in values:
            operations = operations.filter(status__in=values["status"])
        if values["sort"] == "created":
            operations = operations.order_by("-created_at", "-id")
        else:
            prefix = "" if values["order"] == "asc" else "-"
            operations = operations.order_by(f"{prefix}scheduled_date", f"{prefix}scheduled_time", f"{prefix}id")
        start = values["offset"]
        operations = operations[start : start + values["limit"]]
        return Response(OperationResponseSerializer(operations, many=True).data)


class OperationCalendarView(PrivateView):
    def get(self, request):
        serializer = OperationCalendarQuerySerializer(data=query_data(request.query_params))
        serializer.is_valid(raise_exception=True)
        values = serializer.validated_data
        operations = [
            operation
            for operation in operation_queryset(request.user)
            if values["from"] <= effective_date(operation) <= values["to"]
        ]
        operations.sort(key=lambda operation: (effective_date(operation), operation.scheduled_time or time.min, operation.pk))
        return Response(OperationResponseSerializer(operations, many=True).data)


class OperationCreateView(OperationCollectionView):
    def post(self, request):
        serializer = OperationCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        values = dict(serializer.validated_data)
        plot = owned_plot(request.user, values.pop("plot_id"))
        crop_name, variety = values.pop("crop_name", None), values.pop("variety", None)
        completed_date = values.pop("completed_date", None)
        target_status = values.get("status", "planned")
        if completed_date is not None and target_status != "completed":
            raise serializers.ValidationError({"completed_date": "Completion date requires completed status."})
        if not values.get("title"):
            values["title"] = TYPE_LABELS[values["operation_type"]]
        if target_status == "completed":
            values["completed_at"] = completion_time(completed_date, plot.farm.timezone)
        with transaction.atomic():
            season = None
            if values["operation_type"] == "planting" and crop_name:
                season = CropSeason.objects.create(plot=plot, crop_name=crop_name, variety=variety, start_date=values["scheduled_date"])
            operation = Operation(plot=plot, created_by=request.user, crop_season=season, **values)
            if season:
                sync_planting(season, None, operation)
            elif operation.operation_type == "harvesting" and target_status == "completed":
                complete_harvest(operation)
            operation.save()
        return Response(OperationResponseSerializer(operation).data, status=201)


class OperationDetailView(PrivateView):
    def patch(self, request, operation_id):
        with transaction.atomic():
            operation = owned_operation(request.user, operation_id)
            serializer = OperationUpdateSerializer(data=request.data, partial=True)
            serializer.is_valid(raise_exception=True)
            values = dict(serializer.validated_data)
            previous_status = operation.status
            previous_scheduled_date = operation.scheduled_date
            previous_type = operation.operation_type
            season = (CropSeason.objects.select_for_update().filter(pk=operation.crop_season_id).first()
                      if operation.crop_season_id else None)
            target_status = values.get("status", previous_status)
            target_type = values.get("operation_type", previous_type)
            completed_date = values.pop("completed_date", None)
            if completed_date is not None and target_status != "completed" and previous_status != "completed":
                raise serializers.ValidationError({"completed_date": "Completion date requires completed status."})
            plot_changed = False
            if "plot_id" in values:
                plot = owned_plot(request.user, values.pop("plot_id"))
                if plot.pk != operation.plot_id:
                    plot_changed = True
                    preserve_planting_season = False
                    if previous_type == "planting" and season and season.status == "planned":
                        if Operation.objects.filter(crop_season=season).exclude(pk=operation.pk).exists():
                            raise Conflict("The planned crop season is used by other operations.")
                        # Triggers require temporarily unlinking before the move.
                        Operation.objects.filter(pk=operation.pk).update(crop_season=None)
                        season.plot = plot
                        save_season(season)
                        preserve_planting_season = target_type == "planting"
                    operation.plot = plot
                    operation.crop_season = season if preserve_planting_season else None
            type_changed = previous_type != target_type
            if previous_type == "harvesting" and previous_status == "completed" and (target_status != "completed" or plot_changed or type_changed):
                revert_harvest(season)
                operation.crop_season = None
            if previous_type == "planting" and type_changed and season:
                if previous_status == "completed":
                    # Preserve the season but undo the effect of the former planting.
                    original_plot = operation.plot
                    if plot_changed:
                        operation.plot = season.plot
                    operation.status = "planned"
                    sync_planting(season, previous_status, operation)
                    operation.plot = original_plot
                operation.crop_season = None
            if target_status == "completed":
                if previous_status != "completed" or completed_date is not None:
                    operation.completed_at = completion_time(completed_date, operation.plot.farm.timezone)
            else:
                operation.completed_at = None
            for field, value in values.items():
                setattr(operation, field, value)
            operation.status = target_status
            if target_type == "planting" and previous_type == "planting" and season:
                if not plot_changed or season.plot_id == operation.plot_id:
                    sync_planting(season, previous_status, operation, completion_changed=completed_date is not None)
            elif target_type == "harvesting" and target_status == "completed":
                if previous_type != "harvesting" or previous_status != "completed" or plot_changed:
                    complete_harvest(operation)
                elif completed_date is not None and season and season.status == "completed":
                    season.actual_end_date = operation_completed_date(operation)
                    save_season(season)
            if serializer.validated_data:
                operation.save()
                if (operation.scheduled_date != previous_scheduled_date or
                        (operation.status != previous_status and operation.status in ("completed", "cancelled"))):
                    # Processing/failed reminders without sent_at have not been delivered.
                    operation.reminders.filter(
                        status__in=("pending", "processing", "failed"), sent_at__isnull=True,
                    ).update(status="cancelled", updated_at=timezone.now())
        return Response(OperationResponseSerializer(operation).data)

    def delete(self, request, operation_id):
        with transaction.atomic():
            operation = owned_operation(request.user, operation_id)
            season = (CropSeason.objects.select_for_update().filter(pk=operation.crop_season_id).first()
                      if operation.crop_season_id and operation.operation_type == "planting" else None)
            delete_season = season is not None and season.status == "planned"
            if delete_season and Operation.objects.filter(crop_season=season).exclude(pk=operation.pk).exists():
                raise Conflict("The planned crop season is used by other operations.")
            operation.delete()
            if delete_season:
                season.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
