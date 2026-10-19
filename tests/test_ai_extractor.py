# ============================================================
# IMPORTS
# ============================================================

# Import Pydantic models used to represent extracted values
# and their supporting source evidence.
from models.submission import Candidate, Evidence

# Import the functions being tested.
#
# normalize():
# Converts extracted text into validated Python values.
#
# resolve_field():
# Determines whether extracted information is
# KNOWN, MISSING, CONFLICT, or INVALID.
from services.ai_extractor import (
    normalize,
    resolve_field,
)


# ============================================================
# HELPER FUNCTION: CREATE TEST CANDIDATES
# ============================================================

def make_candidate(value, filename):
    """
    Create a sample extraction candidate for testing.

    Each candidate contains:
    - A raw extracted value.
    - The source document name.
    - The location within the document.
    - Supporting evidence text.

    This helper avoids repeating the same setup
    across multiple test cases.
    """

    return Candidate(
        # Value extracted from the source document.
        raw_value=value,

        # Create evidence identifying where the value originated.
        evidence=Evidence(
            source_file=filename,

            # Simulated document location.
            locator="Page 1",

            # Simulated evidence excerpt.
            excerpt_or_observation=f"Radius: {value}",
        ),
    )


# ============================================================
# TEST 1: MATCHING OPERATING RADIUS
# ============================================================

def test_matching_radius():
    """
    Verify that equivalent values from multiple documents
    are resolved as KNOWN.

    Scenario:
        Application PDF: 150 miles
        Broker email:    150.0 miles

    Expected:
        state = KNOWN
        value = 150.0

    Although the text representations differ,
    both values represent the same operating radius.
    """

    # Resolve the operating radius using two source candidates.
    result = resolve_field(
        "operating_radius_miles",
        [
            make_candidate("150", "application.pdf"),
            make_candidate("150.0", "broker_email.txt"),
        ],
        ["application.pdf", "broker_email.txt"],
    )

    # Confirm that no conflict was detected.
    assert result.state == "KNOWN"

    # Confirm that the normalized radius equals 150 miles.
    assert result.value == 150


# ============================================================
# TEST 2: CONFLICTING OPERATING RADIUS
# ============================================================

def test_conflicting_radius():
    """
    Verify that different values from source documents
    are identified as a conflict.

    Scenario:
        Application PDF: 150 miles
        Broker email:    200 miles

    Expected:
        state = CONFLICT
        value = None
        evidence count = 2

    The system must not automatically choose one value.
    A human reviewer must resolve the discrepancy.
    """

    # Resolve two different operating radius values.
    result = resolve_field(
        "operating_radius_miles",
        [
            make_candidate("150", "application.pdf"),
            make_candidate("200", "broker_email.txt"),
        ],
        ["application.pdf", "broker_email.txt"],
    )

    # Confirm that the system detects conflicting values.
    assert result.state == "CONFLICT"

    # Confirm that no final value is selected.
    assert result.value is None

    # Confirm that evidence from both sources is preserved.
    assert len(result.evidence) == 2


# ============================================================
# TEST 3: MISSING BUSINESS INFORMATION
# ============================================================

def test_missing_field():
    """
    Verify that a field is marked MISSING when no
    extraction candidates are available.

    Scenario:
        The application and broker email do not provide
        a business name.

    Expected:
        state = MISSING
    """

    # Pass an empty candidate list to simulate missing data.
    result = resolve_field(
        "business_name",
        [],
        ["application.pdf", "broker_email.txt"],
    )

    # Confirm that the field is identified as missing.
    assert result.state == "MISSING"


# ============================================================
# TEST 4: INVALID OPERATING RADIUS
# ============================================================

def test_invalid_radius():
    """
    Verify that invalid operating radius values are rejected.

    Scenario:
        Application PDF reports -10 miles.

    Expected:
        state = INVALID

    A negative operating radius is not valid.
    """

    # Attempt to resolve a negative operating radius.
    result = resolve_field(
        "operating_radius_miles",
        [make_candidate("-10", "application.pdf")],
        ["application.pdf"],
    )

    # Confirm that the invalid value is rejected.
    assert result.state == "INVALID"


# ============================================================
# TEST 5: HAZARDOUS MATERIALS = NO
# ============================================================

def test_explicit_hazmat_no():
    """
    Verify that an explicit 'No' answer is normalized
    into the Python boolean False.

    Expected:
        normalize("hazardous_materials", "No") -> False
    """

    # Confirm that "No" becomes boolean False.
    assert normalize("hazardous_materials", "No") is False


# ============================================================
# TEST 6: HAZARDOUS MATERIALS = YES
# ============================================================

def test_explicit_hazmat_yes():
    """
    Verify that an explicit 'Yes' answer is normalized
    into the Python boolean True.

    Expected:
        normalize("hazardous_materials", "Yes") -> True
    """

    # Confirm that "Yes" becomes boolean True.
    assert normalize("hazardous_materials", "Yes") is True