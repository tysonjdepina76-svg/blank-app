import streamlit as st
import pandas as pd
from engine import project_game

st.set_page_config(page_title="THE ONE FOOTBALL – NFL Prop Analyzer", layout="wide")

st.title("THE ONE FOOTBALL – NFL Prop Analyzer")
st.write("Pick a game, hit the button, and see template-adjusted projections for every player.")

st.sidebar.header("Game Selection")
home_team = st.sidebar.text_input("Home Team", value="Lions")
away_team = st.sidebar.text_input("Away Team", value="Cowboys")
game_id = st.sidebar.text_input("Game ID", value="2025-12-04-DAL@DET")

if st.sidebar.button("Run Projections"):
    with st.spinner("Running THE ONE FOOTBALL template..."):
        try:
            results = project_game(game_id, home_team, away_team)

            rows = []
            for name, proj in results.items():
                row = {"Player": name}
                row.update(proj)
                rows.append(row)

            if not rows:
                st.warning("No players returned for this game. Check the game_id format and team names.")
            else:
                df = pd.DataFrame(rows)

                front_cols = [c for c in [
                    "Player", "team", "position",
                    "passing_yards", "passing_tds",
                    "rushing_yards", "receiving_yards", "total_yards",
                    "receptions", "hit_prob",
                ] if c in df.columns]
                other_cols = [c for c in df.columns if c not in front_cols]
                df = df[front_cols + other_cols]

                st.subheader(f"Projections – {away_team} at {home_team}")
                st.dataframe(df, use_container_width=True)

                csv = df.to_csv(index=False).encode("utf-8")
                st.download_button(
                    "Download projections as CSV",
                    csv,
                    file_name=f"{away_team}_at_{home_team}_projections.csv",
                    mime="text/csv",
                )

        except Exception as e:
            st.error(f"Error while running projections: {e}")
else:
    st.info("Enter home/away teams and game ID, then click 'Run Projections' on the left.")