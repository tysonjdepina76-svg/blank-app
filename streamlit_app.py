# streamlit_app.py

import streamlit as st
from engine import StarterConfig, build_team_projections

st.set_page_config(page_title="THE ONE FOOTBALL – NFL Prop Engine")

st.title("THE ONE FOOTBALL – NFL Prop Engine")

# ----------------- SIDEBAR INPUTS -----------------

st.sidebar.header("Game Selection")

week = st.sidebar.number_input("Week", min_value=1, max_value=18, value=15, step=1)
home_team = st.sidebar.text_input("Home Team", value="New England Patriots")
away_team = st.sidebar.text_input("Away Team", value="Buffalo Bills")

st.sidebar.markdown("---")
st.sidebar.header("Home Starters")

home_qb = st.sidebar.text_input("Home QB", value="Drake Maye")
home_rb1 = st.sidebar.text_input("Home RB1", value="Rhamondre Stevenson")
home_rb2 = st.sidebar.text_input("Home RB2", value="")
home_wr1 = st.sidebar.text_input("Home WR1", value="Stefon Diggs")
home_wr2 = st.sidebar.text_input("Home WR2", value="Kayshon Boutte")
home_wr3 = st.sidebar.text_input("Home WR3", value="DeMario Douglas")
home_te1 = st.sidebar.text_input("Home TE1", value="Hunter Henry")
home_te2 = st.sidebar.text_input("Home TE2", value="")

st.sidebar.markdown("---")
st.sidebar.header("Away Starters")

away_qb = st.sidebar.text_input("Away QB", value="Josh Allen")
away_rb1 = st.sidebar.text_input("Away RB1", value="James Cook")
away_rb2 = st.sidebar.text_input("Away RB2", value="")
away_wr1 = st.sidebar.text_input("Away WR1", value="Khalil Shakir")
away_wr2 = st.sidebar.text_input("Away WR2", value="Gabe Davis")
away_wr3 = st.sidebar.text_input("Away WR3", value="Tyrell Shavers")
away_te1 = st.sidebar.text_input("Away TE1", value="Dalton Kincaid")
away_te2 = st.sidebar.text_input("Away TE2", value="Dawson Knox")

run_button = st.sidebar.button("Run Projections")

# ----------------- MAIN LOGIC -----------------

if run_button:
    with st.spinner("Running projection engine..."):
        # Build StarterConfig objects expected by engine.py
        home_starters = StarterConfig(
            qb=home_qb,
            rb1=home_rb1,
            rb2=home_rb2 or None,
            wr1=home_wr1,
            wr2=home_wr2,
            wr3=home_wr3 or None,
            te1=home_te1,
            te2=home_te2 or None,
        )

        away_starters = StarterConfig(
            qb=away_qb,
            rb1=away_rb1,
            rb2=away_rb2 or None,
            wr1=away_wr1,
            wr2=away_wr2,
            wr3=away_wr3 or None,
            te1=away_te1,
            te2=away_te2 or None,
        )

        # New engine entry point (replaces old project_game)
        home_proj = build_team_projections(
            team=home_team,
            opponent=away_team,
            week=week,
            user_starters=home_starters,
        )
        away_proj = build_team_projections(
            team=away_team,
            opponent=home_team,
            week=week,
            user_starters=away_starters,
        )

    # ------------- DISPLAY RESULTS -------------
    def proj_to_rows(team_name, proj_dict):
        rows = []
        for name, p in proj_dict.items():
            rows.append(
                {
                    "Player": name,
                    "Team": team_name,
                    "Mean yards": round(p.mean_yards, 1),
                    "Floor yards": round(p.floor_yards, 1),
                    "Mean TDs": round(p.mean_tds, 2),
                    "Floor TDs": round(p.floor_tds, 2),
                    "Mean receptions": (
                        round(p.mean_recs, 1) if p.mean_recs is not None else ""
                    ),
                    "Floor receptions": (
                        round(p.floor_recs, 1) if p.floor_recs is not None else ""
                    ),
                }
            )
        return rows

    import pandas as pd

    home_rows = proj_to_rows(home_team, home_proj)
    away_rows = proj_to_rows(away_team, away_proj)

    st.subheader(f"{home_team} projections – Week {week}")
    if home_rows:
        st.dataframe(pd.DataFrame(home_rows))
    else:
        st.write("No projections available for home team starters.")

    st.subheader(f"{away_team} projections – Week {week}")
    if away_rows:
        st.dataframe(pd.DataFrame(away_rows))
    else:
        st.write("No projections available for away team starters.")
else:
    st.info("Set teams and starters in the sidebar, then click 'Run Projections'.")