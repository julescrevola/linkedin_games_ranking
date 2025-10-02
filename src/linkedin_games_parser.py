# linkedin_games_parser.py
import re
import pandas as pd
from datetime import datetime

INPUT = "../data/input/_chat.txt"
OUTPUT = "../data/output/games_leaderboard.csv"

# WhatsApp line format:
# [13:20, 01/10/2025] Name: Message
line_re = re.compile(r"^\[(\d{2}/\d{2}/\d{4}) (\d{1,2}:\d{2}:\d{2})]\s(.*?):\s(.*)$")

# Game result regex
game_re = re.compile(
    r"(?P<game>[A-Za-z\s]+)\s*#(?P<number>\d+)\s*\|\s*(?P<time>\d+:\d+).*",
    re.IGNORECASE,
)

# CEO % regex
ceo_re = re.compile(r"\s*(?P<percent>\d{1,3})%")

rows = []
with open(INPUT, encoding="utf-8") as f:
    current_msg = None
    for raw in f:
        raw = raw.strip("\n")
        m = line_re.match(raw)
        if m:
            # start of a new message
            date_str, _, sender, text = m.groups()
            dt = datetime.strptime(date_str, "%d/%m/%Y").date()
            current_msg = {"date": dt, "sender": sender, "text": text}
            # try parse immediately
            g = game_re.match(text)
            if g:
                row = {
                    "date": dt.isoformat(),
                    "sender": sender,
                    "text": text,
                    "game": g.group("game").strip(),
                    "game_number": g.group("number"),
                    "play_time": g.group("time"),
                    "ceo_percent": None,
                }
                rows.append(row)
        else:
            # continuation of last message
            if current_msg and rows:
                rows[-1]["text"] += " " + raw
                # check for CEO percentage in continuation lines
                c = ceo_re.search(raw)
                if c:
                    rows[-1]["ceo_percent"] = c.group("percent")

# fix CEO percent if it was in the same line
for r in rows:
    if r["ceo_percent"] is None:
        m = ceo_re.search(r["text"])
        if m:
            r["ceo_percent"] = m.group("percent")

# Save to CSV
df = (
    pd.DataFrame(
        rows,
        columns=["date", "sender", "game", "game_number", "play_time", "ceo_percent"],
    )
    .sort_values(by="date")
    .reset_index(drop=True)
)
df.to_csv(OUTPUT, index=False, encoding="utf-8")

print(f"Extracted {len(df)} game results → {OUTPUT}")
print(df)
