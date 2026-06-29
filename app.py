import streamlit as st

from data_loader import load_roster_from_csv
from memory import (
    upsert_person,
    find_person_by_name,
    get_feedback,
    get_feedback_for_person,
    get_recommendations,
    get_roster,
    save_feedback,
    save_recommendation,
    seed_roster_if_empty,
    update_person_in_roster,
)
from recommender import extract_contact, recommend

st.set_page_config(
    page_title="U4H Donor Recommendation Agent",
    page_icon="💙",
    layout="wide",
)

st.markdown(
    """
<style>
    .block-container { max-width: 1100px; padding-top: 2rem; }
    h1, h2, h3 { letter-spacing: -0.01em; }
    div[data-testid="stTextArea"] textarea,
    div[data-testid="stTextInput"] input {
        border-radius: 10px !important;
    }
    div.stButton > button[kind="primary"],
    div[data-testid="stFormSubmitButton"] > button[kind="primary"] {
        border-radius: 10px;
        background: linear-gradient(135deg, #2563eb 0%, #4f46e5 100%);
        color: white;
        font-weight: 600;
        border: none;
    }
    .tile {
        color: white;
        padding: 16px 18px;
        border-radius: 12px;
        text-align: center;
        font-weight: 600;
        font-size: 1.05rem;
        margin-bottom: 8px;
        box-shadow: 0 4px 12px rgba(15,23,42,0.08);
    }
    .tile .score { font-weight: 400; font-size: 0.85rem; opacity: 0.92; }
    .request-quote {
        background: #f8fafc;
        border-left: 4px solid #4f46e5;
        padding: 12px 16px;
        border-radius: 6px;
        color: #1f2937;
    }
    .byline { color: #6b7280; margin-top: -12px; margin-bottom: 22px; }
</style>
""",
    unsafe_allow_html=True,
)


@st.cache_resource
def _initial_seed() -> int:
    return seed_roster_if_empty(load_roster_from_csv())


_ = _initial_seed()

TILE_COLORS = ["#f97316", "#3b82f6", "#10b981"]  # orange, blue, green


def _build_connection_map_dot(candidates: list[dict]) -> str:
    lines = [
        "digraph G {",
        "rankdir=LR;",
        'bgcolor="white";',
        'node [shape=box, style="rounded,filled", fontname="Helvetica", fontsize=11, margin="0.18,0.10"];',
        'edge [fontname="Helvetica", fontsize=10, color="#6b7280"];',
        '"User" [shape=ellipse, fillcolor="#1e3a8a", fontcolor=white, fontsize=12];',
    ]
    declared = {"User"}
    for i, c in enumerate(candidates[:3]):
        candidate_name = (c.get("name") or "").strip()
        if not candidate_name:
            continue
        nodes = list(c.get("pathway_nodes") or ["User", candidate_name])
        if not nodes:
            nodes = ["User", candidate_name]
        if nodes[0] != "User":
            nodes = ["User"] + nodes
        if nodes[-1] != candidate_name:
            nodes = nodes + [candidate_name]
        rate = c.get("expected_success_rate", 0)
        color = TILE_COLORS[i % len(TILE_COLORS)]
        for n in nodes:
            if n in declared:
                continue
            safe = n.replace('"', '\\"')
            if n == candidate_name:
                lines.append(f'"{safe}" [fillcolor="{color}", fontcolor=white];')
            else:
                lines.append(f'"{safe}" [fillcolor="#e5e7eb", fontcolor="#111827"];')
            declared.add(n)
        for j in range(len(nodes) - 1):
            label = f"{rate}%" if j == len(nodes) - 2 else ""
            src = nodes[j].replace('"', '\\"')
            dst = nodes[j + 1].replace('"', '\\"')
            lines.append(f'"{src}" -> "{dst}" [label="{label}"];')
    lines.append("}")
    return "\n".join(lines)


def _person_lookup(roster: list[dict], name: str) -> dict:
    target = (name or "").strip().lower()
    for p in roster:
        if (p.get("name") or "").strip().lower() == target:
            return p
    return {}


# ---------- Header ----------

st.title("U4H Donor Recommendation Agent")
st.markdown(
    "<div class='byline'>"
    "Built by <b>Terrence</b>, <b>Hugo</b>, <b>Mahlet</b>, and <b>Josh</b> · "
    "For a given fundraising need, recommend who to contact, through which pathway, and why."
    "</div>",
    unsafe_allow_html=True,
)

tab_rec, tab_add, tab_roster, tab_history = st.tabs(
    ["Get Recommendations", "Add Contact", "Browse Roster", "Feedback & History"]
)

# ---------- Tab: Get Recommendations ----------

with tab_rec:
    st.subheader("Describe your fundraising need")
    need = st.text_area(
        "What are you fundraising for?",
        height=160,
        placeholder=(
            "Example: We're launching a maternal health outreach pilot in Lagos "
            "and need to raise $300K by Q3. Who should I approach?"
        ),
        key="rec_need",
    )

    inp_c1, inp_c2 = st.columns(2)
    with inp_c1:
        region = st.text_input("Target region (optional)", placeholder="e.g., West Africa", key="rec_region")
    with inp_c2:
        industry = st.text_input("Industry focus (optional)", placeholder="e.g., Pharma, Consulting", key="rec_industry")

    if st.button("Get recommendations", type="primary", key="rec_run"):
        if not need.strip():
            st.warning("Enter a fundraising need first.")
        else:
            filters = {k: v.strip() for k, v in {"region": region, "industry": industry}.items() if v.strip()}
            with st.spinner("Asking the agent..."):
                try:
                    result = recommend(need, filters=filters or None)
                    rec_id = save_recommendation(result)
                    st.session_state.last_result = result
                    st.session_state.last_rec_id = rec_id
                except Exception as e:
                    st.session_state.last_result = None
                    st.error(f"Something went wrong: {e}")

    result = st.session_state.get("last_result")
    if result:
        rec_id = st.session_state.get("last_rec_id", "")
        candidates = result.get("candidates", [])
        roster = get_roster()

        st.divider()

        st.markdown("### Request")
        st.markdown(
            f"<div class='request-quote'>{result.get('need', '')}</div>",
            unsafe_allow_html=True,
        )

        st.markdown("### Suggested Contacts")
        if not candidates:
            st.info("No strong matches in the current roster.")
        else:
            tile_cols = st.columns(min(len(candidates), 3))
            for i, c in enumerate(candidates[:3]):
                with tile_cols[i]:
                    name = c.get("name", "?")
                    score = c.get("helpfulness_score", "?")
                    color = TILE_COLORS[i % len(TILE_COLORS)]
                    st.markdown(
                        f"<div class='tile' style='background:{color};'>"
                        f"{name}<br><span class='score'>{score}/100</span>"
                        f"</div>",
                        unsafe_allow_html=True,
                    )
                    person = _person_lookup(roster, name)
                    with st.popover("Bio · Location · Contact", use_container_width=True):
                        st.markdown(f"**Location:** {person.get('location') or '—'}")
                        st.markdown(f"**Affiliation:** {person.get('nonprofit_affiliation') or '—'}")
                        st.markdown(f"**Industry:** {person.get('professional_industry') or '—'}")
                        st.markdown(f"**Current role / org:** {person.get('professional_affiliation') or '—'}")
                        if person.get("linkedin_url"):
                            st.markdown(f"**LinkedIn:** {person['linkedin_url']}")
                        bio = person.get("bio") or "—"
                        st.markdown(f"**Bio:** {bio}")

        if result.get("summary"):
            st.markdown("### Strategy")
            st.write(result["summary"])

        if candidates:
            st.markdown("### Connection Map")
            st.graphviz_chart(_build_connection_map_dot(candidates), use_container_width=True)

            st.markdown("### Detail")
            for c in candidates:
                title = (
                    f"{c.get('name', '?')} — score {c.get('helpfulness_score', '?')}/100  ·  "
                    f"expected success {c.get('expected_success_rate', '?')}%"
                )
                with st.expander(title):
                    st.markdown(f"**Pathway:** {c.get('pathway', '')}")
                    st.markdown(f"**Why:** {c.get('why', '')}")
                    st.markdown(f"**How to approach:** {c.get('how_to_approach', '')}")
                    st.markdown(f"**Suggested next step:** {c.get('suggested_next_step', '')}")

                    applied = c.get("applied_outcomes") or []
                    if applied:
                        st.markdown("**Past outcomes that shaped this recommendation:**")
                        effect_icon = {"supported": "▲", "reduced": "▼", "neutral": "•"}
                        effect_color = {"supported": "#16a34a", "reduced": "#dc2626", "neutral": "#6b7280"}
                        for ao in applied:
                            eff = ao.get("effect", "neutral")
                            icon = effect_icon.get(eff, "•")
                            color = effect_color.get(eff, "#6b7280")
                            st.markdown(
                                f"<div style='margin:4px 0 6px 8px;'>"
                                f"<span style='color:{color};font-weight:700;'>{icon}</span> "
                                f"<b>{ao.get('person_name', '?')}</b> — "
                                f"<i>{ao.get('outcome', '?')}</i> · {ao.get('rationale', '')}"
                                f"</div>",
                                unsafe_allow_html=True,
                            )

        if rec_id:
            st.caption(f"Recommendation ID: `{rec_id}` — record outcomes on the Feedback tab.")

# ---------- Tab: Add Contact ----------

with tab_add:
    st.subheader("Add Contact")
    st.caption(
        "Upload a LinkedIn profile PDF (export it via LinkedIn → More → Save to PDF) "
        "and add any extra context. Gemini extracts a structured profile — "
        "review the fields and confirm before saving to the roster."
    )

    linkedin = st.text_input(
        "LinkedIn URL",
        placeholder="https://www.linkedin.com/in/...",
        key="add_linkedin",
    )
    pdf_file = st.file_uploader(
        "LinkedIn profile PDF (recommended)",
        type=["pdf"],
        key="add_pdf",
        help="On LinkedIn → open the profile → 'More' button → 'Save to PDF' → upload the file here.",
    )
    context = st.text_area(
        "Additional context",
        height=160,
        placeholder=(
            "Optional. Paste meeting notes, donation history, mutual connections, "
            "or anything else not in the LinkedIn PDF."
        ),
        key="add_context",
    )

    if st.button("Import", type="primary", key="add_import"):
        if not (linkedin.strip() or context.strip() or pdf_file is not None):
            st.warning("Upload a PDF, paste context, or provide a URL — at least one is needed.")
        else:
            pdf_bytes = pdf_file.read() if pdf_file is not None else None
            with st.spinner("Extracting contact info..."):
                try:
                    extracted = extract_contact(linkedin, context, pdf_bytes)
                    existing = find_person_by_name(extracted.get("name", "")) if extracted.get("name") else None
                    if existing:
                        merged = {**existing}
                        for k, v in extracted.items():
                            if v and not merged.get(k):
                                merged[k] = v
                        st.session_state.pending_contact = merged
                        st.session_state.pending_existing_name = existing.get("name")
                    else:
                        st.session_state.pending_contact = extracted
                        st.session_state.pop("pending_existing_name", None)
                except Exception as e:
                    st.error(f"Extraction failed: {e}")

    pending = st.session_state.get("pending_contact")
    existing_name = st.session_state.get("pending_existing_name")
    if pending:
        st.divider()
        if existing_name:
            st.warning(
                f"**{existing_name}** is already in the roster. Saving will **update the existing entry** "
                "(empty fields are filled from the new import; existing values are preserved unless you edit them)."
            )
            st.markdown("### Review and update")
        else:
            st.markdown("### Review and confirm")
            st.caption("Edit any field, then click **Save to roster**.")

        with st.form("save_contact_form"):
            c1, c2 = st.columns(2)
            with c1:
                f_name = st.text_input("Name *", value=pending.get("name", ""))
                f_location = st.text_input("Location", value=pending.get("location", ""))
                f_npo = st.text_input("Nonprofit affiliation", value=pending.get("nonprofit_affiliation", ""))
                f_edu = st.text_input("Education", value=pending.get("education", ""))
                f_proaff = st.text_input("Professional affiliation", value=pending.get("professional_affiliation", ""))
                f_proind = st.text_input("Professional industry", value=pending.get("professional_industry", ""))
            with c2:
                f_past = st.text_input("Past industries", value=pending.get("past_industries", ""))
                f_inter = st.text_input("Personal interests", value=pending.get("personal_interests", ""))
                f_don = st.text_input("Donation history", value=pending.get("donation_history", ""))
                f_ev = st.text_input("Events / Awards", value=pending.get("events_awards", ""))
                f_lurl = st.text_input("LinkedIn URL", value=pending.get("linkedin_url", ""))

            f_bio = st.text_area("Bio", value=pending.get("bio", ""), height=120)
            f_fb = st.text_area("Feedback / meeting notes", value=pending.get("feedback_notes", ""), height=80)

            sb1, sb2 = st.columns([1, 5])
            with sb1:
                save_label = "Update existing" if existing_name else "Save to roster"
                saved = st.form_submit_button(save_label, type="primary")
            with sb2:
                discarded = st.form_submit_button("Discard")

            if saved:
                if not f_name.strip():
                    st.warning("Name is required.")
                else:
                    payload = {
                        "name": f_name.strip(),
                        "location": f_location.strip(),
                        "nonprofit_affiliation": f_npo.strip(),
                        "education": f_edu.strip(),
                        "professional_affiliation": f_proaff.strip(),
                        "professional_industry": f_proind.strip(),
                        "past_industries": f_past.strip(),
                        "personal_interests": f_inter.strip(),
                        "donation_history": f_don.strip(),
                        "events_awards": f_ev.strip(),
                        "bio": f_bio.strip(),
                        "feedback_notes": f_fb.strip(),
                        "linkedin_url": f_lurl.strip(),
                    }
                    if existing_name:
                        modified = update_person_in_roster(existing_name, payload)
                        if modified:
                            st.success(f"✓ {f_name.strip()} updated in the roster.")
                        else:
                            st.info(f"No changes were needed for {existing_name}.")
                    else:
                        upsert_person(payload)
                        st.success(f"✓ {f_name.strip()} added to the roster.")
                    del st.session_state["pending_contact"]
                    st.session_state.pop("pending_existing_name", None)
                    st.rerun()
            elif discarded:
                del st.session_state["pending_contact"]
                st.session_state.pop("pending_existing_name", None)
                st.rerun()

# ---------- Tab: Browse Roster ----------

with tab_roster:
    st.subheader("Roster")
    roster = get_roster()
    st.caption(f"{len(roster)} people in the roster.")

    q = st.text_input("Filter (matches any field)", key="roster_filter")
    if q:
        ql = q.lower()
        roster = [p for p in roster if ql in " ".join(str(v).lower() for v in p.values())]
        st.caption(f"{len(roster)} matches")

    for p in roster:
        name = p.get("name", "?")
        outcomes = get_feedback_for_person(name)
        header = f"{name} — {p.get('nonprofit_affiliation', '')}"
        if outcomes:
            header += f"  ·  {len(outcomes)} recorded outcome{'s' if len(outcomes) > 1 else ''}"
        with st.expander(header):
            if outcomes:
                st.markdown("##### Recorded outcomes")
                for o in outcomes:
                    line = f"- **{o.get('outcome', '?')}**"
                    if o.get("note"):
                        line += f" — {o['note']}"
                    if o.get("created_at"):
                        line += f"  _(saved {o['created_at'][:10]})_"
                    st.markdown(line)
                st.divider()
            st.markdown("##### Profile")
            st.json(p)

# ---------- Tab: Feedback & History ----------

with tab_history:
    st.subheader("Past recommendations")
    recs = get_recommendations(limit=25)
    if not recs:
        st.info("No recommendations recorded yet. Generate one on the first tab.")

    for r in recs:
        rec_id = str(r["_id"])
        need_txt = r.get("need", "(no need recorded)")
        title = need_txt if len(need_txt) <= 90 else need_txt[:90] + "..."
        with st.expander(title):
            if r.get("summary"):
                st.markdown(f"**Strategy:** {r['summary']}")
            names = [c.get("name") for c in r.get("candidates", []) if c.get("name")]
            st.markdown(f"**Candidates:** {', '.join(names) if names else '(none)'}")
            st.caption(f"Recommendation ID: `{rec_id}` · Created: {r.get('created_at', '?')}")

            st.markdown("##### Record an outcome")
            with st.form(f"fb_form_{rec_id}"):
                who = st.selectbox(
                    "Who did you contact?",
                    names or ["(no candidates on this recommendation)"],
                    key=f"fb_who_{rec_id}",
                )
                outcome = st.selectbox(
                    "Outcome",
                    ["success", "no_response", "declined"],
                    key=f"fb_out_{rec_id}",
                )
                note = st.text_area("Note (optional)", key=f"fb_note_{rec_id}")
                submitted = st.form_submit_button("Save feedback")
                if submitted:
                    if not names:
                        st.warning("No candidates on this recommendation to give feedback on.")
                    else:
                        save_feedback(rec_id, who, outcome, note)
                        st.success("Feedback saved. The agent will factor this into future recommendations.")

    st.divider()
    st.subheader("All recorded outcomes")
    fbs = get_feedback(limit=100)
    if not fbs:
        st.caption("No feedback yet.")
    for fb in fbs:
        line = f"- **{fb.get('person_name', '?')}** — {fb.get('outcome', '?')}"
        if fb.get("note"):
            line += f" — _{fb['note']}_"
        st.markdown(line)
