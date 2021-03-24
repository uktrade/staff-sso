from django.contrib.auth.models import Group
from rest_framework import serializers

from .models import UserSettings
from ..user.models import User


class JSONSerializerField(serializers.Field):
    """ Serializer for JSONField -- required to make field writable"""

    def to_internal_value(self, data):
        return data

    def to_representation(self, value):
        return value


class UserSettingsSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserSettings
        fields = ["user_id", "app_slug", "settings"]

    user_id = serializers.UUIDField(required=False, default=None)
    app_slug = serializers.CharField(required=False, default=None)
    settings = JSONSerializerField(required=False, default=None)

    def validate(self, data):
        if not data["settings"] or not data["user_id"]:
            raise serializers.ValidationError("Both user_id and settings are required")

        return data


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["id", "user"]
