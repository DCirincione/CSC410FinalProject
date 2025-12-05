from django.contrib.auth import get_user_model
from rest_framework import serializers

from .models import CachedResult, Favorite, SavedSearch


User = get_user_model()


class FavoriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Favorite
        fields = ["id", "player_name", "position", "created_at"]


class SavedSearchSerializer(serializers.ModelSerializer):
    class Meta:
        model = SavedSearch
        fields = ["id", "params_json", "result_json", "created_at", "updated_at"]


class CachedResultSerializer(serializers.ModelSerializer):
    class Meta:
        model = CachedResult
        fields = ["id", "season", "week", "position", "kind", "result_json", "updated_at"]
