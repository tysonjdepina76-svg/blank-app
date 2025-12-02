"""
streamlit_app.py
Front-end for THE ONE FOOTBALL – NFL Prop Analyzer.

Uses demo projections from engine.py so it always runs.
"""

import streamlit as st
import pandas as pd
from engine import project_game

st.set_page_config(page_title="THE ONE FOOTBALL – NFL Prop Analyzer", layout="wide")

st.title("THE ONE FOOTBALL – NFL Prop Analyzer")
st.write("Pick the demo game, hit the button, and see template-adjusted projections with TC floors.")

st.sidebar.header("Game Selection")

season_week = st.sidebar.text_input("Season-Week (for reference only)", value="2025-14")
home_team = st.sidebar.text_input("Home Team", value="Lions")
away_team = st.sidebar.text_input("Away Team", value="Cowboys")

if st.sidebar.button("Run Projections"):
    with st.spinner("Running THE ONE FOOTBALL template..."):
        try:
            results = project_game(season_week, home_team, away_team)

            rows = []
            for name, proj in results.items():
                row = {"Player": name}
                row.update(proj)
                rows.append(row)

            if not rows:
                st.warning("No players returned. For the demo, use Cowboys vs Lions.")
            else:
                df = pd.DataFrame(rows)

                front_cols = [c for c in [
                    "Player", "team", "position",
                    "passing_yards", "passing_tds",
                    "tc_floor_passing_yards", "tc_floor_passing_tds",
                    "rushing_yards", "receiving_yards",
                    "tc_floor_rushing_yards", "tc_floor_receiving_yards",
                    "tc_floor_total_yards",
                    "receptions", "tc_floor_receptions",
                ] if c in df.columns]
                other_cols = [c for c in df.columns if c not in front_cols]
                df = df[front_cols + other_cols]

                st.subheader(f"Projections – Demo {away_team} at {home_team}")
                st.dataframe(df, use_container_width=True)

                csv = df.to_csv(index=False).encode("utf-8")
                st.download_button(
                    "Download projections as CSV",
                    csv,
                    file_name=f"{season_week}_{away_team}_at_{home_team}_projections.csv",
                    mime="text/csv",
                )
        except Exception as e:
            st.error(f"Error while running projections: {e}")
else:
    st.info("Use Cowboys vs Lions for the demo and click 'Run Projections'.")