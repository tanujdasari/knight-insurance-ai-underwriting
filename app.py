
import os
import hashlib
import base64
from pathlib import Path

import streamlit as st
from dotenv import load_dotenv
import knight_theme
from knight_theme import apply_knight_theme, render_knight_header, render_knight_footer

from services.document_parser import parse_submission
from services.ai_extractor import extract_submission
from services.rules_engine import evaluate_rules
from services.summary_generator import generate_review_content
from services.human_overrides import apply_override

# ============================================================
# 1. PAGE CONFIGURATION
# ============================================================

# Load configuration from .env before checking whether live AI is enabled.
load_dotenv()

# Configure the Streamlit browser tab and use the full page width.
st.set_page_config(
    page_title="Knight Insurance | Underwriting Review",
    page_icon="",
    layout="wide",
)

# Use a local company logo inside the existing branded header.
# This avoids displaying the logo twice and works without internet access.
# Resolve the logo relative to app.py, not the terminal working directory.
logo_path = Path(__file__).resolve().parent / "assets" / "knight_logo.png"
if logo_path.is_file():
    encoded_logo = base64.b64encode(logo_path.read_bytes()).decode("ascii")
    knight_theme.LOGO_URL = f"data:image/png;base64,{encoded_logo}"

apply_knight_theme()
render_knight_header()

# Only call the OpenAI extraction service when explicitly enabled.
LIVE_AI_ENABLED = (
    os.getenv("ENABLE_LIVE_AI", "false").strip().lower() == "true"
)


# ============================================================
# 2. SESSION STATE INITIALIZATION
# ============================================================

# Streamlit reruns the script after interactions. Session state keeps
# results, corrections, and the editable email between reruns.
DEFAULT_STATE = {
    "active_packet": None,
    "parsed_submission": None,
    "ai_extraction": None,
    "ai_error": None,
    "processing_error": None,
    "working_extraction": None,
    "override_audit": [],
    "phase5_draft_key": None,
    "phase5_generated_email": None,
}

# Initialize each key only once; do not overwrite existing user work.
for key, default in DEFAULT_STATE.items():
    if key not in st.session_state:
        st.session_state[key] = default


def clear_results():
    """Reset all packet-specific results, corrections, and draft widgets.

    This prevents a previous submission's evidence, decisions, or email
    from being displayed for a different submission packet.
    """
    st.session_state.parsed_submission = None
    st.session_state.ai_extraction = None
    st.session_state.ai_error = None
    st.session_state.processing_error = None
    st.session_state.working_extraction = None
    st.session_state.override_audit = []
    st.session_state.phase5_draft_key = None
    st.session_state.phase5_generated_email = None
    for widget_key in ("phase5_email", "override_field", "override_value", "override_reason"):
        st.session_state.pop(widget_key, None)


# ============================================================
# 3. SUBMISSION INTAKE
# ============================================================

st.subheader("1. Submission Intake")

packet_name = st.text_input(
    "Submission packet name",
    placeholder="Example: SUB-A",
)

uploaded_files = st.file_uploader(
    "Upload submission documents",
    type=["pdf", "csv", "txt"],
    accept_multiple_files=True,
)

broker_email = st.text_area(
    "Paste broker email",
    height=180,
    placeholder="Paste broker email content here (optional).",
)

st.caption(
    "You can upload broker_email.txt instead of pasting "
    "the broker email into the text box."
)

if LIVE_AI_ENABLED:
    st.success("Live OpenAI extraction is enabled.")
else:
    st.info(
        "Development mode: OpenAI calls are disabled. "
        "Document parsing and automated rules tests are available."
    )


# ============================================================
# 4. PACKET ISOLATION
# ============================================================

# Use file content hashes to detect changes, including changes
# to files that have the same filename and size.

# A SHA-256 digest changes when file bytes change, even if the
# filename stays the same. These hashes are used only for packet identity.
file_identity = tuple(
    (
        file.name,
        hashlib.sha256(file.getvalue()).hexdigest(),
    )
    for file in uploaded_files
)

# Include the packet name and pasted email in the identity as well.
current_input = (
    packet_name,
    file_identity,
    broker_email,
)

# Any input change invalidates previously computed results and overrides.
if st.session_state.active_packet != current_input:
    clear_results()
    st.session_state.active_packet = current_input


# ============================================================
# 5. PROCESS SUBMISSION
# ============================================================

# Process only after the user explicitly clicks the button.
if st.button(
    "Process Submission",
    type="primary",
    use_container_width=True,
):

    if not packet_name.strip():
        st.error("Please enter a submission packet name.")

    elif not uploaded_files and not broker_email.strip():
        st.error(
            "Please upload submission documents "
            "or paste a broker email."
        )

    else:
        clear_results()

        # STEP 1: DOCUMENT PARSING
        # Parse attachments and pasted email into a consistent evidence
        # structure before attempting model-based extraction.
        try:
            with st.spinner("Parsing submission documents..."):
                parsed_result = parse_submission(
                    uploaded_files,
                    broker_email,
                )

            st.session_state.parsed_submission = parsed_result

        except Exception as exc:
            st.session_state.processing_error = (
                f"Document parsing failed: {exc}"
            )

        # STEP 2: AI EXTRACTION
        # Parsing can succeed independently of the OpenAI call. The app
        # must never report a real underwriting decision without extraction.
        parsed_result = st.session_state.parsed_submission

        if parsed_result is not None:

            # Gather individual document outcomes for user-facing feedback.
            statuses = [
                document["status"]
                for document in parsed_result["documents"]
            ]

            if statuses and all(
                status == "success" for status in statuses
            ):
                st.success(
                    "Document parsing completed successfully."
                )
            else:
                st.warning(
                    "Some documents could not be parsed. "
                    "Review the attachment inventory."
                )

            # Avoid sending empty or unreadable submissions to the model.
            if not parsed_result["evidence"]:
                st.session_state.ai_error = (
                    "No readable evidence found. "
                    "AI extraction cannot proceed."
                )

            elif not LIVE_AI_ENABLED:
                st.info(
                    "OpenAI extraction skipped because "
                    "ENABLE_LIVE_AI=false. "
                    "No underwriting decision has been made."
                )

            else:
                try:
                    with st.spinner(
                        "Running OpenAI extraction..."
                    ):
                        extraction = extract_submission(
                            parsed_result
                        )

                    if extraction.extraction_status != "success":
                        raise RuntimeError(
                            "AI extraction did not complete successfully."
                        )

                    # Store the original model result separately from later
                    # human corrections, which operate on a deep copy.
                    st.session_state.ai_extraction = extraction

                    st.success(
                        "AI extraction completed successfully."
                    )

                except Exception as exc:
                    st.session_state.ai_error = (
                        f"AI extraction failed: {exc}"
                    )


# ============================================================
# 6. DISPLAY ERRORS
# ============================================================

if st.session_state.processing_error:
    st.error(st.session_state.processing_error)

if st.session_state.ai_error:
    st.error(st.session_state.ai_error)

    st.info(
        "Document parsing results may still be available. "
        "Actual underwriting decisions require successful "
        "AI extraction."
    )


# ============================================================
# 7. ATTACHMENT INVENTORY
# ============================================================

result = st.session_state.parsed_submission

if result is not None:

    st.divider()
    st.subheader("2. Attachment Inventory")

    # Show file status and attachment metadata for traceability.
    inventory = result["attachment_inventory"]

    if inventory:
        st.dataframe(
            inventory,
            use_container_width=True,
            hide_index=True,
        )
    else:
        st.info("No uploaded attachments were provided.")


    # ========================================================
    # 8. EXTRACTED DOCUMENT EVIDENCE
    # ========================================================

    st.divider()
    st.subheader("3. Extracted Document Evidence")

    # Evidence retains its filename and location so reviewers can
    # verify each extracted statement against the source material.
    sources = result["evidence"]

    if not sources:
        st.warning("No readable document evidence found.")

    else:
        st.caption(
            "Text extracted from the uploaded documents, "
            "with original source locations."
        )

        for index, source in enumerate(sources, start=1):

            title = (
                f"{index}. {source['filename']} "
                f"— {source['location']}"
            )

            with st.expander(title):
                st.write(
                    "**Source file:**",
                    source["filename"],
                )

                st.write(
                    "**Location:**",
                    source["location"],
                )

                st.text(source["text"])


    # ========================================================
    # 9. CSV RECORD COUNTS
    # ========================================================

    st.divider()
    st.subheader("4. CSV Record Counts")

    # CSV row counts are informational; R2 uses the validated schedule
    # count computed by the extraction pipeline, not any raw row count.
    csv_documents = [
        document
        for document in result["documents"]
        if document["file_type"] == "csv"
    ]

    if not csv_documents:
        st.info("No CSV vehicle schedule uploaded.")

    else:
        for document in csv_documents:

            with st.container(border=True):
                st.write(
                    "**File:**",
                    document["filename"],
                )

                st.write(
                    "**Nonempty CSV records:**",
                    document.get("row_count", 0),
                )

                st.caption(
                    "Raw CSV record count only. "
                    "The schedule count must pass schema "
                    "validation before being used in R2."
                )


# ============================================================
# PHASE 6: HUMAN OVERRIDES
# The original AI extraction is never mutated. Overrides are
# held in session state and cleared whenever the packet changes.
# ============================================================

# Keep the immutable baseline available for comparison and audit.
original_extraction = st.session_state.ai_extraction

if original_extraction is not None:
    # Initialize a separate working copy on the first successful extraction.
    if st.session_state.working_extraction is None:
        st.session_state.working_extraction = original_extraction.model_copy(deep=True)

    st.divider()
    st.header("5 Human Overrides")
    st.caption(
        "Review source evidence, enter a verified correction, and record "
        "a reason. Overrides are session-only and never change the "
        "original AI extraction."
    )

    working = st.session_state.working_extraction
    field_options = list(working.fields.keys())
    # Highlight fields that still require manual verification.
    unresolved_names = [
        name for name in field_options
        if working.fields[name].state in ("CONFLICT", "MISSING", "INVALID")
    ]
    if unresolved_names:
        st.warning("Unresolved fields: " + ", ".join(unresolved_names))
    else:
        st.success("No unresolved extraction fields remain.")

    selected_field = st.selectbox(
        "Field to correct", options=field_options,
        index=field_options.index(unresolved_names[0]) if unresolved_names else 0,
        key="override_field",
    )
    source_field = original_extraction.fields[selected_field]
    current_field = working.fields[selected_field]
    st.write("**Original AI state:**", source_field.state)
    st.write("**Original AI value:**", source_field.value)
    st.write("**Current reviewed value:**", current_field.value)

    if source_field.candidates:
        st.markdown("**Original source candidates**")
        for candidate in source_field.candidates:
            st.write(
                f"- {candidate.raw_value} — "
                f"{candidate.evidence.source_file}, {candidate.evidence.locator}"
            )
    if source_field.evidence:
        with st.expander("Original source evidence"):
            for evidence in source_field.evidence:
                st.write(
                    f"**{evidence.source_file} — {evidence.locator}:** "
                    f"{evidence.excerpt_or_observation}"
                )

    # A form collects the corrected value and mandatory justification
    # together, rather than triggering a rerun on each keystroke.
    with st.form("human_override_form", clear_on_submit=False):
        corrected_value = st.text_input(
            "Verified corrected value", key="override_value",
            placeholder="Enter the confirmed value",
        )
        override_reason = st.text_area(
            "Reason / supporting verification (required)",
            key="override_reason",
            placeholder="For example: Confirmed by broker on a follow-up call",
        )
        apply_clicked = st.form_submit_button("Apply Human Override")

    # apply_override validates the value and reason, deep-copies the
    # extraction, and returns a structured audit record.
    if apply_clicked:
        try:
            corrected, record = apply_override(
                working, selected_field, corrected_value, override_reason
            )
        except ValueError as exc:
            st.error(str(exc))
        else:
            st.session_state.working_extraction = corrected
            # Preserve the correction history within this Streamlit session.
            st.session_state.override_audit.append(record)
            st.rerun()

    if st.session_state.override_audit:
        st.subheader("Override Audit History")
        for number, record in enumerate(st.session_state.override_audit, 1):
            with st.expander(
                f"{number}. {record.field_name}: "
                f"{record.previous_state} → KNOWN", expanded=False
            ):
                st.write("Previous value:", record.previous_value)
                st.write("Corrected value:", record.new_value)
                st.write("Reason:", record.reason)
                st.write("Timestamp (UTC):", record.timestamp_utc)
                st.json(record.model_dump())
        st.caption(
            "Audit history is stored only in this browser session; "
            "export or persist it before closing the session."
        )

# ============================================================
# 10. AI EXTRACTED BUSINESS FIELDS
# ============================================================

# All downstream displays and rules use the reviewed working version.
extraction = st.session_state.working_extraction

if extraction is not None:

    st.divider()
    st.subheader("6. AI Extracted Business Fields")

    st.caption(
        f"Model: {extraction.model_name} | "
        f"Status: {extraction.extraction_status}"
    )

    fields = extraction.fields

    # Count field-resolution states independently of R1–R5 results.
    known_count = sum(
        field.state == "KNOWN"
        for field in fields.values()
    )

    missing_count = sum(
        field.state == "MISSING"
        for field in fields.values()
    )

    conflict_count = sum(
        field.state == "CONFLICT"
        for field in fields.values()
    )

    invalid_count = sum(
        field.state == "INVALID"
        for field in fields.values()
    )

    col1, col2, col3, col4 = st.columns(4)

    col1.metric("Known Fields", known_count)
    col2.metric("Missing Fields", missing_count)
    col3.metric("Conflicts", conflict_count)
    col4.metric("Invalid Fields", invalid_count)

    rows = []

    for field_name, field in fields.items():

        source_files = sorted({
            item.source_file
            for item in field.evidence
        })

        rows.append({
            "Field": field_name,
            "Value": (
                str(field.value)
                if field.value is not None
                else "Unresolved"
            ),
            "State": field.state,
            "Source Files": ", ".join(source_files),
            "Evidence Count": len(field.evidence),
        })

    st.dataframe(
        rows,
        use_container_width=True,
        hide_index=True,
    )

    conflicts = [
        name
        for name, field in fields.items()
        if field.state == "CONFLICT"
    ]

    if conflicts:
        st.warning(
            "Conflicting fields require human review: "
            + ", ".join(conflicts)
        )


    # ========================================================
    # 11. FIELD EVIDENCE
    # ========================================================

    st.divider()
    st.subheader("7. Field Evidence and Explanations")

    state_icons = {
        "KNOWN": "✅",
        "MISSING": "⚪",
        "CONFLICT": "⚠️",
        "INVALID": "❌",
    }

    for field_name, field in fields.items():

        icon = state_icons.get(field.state, "ℹ️")

        with st.expander(
            f"{icon} {field_name} — {field.state}"
        ):

            st.write(
                "**Resolved value:**",
                field.value
                if field.value is not None
                else "Unresolved",
            )

            st.write("**Field state:**", field.state)

            if field.evidence:
                st.markdown("**Supporting Evidence**")

                for index, item in enumerate(
                    field.evidence,
                    start=1,
                ):
                    st.markdown(f"**Evidence {index}**")
                    st.write("Source:", item.source_file)
                    st.write("Location:", item.locator)
                    st.code(
                        item.excerpt_or_observation,
                        language=None,
                    )
            else:
                st.info("No supporting evidence available.")

            if field.candidates:
                st.markdown("**Original Candidates**")

                for candidate in field.candidates:
                    st.write(
                        f"{candidate.raw_value} "
                        f"— {candidate.evidence.source_file}"
                    )

            if field.notes:
                st.markdown("**Notes**")

                for note in field.notes:
                    st.warning(note)


    # ========================================================
    # 12. PHASE 4: UNDERWRITING RULES ENGINE
    # ========================================================

    st.divider()
    st.subheader("8. Underwriting Rules Evaluation")

    try:
        # Deterministic evaluation: no LLM call is made here.
        decision = evaluate_rules(extraction)

    except Exception as exc:
        st.error(
            f"Underwriting rules evaluation failed: {exc}"
        )
        decision = None

    if decision is not None:

        if decision.overall_status == "READY_FOR_REVIEW":
            st.success(
                "Overall Status: READY_FOR_REVIEW"
            )
        else:
            st.warning(
                "Overall Status: NEEDS_REVIEW"
            )

        col1, col2, col3 = st.columns(3)

        col1.metric("PASS", decision.pass_count)
        col2.metric("FLAG", decision.flag_count)
        col3.metric("UNKNOWN", decision.unknown_count)

        st.markdown("**R1–R5 Rule Results**")

        # Convert Pydantic rule objects to rows for a readable table.
        rule_rows = []

        for rule in decision.rules:
            rule_rows.append({
                "Rule ID": rule.rule_id,
                "Rule Name": rule.rule_name,
                "Status": rule.status,
                "Reason": rule.reason,
                "Evidence Count": len(rule.evidence),
            })

        st.dataframe(
            rule_rows,
            use_container_width=True,
            hide_index=True,
        )

        # ====================================================
        # 13. RULE EVIDENCE
        # ====================================================

        st.divider()
        st.subheader("9. Rule Evidence and Explanations")

        rule_icons = {
            "PASS": "✅",
            "FLAG": "🚩",
            "UNKNOWN": "❓",
        }

        for rule in decision.rules:

            icon = rule_icons.get(rule.status, "ℹ️")

            with st.expander(
                f"{icon} {rule.rule_id} — "
                f"{rule.rule_name} — {rule.status}"
            ):

                st.write("**Status:**", rule.status)
                st.write("**Reason:**", rule.reason)

                if rule.evidence:

                    for index, item in enumerate(
                        rule.evidence,
                        start=1,
                    ):

                        st.markdown(
                            f"**Supporting Evidence {index}**"
                        )

                        st.write(
                            "Source file:",
                            item.source_file,
                        )

                        st.write(
                            "Location:",
                            item.locator,
                        )

                        st.code(
                            item.excerpt_or_observation,
                            language=None,
                        )

                else:
                    st.info(
                        "No direct supporting excerpt is "
                        "available. Review the field state "
                        "and rule explanation."
                    )

        # ====================================================
        # 14. REVIEW SUMMARY
        # ====================================================

        st.divider()
        st.subheader("10. Underwriting Review Summary")

        st.write(
            "**Submission packet:**",
            packet_name,
        )

        st.write(
            "**Overall decision:**",
            decision.overall_status,
        )

        st.write(
            "**Rules passed:**",
            decision.pass_count,
        )

        st.write(
            "**Rules flagged:**",
            decision.flag_count,
        )

        st.write(
            "**Rules unknown:**",
            decision.unknown_count,
        )

        if decision.overall_status == "NEEDS_REVIEW":
            st.warning(
                "This submission requires human review "
                "before proceeding."
            )

            st.markdown("**Issues requiring attention**")

            for rule in decision.rules:
                if rule.status != "PASS":
                    st.write(
                        f"**{rule.rule_id} — {rule.status}:** "
                        f"{rule.reason}"
                    )
        else:
            st.success(
                "All five deterministic underwriting "
                "rules passed. Ready for human review."
            )

        # Show unresolved extraction fields regardless of rule outcome.
        # A field can remain CONFLICT even when all five current rules
        # PASS (for example, an operations-description discrepancy).
        unresolved = [
            name
            for name, field in extraction.fields.items()
            if field.state in ("CONFLICT", "MISSING", "INVALID")
        ]

        if unresolved:
            st.warning(
                "Field clarification required before final review: "
                + ", ".join(unresolved)
            )

else:
    # Never fabricate a real underwriting decision
    # when AI extraction has not completed.
    if result is not None:

        st.divider()
        st.subheader("5. AI Extraction")

        st.info(
            "AI extraction is pending or unavailable."
        )

        st.subheader("7. Underwriting Rules Evaluation")

        st.warning(
            "Evaluation pending. R1–R5 cannot be evaluated "
            "for this real submission until the required "
            "field extraction succeeds."
        )


# ============================================================
# 15. APPLICATION STATUS
# ============================================================

st.divider()

if extraction is not None:
    st.success(
        "Phase 4: AI extraction and deterministic "
        "underwriting rules are integrated."
    )

elif result is not None:
    st.info(
        "Document parsing is available. "
        "AI extraction and live underwriting evaluation "
        "are pending."
    )

else:
    st.info(
        "Upload a submission packet and click "
        "'Process Submission' to begin."
    )

# PHASE 5 - Underwriting summary and broker follow-up

st.divider()
st.header("11. Underwriting Summary and Broker Email")

extraction = st.session_state.get("working_extraction")

if extraction is None:
    st.info(
        "Complete extraction before generating a real submission "
        "summary. You can use demo_rules.py to test Phase 5 "
        "with clearly labeled synthetic data."
    )
else:
    # Recalculate rules and regenerate narrative after any override.
    decision = evaluate_rules(extraction)
    content = generate_review_content(extraction, decision)

    st.subheader("Underwriting Summary")
    st.text_area(
        "Review summary",
        value=content.summary,
        height=350,
        disabled=True,
    )

    st.subheader("Editable Broker Follow-Up Email")

    # Do not silently overwrite a broker email the user has edited.
    # Track the exact reviewed extraction that produced the current draft.
    draft_key = repr(extraction.model_dump())
    old_generated = st.session_state.get("phase5_generated_email")
    old_draft = st.session_state.get("phase5_email")
    # Detect edits made by the reviewer so they are not overwritten.
    draft_changed = old_draft is not None and old_draft != old_generated

    # Refresh only untouched drafts; preserve customized broker wording.
    if st.session_state.get("phase5_draft_key") != draft_key:
        if not draft_changed:
            st.session_state["phase5_email"] = content.broker_email
        st.session_state["phase5_generated_email"] = content.broker_email
        st.session_state["phase5_draft_key"] = draft_key

    if st.session_state["phase5_email"] != content.broker_email:
        st.warning(
            "The editable email differs from the current generated draft. "
            "Review it for outdated requests after an override."
        )
        if st.button("Replace email with updated generated draft"):
            st.session_state["phase5_email"] = content.broker_email
            st.rerun()

    st.text_area(
        "Edit email before sending",
        key="phase5_email",
        height=350,
    )

    # Download is local only: this application does not send email.
    st.download_button(
        "Download Broker Email",
        data=st.session_state["phase5_email"],
        file_name="broker_followup.txt",
        mime="text/plain",
    )

    st.caption(
        "Draft only. No email is sent automatically. "
        "Underwriter approval is required."
    )


# Branded demo footer
render_knight_footer()
