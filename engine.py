"""
engine.py
Core football engine for THE ONE FOOTBALL – NFL Prop Analyzer.

Adds:
- DEMO_DATA fallback if API fails or no key.
- Explicit TC floor outputs for yards and TDs.
"""

import requests
from config_api_keys import (
    SPORTSDATAIO_API_KEY,
    DVOA_API_KEY,
    INJURY_API_KEY,
    ADVANCED_METRICS_API_KEY,
)

# ---------- DEMO DATA (no API needed) ----------

DEMO_BASELINES = {
    # Cowboys
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