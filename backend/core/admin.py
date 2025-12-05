from django.contrib import admin

from .models import CachedResult, Favorite, SavedSearch


@admin.register(Favorite)
class FavoriteAdmin(admin.ModelAdmin):
    list_display = ("user", "player_name", "position", "created_at")
    search_fields = ("player_name", "position", "user__email", "user__username")


@admin.register(SavedSearch)
class SavedSearchAdmin(admin.ModelAdmin):
    list_display = ("user", "created_at", "updated_at")
    search_fields = ("user__email", "user__username")
    readonly_fields = ("created_at", "updated_at")


@admin.register(CachedResult)
class CachedResultAdmin(admin.ModelAdmin):
    list_display = ("user", "kind", "position", "season", "week", "updated_at")
    search_fields = ("user__email", "user__username", "position", "kind")
    readonly_fields = ("updated_at",)
