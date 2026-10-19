# ============================================================
# IMPORTS
# ============================================================

# Import the data models used to construct synthetic
# underwriting submissions and supporting source evidence.
from models.submission import (
    Candidate,
    Evidence,
    FieldResult,
    SubmissionExtraction,
)

# Import the deterministic underwriting rules engine.
from services.rules_engine import evaluate_rules

# Import the service that generates the underwriting summary
# and broker follow-up email.
from services.summary_generator import generate_review_content


# ============================================================
# HELPER FUNCTION: CREATE A RESOLVED FIELD
# ============================================================

def known(value):
    """
    Create a field with a confirmed value.

    The KNOWN state indicates that the field has been
    successfully resolved.

    Example:
        known("ABC Trucking LLC")

    Returns:
        FieldResult(
            value="ABC Trucking LLC",
            state="KNOWN"
        )
    """

    return FieldResult(
        value=value,
        state="KNOWN",
    )


# ============================================================
# TEST 1: CONFLICTING OPERATIONS APPEAR IN REVIEW OUTPUTS
# ============================================================

def test_conflicting_operations_appears_in_summary_and_email():
    """
    Verify that conflicting operations descriptions are
    included in the underwriting summary and broker email.

    Scenario:
        Application PDF:
            Local deliveries

        Broker email:
            Long-haul deliveries

    Expected:
        1. All five underwriting rules pass.
        2. Overall status is READY_FOR_REVIEW.
        3. Summary identifies operations as CONFLICT.
        4. Summary preserves both candidate values.
        5. Summary identifies both source documents.
        6. Broker email requests clarification.

    Important:
        The current five underwriting rules do not directly
        evaluate operations_description.

        Therefore, all five rules can pass even when
        this field contains a conflict.

        The summary generator independently identifies
        unresolved extraction fields.
    """

    # --------------------------------------------------------
    # STEP 1: CREATE EVIDENCE FROM THE APPLICATION PDF
    # --------------------------------------------------------

    # Simulate an operations description extracted
    # from the first page of an application document.
    source1 = Evidence(
        source_file="application.pdf",
        locator="Page 1",
        excerpt_or_observation="Local deliveries",
    )

    # --------------------------------------------------------
    # STEP 2: CREATE EVIDENCE FROM THE BROKER EMAIL
    # --------------------------------------------------------

    # Simulate conflicting information supplied by the broker.
    source2 = Evidence(
        source_file="broker_email.txt",
        locator="Text body",
        excerpt_or_observation="Long-haul deliveries",
    )

    # --------------------------------------------------------
    # STEP 3: CREATE THE UNDERWRITING SUBMISSION FIELDS
    # --------------------------------------------------------

    # Most fields contain valid information.
    # Only operations_description is intentionally conflicting.
    fields = {
        "business_name": known("ABC Trucking LLC"),
        "requested_effective_date": known("2026-11-01"),
        "garaging_state": known("TX"),

        # Create an unresolved operations description.
        "operations_description": FieldResult(
            value=None,
            state="CONFLICT",

            # Preserve both possible values and their evidence.
            candidates=[
                Candidate(
                    raw_value="Local deliveries",
                    evidence=source1,
                ),
                Candidate(
                    raw_value="Long-haul deliveries",
                    evidence=source2,
                ),
            ],
        ),

        # Vehicle counts match, satisfying R2.
        "declared_vehicle_count": known(3),
        "schedule_vehicle_count": known(3),

        # Radius is within the 150-mile limit, satisfying R3.
        "operating_radius_miles": known(150),

        # Hazardous materials are not transported, satisfying R4.
        "hazardous_materials": known(False),

        # Loss runs are present, satisfying R5.
        "loss_runs_present": known(True),
    }

    # --------------------------------------------------------
    # STEP 4: BUILD THE STRUCTURED EXTRACTION OBJECT
    # --------------------------------------------------------

    # Construct a synthetic extraction without using
    # the OpenAI API or uploading actual documents.
    extraction = SubmissionExtraction(
        fields=fields,
        model_name="synthetic-test",
        extraction_status="success",
    )

    # --------------------------------------------------------
    # STEP 5: EVALUATE UNDERWRITING RULES
    # --------------------------------------------------------

    # Run all five deterministic underwriting rules.
    decision = evaluate_rules(extraction)

    # Verify that all five rules pass.
    assert decision.pass_count == 5

    # Verify the current rule-engine overall status.
    assert decision.overall_status == "READY_FOR_REVIEW"

    # --------------------------------------------------------
    # STEP 6: GENERATE SUMMARY AND BROKER EMAIL
    # --------------------------------------------------------

    # Generate both outputs using the structured extraction
    # and the underwriting rule decision.
    content = generate_review_content(
        extraction,
        decision,
    )

    # --------------------------------------------------------
    # STEP 7: VERIFY THE UNDERWRITING SUMMARY
    # --------------------------------------------------------

    # Confirm that the conflict is explicitly identified.
    assert "Operations description: CONFLICT" in content.summary

    # Confirm that the first candidate value is preserved.
    assert "Local deliveries" in content.summary

    # Confirm that the second candidate value is preserved.
    assert "Long-haul deliveries" in content.summary

    # Confirm that the first source document is referenced.
    assert "application.pdf" in content.summary

    # Confirm that the second source document is referenced.
    assert "broker_email.txt" in content.summary

    # --------------------------------------------------------
    # STEP 8: VERIFY THE BROKER FOLLOW-UP EMAIL
    # --------------------------------------------------------

    # Confirm that the broker is asked to identify
    # the correct operations description.
    assert "correct operations description" in content.broker_email

    # Confirm that the email explains why clarification
    # is necessary.
    assert "conflicting information" in content.broker_email


# ============================================================
# TEST 2: RESOLVED FIELDS DO NOT GENERATE CONFLICT REQUESTS
# ============================================================

def test_all_fields_resolved_no_conflict_request():
    """
    Verify that no conflict clarification is requested
    when all extracted fields are resolved.

    Scenario:
        Every submission field is KNOWN.
        All underwriting rules pass.

    Expected:
        1. Summary indicates that all fields are resolved.
        2. Broker email does not mention conflicting information.

    This prevents unnecessary broker follow-up requests
    for submissions without outstanding field conflicts.
    """

    # --------------------------------------------------------
    # STEP 1: CREATE A FULLY RESOLVED SUBMISSION
    # --------------------------------------------------------

    # Every field contains a known value.
    # Vehicle counts match and the radius is within limits.
    fields = {
        "business_name": known("ABC Trucking LLC"),
        "requested_effective_date": known("2026-11-01"),
        "garaging_state": known("TX"),
        "operations_description": known("Local deliveries"),
        "declared_vehicle_count": known(3),
        "schedule_vehicle_count": known(3),
        "operating_radius_miles": known(100),
        "hazardous_materials": known(False),
        "loss_runs_present": known(True),
    }

    # --------------------------------------------------------
    # STEP 2: CREATE THE EXTRACTION OBJECT
    # --------------------------------------------------------

    extraction = SubmissionExtraction(
        fields=fields,
        model_name="synthetic-test",
        extraction_status="success",
    )

    # --------------------------------------------------------
    # STEP 3: EVALUATE UNDERWRITING RULES
    # --------------------------------------------------------

    # Run the deterministic underwriting checks.
    decision = evaluate_rules(extraction)

    # --------------------------------------------------------
    # STEP 4: GENERATE REVIEW CONTENT
    # --------------------------------------------------------

    # Generate the internal summary and broker email.
    content = generate_review_content(
        extraction,
        decision,
    )

    # --------------------------------------------------------
    # STEP 5: VERIFY THE GENERATED OUTPUTS
    # --------------------------------------------------------

    # Confirm that the summary reports all fields as resolved.
    assert "All extracted fields are resolved" in content.summary

    # Confirm that the email does not incorrectly request
    # clarification about conflicting information.
    assert "conflicting information" not in content.broker_email