"""Leaderboard API routes."""

from fastapi import APIRouter, Query
from src.api.services.ranking_service import load_stored_data, compute_rankings

router = APIRouter(tags=["leaderboard"])


@router.get("/leaderboard")
def get_leaderboard(
    day_filter: str = Query("All", description="Specific date (YYYY-MM-DD) or 'All'"),
    day_from: str | None = Query(None, description="Start date for overall ranking"),
    day_to: str | None = Query(None, description="End date for overall ranking"),
):
    """Return all ranking data for the leaderboard page."""
    df = load_stored_data()
    if df.empty:
        return {"error": "No data available"}
    return compute_rankings(df, day_filter=day_filter, day_from=day_from, day_to=day_to)


@router.get("/dates")
def get_available_dates():
    """Return sorted list of available dates for filtering."""
    df = load_stored_data()
    if df.empty:
        return {"dates": []}
    dates = sorted(df["date"].unique(), reverse=True)
    return {"dates": dates}


@router.get("/players")
def get_players():
    """Return list of players found in the data."""
    df = load_stored_data()
    if df.empty:
        return {"players": []}
    return {"players": sorted(df["sender"].unique().tolist())}
