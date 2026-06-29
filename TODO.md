 # TODOs:
 
 ---
  High Impact (limits usability)

  3. Schema validation on Gemini responses
  There's no check that Gemini included pathway_nodes, expected_success_rate, etc. If any field is missing, the UI crashes on access (e.g. app.py:90). Adding a Pydantic model
  or at least .get() fallbacks everywhere would prevent silent failures.

  4. CSV refresh mechanism
  seed_roster_if_empty() runs once at startup via Streamlit cache (app.py:68). After deploy, adding rows to roster.csv does nothing. Either a "Refresh Roster" button in the UI
  or a scheduled reload would close this gap — right now the 169-contact roster is essentially frozen.

  5. Roster not sent to Gemini efficiently
  Every recommendation call fetches the full roster from MongoDB and dumps it into the prompt as raw JSON — potentially 50KB+. This risks hitting context limits and inflating
  costs. A simple fix: only send fields Gemini actually needs (name, affiliation, industry, location) rather than the full document.

  ---
  Medium Impact (UX and data quality)

  6. Add MongoDB indexes
  recommendations and feedback collections have no indexes. find().sort("_id", -1) scans the whole collection. At scale, this gets slow. Index on name for roster queries and
  timestamp / _id for history.

  7. Pathway validation
  The prompt tells Gemini not to invent intermediary contacts, but there's no post-processing check. If Gemini includes a name not in the roster, the connection map renders a
  phantom node. A quick validation pass after parsing would catch this.

  8. Feedback ↔ Recommendation linkage
  Feedback is recorded but not tied back to the original need context or filters used. This weakens the feedback loop — the model can't learn "this recommendation worked for
  fundraising in East Africa" vs. "this one worked for healthcare campaigns."

  ---
  Low Priority (polish / future-proofing)

  - Authentication — public URL, anyone can add/modify contacts
  - Structured logging — currently no audit trail for API calls or errors
  - Batch upsert for CSV seeding — currently N round-trips to MongoDB, one per contact
  - PDF size validation before upload to Gemini
  - CSV header typos ("Affliation", "Ineterest") — work fine via FIELD_MAP but worth fixing in the source data

  ---
## Completed: 
- #1 (JSON error handling)
- #2 MongoDB timeout loop