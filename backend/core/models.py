from django.conf import settings
from django.db import models


class Favorite(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="favorites")
    player_name = models.CharField(max_length=100)
    position = models.CharField(max_length=5, blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("user", "player_name", "position")
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.player_name} ({self.position})"


class SavedSearch(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="saved_searches")
    params_json = models.JSONField()
    result_json = models.JSONField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-updated_at"]

    def __str__(self) -> str:
        return f"Search {self.id} by {self.user}"


class CachedResult(models.Model):
    KIND_CHOICES = (
        ("projection", "Projection"),
        ("historical", "Historical"),
    )

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="cached_results",
        null=True,
        blank=True,
    )
    season = models.IntegerField()
    week = models.IntegerField(null=True, blank=True)
    position = models.CharField(max_length=5)
    kind = models.CharField(max_length=20, choices=KIND_CHOICES)
    result_json = models.JSONField()
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-updated_at"]
        unique_together = ("user", "season", "week", "position", "kind")

    def __str__(self) -> str:
        wk = f"wk{self.week}" if self.week else "season"
        return f"{self.kind} {self.position} {self.season} {wk}"
