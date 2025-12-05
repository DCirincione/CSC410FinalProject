from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

import nflreadpy as nfl
import polars as pl
from django.contrib.auth.decorators import login_required
from django.db import models
from django.utils.decorators import method_decorator
from rest_framework import generics, permissions, response, status, views
from rest_framework.decorators import api_view, permission_classes

from .models import CachedResult, Favorite, SavedSearch
from .serializers import CachedResultSerializer, FavoriteSerializer, SavedSearchSerializer

# Make project root importable so we can reuse fantasy_ml.py and nfl.py
ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

try:
    from fantasy_ml import predict_upcoming_week_topn  # type: ignore
    from nfl import get_top_players_week, _resolve_column, _resolve_fantasy_column, _resolve_position_column  # type: ignore
except Exception:
    predict_upcoming_week_topn = None  # type: ignore
    get_top_players_week = None  # type: ignore
    _resolve_column = None  # type: ignore
    _resolve_fantasy_column = None  # type: ignore
    _resolve_position_column = None  # type: ignore


@api_view(["GET"])
@permission_classes([permissions.AllowAny])
def health(request):
    return response.Response({"status": "ok"})


@api_view(["GET"])
@permission_classes([permissions.AllowAny])
def player_search(request):
    """
    Simple placeholder for typeahead. Replace with real player directory lookup.
    """
    query = request.query_params.get("q", "").lower()
    sample = ["Justin Jefferson", "Christian McCaffrey", "Lamar Jackson", "Travis Kelce"]
    matches = [p for p in sample if query in p.lower()] if query else sample
    return response.Response({"results": matches})


@api_view(["GET"])
@permission_classes([permissions.AllowAny])
def projections(request):
    """
    Bridge to fantasy_ml.predict_upcoming_week_topn. Returns JSON for the UI.
    """
    if predict_upcoming_week_topn is None:
        return response.Response(
            {"error": "fantasy_ml not importable. Install deps and try again."},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

    position = request.query_params.get("position", "WR")
    season = int(request.query_params.get("season", 2025))
    scoring = request.query_params.get("scoring", "ppr")
    top_n = int(request.query_params.get("top", 10))

    try:
        df = predict_upcoming_week_topn(season, position, scoring, top_n)
    except Exception as err:  # pragma: no cover - runtime safety
        return response.Response({"error": str(err)}, status=status.HTTP_400_BAD_REQUEST)

    return response.Response({"rows": df.to_dict(orient="records")})


@api_view(["GET"])
@permission_classes([permissions.AllowAny])
def historical(request):
    """
    Bridge to nfl.get_top_players_week for past weeks/season.
    """
    if get_top_players_week is None:
        return response.Response(
            {"error": "nfl not importable. Install deps and try again."},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

    position = request.query_params.get("position", "WR")
    season = int(request.query_params.get("season", 2024))
    week = request.query_params.get("week")
    week_int = int(week) if week else None
    scoring = request.query_params.get("scoring", "ppr")
    top_n = int(request.query_params.get("top", 10))

    try:
        resolved_week, df = get_top_players_week(season, week_int, position, top_n, scoring)
    except Exception as err:  # pragma: no cover - runtime safety
        return response.Response({"error": str(err)}, status=status.HTTP_400_BAD_REQUEST)

    return response.Response({"week": resolved_week, "rows": df.to_dicts()})


@api_view(["GET"])
@permission_classes([permissions.AllowAny])
def season_leaders(request):
    """
    Top-N season leaders by fantasy points (sum and per-game) for a position.
    """
    if _resolve_fantasy_column is None or _resolve_position_column is None:
        return response.Response(
            {"error": "nfl helpers not importable. Install deps and try again."},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

    position = request.query_params.get("position", "WR").upper()
    season = int(request.query_params.get("season", 2024))
    scoring = request.query_params.get("scoring", "ppr")
    top_n = int(request.query_params.get("top", 10))

    try:
        stats = nfl.load_player_stats(seasons=[season])
        if isinstance(stats, pl.LazyFrame):
            stats = stats.collect()

        pos_col = _resolve_position_column(stats)
        if position not in ("ALL", "DEF"):
            stats = stats.filter(pl.col(pos_col) == position)

        if stats.is_empty():
            return response.Response({"rows": []})

        fantasy_col = _resolve_fantasy_column(set(stats.columns), scoring)

        # Use recent_team or team if available
        team_col = _resolve_column(set(stats.columns), ("recent_team", "team"), required=False) or "team"

        # Limit to regular season only and latest completed week
        game_type_col = _resolve_column(set(stats.columns), ("game_type", "season_type"), required=False)
        if game_type_col:
            stats = stats.filter(pl.col(game_type_col).str.to_uppercase() == "REG")

        max_week = (
            stats.filter(pl.col(fantasy_col).is_not_null())
            .select(pl.col("week").max())
            .row(0)[0]
        )
        stats = stats.filter(pl.col("week") <= max_week)

        available_cols = set(stats.columns)

        def agg_optional(alias: str, candidates: tuple[str, ...]):
            col = _resolve_column(available_cols, candidates, required=False)
            return pl.col(col).sum().alias(alias) if col else None

        # Special handling for team defenses: aggregate by opponent (what they allowed)
        if position == "DEF":
            opp_col = _resolve_column(available_cols, ("opponent_team", "opponent"), required=True)
            pass_yd_col = _resolve_column(available_cols, ("passing_yards", "pass_yards"), required=False)
            rush_yd_col = _resolve_column(available_cols, ("rushing_yards", "rush_yards", "rush_yds"), required=False)
            pass_td_col = _resolve_column(available_cols, ("passing_tds", "pass_td"), required=False)
            rush_td_col = _resolve_column(available_cols, ("rushing_tds", "rush_td", "rushing_touchdowns"), required=False)

            # First aggregate per defense-week totals
            per_game_aggs = [pl.col(fantasy_col).sum().alias("fp_allowed")]
            if pass_yd_col:
                per_game_aggs.append(pl.col(pass_yd_col).sum().alias("pass_yds_allowed"))
            if rush_yd_col:
                per_game_aggs.append(pl.col(rush_yd_col).sum().alias("rush_yds_allowed"))
            if pass_td_col:
                per_game_aggs.append(pl.col(pass_td_col).sum().alias("pass_tds_allowed"))
            if rush_td_col:
                per_game_aggs.append(pl.col(rush_td_col).sum().alias("rush_tds_allowed"))

            per_game = (
                stats.group_by([opp_col, "week"])
                .agg(per_game_aggs)
            )

            # Then aggregate per defense season totals and per-game averages
            total_aggs = [
                pl.col("week").n_unique().alias("games"),
                pl.col("fp_allowed").sum().alias("fantasy_points_total"),
            ]
            if pass_yd_col:
                total_aggs.append(pl.col("pass_yds_allowed").sum().alias("opp_pass_yds_total"))
            if rush_yd_col:
                total_aggs.append(pl.col("rush_yds_allowed").sum().alias("opp_rush_yds_total"))
            if pass_td_col:
                total_aggs.append(pl.col("pass_tds_allowed").sum().alias("opp_pass_tds_total"))
            if rush_td_col:
                total_aggs.append(pl.col("rush_tds_allowed").sum().alias("opp_rush_tds_total"))

            grouped = per_game.group_by(opp_col).agg(total_aggs)

            grouped = grouped.with_columns(
                [
                    (pl.col("fantasy_points_total") / pl.col("games")).alias("fantasy_points_per_game"),
                    (
                        pl.col("opp_pass_yds_total") / pl.col("games")
                        if "opp_pass_yds_total" in grouped.columns
                        else None
                    ).alias("opp_pass_yds_per_g"),
                    (
                        pl.col("opp_rush_yds_total") / pl.col("games")
                        if "opp_rush_yds_total" in grouped.columns
                        else None
                    ).alias("opp_rush_yds_per_g"),
                    (
                        (
                            (pl.col("opp_pass_yds_total").fill_null(0) + pl.col("opp_rush_yds_total").fill_null(0))
                            / pl.col("games")
                        ).alias("opp_total_yds_per_g")
                        if "opp_pass_yds_total" in grouped.columns or "opp_rush_yds_total" in grouped.columns
                        else None
                    ),
                ]
            )

            grouped = (
                grouped.sort("fantasy_points_total", descending=True)
                .head(top_n)
                .rename({opp_col: "team"})
                .with_columns(pl.lit("DEF").alias("player_name"))
            )

            rows = grouped.to_dicts()
            return response.Response({"rows": rows})

        extra_aggs = []
        if position in ("WR", "TE"):
            for alias, cands in [
                ("targets", ("targets",)),
                ("receptions", ("receptions", "rec")),
                ("receiving_yards", ("receiving_yards", "rec_yds")),
                ("receiving_td", ("receiving_tds", "rec_td")),
            ]:
                expr = agg_optional(alias, cands)
                if expr is not None:
                    extra_aggs.append(expr)
        elif position == "RB":
            for alias, cands in [
                ("rushing_attempts", ("rushing_attempts", "rush_attempts", "rush_att")),
                ("rushing_yards", ("rushing_yards", "rush_yards", "rush_yds")),
                ("rushing_td", ("rushing_tds", "rush_td", "rushing_touchdowns")),
                ("receptions", ("receptions", "rec")),
                ("receiving_yards", ("receiving_yards", "rec_yds")),
            ]:
                expr = agg_optional(alias, cands)
                if expr is not None:
                    extra_aggs.append(expr)
        elif position == "QB":
            for alias, cands in [
                ("passing_yards", ("passing_yards", "pass_yards")),
                ("passing_tds", ("passing_tds", "pass_td")),
                ("rushing_yards", ("rushing_yards", "rush_yards", "rush_yds")),
                ("rushing_td", ("rushing_tds", "rush_td", "rushing_touchdowns")),
            ]:
                expr = agg_optional(alias, cands)
                if expr is not None:
                    extra_aggs.append(expr)

        grouped = (
            stats.group_by("player_id")
            .agg(
                pl.col("player_name").last().alias("player_name"),
                pl.col(team_col).last().alias("team"),
                pl.col("week").n_unique().alias("games"),
                pl.col(fantasy_col).sum().alias("fantasy_points_total"),
                pl.col(fantasy_col).mean().alias("fantasy_points_per_game"),
                *extra_aggs,
            )
            .sort("fantasy_points_total", descending=True)
            .head(top_n)
        )

        rows = grouped.to_dicts()
        return response.Response({"rows": rows})
    except Exception as err:  # pragma: no cover - runtime safety
        return response.Response({"error": str(err)}, status=status.HTTP_400_BAD_REQUEST)


@method_decorator(login_required, name="dispatch")
class FavoriteListCreateView(generics.ListCreateAPIView):
    serializer_class = FavoriteSerializer

    def get_queryset(self):
        return Favorite.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


@method_decorator(login_required, name="dispatch")
class SavedSearchListCreateView(generics.ListCreateAPIView):
    serializer_class = SavedSearchSerializer

    def get_queryset(self):
        return SavedSearch.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


@method_decorator(login_required, name="dispatch")
class CachedResultListCreateView(generics.ListCreateAPIView):
    serializer_class = CachedResultSerializer

    def get_queryset(self):
        qs = CachedResult.objects.all()
        user = self.request.user if self.request.user.is_authenticated else None
        if user:
            qs = qs.filter(models.Q(user=user) | models.Q(user__isnull=True))
        return qs

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)
