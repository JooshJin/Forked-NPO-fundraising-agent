# Disclaimer:
### Repository is a detached fork of https://github.com/Hugo1223gogo/NPO-fundraising-agent as a working copy for the Summer 2026 Unite for Health fundraising team.

---
title: U4H Donor Recommendation Agent
emoji: 💙
colorFrom: blue
colorTo: indigo
sdk: streamlit
sdk_version: 1.46.0
app_file: app.py
pinned: false
short_description: AI fundraising copilot — who to contact, how, and why.
---

# U4H Donor Recommendation Agent

A prototype AI fundraising copilot for U4H. Given a fundraising need, it recommends **who to contact**, **through which pathway**, **why**, and **what to do next** — grounded in a roster of supporters active at peer nonprofits (Mothers2Mothers, HelpMum, Assist International) and a feedback loop that captures outreach outcomes.

## Features
- **Get Recommendations** — describe a fundraising need; the agent returns up to 3 candidates, each with a 0–100 helpfulness score, pathway (direct / warm intro / event / multi-hop), rationale, tactical approach tips, and a concrete next step.
- **Add Contact** — upload a LinkedIn profile PDF (or paste free-text context) to import a new contact. Detects existing names and offers an in-place update.
- **Browse Roster** — search the seeded roster; each entry shows recorded outreach outcomes alongside the static profile.
- **Feedback & History** — record the outcome of each outreach (success / no_response / declined). Outcomes are fed back into the next recommendation so the agent improves over time, and per-candidate "Past outcomes that shaped this recommendation" makes the loop visible.

## Stack
Streamlit · Google Gemini (`gemini-2.5-flash`) · MongoDB · pandas.

## Local setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env  # then fill in your keys
streamlit run app.py
```

The roster auto-seeds from [data/demo_roster.csv](data/demo_roster.csv) on first run.

## Environment variables / secrets
- `GEMINI_API_KEY` — Google Gemini API key
- `MONGODB_URI` — MongoDB connection string

Database: `u4h_fundraising` · collections: `roster`, `recommendations`, `feedback`.

## Deployment

### Hugging Face Spaces (recommended — free, always-on)
1. Create a new Space at https://huggingface.co/new-space (SDK: Streamlit).
2. Push this repo to the Space's git remote, or sync from GitHub.
3. Under **Settings → Variables and secrets**, add `GEMINI_API_KEY` and `MONGODB_URI`.
4. The frontmatter at the top of this README configures the Space automatically.

### Streamlit Community Cloud (alternative — sleeps after 7d idle)
1. Push to GitHub, connect at https://share.streamlit.io.
2. Main file: `app.py`.
3. Add `GEMINI_API_KEY` and `MONGODB_URI` under **Settings → Secrets**.

## Team
Built by **Terrence**, **Hugo**, **Mahlet**, and **Joshua**.
