"""
engine.py
Core football engine for THE ONE FOOTBALL – NFL Prop Analyzer.

- Uses built-in demo data so the app always runs (no 401).
- Provides triple-conservative (TC) floors for yards and TDs.
- Optional RotoBaller news fetch if your SportsDataIO key works.
"""

import requests
from config_api_keys import SPORTSDATAIO_API_KEY


# ---------- DEMO PLAYER DATA (Cowboys @ Lions) ----------

DEMO_BASELINES = {
    "Dak Prescott": {
        "team": "Cowboys",
        "position": "QB",
        "passing_yards": 305.0,
        "passing_tds": 2.4,
        "rushing_yards": 15.0,
        "receiving_yards": 0.0,
        "receptions": 0.0,
        "hit_prob": 0.60,
    },
    "Javonte Williams": {
        "team": "Cowboys",
        "position": "RB",
        "passing_yards": 0.0,
        "passing_tds": 0.0,
        "rushing_yards": 85.0,
        "receiving_yards": 18.0,
        "receptions": 2.0,
        "hit_prob": 0.60,
    },
    "CeeDee Lamb": {
        "team": "Cowboys",
        "position": "WR",
        "passing_yards": 0.0,
        "passing_tds": 0.0,
        "rushing_yards": 5.0,
        "receiving_yards": 98.0,
        "receptions": 8.1,
        "hit_prob": 0.60,
    },
    "George Pickens": {
        "team": "Cowboys",
        "position": "WR",
        "passing_yards": 0.0,
        "passing_tds": 0.0,
        "rushing_yards": 0.0,
        "receiving_yards": 95.0,
        "receptions": 7.0,
        "hit_prob": 0.60,
    },
    "Jake Ferguson": {
        "team": "Cowboys",
        "position": "TE",
        "passing_yards": 0.0,
        "passing_tds": 0.0,
        "rushing_yards": 0.0,
        "receiving_yards": 47.0,
        "receptions": 4.8,
        "hit_prob": 0.60,
    },
    "Jared Goff": {
        "team": "Lions",
        "position": "QB",
        "passing_yards": 278.0,
        "passing_tds": 2.0,
        "rushing_yards": 5.0,
        "receiving_yards": 0.0,
        "receptions": 0.0,
        "hit_prob": 0.60,
    },
    "Jahmyr Gibbs": {
        "team": "Lions",
        "position": "RB",
        "passing_yards": 0.0,
        "passing_tds": 0.0,
        "rushing_yards": 75.0,
        "receiving_yards": 35.0,
        "receptions": 4.0,
        "hit_prob": 0.60,
    },
    "David Montgomery": {
        "team": "Lions",
        "position": "RB",
        "passing_yards": 0.0,
        "passing_tds": 0.0,
        "rushing_yards": 52.0,
        "receiving_yards": 6.0,
        "receptions": 1.0,
        "hit_prob": 0.60,
    },
    "Jameson Williams": {
        "team": "Lions",
        "position": "WR",
        "passing_yards": 0.0,
        "passing_tds": 0.0,
        "rushing_yards": 0.0,
        "receiving_yards": 62.0,
        "receptions": 3.5,
        "hit_prob": 0.60,
    },
}


# ---------- OPTIONAL: RotoBaller NEWS (if key works) ----------

def fetch_rotoballer_articles(date_str: str):
    """
    Optional: Get RotoBaller NFL news articles for a given date (YYYY-MM-DD).

    Uses:
    https://api.sportsdata.io/v3/nfl/articles-rotoballer/json/RotoBallerArticlesByDate/{date}?key=KEY
    """
    if not SPORTSDATAIO_API_KEY or not date_str:
        return []

    url = (
        "https://api.sportsdata.io/v3/nfl/"
        f"articles-rotoballer/json/RotoBallerArticlesByDate/{date_str}"
        f"?key={SPORTSDATAIO_API_KEY}"
    )
    try:
        r = requests.get(url, timeout=5)
        if r.status_code != 200:
            return []
        return r.json()
    except Exception:
        return []


# ---------- TEMPLATE / FLOOR LOGIC (SIMPLE) ----------

def apply_tc_floors(player: dict) -> dict:
    """
    Apply triple-conservative floors:
    - yards_floor = baseline * 0.85
    - tds_floor   = baseline_tds - 0.4 (min 0)
    """
    pos = player.get("position", "")
    p = dict(player)  # copy

    if pos == "QB":
        p["tc_floor_passing_yards"] = p.get("passing_yards", 0.0) * 0.85
        p["tc_floor_passing_tds"] = max(0.0, p.get("passing_tds", 0.0) - 0.4)

    if pos in ("WR", "TE"):
        p["tc_floor_receiving_yards"] = p.get("receiving_yards", 0.0) * 0.85
        p["tc_floor_receptions"] = p.get("receptions", 0.0) * 0.85

    if pos == "RB":
        p["tc_floor_rushing_yards"] = p.get("rushing_yards", 0.0) * 0.85
        p["tc_floor_receiving_yards"] = p.get("receiving_yards", 0.0) * 0.85
        p["tc_floor_total_yards"] = (
            p.get("rushing_yards", 0.0) + p.get("receiving_yards", 0.0)
        ) * 0.85

    return p


# ---------- MAIN ENTRY CALLED BY STREAMLIT ----------

def project_game(season_week: str, home_team: str, away_team: str) -> dict:
    """
    For now, ignores season_week and always returns Cowboys vs Lions demo players,
    split by team and with TC floors added.
    """
    results = {}
    for name, base in DEMO_BASELINES.items():
        if base["team"] not in (home_team, away_team):
            continue
        results[name] = apply_tc_floors(base)

    return results