import streamlit as st
import pandas as pd
from supabase import create_client


# Import parser
from linkedin_games_parser import parse_whatsapp_chat


# Constants
GAMES = ["Tango", "Queens", "Mini Sudoku", "Zip"]

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
    per_game_rankings = {}
    total_score = pd.DataFrame(columns=["Player", "Total Score"])
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

        except Exception as e:
            import traceback

            st.error(f"Error parsing chat: {e}")
            st.code(traceback.format_exc())
            return per_game_rankings, total_score

    if df is None:
        st.warning("No data available. Please upload a WhatsApp chat file.")
        return per_game_rankings, total_score

    # ------------------- Filter by day -------------------
    st.subheader("Filter by day")
    unique_days = sorted(df["date"].unique(), reverse=True)
    day_filter = st.selectbox(
        "Select day (or 'All' for overall)", options=["All"] + unique_days
    )
    filtered_df = df if day_filter == "All" else df[df["date"] == day_filter]
    if day_filter == "All":
        default_start_date = "2025-10-14"
        day_from = st.selectbox(
            "Select the day from which to start the overall ranking (Defaults to 2025-10-14)",
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

    # ------------------- Compute average times -------------------
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

    daily_avg_times["Average Time per Game"] = daily_avg_times[
        "Average Time per Game (sec)"
    ].apply(lambda x: f"{int(x // 60)}:{int(x % 60):02d}")
    daily_avg_times["Total Time"] = daily_avg_times["Total Time (sec)"].apply(
        lambda x: f"{int(x // 3600)}:{int((x % 3600) // 60):02d}:{int(x % 60):02d}"
        if day_filter == "All"
        else f"{int(x // 60)}:{int(x % 60):02d}"
    )

    daily_avg_times = (
        daily_avg_times[
            ["Player", "Total Time", "Games Played", "Average Time per Game"]
        ]
        .sort_values(by="Average Time per Game")
        .reset_index(drop=True)
    )

    # ------------------- Initialize scores -------------------
    total_score = pd.DataFrame(
        {"Player": filtered_df["sender"].unique(), "Total Score": 0}
    )
    overall_best_sum = pd.DataFrame({"Player": filtered_df["sender"].unique()})

    # ------------------- Per-game Rankings -------------------
    for game in GAMES:
        game_df = filtered_df[filtered_df["game"].str.lower() == game.lower()].copy()
        if game_df.empty:
            continue

        # Rank players by time
        score_map = {1: 5, 2: 3, 3: 1}
        game_df["rank"] = game_df.groupby("date")["time_sec"].rank(method="min")
        game_df["score"] = game_df["rank"].map(score_map).fillna(0)

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
        best_per_day = (
            game_df.loc[
                game_df.groupby("date")["time_sec"].idxmin(), ["date", "sender"]
            ]
            .groupby("sender")
            .size()
            .reset_index(name="num_best")
        )

        avg_times = game_df.groupby("sender", as_index=False)["time_sec"].mean()
        min_times = game_df.groupby("sender", as_index=False)["time_sec"].min()
        ceo_avg = game_df.groupby("sender", as_index=False)["ceo_percent"].mean()

        merged = (
            avg_times.merge(ceo_avg, on="sender")
            .merge(min_times, on="sender", suffixes=("_avg", "_min"))
            .merge(best_per_day, on="sender", how="left")
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

        merged = merged.rename(
            columns={
                "sender": "Player",
                "avg_play_time_mmss": "Average Time" if day_filter == "All" else "Time",
                "min_play_time_mmss": "Minimum Time",
                "ceo_percent": "Average CEO %" if day_filter == "All" else "CEO %",
                "num_best": "Times N°1" if day_filter == "All" else "N°1",
            }
        )

        if not day_filter != "All":
            per_game_rankings[game] = merged[
                [
                    "Player",
                    "Average Time",
                    "Minimum Time",
                    "Average CEO %",
                    "Times N°1",
                ]
            ]
        else:
            per_game_rankings[game] = merged[
                [
                    "Player",
                    "Time",
                    "CEO %",
                    "N°1",
                ]
            ]

        # Add dataframe combining all times number of best times
        overall_best_sum = (
            overall_best_sum.merge(
                merged[["Player", "Times N°1" if not day_filter != "All" else "N°1"]],
                on="Player",
                how="left",
            )
            .fillna({"Times N°1" if not day_filter != "All" else "N°1": 0})
            .rename(
                columns={
                    "Times N°1"
                    if not day_filter != "All"
                    else "N°1": f"Times N°1 at {game}"
                    if not day_filter != "All"
                    else f"N°1 at {game}"
                }
            )
        )

    # ------------------- Overall summary -------------------
    # Sum num_best across all games for overall ranking
    overall_best_sum["Overall Times N°1"] = (
        overall_best_sum[
            [
                f"Times N°1 at {game}" if not day_filter != "All" else f"N°1 at {game}"
                for game in GAMES
                if f"Times N°1 at {game}" in overall_best_sum.columns
                or f"N°1 at {game}" in overall_best_sum.columns
            ]
        ]
        .sum(axis=1)
        .astype(int, errors="ignore")
    )
    overall_best_sum = (
        overall_best_sum[["Player", "Overall Times N°1"]]
        .sort_values(by="Overall Times N°1", ascending=False)
        .reset_index(drop=True)
    )

    # Add results to the dictionary
    per_game_rankings["N°1"] = overall_best_sum
    per_game_rankings["Average Time per Game"] = daily_avg_times
    total_score = total_score.sort_values(
        by="Total Score", ascending=False
    ).reset_index(drop=True)

    return per_game_rankings, total_score


############################### Main #####################################
def main():
    per_game_rankings, total_score = streamlit_app(GAMES=GAMES)

    if not per_game_rankings:
        return

    st.subheader("**Total Scores**")
    st.dataframe(total_score)
    st.markdown(
        "_Note: Total scores are computed by awarding 5 points for the best player, "
        "3 points for the second-best player, and 1 point for the third-best player, per game per day._"
    )

    for title, df in per_game_rankings.items():
        st.markdown(f"**{title} Rankings**")
        st.dataframe(df)


if __name__ == "__main__":
    main()
