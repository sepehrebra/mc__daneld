from django.db import IntegrityError, transaction
from django.db.models import Prefetch, Q
from django.shortcuts import get_object_or_404
from rest_framework.response import Response
from rest_framework.views import APIView

from config.errors import Conflict
from farms.details import farm_detail, plot_detail
from farms.models import Farm, Plot
from farms.serializers import FarmCreateSerializer, FarmResponseSerializer, FarmUpdateSerializer, PlotResponseSerializer, PlotWriteSerializer


class PrivateView(APIView):
    def finalize_response(self, request, response, *args, **kwargs):
        response = super().finalize_response(request, response, *args, **kwargs)
        response["Cache-Control"] = "no-store"
        return response


def owned_farm(user, farm_id):
    return get_object_or_404(Farm, pk=farm_id, owner_id=user.pk)


def owned_plot(user, plot_id):
    return get_object_or_404(Plot.objects.select_related("farm"), pk=plot_id, farm__owner_id=user.pk)


def plot_conflicts(farm_id, values, exclude_pk=None):
    query = Q(name=values["name"])
    if values.get("code") is not None:
        query |= Q(code=values["code"])
    matches = Plot.objects.filter(query, farm_id=farm_id)
    if exclude_pk is not None:
        matches = matches.exclude(pk=exclude_pk)
    return matches.exists()


class FarmCollectionView(PrivateView):
    def get(self, request):
        plots = Plot.objects.only("id", "name", "farm_id").order_by("id")
        farms = Farm.objects.filter(owner=request.user).order_by("id").prefetch_related(Prefetch("plots", queryset=plots))
        return Response([{"id": farm.pk, "name": farm.name, "plots": [{"id": plot.pk, "name": plot.name} for plot in farm.plots.all()]} for farm in farms])

    def post(self, request):
        serializer = FarmCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        farm = Farm.objects.create(owner=request.user, **serializer.validated_data)
        return Response(FarmResponseSerializer(farm).data, status=201)


class FarmUpdateView(PrivateView):
    def get(self, request, farm_id):
        return Response(farm_detail(owned_farm(request.user, farm_id)))

    def patch(self, request, farm_id):
        farm = owned_farm(request.user, farm_id)
        serializer = FarmUpdateSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        for field, value in serializer.validated_data.items():
            setattr(farm, field, value)
        if serializer.validated_data:
            farm.save()
        return Response(FarmResponseSerializer(farm).data)


class PlotCreateView(PrivateView):
    def post(self, request, farm_id):
        farm = owned_farm(request.user, farm_id)
        serializer = PlotWriteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        values = serializer.validated_data
        try:
            with transaction.atomic():
                plot = Plot.objects.create(farm=farm, **values)
        except IntegrityError:
            if plot_conflicts(farm.pk, values):
                raise Conflict("Plot name or code already exists in this farm.")
            raise
        return Response(PlotResponseSerializer(plot).data, status=201)


class PlotUpdateView(PrivateView):
    def get(self, request, plot_id):
        return Response(plot_detail(owned_plot(request.user, plot_id)))

    def patch(self, request, plot_id):
        plot = owned_plot(request.user, plot_id)
        serializer = PlotWriteSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        values = serializer.validated_data
        for field, value in values.items():
            setattr(plot, field, value)
        try:
            if values:
                with transaction.atomic():
                    plot.save()
        except IntegrityError:
            if plot_conflicts(plot.farm_id, {"name": plot.name, "code": plot.code}, exclude_pk=plot.pk):
                raise Conflict("Plot name or code already exists in this farm.")
            raise
        return Response(PlotResponseSerializer(plot).data)
