"""Head-to-head API routes."""

from fastapi import APIRouter, Query
from src.api.services.ranking_service import load_stored_data, compute_head_to_head

router = APIRouter(tags=["head-to-head"])


@router.get("/head-to-head")
def get_head_to_head(
    player1: str = Query(..., description="First player name"),
    player2: str = Query(..., description="Second player name"),
    date_from: str | None = Query(None),
    date_to: str | None = Query(None),
    count_missing: bool = Query(False, description="Count missing scores as losses"),
):
    """Return 1v1 head-to-head comparison data."""
    df = load_stored_data()
    if df.empty:
        return {"error": "No data available"}
    return compute_head_to_head(
        df,
        player1=player1,
        player2=player2,
        date_from=date_from,
        date_to=date_to,
        count_missing=count_missing,
    )
