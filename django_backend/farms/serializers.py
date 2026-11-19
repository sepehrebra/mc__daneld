import math

from rest_framework import serializers


class StrictSerializer(serializers.Serializer):
    def to_internal_value(self, data):
        if isinstance(data, dict):
            unknown = set(data) - set(self.fields)
            if unknown:
                raise serializers.ValidationError({key: ["Unknown field."] for key in sorted(unknown)})
        return super().to_internal_value(data)


class OptionalTextField(serializers.CharField):
    def __init__(self, **kwargs):
        super().__init__(required=False, allow_null=True, allow_blank=True, **kwargs)

    def run_validation(self, data=serializers.empty):
        return super().run_validation(data) or None


class FiniteFloatField(serializers.FloatField):
    def to_internal_value(self, data):
        if isinstance(data, bool):
            self.fail("invalid")
        value = super().to_internal_value(data)
        if not math.isfinite(value):
            raise serializers.ValidationError("A finite number is required.")
        return value


class FarmCreateSerializer(StrictSerializer):
    name = serializers.CharField(max_length=120)
    address = OptionalTextField(max_length=500)
    description = OptionalTextField(max_length=2000)


class FarmUpdateSerializer(StrictSerializer):
    name = serializers.CharField(max_length=120, required=False)
    province = OptionalTextField()
    city = OptionalTextField()
    address = OptionalTextField(max_length=500)
    description = OptionalTextField(max_length=2000)
    latitude = FiniteFloatField(required=False, allow_null=True, min_value=-90, max_value=90)
    longitude = FiniteFloatField(required=False, allow_null=True, min_value=-180, max_value=180)

    def validate(self, attrs):
        if ("latitude" in attrs) != ("longitude" in attrs):
            raise serializers.ValidationError("Latitude and longitude must be supplied together.")
        if "latitude" in attrs and ((attrs["latitude"] is None) != (attrs["longitude"] is None)):
            raise serializers.ValidationError("Latitude and longitude must both be set or null.")
        return attrs


class FarmResponseSerializer(serializers.Serializer):
    id = serializers.IntegerField(read_only=True)
    name = serializers.CharField(read_only=True)
    province = serializers.CharField(read_only=True, allow_null=True)
    city = serializers.CharField(read_only=True, allow_null=True)
    address = serializers.CharField(read_only=True, allow_null=True)
    latitude = serializers.FloatField(read_only=True, allow_null=True)
    longitude = serializers.FloatField(read_only=True, allow_null=True)
    timezone = serializers.CharField(read_only=True)
    description = serializers.CharField(read_only=True, allow_null=True)
    plots = serializers.SerializerMethodField()

    def get_plots(self, farm):
        return PlotResponseSerializer(farm.plots.order_by("id"), many=True).data


class PlotWriteSerializer(StrictSerializer):
    name = serializers.CharField(max_length=120)
    code = OptionalTextField(max_length=30)
    area_m2 = FiniteFloatField(min_value=0)
    soil_type = OptionalTextField(max_length=60)
    description = OptionalTextField(max_length=2000)

    def validate_area_m2(self, value):
        if value <= 0:
            raise serializers.ValidationError("Area must be positive.")
        return value


class PlotResponseSerializer(serializers.Serializer):
    id = serializers.IntegerField(read_only=True)
    name = serializers.CharField(read_only=True)
    code = serializers.CharField(read_only=True, allow_null=True)
    area_m2 = serializers.FloatField(read_only=True)
    soil_type = serializers.CharField(read_only=True, allow_null=True)
    description = serializers.CharField(read_only=True, allow_null=True)
