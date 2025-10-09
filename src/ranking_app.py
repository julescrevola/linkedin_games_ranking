import streamlit as st
import pandas as pd

# Import your parser and ranking functions
from linkedin_games_parser import parse_whatsapp_chat

# Constants
GAMES = ["Tango", "Queens", "Mini Sudoku", "Zip"]
PARSER_SCRIPT = "linkedin_games_parser.py"  # Optional: can be run inside Streamlit
OUTPUT_DIR = "../data/output"


################################### Tools #########################################
# Convert play_time to seconds
def time_to_seconds(time_str):
    parts = [int(p) for p in time_str.strip().split(":")]
    if len(parts) == 2:
        return parts[0] * 60 + parts[1]
    elif len(parts) == 3:
        return parts[0] * 3600 + parts[1] * 60 + parts[2]
    else:
        return None


############################### Streamlit App #####################################
st.title("LinkedIn Mini Games Leaderboard")

# Upload WhatsApp chat
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
        df = df[df["sender"] != "X - Games (Nazionale di Zip)"]
        st.dataframe(df)
    except Exception as e:
        st.error(f"Error parsing chat: {e}")
        df = None

    if df is not None and not df.empty:
        # Filter by day
        st.subheader("Filter by day")
        unique_days = sorted(df["date"].unique(), reverse=True)
        day_filter = st.selectbox(
            "Select day (or 'All' for overall)", options=["All"] + unique_days
        )
        if day_filter != "All":
            filtered_df = df[df["date"] == day_filter]
        else:
            filtered_df = df

        # Convert play_time to seconds
        filtered_df["time_sec"] = (
            filtered_df["play_time"].astype(str).apply(time_to_seconds)
        )
        filtered_df["ceo_percent"] = pd.to_numeric(
            filtered_df["ceo_percent"], errors="coerce"
        )

        # Daily total time and normalized average
        # Sum total time per player per day
        daily_times = filtered_df.groupby(["date", "sender"], as_index=False)[
            "time_sec"
        ].sum()
        daily_times = daily_times.rename(
            columns={"sender": "Player", "time_sec": "Total Time (sec)"}
        )

        # Count total number of games played per player
        games_played = (
            filtered_df.groupby("sender", as_index=False)
            .size()
            .rename(columns={"size": "Games Played"})
        )
        games_played = games_played.rename(columns={"sender": "Player"})

        # Compute total time across all days per player
        total_time_all_days = daily_times.groupby("Player", as_index=False)[
            "Total Time (sec)"
        ].sum()

        # Merge with number of games played
        daily_avg_times = total_time_all_days.merge(
            games_played, on="Player", how="left"
        )

        # Compute normalized average time (total_time / total_games)
        daily_avg_times["Average Time per Game (sec)"] = (
            daily_avg_times["Total Time (sec)"] / daily_avg_times["Games Played"]
        ).round(2)

        # Convert to mm:ss for readability
        daily_avg_times["Average Time per Game"] = daily_avg_times[
            "Average Time per Game (sec)"
        ].apply(lambda x: f"{int(x // 60)}:{int(x % 60):02d}")
        daily_avg_times["Total Time"] = daily_avg_times["Total Time (sec)"].apply(
            lambda x: f"{int(x // 3600)}:{int((x % 3600) // 60):02d}:{int(x % 60):02d}"
        )

        # Keep clean columns
        daily_avg_times = (
            daily_avg_times[
                ["Player", "Total Time", "Games Played", "Average Time per Game"]
            ]
            .sort_values(by="Average Time per Game")
            .reset_index(drop=True)
        )

        per_game_rankings = {}
        overall_best_sum = pd.DataFrame({"Player": df["sender"].unique()})

        # Compute per-game rankings
        st.subheader("Per-game Rankings")
        # Initialize final df for totals across all games
        overall_best_sum = pd.DataFrame({"Player": filtered_df["sender"].unique()})
        for game in GAMES:
            game_df = filtered_df[
                filtered_df["game"].str.lower() == game.lower()
            ].copy()
            if game_df.empty:
                continue

            # For each date, find the player with the lowest time
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

            # Rename and keep only relevant columns
            merged = merged.rename(
                columns={
                    "sender": "Player",
                    "avg_play_time_mmss": "Average Time"
                    if not day_filter != "All"
                    else "Time",
                    "min_play_time_mmss": "Minimum Time",
                    "ceo_percent": "Average CEO %"
                    if not day_filter != "All"
                    else "CEO %",
                    "num_best": "Times N°1" if not day_filter != "All" else "N°1",
                }
            )

            # Add dataframe combining all times number of best times
            overall_best_sum = (
                overall_best_sum.merge(
                    merged[
                        ["Player", "Times N°1" if not day_filter != "All" else "N°1"]
                    ],
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

            st.markdown(f"**{game} Rankings**")
            st.dataframe(
                merged[
                    [
                        "Player",
                        "Average Time" if not day_filter != "All" else "Time",
                        "Minimum Time",
                        "Average CEO %" if not day_filter != "All" else "CEO %",
                        "Times N°1" if not day_filter != "All" else "N°1",
                    ]
                ].reset_index(drop=True)
            )

        # Sum num_best across all games for overall ranking
        overall_best_sum["Overall Times N°1"] = (
            overall_best_sum[
                [
                    f"Times N°1 at {game}"
                    for game in GAMES
                    if f"Times N°1 at {game}" in overall_best_sum.columns
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

        st.subheader("**Overall Times N°1 of each Game**")
        st.dataframe(overall_best_sum)

        # Display average times per game
        st.subheader("**Average Time per Game**")
        st.dataframe(daily_avg_times)
