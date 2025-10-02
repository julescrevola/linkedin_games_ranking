# linkedin_games_parser.py
import re
import pandas as pd
from datetime import datetime


def parse_whatsapp_chat(
    input_path: str | None = None, output_path: str | None = None
) -> pd.DataFrame:
    """
    Parse WhatsApp chat exported from LinkedIn games and return a DataFrame.

    Args:
        input_path (str): Path to the WhatsApp chat TXT file, or an UploadedFile object.
        output_path (str, optional): If provided, saves the DataFrame to CSV.

    Returns:
        pd.DataFrame: Parsed game results with columns:
                      date, sender, game, game_number, play_time, ceo_percent
    """

    # Regex patterns
    line_re = re.compile(
        r"^\[(\d{2}/\d{2}/\d{4}) (\d{1,2}:\d{2}:\d{2})]\s(.*?):\s(.*)$"
    )
    game_re = re.compile(
        r"(?P<game>[A-Za-z\s]+)\s*#(?P<number>\d+)\s*\|\s*(?P<time>\d+:\d+).*",
        re.IGNORECASE,
    )
    ceo_re = re.compile(r"\s*(?P<percent>\d{1,3})%")

    rows = []
    current_msg = None

    # Check if input_source is a path or a file-like object
    if isinstance(input_path, str):
        f = open(input_path, encoding="utf-8")
        close_file = True
    else:
        # Streamlit uploaded file: read text lines
        f = (
            line.decode("utf-8") if isinstance(line, bytes) else line
            for line in input_path
        )
        close_file = False

    try:
        for raw in f:
            raw = raw.strip("\n")
            m = line_re.match(raw)
            if m:
                # Start of a new message
                date_str, _, sender, text = m.groups()
                dt = datetime.strptime(date_str, "%d/%m/%Y").date()
                current_msg = {"date": dt, "sender": sender, "text": text}

                # Try parsing game immediately
                g = game_re.match(text)
                ceo_match = ceo_re.search(text)
                row = {
                    "date": dt.isoformat(),
                    "sender": sender,
                    "text": text,
                    "game": g.group("game").strip() if g else None,
                    "game_number": g.group("number") if g else None,
                    "play_time": g.group("time") if g else None,
                    "ceo_percent": ceo_match.group("percent") if ceo_match else None,
                }
                if g:
                    rows.append(row)
            else:
                # Continuation of last message
                if current_msg and rows:
                    rows[-1]["text"] += " " + raw
                    # Check for CEO percentage in continuation lines
                    c = ceo_re.search(raw)
                    if c:
                        rows[-1]["ceo_percent"] = c.group("percent")

    finally:
        if close_file:
            f.close()

    # Fix CEO percent if it was in the same line but not detected before
    for r in rows:
        if r["ceo_percent"] is None:
            m = ceo_re.search(r["text"])
            if m:
                r["ceo_percent"] = m.group("percent")

    # Build DataFrame
    df = (
        pd.DataFrame(
            rows,
            columns=[
                "date",
                "sender",
                "game",
                "game_number",
                "play_time",
                "ceo_percent",
            ],
        )
        .sort_values(by="date")
        .reset_index(drop=True)
    )

    # Optionally save CSV
    if output_path:
        df.to_csv(output_path, index=False, encoding="utf-8")
        print(f"Extracted {len(df)} game results → {output_path}")

    return df
