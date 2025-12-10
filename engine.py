# engine.py
# Main back-end for THE ONE FOOTBALL – NFL Prop Engine

from dataclasses import dataclass
from typing import Dict, List, Optional

# ---------------------------------------------------------------------
# 1. CONFIG / API HELPERS
# ---------------------------------------------------------------------

# Your existing config file – keep this exactly as you already use it.
import config_api_keys as cfg


# These helpers are thin wrappers around whatever API calls
# you already have in the project. Fill the bodies with your
# existing logic – do NOT change how keys are loaded.

def fetch_depth_chart(team: str, week: int) -> Dict[str, List[str]]:
    """
    Return official depth chart for a team.
    Example:
      {
        "QB": ["Drake Maye"],
        "RB": ["Rhamondre Stevenson", "TreVeyon Henderson"],
        "WR": ["Stefon Diggs", "Kayshon Boutte", "DeMario Douglas"],
        "TE": ["Hunter Henry", "Austin Hooper"]
      }
    """
    # TODO: drop in your current depth‑chart code, using cfg.<KEY> as you do now.
    raise NotImplementedError


def fetch_recent_snaps(team: str, week: int) -> Dict[str, Dict]:
    """
    Return last 3–5 games of snap/touch data per player.
    Example per player:
      {
        "snap_pct": 0.65,
        "rush_att": 40,
        "targets": 18,
        "rz_rush": 8,
        "rz_tgt": 6
      }
    """
    # TODO: drop in your current snap / utilization code.
    raise NotImplementedError


def fetch_news_flags(team: str, week: int) -> Dict[str, str]:
    """
    Map players to simple news flags: 'arrow_up', 'arrow_down', or ''.
    Used to bump or trim usage (e.g., Henderson up, Stevenson down).
    """
    # TODO: use whatever news/injury source you already call.
    return {}


def fetch_matchup_metrics(team: str, week: int) -> Dict:
    """
    Return team‑level matchup info you already compute:
      - projected team_pass_yards, team_rush_yards
      - booleans like 'elite_run_d', 'wr1_vs_elite_cb', 'pass_rush_edge'
      - 'is_divisional' flag for rivalry block
    """
    # TODO: plug in your existing matchup logic here.
    raise NotImplementedError


def fetch_weather(team: str, week: int) -> Dict:
    """
    Return weather dict for game:
      { 'wind_mph': int, 'precip': bool, ... }
    """
    # TODO: drop in your current weather call (if you have one).
    return {"wind_mph": 0, "precip": False}


def fetch_ref_crew(team: str, week: int) -> Dict:
    """
    Optional: referee / crew info if you already fetch it.
    """
    return {}


# ---------------------------------------------------------------------
# 2. PROJECTION ENGINE (merged from projections_pipeline.py)
# ---------------------------------------------------------------------

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


def load_official_depth_chart(team: str, week: int) -> Dict[str, List[str]]:
    return fetch_depth_chart(team, week)


def validate_and_build_starters(
    depth: Dict[str, List[str]],
    user_starters: StarterConfig,
) -> StarterConfig:
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


def derive_usage_from_snaps(
    snaps: Dict[str, Dict],
    news_flags: Dict[str, str],
) -> Dict[str, PlayerUsage]:
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

        flag = news_flags.get(name, "")
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

    rush_total = sum(u.rush_share for u in usage.values()) or 1.0
    tgt_total = sum(u.target_share for u in usage.values()) or 1.0
    for u in usage.values():
        u.rush_share /= rush_total
        u.target_share /= tgt_total

    return usage


def scenario_probs(matchup_features: Dict) -> Dict[str, float]:
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
    scen_p = scenario_probs(matchup_features)

    adj = base_yards
    if matchup_features.get("is_wr1") and scen_p["wr1_bracket"] > 0:
        adj *= (1 - 0.15 * scen_p["wr1_bracket"])
    if matchup_features.get("is_rb1") and scen_p["rb_erased"] > 0:
        adj *= (1 - 0.15 * scen_p["rb_erased"])

    adj = apply_weather_factor(adj, weather, is_pass_stat=is_pass_stat)
    adj = apply_rivalry_factor(adj, rivalry)

    mean_yards = adj
    floor_yards = adj * 0.85

    mean_recs = None
    floor_recs = None
    if usage.target_share > 0:
        est_recs = 40 * usage.target_share * 0.65
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


def build_team_projections(
    team: str,
    opponent: str,
    week: int,
    user_starters: StarterConfig,
) -> Dict[str, PlayerProjection]:
    """Main entry point your Streamlit app will call."""

    depth = load_official_depth_chart(team, week)
    starters = validate_and_build_starters(depth, user_starters)

    snaps = fetch_recent_snaps(team, week)
    news_flags = fetch_news_flags(team, week)
    usage = derive_usage_from_snaps(snaps, news_flags)

    matchup = fetch_matchup_metrics(team, week)
    weather = fetch_weather(team, week)
    _refs = fetch_ref_crew(team, week)

    team_pass_yards = matchup["team_pass_yards_proj"]
    team_rush_yards = matchup["team_rush_yards_proj"]
    rivalry = matchup.get("is_divisional", False)

    projections: Dict[str, PlayerProjection] = {}

    # WR1
    wr1 = starters.wr1
    u_wr1 = usage[wr1]
    f_wr1 = {"is_wr1": True, "wr1_vs_elite_cb": matchup.get("wr1_vs_elite_cb", False)}
    projections[wr1] = project_player_yards(
        base_yards=team_pass_yards * u_wr1.target_share,
        usage=u_wr1,
        matchup_features=f_wr1,
        weather=weather,
        rivalry=rivalry,
        is_pass_stat=True,
    )

    # RB1
    rb1 = starters.rb1
    u_rb1 = usage[rb1]
    f_rb1 = {"is_rb1": True, "elite_run_d": matchup.get("elite_run_d", False)}
    rb1_base = (
        team_rush_yards * u_rb1.rush_share
        + team_pass_yards * 0.25 * u_rb1.target_share
    )
    projections[rb1] = project_player_yards(
        base_yards=rb1_base,
        usage=u_rb1,
        matchup_features=f_rb1,
        weather=weather,
        rivalry=rivalry,
        is_pass_stat=False,
    )

    # RB2 (if present)
    if starters.rb2 and starters.rb2 in usage:
        rb2 = starters.rb2
        u_rb2 = usage[rb2]
        f_rb2 = {"is_rb1": False, "elite_run_d": matchup.get("elite_run_d", False)}
        rb2_base = (
            team_rush_yards * u_rb2.rush_share
            + team_pass_yards * 0.25 * u_rb2.target_share
        )
        projections[rb2] = project_player_yards(
            base_yards=rb2_base,
            usage=u_rb2,
            matchup_features=f_rb2,
            weather=weather,
            rivalry=rivalry,
            is_pass_stat=False,
        )

    # WR2 / WR3 / TE1 / TE2 follow same pattern (omitted for brevity)

    return projections