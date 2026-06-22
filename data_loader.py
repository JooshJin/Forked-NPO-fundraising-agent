from pathlib import Path

import pandas as pd

CSV_PATH = Path(__file__).parent / "data" / "roster.csv"

FIELD_MAP = {
    "Name": "name",
    "Location": "location",
    "Non-Profit Affliation": "nonprofit_affiliation",
    "Education": "education",
    "Professional Affliation": "professional_affiliation",
    "Professional Industry": "professional_industry",
    "Past/Other Professional Industries": "past_industries",
    "Personal Ineterest": "personal_interests",
    "Donation History": "donation_history",
    "Events / Awards": "events_awards",
    "Bio": "bio",
    "Feedback / Meeting Notes": "feedback_notes",
}


def load_roster_from_csv(path: Path = CSV_PATH) -> list[dict]:
    df = pd.read_csv(path, skiprows=1)
    df = df.rename(columns=FIELD_MAP)
    df = df.fillna("")
    df = df[df["name"].astype(str).str.strip() != ""]
    keep = [c for c in FIELD_MAP.values() if c in df.columns]
    return df[keep].to_dict(orient="records")
