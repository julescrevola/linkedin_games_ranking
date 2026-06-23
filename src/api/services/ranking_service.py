"""Ranking computation service.

All Pandas-based ranking logic lives here, independent of any web framework.
"""

import math
import pandas as pd
from src.api.config import GAMES, PLAYERS, get_supabase
from src.linkedin_games_parser import parse_whatsapp_chat


def _sanitize(df: pd.DataFrame) -> list[dict]:
    """Convert DataFrame to list of dicts with NaN replaced by None for JSON."""
    records = df.to_dict(orient="records")
    for row in records:
        for key, val in row.items():
            if isinstance(val, float) and (math.isnan(val) or math.isinf(val)):
                row[key] = None
    return records


def time_to_seconds(time_str) -> int | None:
    if not isinstance(time_str, str):
        return None
    parts = [int(p) for p in time_str.strip().split(":")]
    if len(parts) == 2:
        return parts[0] * 60 + parts[1]
    elif len(parts) == 3:
        return parts[0] * 3600 + parts[1] * 60 + parts[2]
    return None


def load_stored_data() -> pd.DataFrame:
    """Load data from Supabase, filtering to valid games/players."""
    supabase = get_supabase()
    supabase.table("game_data").delete().not_.in_("game", GAMES).execute()
    supabase.table("game_data").delete().not_.in_("sender", PLAYERS).execute()
    df = pd.DataFrame(
        supabase.table("game_data")
        .select("*")
        .order("uploaded_at", desc=True)
        .execute()
        .data
    ).drop_duplicates(subset=["date", "sender", "game", "game_number"])
    return df


def upload_chat_data(file_content: bytes) -> dict:
    """Parse an uploaded WhatsApp chat and upsert new data into Supabase.

    Returns summary of new entries added.
    """
    supabase = get_supabase()
    lines = file_content.decode("utf-8").splitlines(keepends=True)
    df = parse_whatsapp_chat(iter(lines)).drop_duplicates(
        subset=["date", "sender", "game", "game_number"]
    )
    df = df[df["game"].isin(GAMES)]
    df = df[df["sender"].isin(PLAYERS)]

    df_existing = pd.DataFrame(
        supabase.table("game_data")
        .select("*")
        .order("uploaded_at", desc=True)
        .execute()
        .data
    )

    if df_existing.empty:
        df_new = df
    else:
        df_new = (
            df.merge(
                df_existing,
                on=[
                    "date",
                    "sender",
                    "game",
                    "game_number",
                    "play_time",
                    "ceo_percent",
                ],
                how="left",
                indicator=True,
            )
            .query('_merge=="left_only"')
            .drop(columns=["_merge", "id", "uploaded_at"], errors="ignore")
        )

    added = 0
    if not df_new.empty:
        supabase.table("game_data").insert(
            df_new[
                ["date", "sender", "game", "game_number", "play_time", "ceo_percent"]
            ].to_dict(orient="records")
        ).execute()
        added = len(df_new)

    # Reload full dataset
    full_df = pd.DataFrame(
        supabase.table("game_data")
        .select("*")
        .order("uploaded_at", desc=True)
        .execute()
        .data
    ).drop_duplicates(subset=["date", "sender", "game", "game_number"])
    return {"added": added, "total": len(full_df)}


def compute_rankings(
    df: pd.DataFrame,
    day_filter: str = "All",
    day_from: str | None = None,
    day_to: str | None = None,
) -> dict:
    """Compute all rankings and return them as JSON-serializable dicts.

    This replicates the full logic of streamlit_app() + leaderboard_page().
    """
    if df.empty:
        return {"error": "No data available"}

    df["Weekday"] = pd.to_datetime(df["date"]).dt.day_name()

    # Filter by specific day
    if day_filter != "All":
        filtered_df = df[df["date"] == day_filter].copy()
    else:
        filtered_df = df.copy()
        if day_from:
            filtered_df = filtered_df[filtered_df["date"] >= day_from]
        if day_to:
            filtered_df = filtered_df[filtered_df["date"] <= day_to]

    if filtered_df.empty:
        return {"error": "No data for selected filters"}

    # Preprocess
    filtered_df["time_sec"] = (
        filtered_df["play_time"].astype(str).apply(time_to_seconds).astype(int)
    )
    filtered_df["ceo_percent"] = pd.to_numeric(
        filtered_df["ceo_percent"], errors="coerce"
    )

    # --- Total and average times ---
    daily_times = filtered_df.groupby(["date", "sender"], as_index=False)[
        "time_sec"
    ].sum()
    daily_times = daily_times.rename(
        columns={"sender": "Player", "time_sec": "Total Time (sec)"}
    )

    games_played = (
        filtered_df.groupby("sender", as_index=False)
        .size()
        .rename(columns={"size": "Games Played", "sender": "Player"})
    )

    total_time_all_days = daily_times.groupby("Player", as_index=False)[
        "Total Time (sec)"
    ].sum()
    daily_avg_times = total_time_all_days.merge(games_played, on="Player", how="left")
    daily_avg_times["Average Time per Game (sec)"] = (
        daily_avg_times["Total Time (sec)"] / daily_avg_times["Games Played"]
    ).round(2)
    daily_avg_times["Total Time (sec)"] = daily_avg_times.apply(
        lambda row: row["Total Time (sec)"]
        if row["Games Played"] == daily_avg_times["Games Played"].max()
        else (daily_avg_times["Games Played"].max() - row["Games Played"])
        * row["Average Time per Game (sec)"]
        + row["Total Time (sec)"],
        axis=1,
    )

    daily_avg_times["Average Time per Game"] = daily_avg_times[
        "Average Time per Game (sec)"
    ].apply(lambda x: f"{int(x // 60)}:{int(x % 60):02d}")
    daily_avg_times["Total Time"] = daily_avg_times["Total Time (sec)"].apply(
        lambda x: f"{int(x // 3600)}:{int((x % 3600) // 60):02d}:{int(x % 60):02d}"
        if day_filter == "All"
        else f"{int(x // 60)}:{int(x % 60):02d}"
    )

    final_daily_avg_times = (
        daily_avg_times[["Player", "Games Played", "Average Time per Game"]]
        .sort_values(by="Average Time per Game", ascending=True)
        .reset_index(drop=True)
    )

    final_total_times = (
        daily_avg_times[["Player", "Games Played", "Total Time"]]
        .sort_values(by="Total Time", ascending=True)
        .reset_index(drop=True)
    )

    # --- Initialize scores ---
    total_score = pd.DataFrame(
        {"Player": filtered_df["sender"].unique(), "Total Score": 0}
    ).merge(games_played, on="Player", how="left")

    overall_best_sum = pd.DataFrame({"Player": filtered_df["sender"].unique()})

    weekday_score = pd.DataFrame(
        {
            "Player": filtered_df["sender"].unique(),
            "Monday": 0.0,
            "Tuesday": 0.0,
            "Wednesday": 0.0,
            "Thursday": 0.0,
            "Friday": 0.0,
            "Saturday": 0.0,
            "Sunday": 0.0,
        }
    )

    overall_best_per_weekday = pd.DataFrame(
        {
            "Player": filtered_df["sender"].unique(),
            "Monday": 0,
            "Tuesday": 0,
            "Wednesday": 0,
            "Thursday": 0,
            "Friday": 0,
            "Saturday": 0,
            "Sunday": 0,
        }
    )

    # --- Per-game Rankings ---
    per_game_rankings = {}
    for game in GAMES:
        game_df = filtered_df[filtered_df["game"].str.lower() == game.lower()].copy()
        if game_df.empty:
            continue

        score_map = {1: 5, 2: 3, 3: 1}
        game_df["rank"] = game_df.groupby("date")["time_sec"].rank(method="min")
        game_df["score"] = game_df["rank"].map(score_map).fillna(0).astype(float)

        for date in game_df["date"].unique():
            date_df = game_df[game_df["date"] == date]
            if date_df["score"].sum() != 9:
                dict_scores = date_df["score"].value_counts().to_dict().items()
                for key, val in dict_scores:
                    if key == 5 and val == 2:
                        game_df.loc[
                            (game_df["date"] == date) & (game_df["score"] == key),
                            "score",
                        ] = 4
                    elif key == 5 and val > 2:
                        game_df.loc[
                            (game_df["date"] == date) & (game_df["score"] == key),
                            "score",
                        ] = 9 / val
                    elif key == 3 and val > 1:
                        game_df.loc[
                            (game_df["date"] == date) & (game_df["score"] == key),
                            "score",
                        ] = 4 / val
                    elif key == 1 and val > 1:
                        game_df.loc[
                            (game_df["date"] == date) & (game_df["score"] == key),
                            "score",
                        ] = 1 / val

        # Update total score
        score_sum = (
            game_df.groupby("sender", as_index=False)["score"]
            .sum()
            .rename(columns={"sender": "Player"})
            .fillna(0)
        )
        total_score = total_score.merge(score_sum, on="Player", how="left")
        total_score["Total Score"] = total_score["Total Score"] + total_score[
            "score"
        ].fillna(0)
        total_score = total_score.drop(columns=["score"])

        # Update weekday score
        weekday_score_sum = (
            game_df.groupby(["sender", "Weekday"], as_index=False)["score"]
            .sum()
            .rename(columns={"sender": "Player", "score": "Score"})
            .fillna(0)
        )
        for day in weekday_score.columns[1:]:
            for player in weekday_score["Player"].unique().tolist():
                try:
                    weekday_score.loc[weekday_score["Player"] == player, day] += (
                        weekday_score_sum[
                            (weekday_score_sum["Player"] == player)
                            & (weekday_score_sum["Weekday"] == day)
                        ]["Score"].values[0]
                    )
                except IndexError:
                    pass

        # Compute stats
        gp = (
            game_df.groupby("sender", as_index=False)
            .size()
            .rename(columns={"size": "Games Played"})
        )
        min_per_day = game_df.groupby("date")["time_sec"].min()
        best_rows = game_df[game_df["time_sec"].eq(game_df["date"].map(min_per_day))]
        best_per_day = best_rows.groupby("sender").size().reset_index(name="num_best")

        best_per_weekday_counts = (
            best_rows.groupby(["sender", "Weekday"]).size().reset_index(name="count")
        )
        for _, row in best_per_weekday_counts.iterrows():
            overall_best_per_weekday.loc[
                overall_best_per_weekday["Player"] == row["sender"], row["Weekday"]
            ] += row["count"]

        avg_times = game_df.groupby("sender", as_index=False)["time_sec"].mean()
        min_times = game_df.groupby("sender", as_index=False)["time_sec"].min()
        ceo_avg = game_df.groupby("sender", as_index=False)["ceo_percent"].mean()
        score_sum_copy = (
            game_df.groupby("sender", as_index=False)["score"].sum().fillna(0)
        )

        merged = (
            avg_times.merge(ceo_avg, on="sender")
            .merge(min_times, on="sender", suffixes=("_avg", "_min"))
            .merge(best_per_day, on="sender", how="left")
            .merge(score_sum_copy, on="sender", how="left")
            .merge(gp, on="sender", how="left")
            .fillna({"num_best": 0, "Games Played": 0, "score": 0})
        )

        merged = merged.sort_values(
            by="time_sec_avg" if day_filter != "All" else "num_best",
            ascending=True if day_filter != "All" else False,
        ).reset_index(drop=True)

        merged["avg_play_time_mmss"] = merged["time_sec_avg"].apply(
            lambda x: f"{int(x // 60)}:{int(x % 60):02d}"
        )
        merged["min_play_time_mmss"] = merged["time_sec_min"].apply(
            lambda x: f"{int(x // 60)}:{int(x % 60):02d}"
        )
        merged["ceo_percent"] = merged["ceo_percent"].round(2)
        merged["num_best"] = merged["num_best"].astype(int, errors="ignore")
        merged["score"] = merged["score"].astype(float, errors="ignore").round(2)

        merged = merged.rename(
            columns={
                "sender": "Player",
                "avg_play_time_mmss": "Average Time" if day_filter == "All" else "Time",
                "min_play_time_mmss": "Minimum Time",
                "ceo_percent": "Average CEO %" if day_filter == "All" else "CEO %",
                "num_best": "Times N°1" if day_filter == "All" else "N°1",
            }
        )

        if day_filter == "All":
            merged_final = (
                merged[
                    [
                        "Player",
                        "Games Played",
                        "Average Time",
                        "Minimum Time",
                        "Average CEO %",
                        "Times N°1",
                        "score",
                    ]
                ]
                .sort_values(by="Times N°1", ascending=False)
                .reset_index(drop=True)
                .rename(columns={"score": "Total Score"})
            )
            per_game_rankings[game] = _sanitize(merged_final)
        else:
            merged_final = (
                merged[["Player", "Time", "CEO %", "N°1", "score"]]
                .sort_values(by="Time", ascending=True)
                .reset_index(drop=True)
                .rename(columns={"score": "Score"})
            )
            per_game_rankings[game] = _sanitize(merged_final)

        # Overall best sum
        col_name = "Times N°1" if day_filter == "All" else "N°1"
        overall_best_sum = (
            overall_best_sum.merge(
                merged[["Player", col_name]], on="Player", how="left"
            )
            .fillna({col_name: 0})
            .rename(
                columns={
                    col_name: f"Times N°1 at {game}"
                    if day_filter == "All"
                    else f"N°1 at {game}"
                }
            )
        )

    # --- Overall summary ---
    best_cols = [
        f"Times N°1 at {game}" if day_filter == "All" else f"N°1 at {game}"
        for game in GAMES
        if (
            f"Times N°1 at {game}" in overall_best_sum.columns
            or f"N°1 at {game}" in overall_best_sum.columns
        )
    ]
    overall_best_sum["Overall Times N°1"] = (
        overall_best_sum[best_cols].sum(axis=1).astype(int, errors="ignore")
    )
    col_overall = overall_best_sum.pop("Overall Times N°1")
    overall_best_sum.insert(1, "Overall Times N°1", col_overall)
    overall_best_sum = overall_best_sum.sort_values(
        by="Overall Times N°1", ascending=False
    ).reset_index(drop=True)

    # Total score finalize
    col_gp = total_score.pop("Games Played")
    total_score.insert(1, "Games Played", col_gp)
    total_score["Total Score"] = total_score["Total Score"].round(2)
    total_score = total_score.sort_values(
        by="Total Score", ascending=False
    ).reset_index(drop=True)
    total_score.insert(
        0,
        "Rank",
        total_score["Total Score"].rank(method="min", ascending=False).astype(int),
    )

    # Round weekday scores
    for day in weekday_score.columns[1:]:
        weekday_score[day] = weekday_score[day].round(2)

    for day in overall_best_per_weekday.columns[1:]:
        overall_best_per_weekday[day] = overall_best_per_weekday[day].astype(int)

    return {
        "day_filter": day_filter,
        "total_score": _sanitize(total_score),
        "total_times": _sanitize(final_total_times),
        "average_times": _sanitize(final_daily_avg_times),
        "overall_best": _sanitize(overall_best_sum),
        "weekday_scores": _sanitize(weekday_score),
        "weekday_best": _sanitize(overall_best_per_weekday),
        "per_game_rankings": per_game_rankings,
    }


def compute_head_to_head(
    df: pd.DataFrame,
    player1: str,
    player2: str,
    date_from: str | None = None,
    date_to: str | None = None,
    count_missing: bool = False,
) -> dict:
    """Compute 1v1 head-to-head stats between two players."""
    if df.empty:
        return {"error": "No data available"}

    if date_from:
        df = df[df["date"] >= date_from]
    if date_to:
        df = df[df["date"] <= date_to]

    df["time_sec"] = df["play_time"].astype(str).apply(time_to_seconds)
    df["Weekday"] = pd.to_datetime(df["date"]).dt.day_name()

    p1_df = df[df["sender"] == player1][["date", "game", "time_sec", "Weekday"]]
    p2_df = df[df["sender"] == player2][["date", "game", "time_sec", "Weekday"]]

    merged = p1_df.merge(
        p2_df, on=["date", "game", "Weekday"], how="outer", suffixes=("_p1", "_p2")
    )

    results = []
    for _, row in merged.iterrows():
        t1, t2 = row["time_sec_p1"], row["time_sec_p2"]
        has_p1, has_p2 = pd.notna(t1), pd.notna(t2)

        if has_p1 and has_p2:
            winner = player1 if t1 < t2 else (player2 if t2 < t1 else "draw")
        elif has_p1 and not has_p2:
            if not count_missing:
                continue
            winner = player1
        elif has_p2 and not has_p1:
            if not count_missing:
                continue
            winner = player2
        else:
            continue

        results.append(
            {
                "date": row["date"],
                "game": row["game"],
                "weekday": row["Weekday"],
                "winner": winner,
            }
        )

    if not results:
        return {"error": "No matchups found"}

    results_df = pd.DataFrame(results)
    p1_wins = int((results_df["winner"] == player1).sum())
    p2_wins = int((results_df["winner"] == player2).sum())
    draws = int((results_df["winner"] == "draw").sum())
    total = p1_wins + p2_wins + draws

    # Win % over time
    daily = results_df[results_df["winner"] != "draw"].copy()
    win_over_time = []
    if not daily.empty:
        daily["is_p1"] = (daily["winner"] == player1).astype(int)
        daily["is_p2"] = (daily["winner"] == player2).astype(int)
        by_date = daily.groupby("date")[["is_p1", "is_p2"]].sum().sort_index()
        cum = by_date.cumsum()
        for date, row in cum.iterrows():
            total_at_date = row["is_p1"] + row["is_p2"]
            win_over_time.append(
                {
                    "date": date,
                    "p1_pct": round(row["is_p1"] / total_at_date * 100, 1)
                    if total_at_date > 0
                    else 0,
                    "p2_pct": round(row["is_p2"] / total_at_date * 100, 1)
                    if total_at_date > 0
                    else 0,
                }
            )

    # Wins by weekday
    days_order = [
        "Monday",
        "Tuesday",
        "Wednesday",
        "Thursday",
        "Friday",
        "Saturday",
        "Sunday",
    ]
    wins_by_weekday = []
    for day in days_order:
        day_df = results_df[results_df["weekday"] == day]
        if day_df.empty:
            continue
        w1 = int((day_df["winner"] == player1).sum())
        w2 = int((day_df["winner"] == player2).sum())
        if w1 + w2 > 0:
            wins_by_weekday.append({"day": day, "p1_wins": w1, "p2_wins": w2})

    # Wins by game
    wins_by_game = []
    for game in GAMES:
        game_df = results_df[results_df["game"].str.lower() == game.lower()]
        if game_df.empty:
            continue
        w1 = int((game_df["winner"] == player1).sum())
        w2 = int((game_df["winner"] == player2).sum())
        if w1 + w2 > 0:
            wins_by_game.append({"game": game, "p1_wins": w1, "p2_wins": w2})

    return {
        "player1": player1,
        "player2": player2,
        "p1_wins": p1_wins,
        "p2_wins": p2_wins,
        "draws": draws,
        "total": total,
        "win_over_time": win_over_time,
        "wins_by_weekday": wins_by_weekday,
        "wins_by_game": wins_by_game,
    }
