# Deployment Guide — Streamlit Community Cloud

The app is deploy-ready. It **self-bootstraps**: on first run, if
`models/model.pkl` is missing, the dashboard generates the data and trains the
model automatically (≈1 minute), so you do **not** need to commit the model
artifact.

## Prerequisites
- A GitHub account with this repository pushed (public or private).
- A free [Streamlit Community Cloud](https://share.streamlit.io) account linked to
  that GitHub account.

## Steps

1. **Push to GitHub** (once you've created a repo):
   ```bash
   git remote add origin https://github.com/<you>/credit-risk-scoring-simulator.git
   git branch -M main
   git push -u origin main
   ```

2. **Create the app on Streamlit Cloud**
   - Go to <https://share.streamlit.io> → **New app**.
   - Repository: your repo. Branch: `main`.
   - **Main file path:** `src/dashboard.py`
   - Click **Deploy**.

3. **First load** — the app shows *"generating data and training the model…"*,
   then renders. Subsequent loads are instant (cached).

4. **Verify** — check all four tabs load and a prediction returns in <2 s
   (PRD usability target).

5. **Add the public link** to `README.md` and your portfolio/CV.

## Python version
`requirements.txt` targets Python 3.11+. Streamlit Cloud's default interpreter is
fine; if you want to pin it, add a `runtime.txt` containing e.g. `python-3.12`.

## Notes
- `models/` and `data/processed/` are gitignored and regenerated on first run.
- If you'd rather ship a pre-trained model (faster cold start), remove
  `models/*.pkl` from `.gitignore`, run `python -m src.train_model`, and commit
  `models/model.pkl` + `models/metrics.json`.
- Memory: training XGBoost on 30k rows fits comfortably in the free tier.
