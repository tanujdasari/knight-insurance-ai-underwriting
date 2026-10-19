# ============================================================
# IMPORTS
# ============================================================

# pytest provides testing utilities, including checking
# whether a function raises an expected exception.
import pytest

# Import the models used to create sample underwriting data.
from models.submission import (
    Candidate,
    Evidence,
    FieldResult,
    SubmissionExtraction,
)

# Import the human override function being tested.
from services.human_overrides import apply_override

# Import the rules engine to verify that underwriting rules
# can be reevaluated after a human correction.
from services.rules_engine import evaluate_rules

# Import the summary generator to verify that corrected
# information appears in the underwriting summary and email.
from services.summary_generator import generate_review_content


# ============================================================
# HELPER FUNCTION: CREATE A KNOWN FIELD
# ============================================================

def known(value):
    """
    Create a FieldResult with a resolved value.

    This helper reduces repeated test setup.

    Example:
        known(150)

    Produces:
        value = 150
        state = KNOWN
    """

    return FieldResult(value=value, state="KNOWN")


# ============================================================
# HELPER FUNCTION: CREATE SAMPLE SUBMISSION
# ============================================================

def sample_extraction():
    """
    Create a synthetic commercial auto submission for testing.

    Most fields contain valid, resolved information.

    The operations_description field intentionally contains
    a CONFLICT state so that human correction behavior
    can be tested.

    The submission is synthetic and does not require
    a real uploaded document or an OpenAI API call.
    """

    # Create sample source evidence.
    # This represents text extracted from an application PDF.
    source = Evidence(
        source_file="application.pdf",
        locator="Page 1",
        excerpt_or_observation="Local deliveries",
    )

    # Return a complete structured submission.
    return SubmissionExtraction(
        fields={

            # Business name is already resolved.
            "business_name": known("ABC Trucking LLC"),

            # Requested policy effective date.
            "requested_effective_date": known("2026-11-01"),

            # State where vehicles are garaged.
            "garaging_state": known("TX"),

            # Intentionally create an unresolved field.
            # The human override tests will correct this value.
            "operations_description": FieldResult(
                value=None,
                state="CONFLICT",

                # Preserve the original extracted candidate.
                candidates=[
                    Candidate(
                        raw_value="Local deliveries",
                        evidence=source,
                    )
                ],

                # Preserve the supporting source evidence.
                evidence=[source],
            ),

            # Vehicle counts match.
            "declared_vehicle_count": known(3),
            "schedule_vehicle_count": known(3),

            # Operating radius is within the 150-mile limit.
            "operating_radius_miles": known(150),

            # Hazardous materials are not transported.
            "hazardous_materials": known(False),

            # Loss runs attachment is present.
            "loss_runs_present": known(True),
        },

        # Identify this as synthetic test data.
        model_name="synthetic-test",

        # Simulate successful extraction.
        extraction_status="success",
    )


# ============================================================
# TEST 1: HUMAN OVERRIDE RESOLVES A CONFLICT
# ============================================================

def test_override_resolves_conflict():
    """
    Verify that a human correction resolves a conflicting field.

    Scenario:
        operations_description = CONFLICT

    Human correction:
        Local deliveries

    Expected:
        state = KNOWN
        human_override = True
        audit reason is preserved
    """

    # Create the original test submission.
    original = sample_extraction()

    # Apply a human correction to the conflicting field.
    corrected, audit = apply_override(
        original,
        "operations_description",
        "Local deliveries",
        "Confirmed with broker",
    )

    # Verify that the conflict is resolved.
    assert corrected.fields["operations_description"].state == "KNOWN"

    # Verify that the field is marked as human-corrected.
    assert corrected.fields["operations_description"].human_override

    # Verify that the audit record stores the correction reason.
    assert audit.reason == "Confirmed with broker"


# ============================================================
# TEST 2: ORIGINAL EXTRACTION REMAINS UNCHANGED
# ============================================================

def test_original_extraction_unchanged():
    """
    Verify that applying an override does not modify
    the original AI extraction object.

    Expected:
        Original state remains CONFLICT.
        Original value remains None.
        Corrected object is a separate instance.

    This validates the deep-copy behavior of apply_override().
    """

    original = sample_extraction()

    # Apply a correction and receive a new extraction object.
    corrected, _ = apply_override(
        original,
        "operations_description",
        "Local deliveries",
        "Verified against application",
    )

    # Original extraction must remain unchanged.
    assert original.fields["operations_description"].state == "CONFLICT"
    assert original.fields["operations_description"].value is None

    # Verify that the corrected object is not the original object.
    assert corrected is not original


# ============================================================
# TEST 3: ORIGINAL EVIDENCE IS PRESERVED
# ============================================================

def test_original_evidence_preserved():
    """
    Verify that source evidence and candidate values
    remain available after a human correction.

    Expected:
        Corrected field retains evidence.
        Audit record retains original candidates.
        Audit record retains original evidence.

    This supports traceability during underwriting review.
    """

    original = sample_extraction()

    corrected, audit = apply_override(
        original,
        "operations_description",
        "Local deliveries",
        "Verified with broker",
    )

    # Confirm supporting evidence remains on the corrected field.
    assert corrected.fields["operations_description"].evidence

    # Confirm original candidate values are saved in the audit.
    assert audit.original_candidates

    # Confirm original evidence is saved in the audit.
    assert audit.original_evidence


# ============================================================
# TEST 4: OVERRIDE REASON IS REQUIRED
# ============================================================

def test_reason_required():
    """
    Verify that an override cannot be applied
    without a reviewer-provided reason.

    Scenario:
        Corrected value is provided.
        Reason is an empty string.

    Expected:
        ValueError is raised.

    This prevents undocumented human corrections.
    """

    # pytest.raises verifies that the expected exception occurs.
    with pytest.raises(ValueError):
        apply_override(
            sample_extraction(),
            "operations_description",
            "Local deliveries",
            "",
        )


# ============================================================
# TEST 5: UNKNOWN FIELD IS REJECTED
# ============================================================

def test_unknown_field_rejected():
    """
    Verify that reviewers cannot override a field
    that does not exist in the submission.

    Scenario:
        field_name = unknown_field

    Expected:
        ValueError is raised.

    This prevents accidental updates to unsupported fields.
    """

    with pytest.raises(ValueError):
        apply_override(
            sample_extraction(),
            "unknown_field",
            "Something",
            "Verified",
        )


# ============================================================
# TEST 6: RULES RECALCULATE AFTER OVERRIDE
# ============================================================

def test_rules_recalculate_after_override():
    """
    Verify that underwriting rules use corrected field values.

    Scenario:
        Original operating radius = 150 miles.
        Human-corrected radius = 200 miles.

    Expected:
        Rule R3 returns FLAG.

    R3 flags operating radii greater than 150 miles.
    """

    original = sample_extraction()

    # Override the original 150-mile radius with 200 miles.
    corrected, _ = apply_override(
        original,
        "operating_radius_miles",
        "200",
        "Updated mileage confirmed by broker",
    )

    # Reevaluate the underwriting rules using corrected data.
    decision = evaluate_rules(corrected)

    # Confirm that R3 identifies the 200-mile radius as a flag.
    assert any(
        rule.rule_id == "R3" and rule.status == "FLAG"
        for rule in decision.rules
    )


# ============================================================
# TEST 7: SUMMARY UPDATES AFTER OVERRIDE
# ============================================================

def test_summary_updates_after_override():
    """
    Verify that the generated summary and broker email
    reflect the corrected extraction.

    Scenario:
        operations_description changes from CONFLICT
        to KNOWN with value "Local deliveries".

    Expected:
        Summary displays the corrected value.
        Summary no longer lists the field as CONFLICT.
        Email no longer requests correction of that field.
    """

    original = sample_extraction()

    # Resolve the operations description conflict.
    corrected, _ = apply_override(
        original,
        "operations_description",
        "Local deliveries",
        "Broker confirmed",
    )

    # Generate a new underwriting decision.
    decision = evaluate_rules(corrected)

    # Generate updated summary and broker email content.
    content = generate_review_content(corrected, decision)

    # Confirm that the summary contains the corrected value.
    assert "Operations: Local deliveries" in content.summary

    # Confirm that the old conflict is no longer reported.
    assert "Operations description: CONFLICT" not in content.summary

    # Confirm that the email does not request another correction
    # for the already resolved operations description.
    assert "correct operations description" not in content.broker_email


# ============================================================
# TEST 8: DUPLICATE OVERRIDE IS REJECTED
# ============================================================

def test_duplicate_override_is_rejected():
    """
    Verify that the system rejects a repeated correction
    when the field already contains the same verified value.

    Scenario:
        First override:  Local deliveries
        Second override: Local deliveries

    Expected:
        Second override raises ValueError.

    This avoids unnecessary duplicate audit records.
    """

    original = sample_extraction()

    # First override resolves the conflict.
    corrected, _ = apply_override(
        original,
        "operations_description",
        "Local deliveries",
        "Verified against application",
    )

    # Attempt to apply the same correction again.
    # The error message should contain "same verified value".
    with pytest.raises(
        ValueError,
        match="same verified value",
    ):
        apply_override(
            corrected,
            "operations_description",
            "Local deliveries",
            "Repeated submission",
        )


# ============================================================
# TEST 9: GENUINE SECOND CORRECTION IS ALLOWED
# ============================================================

def test_genuine_second_correction_is_allowed():
    """
    Verify that a reviewer can apply another correction
    when new verified information changes the value.

    Scenario:
        First override:  Local deliveries
        Second override: Regional deliveries

    Expected:
        New value is Regional deliveries.
        Audit previous value is Local deliveries.
        Audit new value is Regional deliveries.

    This supports legitimate updates during human review.
    """

    original = sample_extraction()

    # First correction resolves the original conflict.
    corrected, _ = apply_override(
        original,
        "operations_description",
        "Local deliveries",
        "Verified against application",
    )

    # Apply a second correction with a genuinely different value.
    updated, audit = apply_override(
        corrected,
        "operations_description",
        "Regional deliveries",
        "Broker provided updated information",
    )

    # Confirm the updated extraction contains the new value.
    assert updated.fields["operations_description"].value == (
        "Regional deliveries"
    )

    # Confirm the audit records the previous value.
    assert audit.previous_value == "Local deliveries"

    # Confirm the audit records the new value.
    assert audit.new_value == "Regional deliveries"


# ============================================================
# TEST 10: DUPLICATE NUMERIC VALUE IS REJECTED
# ============================================================

def test_duplicate_numeric_value_is_rejected():
    """
    Verify that numerically equivalent corrections
    are recognized as duplicates.

    Scenario:
        Original radius: 100 miles
        First override:  150
        Second override: 150.0

    Expected:
        First override succeeds.
        Second override raises ValueError.

    Both 150 and 150.0 represent the same numeric value.
    """

    original = sample_extraction()

    # Start with 100 miles so the first override is a real change.
    original.fields["operating_radius_miles"].value = 100

    # First override: 100 -> 150 (should succeed).
    corrected, _ = apply_override(
        original,
        "operating_radius_miles",
        "150",
        "Verified operating radius",
    )

    # Confirm that normalization produced the numeric value 150.0.
    assert corrected.fields["operating_radius_miles"].value == 150.0

    # Second override: 150 -> 150.0 (should be rejected).
    with pytest.raises(
        ValueError,
        match="same verified value",
    ):
        apply_override(
            corrected,
            "operating_radius_miles",
            "150.0",
            "Repeated value",
        )