import phonenumbers
from rest_framework import serializers


def normalize_phone(value):
    value = value.translate(str.maketrans("۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩", "01234567890123456789"))
    try:
        number = phonenumbers.parse(value, "IR")
    except phonenumbers.NumberParseException:
        raise serializers.ValidationError("Invalid Iranian mobile number.")
    if number.country_code != 98 or not phonenumbers.is_valid_number(number) or phonenumbers.number_type(number) != phonenumbers.PhoneNumberType.MOBILE:
        raise serializers.ValidationError("Invalid Iranian mobile number.")
    return phonenumbers.format_number(number, phonenumbers.PhoneNumberFormat.E164)


class RegistrationSerializer(serializers.Serializer):
    full_name = serializers.CharField(max_length=100)
    phone = serializers.CharField(max_length=32)
    email = serializers.EmailField(max_length=254, required=False, allow_null=True, allow_blank=True)
    password = serializers.CharField(min_length=8, max_length=128, trim_whitespace=False, write_only=True)

    def validate_phone(self, value):
        return normalize_phone(value)

    def validate_email(self, value):
        return value.lower() if value else None


class LoginSerializer(serializers.Serializer):
    phone = serializers.CharField(max_length=32)
    password = serializers.CharField(max_length=128, trim_whitespace=False, write_only=True)

    def validate_phone(self, value):
        return normalize_phone(value)


class UserSerializer(serializers.Serializer):
    id = serializers.IntegerField(read_only=True)
    full_name = serializers.CharField(read_only=True)
    phone = serializers.CharField(read_only=True)
    email = serializers.EmailField(read_only=True, allow_null=True)
