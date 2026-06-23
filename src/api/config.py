"""Configuration — loads Supabase credentials from environment."""

import os
from dotenv import load_dotenv
from supabase import create_client, Client

load_dotenv()

SUPABASE_URL = os.environ.get("SUPABASE_URL", "")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY", "")

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


def get_supabase() -> Client:
    if not SUPABASE_URL or not SUPABASE_KEY:
        raise RuntimeError(
            "SUPABASE_URL and SUPABASE_KEY must be set for the API container"
        )
    return create_client(SUPABASE_URL, SUPABASE_KEY)
