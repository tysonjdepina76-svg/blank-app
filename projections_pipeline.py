# projections_pipeline.py
# Core projection engine wired to your existing data helpers.

from dataclasses import dataclass
from typing import Dict, List, Optional

# Use your existing helpers that already know about API keys.
# Adjust imports to match real names in engine.py or other modules.
from engine import (
    fetch_depth_chart,      # (team, week) -> depth dict
    fetch_recent_snaps,     # (team, week) -> snaps dict
    fetch_news_flags,       # (team, week) -> {player: "arrow_up"/"arrow_down"/None}
    fetch_matchup_metrics,  # (team, week) -> matchup_features dict
    fetch_weather,          # (team, week) -> {"wind_mph": int, "precip": bool, ...}
    fetch_ref_crew,         # (team, week) -> ref/penalty info (optional)
)


# ---------- DATA MODELS ----------

@dataclass
class StarterConfig:
    qb: str
    rb1: str
    rb2: Optional[str]
    wr1: str
    wr2: str
    wr3: Optional[str]
    te1: str
    te2: Optional[str]


@dataclass
class PlayerUsage:
    snap_share: float
    rush_share: float
    target_share: float
    rz_rush_share: float
    rz_target_share: float


@dataclass
class PlayerProjection:
    mean_yards: float
    floor_yards: float
    mean_recs: Optional[float]
    floor_recs: Optional[float]
    mean_tds: float
    floor_tds: float


# ---------- DEPTH CHART + STARTERS ----------

def load_official_depth_chart(team: str, week: int) -> Dict[str, List[str]]:
    """
    Thin wrapper around your depth-chart function so the rest of the engine
    does not care about API keys or endpoints.
    """
    return fetch_depth_chart(team, week)


def validate_and_build_starters(
    depth: Dict[str, List[str]],
    user_starters: StarterConfig,
) -> StarterConfig:
    """Guarantee starters are on depth chart; fill blanks from chart."""

    def ensure(pos_key: str, name: Optional[str], index: int = 0) -> str:
        if name is None:
            return depth[pos_key][index]
        if name not in depth[pos_key]:
            raise ValueError(f"{name} not listed at {pos_key}")
        return name

    return StarterConfig(
        qb=ensure("QB", user_starters.qb),
        rb1=ensure("RB", user_starters.rb1, 0),
        rb2=ensure("RB", user_starters.rb2, 1) if user_starters.rb2 else None,
        wr1=ensure("WR", user_starters.wr1, 0),
        wr2=ensure("WR", user_starters.wr2, 1),
        wr3=ensure("WR", user_starters.wr3, 2) if user_starters.wr3 else None,
        te1=ensure("TE", user_starters.te1, 0),
        te2=ensure("TE", user_starters.te2, 1) if user_starters.te2 else None,
    )


# ---------- USAGE / ROLE BLOCK ----------

def derive_usage_from_snaps(
    snaps: Dict[str, Dict],
    news_flags: Dict[str, str],
) -> Dict[str, PlayerUsage]:
    """
    snaps[player] example:
      {
        "snap_pct": 0.65,
        "rush_att": 40,
        "targets": 18,
        "rz_rush": 8,
        "rz_tgt": 6
      }
    news_flags[player] in {"arrow_up","arrow_down", None}
    """

    usage: Dict[str, PlayerUsage] = {}

    total_rush = sum(p["rush_att"] for p in snaps.values()) or 1.0
    total_tgt = sum(p["targets"] for p in snaps.values()) or 1.0
    total_rz_r = sum(p["rz_rush"] for p in snaps.values()) or 1.0
    total_rz_t = sum(p["rz_tgt"] for p in snaps.values()) or 1.0

    for name, p in snaps.items():
        rush_share = p["rush_att"] / total_rush
        tgt_share = p["targets"] / total_tgt
        rz_r_share = p["rz_rush"] / total_rz_r
        rz_t_share = p["rz_tgt"] / total_rz_t

        flag = news_flags.get(name)
        mult = 1.0
        if flag == "arrow_up":
            mult = 1.1
        elif flag == "arrow_down":
            mult = 0.9

        usage[name] = PlayerUsage(
            snap_share=p["snap_pct"],
            rush_share=rush_share * mult,
            target_share=tgt_share * mult,
            rz_rush_share=rz_r_share * mult,
            rz_target_share=rz_t_share * mult,
        )

    # normalize rush/target shares after news tweaks
    rush_total = sum(u.rush_share for u in usage.values()) or 1.0
    tgt_total = sum(u.target_share for u in usage.values()) or 1.0
    for u in usage.values():
        u.rush_share /= rush_total
        u.target_share /= tgt_total

    return usage


# ---------- SCENARIOS + ENVIRONMENT ----------

def scenario_probs(matchup_features: Dict) -> Dict[str, float]:
    """Return probabilities for key scenarios; heuristics for now."""
    return {
        "normal": 0.5,
        "wr1_bracket": 0.2 if matchup_features.get("wr1_vs_elite_cb") else 0.1,
        "rb_erased": 0.2 if matchup_features.get("elite_run_d") else 0.1,
        "ol_collapse": 0.1 if matchup_features.get("pass_rush_edge") else 0.05,
    }


def apply_weather_factor(stat: float, weather: Dict, is_pass_stat: bool) -> float:
    wind = weather.get("wind_mph", 0)
    precip = weather.get("precip", False)

    factor = 1.0
    if is_pass_stat:
        if wind >= 15:
            factor -= 0.07
        if precip:
            factor -= 0.05
    else:
        # light bump for rushing in ugly weather
        if wind >= 15 or precip:
            factor *= 1.03
    return max(stat * factor, 0.0)


def apply_rivalry_factor(stat: float, rivalry: bool) -> float:
    return stat * 0.96 if rivalry else stat


# ---------- PLAYER PROJECTION CORE ----------

def project_player_yards(
    base_yards: float,
    usage: PlayerUsage,
    matchup_features: Dict,
    weather: Dict,
    rivalry: bool,
    is_pass_stat: bool,
) -> PlayerProjection:
    scen_p = scenario_probs(matchup_features)

    adj = base_yards
    if matchup_features.get("is_wr1") and scen_p["wr1_bracket"] > 0:
        adj *= (1 - 0.15 * scen_p["wr1_bracket"])
    if matchup_features.get("is_rb1") and scen_p["rb_erased"] > 0:
        adj *= (1 - 0.15 * scen_p["rb_erased"])

    adj = apply_weather_factor(adj, weather, is_pass_stat=is_pass_stat)
    adj = apply_rivalry_factor(adj, rivalry)

    mean_yards = adj
    floor_yards = adj * 0.85  # TC floor

    mean_recs = None
    floor_recs = None
    if usage.target_share > 0:
        # 40 team attempts * target_share ~ targets; catch% ≈ 65%
        est_recs = 40 * usage.target_share * 0.65
        mean_recs = est_recs
        floor_recs = est_recs * 0.85

    # TDs from red‑zone shares (simple for now)
    rz_share = usage.rz_rush_share + usage.rz_target_share
    mean_tds = 0.3 * (1 + rz_share)
    floor_tds = mean_tds * 0.7

    return PlayerProjection(
        mean_yards=mean_yards,
        floor_yards=floor_yards,
        mean_recs=mean_recs,
        floor_recs=floor_recs,
        mean_tds=mean_tds,
        floor_tds=floor_tds,
    )


# ---------- HIGH‑LEVEL ENTRY POINT FOR A TEAM ----------

def build_team_projections(team: str, opponent: str, week: int,
                           user_starters: StarterConfig,
                           rivalry: bool) -> Dict[str, PlayerProjection]:
    """
    Main function your Streamlit app can call.
    All API access happens in the helper functions imported from engine.py.
    """

    depth = load_official_depth_chart(team, week)
    starters = validate_and_build_starters(depth, user_starters)

    snaps = fetch_recent_snaps(team, week)
    news_flags = fetch_news_flags(team, week)
    usage = derive_usage_from_snaps(snaps, news_flags)

    matchup = fetch_matchup_metrics(team, week)
    weather = fetch_weather(team, week)
    _ = fetch_ref_crew(team, week)  # ready if you later want ref adjustments

    team_pass_yards = matchup["team_pass_yards_proj"]
    team_rush_yards = matchup["team_rush_yards_proj"]

    projections: Dict[str, PlayerProjection] = {}

    # Example: WR1
    wr1_name = starters.wr1
    wr1_usage = usage[wr1_name]
    wr1_feats = {
        "is_wr1": True,
        "wr1_vs_elite_cb": matchup.get("wr1_vs_elite_cb", False),
    }
    projections[wr1_name] = project_player_yards(
        base_yards=team_pass_yards * wr1_usage.target_share,
        usage=wr1_usage,
        matchup_features=wr1_feats,
        weather=weather,
        rivalry=rivalry,
        is_pass_stat=True,
    )

    # You repeat the pattern for QB, RB1, RB2, WR2, WR3, TE1, TE2
    # using appropriate base_yards and feature flags.

    return projections