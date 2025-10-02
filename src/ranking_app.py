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
        unique_days = sorted(df["date"].unique())
        day_filter = st.selectbox(
            "Select day (or 'All' for overall)", options=["All"] + unique_days
        )
        if day_filter != "All":
            filtered_df = df[df["date"] == day_filter]
        else:
            filtered_df = df

        # --- Step 3: Compute per-game rankings ---
        st.subheader("Per-game Rankings")
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

            # Compute averages and min times per player
            avg_times = game_df.groupby("sender", as_index=False)["time_sec"].mean()
            min_times = game_df.groupby("sender", as_index=False)["time_sec"].min()
            ceo_avg = game_df.groupby("sender", as_index=False)["ceo_percent"].mean()

            merged = avg_times.merge(ceo_avg, on="sender").merge(
                min_times, on="sender", suffixes=("_avg", "_min")
            )

            # Sort by best avg time
            merged = merged.sort_values("time_sec_avg")

            # Convert seconds back to mm:ss
            merged["avg_play_time_mmss"] = merged["time_sec_avg"].apply(
                lambda x: f"{int(x // 60)}:{int(x % 60):02d}"
            )
            merged["min_play_time_mmss"] = merged["time_sec_min"].apply(
                lambda x: f"{int(x // 60)}:{int(x % 60):02d}"
            )

            st.markdown(f"**{game} Rankings**")
            st.dataframe(
                merged[
                    [
                        "sender",
                        "avg_play_time_mmss",
                        "min_play_time_mmss",
                        "ceo_percent",
                    ]
                ].reset_index(drop=True)
            )
