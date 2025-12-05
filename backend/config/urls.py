from django.contrib import admin
from django.urls import include, path
from django.views.generic import TemplateView

urlpatterns = [
    path(
        "",
        TemplateView.as_view(template_name="home.html"),
        name="home",
    ),
    path(
        "stats-predictor/",
        TemplateView.as_view(template_name="stats_predictor.html"),
        name="stats-predictor",
    ),
    path(
        "player-stats/",
        TemplateView.as_view(template_name="player_stats.html"),
        name="player-stats",
    ),
    path("admin/", admin.site.urls),
    path("api/", include("core.urls")),
]
