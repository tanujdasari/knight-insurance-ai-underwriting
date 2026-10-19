# ============================================================
# IMPORTS
# ============================================================

# pytest provides testing utilities, including parametrize,
# which allows one test to run with multiple input values.
import pytest

# Import the models used to create synthetic underwriting data.
from models.submission import FieldResult, SubmissionExtraction

# Import the deterministic underwriting rules engine.
from services.rules_engine import evaluate_rules


# ============================================================
# HELPER FUNCTION: CREATE A FIELD RESULT
# ============================================================

def field(value=None, state="KNOWN"):
    """
    Create a FieldResult for testing.

    By default, the field is marked KNOWN.

    Examples:
        field(100)             -> KNOWN with value 100
        field(None, "MISSING") -> MISSING with no value

    This helper reduces repeated setup across tests.
    """
    return FieldResult(value=value, state=state)


# ============================================================
# HELPER FUNCTION: CREATE A SAMPLE SUBMISSION
# ============================================================

def submission(**overrides):
    """
    Create a synthetic commercial auto submission.

    The default submission contains valid information
    that satisfies all five underwriting rules.

    Individual tests can replace selected fields
    using keyword arguments.

    Example:
        submission(declared_vehicle_count=field(5))

    This creates a submission with five declared vehicles
    while keeping all other default values unchanged.
    """

    # Create default underwriting fields.
    # These values are designed to produce five PASS results.
    fields = {
        "business_name": field("ABC Trucking LLC"),
        "requested_effective_date": field("2026-11-01"),
        "garaging_state": field("TX"),
        "operations_description": field("Local freight"),
        "declared_vehicle_count": field(3),
        "operating_radius_miles": field(100),
        "hazardous_materials": field(False),
        "loss_runs_present": field(True),
        "schedule_vehicle_count": field(3),
    }

    # Replace default fields with values supplied by a test.
    # This allows each test to focus on one specific scenario.
    fields.update(overrides)

    # Return the structured submission used by the rules engine.
    return SubmissionExtraction(
        fields=fields,
        model_name="synthetic-test",
        extraction_status="success",
    )


# ============================================================
# HELPER FUNCTION: GET AN INDIVIDUAL RULE STATUS
# ============================================================

def status(result, rule_id):
    """
    Retrieve the status of a specific underwriting rule.

    Example:
        status(result, "R3")

    Returns:
        PASS, FLAG, or UNKNOWN.

    next() returns the first matching rule status.
    """
    return next(
        rule.status for rule in result.rules
        if rule.rule_id == rule_id
    )


# ============================================================
# TEST 1: ALL UNDERWRITING RULES PASS
# ============================================================

def test_all_pass():
    """
    Verify that a valid submission passes all five rules.

    Scenario:
        Required fields are valid.
        Vehicle counts match.
        Operating radius is within 150 miles.
        Hazardous materials = No.
        Loss runs are present.

    Expected:
        overall_status = READY_FOR_REVIEW
        pass_count = 5
    """

    # Evaluate the default valid submission.
    result = evaluate_rules(submission())

    # Confirm that the submission is ready for human review.
    assert result.overall_status == "READY_FOR_REVIEW"

    # Confirm that all five underwriting rules passed.
    assert result.pass_count == 5


# ============================================================
# TEST 2: MISSING BUSINESS NAME - R1
# ============================================================

def test_missing_business_name():
    """
    Verify that R1 flags a missing business name.

    Scenario:
        business_name = MISSING

    Expected:
        R1 = FLAG

    Business name is a required submission field.
    """

    # Replace the valid business name with a missing field.
    result = evaluate_rules(submission(
        business_name=field(None, "MISSING")
    ))

    # Confirm that R1 identifies the missing information.
    assert status(result, "R1") == "FLAG"


# ============================================================
# TEST 3: CONFLICTING EFFECTIVE DATE - R1
# ============================================================

def test_conflicting_date():
    """
    Verify that R1 returns UNKNOWN when the requested
    effective date contains conflicting information.

    Scenario:
        requested_effective_date = CONFLICT

    Expected:
        R1 = UNKNOWN

    The rules engine must not select a conflicting date.
    """

    result = evaluate_rules(submission(
        requested_effective_date=field(None, "CONFLICT")
    ))

    # Confirm that the unresolved date produces UNKNOWN.
    assert status(result, "R1") == "UNKNOWN"


# ============================================================
# TEST 4: VEHICLE COUNT MISMATCH - R2
# ============================================================

def test_vehicle_mismatch():
    """
    Verify that R2 flags mismatched vehicle counts.

    Scenario:
        Declared vehicles = 5
        Scheduled vehicles = 3

    Expected:
        R2 = FLAG

    The applicant's declared count must match
    the uploaded vehicle schedule count.
    """

    result = evaluate_rules(submission(
        declared_vehicle_count=field(5)
    ))

    # Confirm that the mismatch is flagged.
    assert status(result, "R2") == "FLAG"


# ============================================================
# TEST 5: ZERO VEHICLE COUNT - R2
# ============================================================

def test_zero_vehicle_count():
    """
    Verify the current R2 behavior for zero vehicles.

    Scenario:
        Declared vehicles = 0
        Scheduled vehicles = 0

    Expected:
        R2 = PASS

    The current rules engine accepts nonnegative
    integer counts when both values match.
    """

    result = evaluate_rules(submission(
        declared_vehicle_count=field(0),
        schedule_vehicle_count=field(0),
    ))

    # Confirm that two matching zero counts pass R2.
    assert status(result, "R2") == "PASS"


# ============================================================
# TEST 6: MISSING VEHICLE COUNT - R2
# ============================================================

def test_missing_vehicle_count():
    """
    Verify that R2 returns UNKNOWN when the declared
    vehicle count is missing.

    Scenario:
        Declared vehicle count = MISSING

    Expected:
        R2 = UNKNOWN

    Vehicle reconciliation cannot be completed
    without both counts.
    """

    result = evaluate_rules(submission(
        declared_vehicle_count=field(None, "MISSING")
    ))

    # Confirm that R2 cannot make a reliable comparison.
    assert status(result, "R2") == "UNKNOWN"


# ============================================================
# TEST 7: OPERATING RADIUS BOUNDARIES - R3
# ============================================================

# parametrize runs the same test with three different values.
#
# Test cases:
# 0 miles   -> PASS
# 150 miles -> PASS
# 151 miles -> FLAG
#
# This validates the exact 150-mile underwriting threshold.
@pytest.mark.parametrize(
    "radius,expected",
    [(0, "PASS"), (150, "PASS"), (151, "FLAG")]
)
def test_radius_boundary(radius, expected):
    """
    Verify that R3 correctly evaluates operating radius
    values at and around the 150-mile threshold.

    The rule allows radii up to and including 150 miles.
    Values greater than 150 miles must be flagged.
    """

    # Evaluate the submission using the current test radius.
    result = evaluate_rules(submission(
        operating_radius_miles=field(radius)
    ))

    # Compare the actual R3 result with the expected status.
    assert status(result, "R3") == expected


# ============================================================
# TEST 8: NEGATIVE OPERATING RADIUS - R3
# ============================================================

def test_negative_radius():
    """
    Verify that R3 rejects a negative operating radius.

    Scenario:
        Operating radius = -10 miles

    Expected:
        R3 = UNKNOWN

    Negative mileage is not a valid operating radius.
    """

    result = evaluate_rules(submission(
        operating_radius_miles=field(-10)
    ))

    # Confirm that R3 does not treat invalid mileage as PASS.
    assert status(result, "R3") == "UNKNOWN"


# ============================================================
# TEST 9: HAZARDOUS MATERIALS = YES - R4
# ============================================================

def test_hazmat_yes():
    """
    Verify that R4 flags hazardous materials transportation.

    Scenario:
        hazardous_materials = True

    Expected:
        R4 = FLAG

    An explicit Yes answer triggers the rule.
    """

    result = evaluate_rules(submission(
        hazardous_materials=field(True)
    ))

    # Confirm that hazardous materials are flagged.
    assert status(result, "R4") == "FLAG"


# ============================================================
# TEST 10: MISSING HAZARDOUS MATERIALS - R4
# ============================================================

def test_hazmat_missing():
    """
    Verify that R4 returns UNKNOWN when hazardous
    materials information is missing.

    Scenario:
        hazardous_materials = MISSING

    Expected:
        R4 = UNKNOWN

    Missing information must not be interpreted as No.
    """

    result = evaluate_rules(submission(
        hazardous_materials=field(None, "MISSING")
    ))

    # Confirm that unresolved hazardous materials information
    # produces UNKNOWN instead of PASS.
    assert status(result, "R4") == "UNKNOWN"


# ============================================================
# TEST 11: LOSS RUNS REPORT MISSING - R5
# ============================================================

def test_missing_loss_runs():
    """
    Verify that R5 flags an absent loss runs report.

    Scenario:
        loss_runs_present = False

    Expected:
        R5 = FLAG

    The rule requires a readable loss runs attachment.
    """

    result = evaluate_rules(submission(
        loss_runs_present=field(False)
    ))

    # Confirm that the missing report triggers a flag.
    assert status(result, "R5") == "FLAG"


# ============================================================
# TEST 12: LOSS RUNS REPORT UNREADABLE - R5
# ============================================================

def test_unreadable_loss_runs():
    """
    Verify that R5 returns UNKNOWN when the loss runs
    attachment cannot be verified.

    Scenario:
        loss_runs_present = INVALID

    Expected:
        R5 = UNKNOWN

    An unreadable report must not be treated as present.
    """

    result = evaluate_rules(submission(
        loss_runs_present=field(None, "INVALID")
    ))

    # Confirm that R5 requires further verification.
    assert status(result, "R5") == "UNKNOWN"


# ============================================================
# TEST 13: ANY FLAG REQUIRES HUMAN REVIEW
# ============================================================

def test_any_flag_requires_review():
    """
    Verify that one flagged rule prevents the submission
    from receiving READY_FOR_REVIEW status.

    Scenario:
        All default fields are valid except:
        hazardous_materials = True

    Expected:
        overall_status = NEEDS_REVIEW

    The overall decision requires every rule to PASS.
    """

    result = evaluate_rules(submission(
        hazardous_materials=field(True)
    ))

    # Confirm that one FLAG changes the overall status.
    assert result.overall_status == "NEEDS_REVIEW"