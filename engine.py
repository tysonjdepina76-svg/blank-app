# engine.py
# NFL prop engine that outputs the actual starter names you set in Streamlit.

from dataclasses import dataclass
from typing import Dict, List, Optional


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


# ---------- DATA FETCHERS (SAFE DEFAULTS) ----------

def fetch_depth_chart(team: str, week: int) -> Dict[str, List[str]]:
    """
    Simple positional depth chart. Names here are only structural labels.
    Actual player names will come from StarterConfig.
    """
    return {
        "QB": ["QB"],
        "RB": ["RB1", "RB2"],
        "WR": ["WR1", "WR2", "WR3"],
        "TE": ["TE1", "TE2"],
    }


def fetch_recent_snaps(team: str, week: int) -> Dict[str, Dict]:
    """
    Usage keyed by role labels. These labels will be mapped onto the
    actual starter names later so projections show real names.
    """
    return {
        "RB1": {"snap_pct": 0.65, "rush_att": 180, "targets": 40, "rz_rush": 25, "rz_tgt": 6},
        "RB2": {"snap_pct": 0.35, "rush_att": 80, "targets": 25, "rz_rush": 10, "rz_tgt": 3},
        "WR1": {"snap_pct": 0.90, "rush_att": 5,  "targets": 150, "rz_rush": 1,  "rz_tgt": 25},
        "WR2": {"snap_pct": 0.80, "rush_att": 3,  "targets": 110, "rz_rush": 1,  "rz_tgt": 18},
        "WR3": {"snap_pct": 0.65, "rush_att": 2,  "targets": 80,  "rz_rush": 0,  "rz_tgt": 10},
        "TE1": {"snap_pct": 0.80, "rush_att": 0,  "targets": 90,  "rz_rush": 0,  "rz_tgt": 20},
        "TE2": {"snap_pct": 0.40, "rush_att": 0,  "targets": 30,  "rz_rush": 0,  "rz_tgt": 6},
    }


def fetch_news_flags(team: str, week: int) -> Dict[str, str]:
    return {}


def fetch_matchup_metrics(team: str, week: int) -> Dict:
    return {
        "team_pass_yards_proj": 240.0,
        "team_rush_yards_proj": 115.0,
        "elite_run_d": False,
        "wr1_vs_elite_cb": False,
        "pass_rush_edge": False,
        "is_divisional": True,
    }


def fetch_weather(team: str, week: int) -> Dict:
    return {"wind_mph": 7, "precip": False}


def fetch_ref_crew(team: str, week: int) -> Dict:
    return {}


# ---------- HELPERS ----------

def load_official_depth_chart(team: str, week: int) -> Dict[str, List[str]]:
    return fetch_depth_chart(team, week)


def validate_and_build_starters(
    depth: Dict[str, List[str]],
    user_starters: StarterConfig,
) -> StarterConfig:
    """
    Do NOT overwrite names from StarterConfig; depth is only for structure.
    """
    return StarterConfig(
        qb=user_starters.qb,
        rb1=user_starters.rb1,
        rb2=user_starters.rb2,
        wr1=user_starters.wr1,
        wr2=user_starters.wr2,
        wr3=user_starters.wr3,
        te1=user_starters.te1,
        te2=user_starters.te2,
    )


def derive_usage_from_snaps(
    snaps: Dict[str, Dict],
    news_flags: Dict[str, str],
) -> Dict[str, PlayerUsage]:
    usage: Dict[str, PlayerUsage] = {}

    total_rush = sum(p["rush_att"] for p in snaps.values()) or 1.0
    total_tgt = sum(p["targets"] for p in snaps.values()) or 1.0
    total_rz_r = sum(p["rz_rush"] for p in snaps.values()) or 1.0
    total_rz_t = sum(p["rz_tgt"] for p in snaps.values()) or 1.0

    for role, p in snaps.items():
        rush_share = p["rush_att"] / total_rush
        tgt_share = p["targets"] / total_tgt
        rz_r_share = p["rz_rush"] / total_rz_r
        rz_t_share = p["rz_tgt"] / total_rz_t

        flag = news_flags.get(role, "")
        mult = 1.0
        if flag == "arrow_up":
            mult = 1.1
        elif flag == "arrow_down":
            mult = 0.9

        u = PlayerUsage(
            snap_share=p["snap_pct"],
            rush_share=rush_share * mult,
            target_share=tgt_share * mult,
            rz_rush_share=rz_r_share * mult,
            rz_target_share=rz_t_share * mult,
        )
        usage[role] = u

    rush_total = sum(u.rush_share for u in usage.values()) or 1.0
    tgt_total = sum(u.target_share for u in usage.values()) or 1.0
    for u in usage.values():
        u.rush_share /= rush_total
        u.target_share /= tgt_total

    return usage


def scenario_probs(matchup_features: Dict) -> Dict[str, float]:
    return {
        "normal": 0.55,
        "wr1_bracket": 0.10,
        "rb_erased": 0.10,
        "ol_collapse": 0.05,
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
        if wind >= 15 or precip:
            factor *= 1.03

    return max(stat * factor, 0.0)


def apply_rivalry_factor(stat: float, rivalry: bool) -> float:
    return stat * 0.96 if rivalry else stat


def project_player_yards(
    base_yards: float,
    usage: PlayerUsage,
    matchup_features: Dict,
    weather: Dict,
    rivalry: bool,
    is_pass_stat: bool,
) -> PlayerProjection:
    scen = scenario_probs(matchup_features)

    adj = base_yards
    if matchup_features.get("is_wr1") and scen["wr1_bracket"] > 0:
        adj *= (1 - 0.15 * scen["wr1_bracket"])
    if matchup_features.get("is_rb1") and scen["rb_erased"] > 0:
        adj *= (1 - 0.15 * scen["rb_erased"])

    adj = apply_weather_factor(adj, weather, is_pass_stat=is_pass_stat)
    adj = apply_rivalry_factor(adj, rivalry)

    mean_yards = adj
    floor_yards = adj * 0.85

    mean_recs = None
    floor_recs = None
    if usage.target_share > 0:
        est_recs = 38 * usage.target_share * 0.66
        mean_recs = est_recs
        floor_recs = est_recs * 0.85

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


# ---------- MAIN ENTRY POINT ----------

def build_team_projections(
    team: str,
    opponent: str,
    week: int,
    user_starters: StarterConfig,
) -> Dict[str, PlayerProjection]:
    """
    Produces projections keyed by the actual starter names, not WR1/RB1 labels.
    """
    _depth = load_official_depth_chart(team, week)
    starters = validate_and_build_starters(_depth, user_starters)

    role_usage = derive_usage_from_snaps(
        fetch_recent_snaps(team, week),
        fetch_news_flags(team, week),
    )

    matchup = fetch_matchup_metrics(team, week)
    weather = fetch_weather(team, week)
    _refs = fetch_ref_crew(team, week)

    team_pass_yards = matchup["team_pass_yards_proj"]
    team_rush_yards = matchup["team_rush_yards_proj"]
    rivalry = matchup.get("is_divisional", False)

    projections: Dict[str, PlayerProjection] = {}

    # Map roles -> actual names and project on those names
    # WR1
    if starters.wr1:
        u_wr1 = role_usage["WR1"]
        feats_wr1 = {"is_wr1": True}
        base_wr1 = team_pass_yards * u_wr1.target_share
        projections[starters.wr1] = project_player_yards(
            base_yards=base_wr1,
            usage=u_wr1,
            matchup_features=feats_wr1,
            weather=weather,
            rivalry=rivalry,
            is_pass_stat=True,
        )

    # RB1
    if starters.rb1:
        u_rb1 = role_usage["RB1"]
        feats_rb1 = {"is_rb1": True}
        rb1_base = (
            team_rush_yards * u_rb1.rush_share
            + team_pass_yards * 0.25 * u_rb1.target_share
        )
        projections[starters.rb1] = project_player_yards(
            base_yards=rb1_base,
            usage=u_rb1,
            matchup_features=feats_rb1,
            weather=weather,
            rivalry=rivalry,
            is_pass_stat=False,
        )

    # TE1
    if starters.te1:
        u_te1 = role_usage["TE1"]
        feats_te1 = {}
        te1_base = team_pass_yards * u_te1.target_share
        projections[starters.te1] = project_player_yards(
            base_yards=te1_base,
            usage=u_te1,
            matchup_features=feats_te1,
            weather=weather,
            rivalry=rivalry,
            is_pass_stat=True,
        )

    return projections