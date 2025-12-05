from django.urls import path

from . import views

urlpatterns = [
    path("health/", views.health, name="health"),
    path("player-search/", views.player_search, name="player-search"),
    path("projections/", views.projections, name="projections"),
    path("historical/", views.historical, name="historical"),
    path("season-leaders/", views.season_leaders, name="season-leaders"),
    path("favorites/", views.FavoriteListCreateView.as_view(), name="favorites"),
    path("saved-searches/", views.SavedSearchListCreateView.as_view(), name="saved-searches"),
    path("cached-results/", views.CachedResultListCreateView.as_view(), name="cached-results"),
]
