import requests
from config_api_keys import (
    SPORTSDATAIO_API_KEY,
    DVOA_API_KEY,
    INJURY_API_KEY,
    ADVANCED_METRICS_API_KEY,
)

# ---------- DATA FETCH HELPERS ----------

def fetch_player_baselines(game_id: str):
    """
    Get baseline projections for all players in a game.
    NOTE: Adjust the URL/path to match your real provider format.
    """
    url = f"https://api.sportsdata.io/v3/nfl/projections/json/PlayerGameProjectionStatsByWeek/{game_id}"
    headers = {"Ocp-Apim-Subscription-Key": SPORTSDATAIO_API_KEY}
    r = requests.get(url, headers=headers)
    r.raise_for_status()
    data = r.json()

    players = {}
    for row in data:
        name = row.get("Name")
        if not name:
            continue

        players[name] = {
            "team": row.get("Team"),
            "position": row.get("Position"),
            "passing_yards": float(row.get("PassingYards", 0.0)),
            "passing_tds": float(row.get("PassingTouchdowns", 0.0)),
            "rushing_yards": float(row.get("RushingYards", 0.0)),
            "receiving_yards": float(row.get("ReceivingYards", 0.0)),
            "receptions": float(row.get("Receptions", 0.0)),
            "hit_prob": 0.60,  # base neutral hit probability
        }
    return players


def fetch_dvoa_stats(team: str):
    """Offensive and defensive DVOA for a team."""
    url = f"https://api.dvoadata.com/team/{team}"
    headers = {"Authorization": f"Bearer {DVOA_API_KEY}"}
    r = requests.get(url, headers=headers)
    r.raise_for_status()
    data = r.json()
    return {
        "offense_dvoa": float(data.get("offense_dvoa", 0.0)),
        "defense_dvoa": float(data.get("defense_dvoa", 0.0)),
    }


def fetch_injury_report(team: str):
    """
    Simplified injury model.
    Right now: track if O-line is banged up.
    """
    url = f"https://api.sportsdata.io/v3/nfl/injuries/json/InjuriesByTeam/{team}"
    headers = {"Ocp-Apim-Subscription-Key": INJURY_API_KEY or SPORTSDATAIO_API_KEY}
    r = requests.get(url, headers=headers)
    r.raise_for_status()
    data = r.json()

    injuries = {"OLINE": "healthy"}
    for row in data:
        pos = row.get("Position", "")
        status = row.get("InjuryStatus", "")
        if pos in ("C", "G", "T", "OL") and status in ("Questionable", "Doubtful", "Out"):
            injuries["OLINE"] = "injured"
    return injuries


def fetch_game_script(game_id: str):
    """
    Game script stub.
    You can later wire in your real model; for now it's neutral.
    """
    return {"run_pass_ratio": 1.0, "score_diff": 0}


def fetch_game_matchup_advanced(home: str, away: str):
    """
    Defensive pressure + coverage type.
    """
    url = f"https://api.advmetrics.com/nfl/matchup/{home}/{away}"
    headers = {"Authorization": f"Bearer {ADVANCED_METRICS_API_KEY}"}
    r = requests.get(url, headers=headers)
    r.raise_for_status()
    data = r.json()
    return {
        "pressure_rate_home_def": float(data.get("pressure_rate_home_def", 0.28)),
        "pressure_rate_away_def": float(data.get("pressure_rate_away_def", 0.28)),
        "coverage_type_home_def": data.get("coverage_type_home_def", "man"),
        "coverage_type_away_def": data.get("coverage_type_away_def", "man"),
    }


def fetch_efficiency_metrics(team: str):
    """
    EPA/play and performance under pressure.
    """
    url = f"https://api.advmetrics.com/nfl/efficiency/{team}"
    headers = {"Authorization": f"Bearer {ADVANCED_METRICS_API_KEY}"}
    r = requests.get(url, headers=headers)
    r.raise_for_status()
    data = r.json()
    return {
        "EPA_per_play": float(data.get("EPA_per_play", 0.05)),
        "comp_under_pressure": float(data.get("comp_under_pressure", 0.60)),
    }


# ---------- ADJUSTMENT / TEMPLATE LOGIC ----------

def adjust_proj_with_dvoa(base_proj: float, dvoa_off: float, dvoa_def: float) -> float:
    """
    Core DVOA bump:
    - Offense better than defense -> bump up
    - Defense better than offense -> bump down
    """
    dvoa_effect = (dvoa_off - dvoa_def) * 0.2
    return base_proj * (1.0 + dvoa_effect / 100.0)


def adjust_projections(
    base_projections: dict,
    defense_stats: dict,
    offense_stats: dict,
    injuries: dict,
    game_script: dict,
    coverage_scheme: dict,
    efficiency_metrics: dict,
) -> dict:
    league_avg_pressure = 0.28
    league_avg_EPA = 0.05

    adjusted = {}

    pressure_factor = max(0.7, 1.0 - (defense_stats["pressure_rate"] - league_avg_pressure) * 0.3)
    run_pass_factor = max(0.5, min(1.5, float(game_script.get("run_pass_ratio", 1.0))))
    oline_injury_factor = 0.85 if injuries.get("OLINE") == "injured" else 1.0
    coverage_factor = 0.9 if coverage_scheme.get("type") == "zone" else 1.0
    efficiency_factor = 1.0 + (efficiency_metrics.get("EPA_per_play", league_avg_EPA) - league_avg_EPA) * 0.2

    for player, proj in base_projections.items():
        pos = proj.get("position", "")
        base_yds = proj.get(
            "passing_yards",
            proj.get("receiving_yards", proj.get("rushing_yards", 0.0)),
        )

        dvoa_yds = adjust_proj_with_dvoa(
            base_yds,
            offense_stats["offense_dvoa"],
            defense_stats["defense_dvoa"],
        )

        if pos == "QB":
            yards = dvoa_yds * pressure_factor * oline_injury_factor * efficiency_factor
            tds = proj.get("passing_tds", 0.0) * pressure_factor * oline_injury_factor * efficiency_factor
            hit_prob = proj["hit_prob"] * pressure_factor

            adjusted[player] = {
                **proj,
                "passing_yards": yards,
                "passing_tds": tds,
                "hit_prob": hit_prob,
            }

        elif pos in ("WR", "TE"):
            rec_yds = dvoa_yds * coverage_factor * efficiency_factor * run_pass_factor
            recs = proj.get("receptions", 0.0) * coverage_factor * efficiency_factor * run_pass_factor
            hit_prob = proj["hit_prob"] * coverage_factor

            adjusted[player] = {
                **proj,
                "receiving_yards": rec_yds,
                "receptions": recs,
                "hit_prob": hit_prob,
            }

        elif pos == "RB":
            rush_yds = proj.get("rushing_yards", 0.0) * run_pass_factor * efficiency_factor
            rec_yds = proj.get("receiving_yards", 0.0) * run_pass_factor * efficiency_factor
            total_yds = rush_yds + rec_yds
            hit_prob = proj["hit_prob"] * run_pass_factor

            adjusted[player] = {
                **proj,
                "rushing_yards": rush_yds,
                "receiving_yards": rec_yds,
                "total_yards": total_yds,
                "hit_prob": hit_prob,
            }

        else:
            adjusted[player] = proj

    return adjusted


# ---------- MAIN ENTRY CALLED BY STREAMLIT ----------

def project_game(game_id: str, home_team: str, away_team: str) -> dict:
    base = fetch_player_baselines(game_id)

    dvoa_home = fetch_dvoa_stats(home_team)
    dvoa_away = fetch_dvoa_stats(away_team)
    matchup = fetch_game_matchup_advanced(home_team, away_team)
    inj_home = fetch_injury_report(home_team)
    inj_away = fetch_injury_report(away_team)
    script = fetch_game_script(game_id)
    eff_home = fetch_efficiency_metrics(home_team)
    eff_away = fetch_efficiency_metrics(away_team)

    offense_home = {"team": home_team, **dvoa_home}
    offense_away = {"team": away_team, **dvoa_away}
    defense_home = {
        "team": home_team,
        "pressure_rate": matchup["pressure_rate_home_def"],
        "defense_dvoa": dvoa_home["defense_dvoa"],
    }
    defense_away = {
        "team": away_team,
        "pressure_rate": matchup["pressure_rate_away_def"],
        "defense_dvoa": dvoa_away["defense_dvoa"],
    }
    cover_home = {"type": matchup["coverage_type_home_def"]}
    cover_away = {"type": matchup["coverage_type_away_def"]}

    base_home = {p: v for p, v in base.items() if v.get("team") == home_team}
    base_away = {p: v for p, v in base.items() if v.get("team") == away_team}

    adj_home = adjust_projections(base_home, defense_away, offense_home, inj_home, script, cover_away, eff_away)
    adj_away = adjust_projections(base_away, defense_home, offense_away, inj_away, script, cover_home, eff_home)

    return {**adj_home, **adj_away}