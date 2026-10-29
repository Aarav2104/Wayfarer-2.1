# Wayfarer 2.1

Errand planner with a Python brain. Add tasks ("Bank before 2 pm, buy medicines, collect parcel"); Wayfarer finds nearby places, checks opening hours, plans the order with Google OR-Tools, guides you by voice and re-plans when things change.

![tests](../../actions/workflows/tests.yml/badge.svg)

## Run locally (free)
    python -m venv .venv && source .venv/bin/activate     # Windows: .venv\Scripts\activate
    pip install -r requirements-dev.txt
    cd backend && uvicorn app.main:app --reload            # open http://localhost:8000
    pytest                                                 # 13 tests

## Deploy (free): GitHub → Render
1. Create an empty GitHub repo, then in this folder:
       git init && git add . && git commit -m "Wayfarer 2.1" && git branch -M main
       git remote add origin https://github.com/<you>/wayfarer.git && git push -u origin main
   `.env` is git-ignored. Never commit keys.
2. render.com → New → **Blueprint** → pick the repo (it reads `render.yaml`). Choose the free plan.
3. In the service's Environment tab, optionally set `GEMINI_API_KEY`, `GEMINI_MODEL` (copy the current name from Google AI Studio) and `WAYFARER_CONTACT` (your email, used in the User-Agent for OpenStreetMap services).
4. Open `https://<name>.onrender.com`. HTTPS is automatic, which phones need for location.

Free-plan behaviour: sleeps after ~15 min idle (about a minute to wake) and the disk resets on restart, so the learned durations file is not permanent. Any host that runs a Dockerfile also works (`Dockerfile` included).

## Streamlit
Streamlit Community Cloud runs Streamlit scripts only, so it cannot host this FastAPI + map app. `streamlit_landing/` is a styled Streamlit page (name, description, preview image, "Open Wayfarer" button) that links to the live app:
1. share.streamlit.io → New app → this repo, main file `streamlit_landing/streamlit_app.py`.
2. In the app's **Secrets** add (TOML):
       WAYFARER_URL = "https://<name>.onrender.com"
       REPO_URL = "https://github.com/<you>/wayfarer"
3. Your name and phone number are the `OWNER` and `PHONE_*` lines at the top of `streamlit_app.py`. Clear the phone values to hide the number.
The preview image (`assets/preview.png`) is an illustration with sample data, not a live screenshot. Replace it with a real screenshot any time.

## Protecting a public link
Limits are on by default: 60 API requests per minute per visitor (`WAYFARER_RATE_PER_MIN`), 150 Gemini calls a day (`WAYFARER_LLM_DAILY`), 20 web hours lookups a day (`WAYFARER_WEB_HOURS_DAILY`).

## Layout
`backend/app` planner (OR-Tools), hours, places, nlp, webhours, store · `frontend/index.html` map and UI · `streamlit_landing` Streamlit front door.

Data © OpenStreetMap contributors. Free demo servers have fair-use limits. Times are estimates; check opening hours.
