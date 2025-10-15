# linkedin_games_parser.py
import re
import unicodedata
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
        r"^\[(\d{2}/\d{2}/\d{2,4}),? (\d{1,2}:\d{2}:\d{2})]\s(.*?):\s([\s\S]*)$",
        re.MULTILINE | re.DOTALL,
    )
    game_re = re.compile(
        r"#?(?P<game>[A-Za-z\s]+)\s*#(?P<number>\d+)[(\s\n)\S\n]*?(?P<time>\d{1,2}:\d{2})",
        re.IGNORECASE | re.UNICODE,
    )
    ceo_re = re.compile(r"\s*(?P<percent>\d{1,2})%[\s\S]*(CEOs|CEO|PDG)")

    rows = []
    current_msg_lines = []

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
            raw = raw.rstrip("\n")
            raw = clean_line(raw)

            # Check if line starts a new message
            if re.match(r"^\[(\d{2}/\d{2}/\d{2,4}),? (\d{1,2}:\d{2}:\d{2})]", raw):
                if current_msg_lines:
                    # Join previous message and parse
                    full_msg = " ".join(current_msg_lines)
                    m = line_re.search(full_msg)
                    if m:
                        date_str, _, sender, text = m.groups()
                        dt = (
                            datetime.strptime(date_str, "%d/%m/%y").date()
                            if len(date_str) == 8
                            else datetime.strptime(date_str, "%d/%m/%Y").date()
                        )
                        g = game_re.search(text)
                        c = ceo_re.search(text)
                        row = {
                            "date": dt.isoformat(),
                            "sender": sender,
                            "text": text,
                            "game": g.group("game").strip() if g else None,
                            "game_number": g.group("number") if g else None,
                            "play_time": g.group("time") if g else None,
                            "ceo_percent": c.group("percent") if c else None,
                        }
                        rows.append(row)
                    current_msg_lines = []

                current_msg_lines.append(raw)
            else:
                # Continuation line of the current message
                current_msg_lines.append(raw)

        # Parse the last message after file ends
        if current_msg_lines:
            full_msg = " ".join(current_msg_lines)
            m = line_re.search(full_msg)
            if m:
                date_str, _, sender, text = m.groups()
                dt = (
                    datetime.strptime(date_str, "%d/%m/%y").date()
                    if len(date_str) == 8
                    else datetime.strptime(date_str, "%d/%m/%Y").date()
                )
                g = game_re.search(text)
                c = ceo_re.search(text)
                row = {
                    "date": dt.isoformat(),
                    "sender": sender,
                    "text": text,
                    "game": g.group("game").strip() if g else None,
                    "game_number": g.group("number") if g else None,
                    "play_time": g.group("time") if g else None,
                    "ceo_percent": c.group("percent") if c else None,
                }
                rows.append(row)

            current_msg_lines = []

            current_msg_lines.append(raw)
        else:
            # Continuation of last message — just append to current_msg_lines
            current_msg_lines.append(raw)

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
        .dropna(subset=["game"])
        .reset_index(drop=True)
    )

    # Optionally save CSV
    if output_path:
        df.to_csv(output_path, index=False, encoding="utf-8")
        print(f"Extracted {len(df)} game results → {output_path}")

    return df


###################### Tools ######################
def clean_line(raw):
    # Normalize unicode
    raw = unicodedata.normalize("NFKC", raw)
    # Remove invisible characters (common WhatsApp ones)
    invisible_chars = [
        "\u200e",  # LEFT-TO-RIGHT MARK
        "\u200f",  # RIGHT-TO-LEFT MARK
        "\u202a",
        "\u202b",
        "\u202c",
        "\u202d",
        "\u202e",  # Directional overrides
    ]
    for ch in invisible_chars:
        raw = raw.replace(ch, "")
    return raw
