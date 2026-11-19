"""Owner-scoped callers supply farms/plots; summaries use bounded bulk queries."""
from zoneinfo import ZoneInfo

from django.db.models import Case, Count, IntegerField, Max, OuterRef, Q, Subquery, Value, When
from django.utils import timezone
from rest_framework import serializers

from farms.models import CropSeason, Plot
from farms.serializers import FarmResponseSerializer, PlotResponseSerializer
from operations.models import Operation
from operations.serializers import OperationResponseSerializer


OPEN_STATUSES = ("planned", "in_progress")


def summarized_plots(farm, plot_id=None):
    today = timezone.localtime(timezone.now(), ZoneInfo(farm.timezone)).date()
    next_operation = Operation.objects.filter(plot_id=OuterRef("pk"), status__in=OPEN_STATUSES).order_by(
        "scheduled_date", "scheduled_time", "id")
    season = CropSeason.objects.filter(plot_id=OuterRef("pk"), status__in=("active", "planned")).annotate(
        priority=Case(When(status="active", then=Value(0)), default=Value(1), output_field=IntegerField()),
        active_start=Case(When(status="active", then="actual_start_date")),
    ).order_by("priority", "-active_start", "-created_at", "-id")
    plots = Plot.objects.filter(farm=farm)
    if plot_id is not None:
        plots = plots.filter(pk=plot_id)
    open_filter = Q(operations__status__in=OPEN_STATUSES)
    return plots.annotate(
        today_count=Count("operations", filter=open_filter & Q(operations__scheduled_date=today)),
        overdue_count=Count("operations", filter=open_filter & Q(operations__scheduled_date__lt=today)),
        next_id=Subquery(next_operation.values("pk")[:1]),
        season_id=Subquery(season.values("pk")[:1]),
        **{f"last_{kind}": Max("operations__completed_at", filter=Q(
            operations__status="completed", operations__operation_type=kind))
           for kind in ("irrigation", "fertilizing", "spraying")},
    ).order_by("id")


class SeasonSummarySerializer(serializers.Serializer):
    crop_name = serializers.CharField()
    variety = serializers.CharField(allow_null=True)
    start_date = serializers.DateField()
    actual_start_date = serializers.DateField(allow_null=True)
    status = serializers.CharField()


class NextOperationSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    title = serializers.CharField()
    operation_type = serializers.CharField()
    scheduled_date = serializers.DateField()
    scheduled_time = serializers.TimeField(format="%H:%M", allow_null=True)


class FarmDetailSerializer(FarmResponseSerializer):
    def get_plots(self, farm):
        return self.context["plots"]


def summary(plot, seasons):
    data = dict(PlotResponseSerializer(plot).data)
    season = seasons.get(plot.season_id)
    data.update(today_count=plot.today_count, overdue_count=plot.overdue_count,
                current_season=SeasonSummarySerializer(season).data if season else None)
    return data


def farm_detail(farm):
    plots = list(summarized_plots(farm))
    seasons = CropSeason.objects.in_bulk([plot.season_id for plot in plots if plot.season_id])
    operations = Operation.objects.in_bulk([plot.next_id for plot in plots if plot.next_id])
    results = []
    for plot in plots:
        data = summary(plot, seasons)
        operation = operations.get(plot.next_id)
        data.update(next_operation=NextOperationSerializer(operation).data if operation else None,
                    last_irrigation_at=serializers.DateTimeField().to_representation(plot.last_irrigation))
        results.append(data)
    return FarmDetailSerializer(farm, context={"plots": results}).data


def plot_detail(plot):
    farm = plot.farm
    annotated = summarized_plots(farm, plot.pk).get()
    seasons = CropSeason.objects.in_bulk([annotated.season_id] if annotated.season_id else [])
    data = summary(annotated, seasons)
    operations = Operation.objects.filter(plot=plot).select_related("plot__farm")
    upcoming = operations.filter(status__in=OPEN_STATUSES).order_by("scheduled_date", "scheduled_time", "id")[:3]
    recent = operations.filter(status="completed").order_by("-completed_at", "-id")[:3]
    data.update(
        farm={"id": farm.pk, "name": farm.name},
        last_done={kind: serializers.DateTimeField().to_representation(getattr(annotated, f"last_{kind}"))
                   for kind in ("irrigation", "fertilizing", "spraying")},
        next_operations=OperationResponseSerializer(upcoming, many=True).data,
        recent_operations=OperationResponseSerializer(recent, many=True).data,
    )
    return data
