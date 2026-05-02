import streamlit as st
import pandas as pd
from supabase import create_client
from linkedin_games_parser import parse_whatsapp_chat


# Constants
GAMES = ["Zip", "Tango", "Queens", "Mini Sudoku", "Patches"]
PLAYERS = [
    "Antonio Ventura",
    "Carlo Patti",
    "Jules Crevola",
    "Samuele Bodon",
    "Alessio Teruzzi",
    "Alessandro Viletto",
    "Edoardo Occhilupo",
    "Andrea Pisetta",
    "Giorgio Cappuccinelli",
]

# Set up Supabase
SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_KEY = st.secrets["SUPABASE_KEY"]

supabase_cred_jules = create_client(SUPABASE_URL, SUPABASE_KEY)


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


# Load data from Supabase structured tables or from uploaded WhatsApp chat if data is outdated
def load_data_from_supabase():
    use_existing = st.radio(
        "What would you like to do?",
        ["Use Stored Data", "Upload New Data"],
        horizontal=True,
    )
    if use_existing == "Use Stored Data":
        df = pd.DataFrame(
            (
                supabase_cred_jules.table("game_data")
                .select("*")
                .order("uploaded_at", desc=True)
                .execute()
            ).data
        ).drop_duplicates(subset=["date", "sender", "game"])
    else:
        uploaded_file = st.file_uploader(
            "Upload new WhatsApp chat (.txt)", type=["txt"]
        )
        if uploaded_file is not None:
            df = parse_whatsapp_chat(uploaded_file).drop_duplicates(
                subset=["date", "sender", "game"]
            )
            df = df[df["game"].isin(GAMES)]
            df = df[df["sender"].isin(PLAYERS)]

            # Fetch existing data to check for duplicates
            existing_df = pd.DataFrame(
                supabase_cred_jules.table("game_data")
                .select("date,sender,game")
                .execute()
                .data
            )
            if not existing_df.empty:
                existing_set = set(
                    zip(existing_df["date"], existing_df["sender"], existing_df["game"])
                )

                # Filter to only new rows
                new_df = df[
                    ~df.apply(
                        lambda row: (row["date"], row["sender"], row["game"])
                        in existing_set,
                        axis=1,
                    )
                ]

                if not new_df.empty:
                    supabase_cred_jules.table("game_data").insert(
                        new_df.to_dict(orient="records"),
                    ).execute()
                    st.success(f"Added {len(new_df)} new game entries!")
                else:
                    st.info("No new entries to add.")
            else:
                supabase_cred_jules.table("game_data").insert(
                    df.to_dict(orient="records"),
                ).execute()
                st.success(f"Added {len(df)} game entries!")
        else:
            df = pd.DataFrame()  # Empty if no file uploaded
    return df, use_existing


############################### Streamlit App #####################################
def streamlit_app(GAMES: list[str] = GAMES):
    """Runs the Streamlit leaderboard app and returns ranking data."""

    st.image(
        "anto.jpg",
        caption="Antonio Roberto Ventura, 2026 Q1 Champion",
    )

    per_game_rankings = {}
    total_score = pd.DataFrame(columns=["Player", "Total Score"])
    final_total_times = pd.DataFrame()
    final_daily_avg_times = pd.DataFrame()
    overall_best_sum = pd.DataFrame()
    day_filter = "All"

    st.title("LinkedIn Mini Games Leaderboard")

    df, mode = load_data_from_supabase()

    if (mode == "Upload New Data" and df.empty) or (
        mode == "Use Stored Data" and df.empty
    ):
        st.info("Please upload a WhatsApp chat .txt file to load new data.")
        return (
            "All",
            {},
            pd.DataFrame(),
            pd.DataFrame(),
            pd.DataFrame(),
            pd.DataFrame(),
            pd.DataFrame(),
            pd.DataFrame(),
        )
    elif df is None or df.empty:
        st.warning("No data available. Please upload a new WhatsApp chat .txt file.")
        return (
            "All",
            {},
            pd.DataFrame(),
            pd.DataFrame(),
            pd.DataFrame(),
            pd.DataFrame(),
            pd.DataFrame(),
            pd.DataFrame(),
        )

    df["Weekday"] = pd.to_datetime(df["date"]).dt.day_name()

    # ------------------- Filter by day -------------------
    st.subheader("Filter by day")
    unique_days = sorted(df["date"].unique(), reverse=True)
    day_filter = st.selectbox(
        "Select day (or 'All' for overall)", options=["All"] + unique_days
    )
    filtered_df = df if day_filter == "All" else df[df["date"] == day_filter]
    if day_filter == "All":
        # Start date
        default_start_date = "2026-04-01"
        day_from = st.selectbox(
            f"Select the day from which to start the overall ranking (Defaults to {default_start_date})",
            options=[default_start_date] + unique_days,
        )
        filtered_df = filtered_df[filtered_df["date"] >= day_from]
        # End date
        default_end_date = filtered_df["date"].max()
        unique_days_after = [day for day in unique_days if day >= day_from]
        day_to = st.selectbox(
            f"Select the day until which to show the overall ranking (Defaults to {default_end_date})",
            options=[default_end_date] + unique_days_after,
        )
        filtered_df = filtered_df[filtered_df["date"] <= day_to]
        st.write(f"Showing {len(filtered_df)} entries from {day_from} to {day_to}")

    # ------------------- Preprocess -------------------
    filtered_df["time_sec"] = (
        filtered_df["play_time"].astype(str).apply(time_to_seconds).astype(int)
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

    # ------------------- Initialize scores -------------------
    # Total score
    total_score = pd.DataFrame(
        {"Player": filtered_df["sender"].unique(), "Total Score": 0}
    ).merge(games_played, on="Player", how="left")
    # Times N°1
    overall_best_sum = pd.DataFrame({"Player": filtered_df["sender"].unique()})
    # Score per weekday
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
        },
    )
    # Times N°1 per weekday
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
        },
    )

    # ------------------- Per-game Rankings -------------------
    for game in GAMES:
        game_df = filtered_df[filtered_df["game"].str.lower() == game.lower()].copy()
        if game_df.empty:
            continue

        # Rank players by time
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
        weekday_score_sum = pd.DataFrame(
            game_df.groupby(["sender", "Weekday"], as_index=False)["score"]
            .sum()
            .rename(columns={"sender": "Player", "score": "Score"})
            .fillna(0)
        )
        for day in weekday_score.columns[1:]:  # Skip "Player" column
            for player in weekday_score["Player"].unique().tolist():
                try:
                    weekday_score.loc[weekday_score["Player"] == player, day] += (
                        weekday_score_sum[
                            (weekday_score_sum["Player"] == player)
                            & (weekday_score_sum["Weekday"] == day)
                        ]["Score"].values[0]
                    )
                except IndexError:
                    weekday_score.loc[weekday_score["Player"] == player, day] += 0

        # Compute stats
        # Compute number of games played for each player in this game
        games_played = (
            game_df.groupby("sender", as_index=False)
            .size()
            .rename(columns={"size": "Games Played"})
        )
        # Find the minimum time per day
        min_per_day = game_df.groupby("date")["time_sec"].min()
        # Keep all rows that match the daily minimum (ties included)
        best_rows = game_df[game_df["time_sec"].eq(game_df["date"].map(min_per_day))]
        # Count how many times each sender was best
        best_per_day = best_rows.groupby("sender").size().reset_index(name="num_best")
        # Count how many times each sender was best per weekday
        best_per_weekday_counts = (
            best_rows.groupby(["sender", "Weekday"]).size().reset_index(name="count")
        )
        for _, row in best_per_weekday_counts.iterrows():
            player = row["sender"]
            day = row["Weekday"]
            count = row["count"]
            overall_best_per_weekday.loc[
                overall_best_per_weekday["Player"] == player, day
            ] += count

        # Other stats
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
            .merge(games_played, on="sender", how="left")
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
    total_score.insert(
        0,
        "Rank",
        total_score["Total Score"].rank(method="min", ascending=False).astype(int),
    )
    total_score.index += 1

    # Round score and reset weekday scores index
    for day in weekday_score.columns[1:]:  # Skip "Player" column
        weekday_score[day] = weekday_score[day].round(2)
    weekday_score.index += 1

    # Reset times n°1 per weekday index and convert to int
    for day in overall_best_per_weekday.columns[1:]:  # Skip "Player" column
        overall_best_per_weekday[day] = overall_best_per_weekday[day].astype(int)
    overall_best_per_weekday.index += 1

    return (
        day_filter,
        per_game_rankings,
        total_score,
        final_total_times,
        final_daily_avg_times,
        overall_best_sum,
        weekday_score,
        overall_best_per_weekday,
    )


############################### 1v1 Head-to-Head #####################################
def head_to_head_page():
    """1v1 head-to-head comparison between two players."""
    st.title("1v1 Head-to-Head")

    df, mode = load_data_from_supabase()
    if df is None or df.empty:
        if mode == "Upload New Data":
            st.info(
                "Please upload a WhatsApp chat .txt file to load data for head-to-head comparison."
            )
        else:
            st.warning("No data available yet.")
        return

    players = sorted(df["sender"].unique())
    if len(players) < 2:
        st.warning("Need at least 2 players for a head-to-head comparison.")
        return

    # Player selectors
    col1, col2 = st.columns(2)
    with col1:
        player1 = st.selectbox("Player 1", players, index=0)
    with col2:
        default_p2 = 1 if len(players) > 1 else 0
        player2 = st.selectbox("Player 2", players, index=default_p2)

    if player1 == player2:
        st.warning("Select two different players.")
        return

    # Date range slider
    dates = pd.to_datetime(df["date"])
    min_date, max_date = dates.min().date(), dates.max().date()
    date_from, date_to = st.slider(
        "Date range",
        min_value=min_date,
        max_value=max_date,
        value=(min_date, max_date),
        format="YYYY-MM-DD",
    )
    df = df[(df["date"] >= str(date_from)) & (df["date"] <= str(date_to))]

    count_missing = st.toggle(
        "Count missing scores as losses",
        value=False,
        help="When enabled, if only one player shared a score for a game on a given day, "
        "the other player is counted as a loss. When disabled, only games where both "
        "players shared their times are compared.",
    )

    # Preprocess
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
        st.info("No head-to-head matchups found between these players.")
        return

    results_df = pd.DataFrame(results)
    p1_wins = int((results_df["winner"] == player1).sum())
    p2_wins = int((results_df["winner"] == player2).sum())
    draws = int((results_df["winner"] == "draw").sum())
    total = p1_wins + p2_wins + draws

    P1_COLOR = "#4A90D9"
    P2_COLOR = "#E74C3C"

    def _bar_html(w1, w2, label, height=28, font_size=14):
        """Render a split bar with player colors. Returns HTML string."""
        t = w1 + w2
        if t == 0:
            return ""
        p1_pct = w1 / t * 100
        p2_pct = w2 / t * 100
        # Minimum visible width for the side that has wins
        min_w = "2px" if w1 > 0 else "0"
        min_w2 = "2px" if w2 > 0 else "0"
        return f"""
        <div style="margin-bottom:4px;">
          <div style="font-size:15px; color:#ccc; margin-bottom:3px; font-weight:500;">{label}</div>
          <div style="display:flex; align-items:center; gap:6px;">
            <span style="min-width:28px; text-align:right; font-size:{font_size}px; font-weight:600; color:{P1_COLOR};">{w1}</span>
            <div style="flex:1; display:flex; height:{height}px; border-radius:4px; overflow:hidden;">
              <div style="width:{p1_pct}%; min-width:{min_w}; background:{P1_COLOR};"></div>
              <div style="width:{p2_pct}%; min-width:{min_w2}; background:{P2_COLOR};"></div>
            </div>
            <span style="min-width:28px; text-align:left; font-size:{font_size}px; font-weight:600; color:{P2_COLOR};">{w2}</span>
          </div>
        </div>
        """

    # --- Overall record ---
    st.subheader("Overall Record")
    p1_pct = int(p1_wins / (p1_wins + p2_wins) * 100) if p1_wins + p2_wins > 0 else 0
    p2_pct = int(p2_wins / (p1_wins + p2_wins) * 100) if p1_wins + p2_wins > 0 else 0
    st.markdown(
        f"""
    <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:8px;">
      <div style="text-align:center;">
        <div style="font-size:14px; color:#ccc;">{player1}</div>
        <div style="font-size:28px; font-weight:700; color:{P1_COLOR};">{p1_wins} <span style="font-size:20px;">({p1_pct}%)</span></div>
      </div>
      <div style="text-align:center;">
        <div style="font-size:14px; color:#888;">Draws</div>
        <div style="font-size:22px; font-weight:600; color:#888;">{draws}</div>
      </div>
      <div style="text-align:center;">
        <div style="font-size:14px; color:#ccc;">{player2}</div>
        <div style="font-size:28px; font-weight:700; color:{P2_COLOR};">{p2_wins} <span style="font-size:20px;">({p2_pct}%)</span></div>
      </div>
    </div>
    """,
        unsafe_allow_html=True,
    )

    st.markdown(
        _bar_html(p1_wins, p2_wins, "", height=32, font_size=16), unsafe_allow_html=True
    )
    st.caption(f"{total} matchups compared")

    # --- Win % over time (normalized stacked area) ---
    st.subheader("Win % Over Time")
    daily = results_df[results_df["winner"] != "draw"].copy()
    if not daily.empty:
        import altair as alt

        daily["is_p1"] = (daily["winner"] == player1).astype(int)
        daily["is_p2"] = (daily["winner"] == player2).astype(int)
        by_date = daily.groupby("date")[["is_p1", "is_p2"]].sum().sort_index()
        cum = by_date.cumsum()
        melted = cum.reset_index().melt("date", var_name="player", value_name="wins")
        melted["date"] = pd.to_datetime(melted["date"])
        melted["player"] = melted["player"].map({"is_p1": player1, "is_p2": player2})
        # Order so player1 is on top, player2 on bottom
        area = (
            alt.Chart(melted)
            .mark_area()
            .encode(
                x=alt.X("date:T", title=None),
                y=alt.Y(
                    "wins:Q", stack="normalize", title=None, axis=alt.Axis(format="%")
                ),
                color=alt.Color(
                    "player:N",
                    scale=alt.Scale(
                        domain=[player1, player2],
                        range=[P1_COLOR, P2_COLOR],
                    ),
                    legend=None,
                ),
                order=alt.Order("player:N", sort="ascending"),
            )
            .properties(height=300)
        )
        st.altair_chart(area, use_container_width=True)

    # --- Wins by day of week ---
    st.subheader("Wins by Day of Week")
    days_order = [
        "Monday",
        "Tuesday",
        "Wednesday",
        "Thursday",
        "Friday",
        "Saturday",
        "Sunday",
    ]
    weekday_html = ""
    for day in days_order:
        day_df = results_df[results_df["weekday"] == day]
        if day_df.empty:
            continue
        w1 = int((day_df["winner"] == player1).sum())
        w2 = int((day_df["winner"] == player2).sum())
        if w1 + w2 == 0:
            continue
        weekday_html += _bar_html(w1, w2, day, height=22, font_size=13)
    if weekday_html:
        st.markdown(weekday_html, unsafe_allow_html=True)

    # --- Wins by game ---
    st.subheader("Wins by Game")
    game_emoji = {
        "zip": "⚡",
        "tango": "💃",
        "queens": "👑",
        "mini sudoku": "🔢",
        "patches": "🧩",
    }
    game_html = ""
    for game in GAMES:
        game_df = results_df[results_df["game"].str.lower() == game.lower()]
        if game_df.empty:
            continue
        w1 = int((game_df["winner"] == player1).sum())
        w2 = int((game_df["winner"] == player2).sum())
        if w1 + w2 == 0:
            continue
        emoji = game_emoji.get(game.lower(), "🎮")
        game_html += _bar_html(w1, w2, f"{emoji} {game}", height=22, font_size=13)
    if game_html:
        st.markdown(game_html, unsafe_allow_html=True)


############################### Main #####################################
def leaderboard_page():
    """Original leaderboard page."""
    (
        day_filter,
        per_game_rankings,
        total_score,
        final_total_times,
        final_daily_avg_times,
        overall_best_sum,
        weekday_score,
        overall_best_per_weekday,
    ) = streamlit_app(GAMES=GAMES)

    if not per_game_rankings:
        return

    if day_filter != "All":
        ranking_type = st.radio(
            "What kind of ranking would you like to see?",
            ["Total Points", "Total Time", "Average Time", "Times N°1"],
            horizontal=True,
        )
    else:
        ranking_type = st.radio(
            "What kind of ranking would you like to see?",
            [
                "Total Points",
                "Total Time",
                "Average Time",
                "Times N°1",
                "Weekday Scores",
                "Times N°1 per Weekday",
            ],
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
    elif ranking_type == "Weekday Scores":
        st.subheader("**Overall Weekday Scores**")
        st.dataframe(weekday_score)
    elif ranking_type == "Times N°1 per Weekday":
        st.subheader("**Times N°1 per Weekday**")
        st.dataframe(overall_best_per_weekday)

    st.subheader("**Per-Game Rankings**")
    for title, df in per_game_rankings.items():
        st.markdown(f"**{title} Rankings**")
        st.dataframe(df)


def main():
    page = st.sidebar.radio("Navigation", ["Leaderboard", "1v1 Head-to-Head"])
    if page == "Leaderboard":
        leaderboard_page()
    else:
        head_to_head_page()


if __name__ == "__main__":
    main()
