import streamlit as st
import pandas as pd

# Import your parser and ranking functions
from linkedin_games_parser import parse_whatsapp_chat

# Constants
GAMES = ["Tango", "Queens", "Mini Sudoku", "Zip"]
PARSER_SCRIPT = "linkedin_games_parser.py"  # Optional: can be run inside Streamlit
OUTPUT_DIR = "../data/output"

st.title("LinkedIn Mini Games Leaderboard")

# --- Step 1: Upload WhatsApp chat ---
uploaded_file = st.file_uploader(
    "Upload your WhatsApp chat (.txt format)", type=["txt"]
)

if uploaded_file:
    st.info("Parsing WhatsApp chat...")
    try:
        df = parse_whatsapp_chat(
            uploaded_file
        )  # returns DataFrame with correct columns
        st.success(f"Parsed {len(df)} game entries!")
        st.dataframe(df)
    except Exception as e:
        st.error(f"Error parsing chat: {e}")
        df = None

    if df is not None and not df.empty:
        # --- Step 2: Filter by day ---
        st.subheader("Filter by day")
        unique_days = sorted(df["date"].unique(), reverse=True)
        day_filter = st.selectbox(
            "Select day (or 'All' for overall)", options=["All"] + unique_days
        )
        if day_filter != "All":
            filtered_df = df[df["date"] == day_filter]
        else:
            filtered_df = df

        # --- Step 3: Compute per-game rankings ---
        st.subheader("Per-game Rankings")
        # Initialize final df for totals across all games
        overall_best_sum = pd.DataFrame({"sender": filtered_df["sender"].unique()})
        for game in GAMES:
            game_df = filtered_df[
                filtered_df["game"].str.lower() == game.lower()
            ].copy()
            if game_df.empty:
                continue

            # Convert play_time to seconds
            def time_to_seconds(time_str):
                parts = [int(p) for p in time_str.strip().split(":")]
                if len(parts) == 2:
                    return parts[0] * 60 + parts[1]
                elif len(parts) == 3:
                    return parts[0] * 3600 + parts[1] * 60 + parts[2]
                else:
                    return None

            game_df["time_sec"] = game_df["play_time"].apply(time_to_seconds)
            game_df["ceo_percent"] = pd.to_numeric(
                game_df["ceo_percent"], errors="coerce"
            )

            # For each date, find the player(s) with the lowest time
            best_per_day = (
                game_df.loc[
                    game_df.groupby("date")["time_sec"].idxmin(), ["date", "sender"]
                ]
                .groupby("sender")
                .size()
                .reset_index(name="num_best")
            )

            # Compute averages and min times per player
            avg_times = game_df.groupby("sender", as_index=False)["time_sec"].mean()
            min_times = game_df.groupby("sender", as_index=False)["time_sec"].min()
            ceo_avg = game_df.groupby("sender", as_index=False)["ceo_percent"].mean()

            merged = (
                avg_times.merge(ceo_avg, on="sender")
                .merge(min_times, on="sender", suffixes=("_avg", "_min"))
                .merge(best_per_day, on="sender", how="left")
                .fillna({"num_best": 0})
            )

            if day_filter != "All":
                # Sort by lowest time (best performance first)
                merged = merged.sort_values(
                    by="time_sec_avg", ascending=True
                ).reset_index(drop=True)
            else:
                # Sort by number of times best (highest first)
                merged = merged.sort_values(by="num_best", ascending=False).reset_index(
                    drop=True
                )

            # Convert seconds back to mm:ss
            merged["avg_play_time_mmss"] = merged["time_sec_avg"].apply(
                lambda x: f"{int(x // 60)}:{int(x % 60):02d}"
            )
            merged["min_play_time_mmss"] = merged["time_sec_min"].apply(
                lambda x: f"{int(x // 60)}:{int(x % 60):02d}"
            )
            # Round CEO percentage to 2 decimals
            merged["ceo_percent"] = merged["ceo_percent"].round(2)
            # Convert num_best to int
            merged["num_best"] = merged["num_best"].astype(int, errors="ignore")

            # Add dataframe combining all times number of best times
            overall_best_sum = (
                overall_best_sum.merge(
                    merged[["sender", "num_best"]], on="sender", how="left"
                )
                .fillna({"num_best": 0})
                .rename(columns={"num_best": f"num_best_{game}"})
            )

            st.markdown(f"**{game} Rankings**")
            st.dataframe(
                merged[
                    [
                        "sender",
                        "avg_play_time_mmss",
                        "min_play_time_mmss",
                        "ceo_percent",
                        "num_best",
                    ]
                ].reset_index(drop=True)
            )

        # Sum num_best across all games for overall ranking
        overall_best_sum["num_best_total"] = (
            overall_best_sum[
                [
                    f"num_best_{game}"
                    for game in GAMES
                    if f"num_best_{game}" in overall_best_sum.columns
                ]
            ]
            .sum(axis=1)
            .astype(int, errors="ignore")
        )
        overall_best_sum = (
            overall_best_sum[["sender", "num_best_total"]]
            .sort_values(by="num_best_total", ascending=False)
            .reset_index(drop=True)
        )

        st.subheader("**Overall Times N°1 of each Game**")
        st.dataframe(overall_best_sum)
