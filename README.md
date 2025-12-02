# THE ONE FOOTBALL – NFL Prop Analyzer

This app runs the THE ONE FOOTBALL template for any NFL game.

It:
1. Pulls baseline player projections from your data provider.
2. Adjusts them using football context (DVOA, pass rush, coverage type, injuries, game script, efficiency).
3. Outputs a clean table you can use for props, parlays, and analysis.

---

## Files in this project

- `streamlit_app.py` – The main Streamlit app (user interface).
- `engine.py` – The football brain (data fetch + projection adjustments).
- `config_api_keys.py` – Loads API keys from environment or Streamlit secrets.
- `requirements.txt` – List of Python packages needed.
- `.streamlit/secrets.toml` – (Created on Streamlit Cloud) holds your API keys.
- `.gitignore` – Tells Git which files/folders to ignore.

Folders like `.devcontainer` and `.github` are optional helper/config folders and are not required for the app to run.

---

## How to run locally (computer / phone with Python)

1. Install Python 3.9+.
2. Open a terminal in this folder.
3. Install packages:
# 🎈 Blank app template

A simple Streamlit app template for you to modify!

[![Open in Streamlit](https://static.streamlit.io/badges/streamlit_badge_black_white.svg)](https://blank-app-template.streamlit.app/)

### How to run it on your own machine

1. Install the requirements

   ```
   $ pip install -r requirements.txt
   ```

2. Run the app

   ```
   $ streamlit run streamlit_app.py
   ```
