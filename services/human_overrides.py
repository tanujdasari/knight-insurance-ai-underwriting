# ============================================================
# IMPORTS
# ============================================================

# Used to record when a human override was applied.
from datetime import datetime, timezone

# Allows fields to contain different Python data types.
from typing import Any

# Pydantic provides structured data models and validation.
from pydantic import BaseModel, Field

# Import the models used for submission extraction.
from models.submission import (
    FieldResult,
    SubmissionExtraction,
)

# Reuse the same normalization logic used during AI extraction.
from services.ai_extractor import normalize


# ============================================================
# 1. HUMAN OVERRIDE AUDIT MODEL
# ============================================================

class OverrideRecord(BaseModel):
    """
    Stores the audit history of a human correction.

    Each audit record contains:
    - Name of the corrected field
    - Previous extraction state
    - Previous extracted value
    - New corrected value
    - Reason for the correction
    - UTC timestamp
    - Original extracted candidates
    - Original supporting evidence

    This helps maintain transparency and traceability
    throughout the underwriting review process.
    """

    # Field being corrected.
    # Example: "operating_radius_miles"
    field_name: str

    # Previous state:
    # KNOWN, MISSING, CONFLICT, or INVALID.
    previous_state: str

    # Value before the correction.
    previous_value: Any = None

    # New validated value entered by the reviewer.
    new_value: Any

    # Explanation for the correction.
    reason: str

    # UTC timestamp of the correction.
    timestamp_utc: str

    # Preserve original candidate values from the documents.
    original_candidates: list = Field(default_factory=list)

    # Preserve original source evidence.
    original_evidence: list = Field(default_factory=list)


# ============================================================
# 2. APPLY HUMAN OVERRIDE
# ============================================================

def apply_override(
    original: SubmissionExtraction,
    field_name: str,
    raw_value: str,
    reason: str,
) -> tuple[SubmissionExtraction, OverrideRecord]:
    """
    Apply a human correction to an extracted underwriting field.

    Processing steps:

    1. Validate the selected field.
    2. Validate the correction reason.
    3. Validate the corrected value.
    4. Normalize the value.
    5. Prevent duplicate corrections.
    6. Create a deep copy of the original extraction.
    7. Update the selected field.
    8. Create an audit record.
    9. Return the corrected extraction and audit record.

    Important:
        The original extraction is never modified.

    Returns:
        tuple[SubmissionExtraction, OverrideRecord]
    """

    # --------------------------------------------------------
    # STEP 1: VALIDATE FIELD NAME
    # --------------------------------------------------------

    # Ensure the field exists in the submission.
    if field_name not in original.fields:
        raise ValueError(
            f"Unknown field: {field_name}"
        )

    # --------------------------------------------------------
    # STEP 2: VALIDATE CORRECTION REASON
    # --------------------------------------------------------

    # Every correction must have a reason.
    if not reason.strip():
        raise ValueError(
            "An override reason is required."
        )

    # --------------------------------------------------------
    # STEP 3: VALIDATE CORRECTED VALUE
    # --------------------------------------------------------

    # Reject empty or whitespace-only values.
    if not raw_value.strip():
        raise ValueError(
            "A corrected value is required."
        )

    # --------------------------------------------------------
    # STEP 4: NORMALIZE THE CORRECTED VALUE
    # --------------------------------------------------------

    # Normalize using the same logic as AI extraction.
    #
    # Examples:
    #
    # "80 miles" -> 80.0
    # "Yes"      -> True
    # "No"       -> False
    # "4"        -> 4

    normalized = normalize(
        field_name,
        raw_value.strip()
    )

    # Reject values that cannot be normalized.
    if normalized is None:
        raise ValueError(
            f"Invalid corrected value for {field_name}."
        )

    # Retrieve the field before modification.
    original_field = original.fields[field_name]

    # --------------------------------------------------------
    # STEP 5: PREVENT DUPLICATE OVERRIDES
    # --------------------------------------------------------

    # If the field is already KNOWN and has the same value,
    # there is no need to create another override.
    if (
        original_field.state == "KNOWN"
        and original_field.value == normalized
    ):
        raise ValueError(
            "This field already has the same verified value. "
            "No new override was recorded."
        )

    # --------------------------------------------------------
    # STEP 6: PRESERVE THE ORIGINAL EXTRACTION
    # --------------------------------------------------------

    # Create a deep copy so the original AI extraction
    # remains unchanged.
    corrected = original.model_copy(deep=True)

    # --------------------------------------------------------
    # STEP 7: UPDATE THE SELECTED FIELD
    # --------------------------------------------------------

    # Replace only the selected field.
    #
    # The new field:
    # - Uses the normalized corrected value
    # - Has state KNOWN
    # - Preserves original candidates
    # - Preserves original evidence
    # - Records the correction reason
    # - Is marked as a human override

    corrected.fields[field_name] = FieldResult(
        value=normalized,

        # Human-verified value is now known.
        state="KNOWN",

        # Preserve original AI candidate values.
        candidates=original_field.candidates,

        # Preserve original source evidence.
        evidence=original_field.evidence,

        # Keep existing notes and append the correction reason.
        notes=[
            *original_field.notes,
            f"Human override: {reason.strip()}",
        ],

        # Identify the field as human-corrected.
        human_override=True,
    )

    # --------------------------------------------------------
    # STEP 8: CREATE THE AUDIT RECORD
    # --------------------------------------------------------

    # Store information about the correction.
    audit = OverrideRecord(

        # Name of the corrected field.
        field_name=field_name,

        # Previous extraction state.
        previous_state=original_field.state,

        # Previous extracted value.
        previous_value=original_field.value,

        # New normalized value.
        new_value=normalized,

        # Human-provided explanation.
        reason=reason.strip(),

        # Timestamp in UTC.
        timestamp_utc=datetime.now(
            timezone.utc
        ).isoformat(),

        # Preserve original candidate information.
        original_candidates=[
            candidate.model_dump()
            for candidate in original_field.candidates
        ],

        # Preserve original evidence information.
        original_evidence=[
            evidence.model_dump()
            for evidence in original_field.evidence
        ],
    )

    # --------------------------------------------------------
    # STEP 9: RETURN RESULTS
    # --------------------------------------------------------

    # IMPORTANT:
    #
    # app.py expects two return values:
    #
    # corrected, record = apply_override(...)
    #
    # Without this return statement, Python returns None,
    # causing:
    #
    # TypeError:
    # cannot unpack non-iterable NoneType object
    #
    # Return both the corrected submission and audit record.

    return corrected, audit