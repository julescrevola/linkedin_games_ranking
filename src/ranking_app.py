import re
import streamlit as st
import pandas as pd
from supabase import create_client


# Import parser
from linkedin_games_parser import parse_whatsapp_chat


# Constants
GAMES = ["Zip", "Tango", "Queens", "Mini Sudoku"]

# Set up Supabase
SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_KEY = st.secrets["SUPABASE_KEY"]

supabase_cred = create_client(SUPABASE_URL, SUPABASE_KEY)


################################### Tools #########################################
# Convert play_time to seconds
def time_to_seconds(time_str):
    if not isinstance(time_str, str):
        return None
    parts = [int(p) for p in time_str.strip().split(":")]
    if len(parts) == 2:
        return parts[0] * 60 + parts[1]
    elif len(parts) == 3:
        return parts[0] * 3600 + parts[1] * 60 + parts[2]
    else:
        return None


# Load existing data from Supabase
@st.cache_data
def load_data_from_supabase():
    result = (
        supabase_cred.table("game_data")
        .select("*")
        .order("uploaded_at", desc=True)
        .limit(1)
        .execute()
    )
    if result.data:
        return pd.DataFrame(result.data[0]["data"])
    return None


############################### Streamlit App #####################################
def streamlit_app(GAMES: list[str] = GAMES):
    """Runs the Streamlit leaderboard app and returns ranking data."""

    st.image(
        "data/input/anto.jpg",
        caption="Antonio Roberto Ventura, 2025 Champion 💪",
    )

    per_game_rankings = {}
    total_score = pd.DataFrame(columns=["Player", "Total Score"])
    final_total_times = pd.DataFrame()
    final_daily_avg_times = pd.DataFrame()
    overall_best_sum = pd.DataFrame()
    day_filter = "All"

    st.title("LinkedIn Mini Games Leaderboard")

    # Check if existing data exists
    st.info("Checking for stored leaderboard data...")
    existing = load_data_from_supabase()  # Should return a DataFrame or None
    uploaded_file = None
    df = None

    if existing is not None:
        st.success(f"Found existing data from Supabase! ({len(existing)} entries)")
        use_existing = st.radio(
            "What would you like to do?",
            ["Use Stored Data", "Upload New Data"],
            horizontal=True,
        )

        if use_existing == "Use Stored Data":
            df = existing.copy()
            st.success(f"Using stored data with {len(df)} entries.")
        else:
            uploaded_file = st.file_uploader(
                "Upload new WhatsApp chat (.txt)", type=["txt"]
            )
    else:
        st.info("No existing data found. Please upload a WhatsApp chat file.")
        uploaded_file = st.file_uploader(
            "Upload WhatsApp chat (.txt format)", type=["txt"]
        )

    # Parse and save new upload
    if df is None and uploaded_file is not None:
        try:
            st.info("Parsing WhatsApp chat...")
            df = parse_whatsapp_chat(uploaded_file)
            st.success(f"Parsed {len(df)} game entries!")
            df = df[df["sender"] != "X - Games (Nazionale di Zip)"]

            # Save parsed data to Supabase
            st.info("Saving parsed data to Supabase...")
            supabase_cred.table("game_data").insert(
                {"data": df.to_dict(orient="records")}
            ).execute()
            st.success("Data saved to Supabase successfully!")
            load_data_from_supabase.clear()

        except Exception as e:
            import traceback

            st.error(f"Error parsing chat: {e}")
            st.code(traceback.format_exc())
            return per_game_rankings, total_score

    if df is None:
        st.warning("No data available. Please upload a WhatsApp chat file.")
        return (
            per_game_rankings,
            total_score,
            final_total_times,
            final_daily_avg_times,
            overall_best_sum,
        )

    # Hard code unsaved results for Samuele on 2025-10-17 for Queens
    # Regex pattern — case-insensitive search for 'samu'
    pattern = re.compile(r"samu", re.IGNORECASE)
    # Find name that matches
    match = [name for name in df["sender"].unique() if pattern.search(name)][0].title()
    unsaved_data = pd.DataFrame(
        {
            "date": ["2025-10-17"],
            "game": ["Queens"],
            "game_number": [535],
            "sender": [match],
            "play_time": ["1:45"],
            "ceo_percent": None,
        }
    )
    df = pd.concat([df, unsaved_data], ignore_index=True).drop_duplicates()

    # ------------------- Filter by day -------------------
    st.subheader("Filter by day")
    unique_days = sorted(df["date"].unique(), reverse=True)
    day_filter = st.selectbox(
        "Select day (or 'All' for overall)", options=["All"] + unique_days
    )
    filtered_df = df if day_filter == "All" else df[df["date"] == day_filter]
    if day_filter == "All":
        default_start_date = "2026-01-01"
        day_from = st.selectbox(
            "Select the day from which to start the overall ranking (Defaults to 2026-01-01)",
            options=[default_start_date] + unique_days,
        )
        filtered_df = filtered_df[filtered_df["date"] >= day_from]
        st.write(f"Showing {len(filtered_df)} entries starting from {day_from}")

    # ------------------- Preprocess -------------------
    filtered_df["time_sec"] = (
        filtered_df["play_time"].astype(str).apply(time_to_seconds)
    )
    filtered_df["ceo_percent"] = pd.to_numeric(
        filtered_df["ceo_percent"], errors="coerce"
    )

    # ------------------- Compute total and average times for all games together -------------------
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
    final_daily_avg_times.index += 1

    final_total_times = (
        daily_avg_times[["Player", "Games Played", "Total Time"]]
        .sort_values(by="Total Time", ascending=True)
        .reset_index(drop=True)
    )
    final_total_times.index += 1

    # ------------------- Compute variance for all games together -------------------
    variance_df = filtered_df.merge(
        filtered_df.groupby(["date", "sender"], as_index=False)["time_sec"].mean(),
        suffixes=("", "_avg"),
        on=["date", "sender"],
        how="left",
    )
    variance_df["mean_diff"] = abs(
        variance_df["time_sec"] - variance_df["time_sec_avg"]
    ).round(2)
    variance_summary = (
        variance_df.groupby("sender", as_index=False)["mean_diff"]
        .mean()
        .rename(columns={"sender": "Player", "mean_diff": "Variance"})
        .sort_values(by="Variance", ascending=True)
        .reset_index(drop=True)
    )
    variance_summary.index += 1

    # ------------------- Initialize scores -------------------
    total_score = pd.DataFrame(
        {"Player": filtered_df["sender"].unique(), "Total Score": 0}
    ).merge(games_played, on="Player", how="left")
    overall_best_sum = pd.DataFrame({"Player": filtered_df["sender"].unique()})

    # ------------------- Per-game Rankings -------------------
    for game in GAMES:
        game_df = filtered_df[filtered_df["game"].str.lower() == game.lower()].copy()
        if game_df.empty:
            st.info(f"No data for game: {game}")
            continue

        # Rank players by time
        score_map = {1: 5, 2: 3, 3: 1}
        game_df["rank"] = game_df.groupby("date")["time_sec"].rank(method="min")
        game_df["score"] = game_df["rank"].map(score_map).fillna(0).astype(float)
        success_list = []
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
            if (
                (9 <= game_df[game_df["date"] == date]["score"].sum() <= 9.00001)
                or (
                    len(date_df) == 2
                    and game_df[game_df["date"] == date]["score"].sum() == 8
                )
                or (
                    len(date_df) == 1
                    and game_df[game_df["date"] == date]["score"].sum() == 5
                )
                or (len(date_df) == 0)
            ):
                success_list.append(True)
        if len(success_list) == len(game_df["date"].unique()):
            st.success(f"Scores computed successfully for {game}!")

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

        # Compute stats
        # Find the minimum time per day
        min_per_day = game_df.groupby("date")["time_sec"].min()
        # Keep all rows that match the daily minimum (ties included)
        best_rows = game_df[game_df["time_sec"].eq(game_df["date"].map(min_per_day))]
        # Count how many times each sender was best
        best_per_day = best_rows.groupby("sender").size().reset_index(name="num_best")

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
            .fillna({"num_best": 0})
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
            merged_final.index += 1
            per_game_rankings[game] = merged_final
        else:
            merged_final = (
                merged[
                    [
                        "Player",
                        "Time",
                        "CEO %",
                        "N°1",
                        "score",
                    ]
                ]
                .sort_values(by="Time", ascending=True)
                .reset_index(drop=True)
                .rename(columns={"score": "Score"})
            )
            merged_final.index += 1
            per_game_rankings[game] = merged_final

        # Add dataframe combining all times number of best times
        overall_best_sum = (
            overall_best_sum.merge(
                merged[["Player", "Times N°1" if day_filter == "All" else "N°1"]],
                on="Player",
                how="left",
            )
            .fillna({"Times N°1" if day_filter == "All" else "N°1": 0})
            .rename(
                columns={
                    "Times N°1"
                    if day_filter == "All"
                    else "N°1": f"Times N°1 at {game}"
                    if day_filter == "All"
                    else f"N°1 at {game}"
                }
            )
        )

    # ------------------- Overall summary -------------------
    # Sum num_best across all games for overall ranking
    overall_best_sum["Overall Times N°1"] = (
        overall_best_sum[
            [
                f"Times N°1 at {game}" if day_filter == "All" else f"N°1 at {game}"
                for game in GAMES
                if f"Times N°1 at {game}" in overall_best_sum.columns
                or f"N°1 at {game}" in overall_best_sum.columns
            ]
        ]
        .sum(axis=1)
        .astype(int, errors="ignore")
    )
    col_overall = overall_best_sum.pop("Overall Times N°1")
    overall_best_sum.insert(1, "Overall Times N°1", col_overall)
    overall_best_sum = overall_best_sum.sort_values(
        by="Overall Times N°1", ascending=False
    ).reset_index(drop=True)
    overall_best_sum.index += 1

    # Sort total scores
    col_games_played = total_score.pop("Games Played")
    total_score.insert(1, "Games Played", col_games_played)
    total_score["Total Score"] = total_score["Total Score"].round(2)
    total_score = total_score.sort_values(
        by="Total Score", ascending=False
    ).reset_index(drop=True)
    total_score.index += 1

    return (
        per_game_rankings,
        total_score,
        final_total_times,
        final_daily_avg_times,
        variance_summary,
        overall_best_sum,
    )


############################### Main #####################################
def main():
    (
        per_game_rankings,
        total_score,
        final_total_times,
        final_daily_avg_times,
        variance_summary,
        overall_best_sum,
    ) = streamlit_app(GAMES=GAMES)

    if not per_game_rankings:
        return

    ranking_type = st.radio(
        "What kind of ranking would you like to see?",
        ["Total Points", "Total Time", "Average Time", "Times N°1", "Variance"],
        horizontal=True,
    )
    if ranking_type == "Total Points":
        st.subheader("**Total Scores**")
        st.dataframe(total_score)
        st.markdown(
            "_Note: Total scores are computed by awarding 5 points for the best player, "
            "3 points for the second-best player, and 1 point for the third-best player, per game per day._"
        )
    elif ranking_type == "Total Time":
        st.subheader("**Total Times**")
        st.dataframe(final_total_times)
        st.markdown(
            "_Note: For players who did not play all games, their total time has been adjusted as if they had played all games at their average time._"
        )
    elif ranking_type == "Average Time":
        st.subheader("**Average Times per Game**")
        st.dataframe(final_daily_avg_times)
    elif ranking_type == "Times N°1":
        st.subheader("**Overall Times N°1**")
        st.dataframe(overall_best_sum)
    elif ranking_type == "Variance":
        st.subheader("**Overall Variance**")
        st.dataframe(variance_summary)

    st.subheader("**Per-Game Rankings**")
    for title, df in per_game_rankings.items():
        st.markdown(f"**{title} Rankings**")
        st.dataframe(df)


if __name__ == "__main__":
    main()
