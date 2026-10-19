# ============================================================
# IMPORTS
# ============================================================

# date is used to validate the requested policy effective date.
from datetime import date

# isfinite ensures numeric values are not infinity or NaN.
from math import isfinite

# Import Pydantic models for individual rule results
# and the final underwriting review decision.
from models.rules import RuleResult, UnderwritingDecision


# ============================================================
# UNDERWRITING RULES ENGINE
# ============================================================

def evaluate_rules(extraction):
    """
    Evaluate a commercial auto insurance submission using
    five deterministic underwriting rules (R1–R5).

    The rules engine uses structured extraction results,
    rather than asking the AI model to make decisions.

    R1: Required business information
    R2: Vehicle count reconciliation
    R3: Operating radius threshold
    R4: Hazardous materials
    R5: Loss runs attachment

    Each rule returns:
        PASS    - Rule requirements are satisfied.
        FLAG    - A defined problem or violation is found.
        UNKNOWN - Information is insufficient or unresolved.

    Overall status:
        READY_FOR_REVIEW - All five rules return PASS.
        NEEDS_REVIEW     - At least one rule is FLAG or UNKNOWN.

    Note:
        READY_FOR_REVIEW is not an insurance approval.
        A human underwriter must make the final decision.
    """

    # Access the dictionary containing extracted business fields.
    fields = extraction.fields

    # --------------------------------------------------------
    # HELPER FUNCTIONS
    # --------------------------------------------------------

    def field(name):
        """
        Retrieve an individual field result by its name.

        Example:
            field("business_name")
        """
        return fields[name]

    def evidence(*names):
        """
        Collect supporting evidence for one or more fields.

        *names allows multiple field names to be passed.

        Example:
            evidence("declared_vehicle_count",
                     "schedule_vehicle_count")
        """
        return [
            item
            for name in names
            for item in field(name).evidence
        ]

    def known(name):
        """
        Check whether a field has a resolved value.

        Returns True only when the field state is KNOWN.
        """
        return field(name).state == "KNOWN"

    # Store the results of all five underwriting rules.
    results = []

    # ========================================================
    # RULE R1: REQUIRED BUSINESS INFORMATION
    # ========================================================

    # Both business name and requested effective date
    # are required for the submission.
    required = ["business_name", "requested_effective_date"]

    # If either required field is MISSING, flag the submission.
    if any(field(n).state == "MISSING" for n in required):
        r1_status = "FLAG"
        r1_reason = "Required business name or effective date is missing."

    # If a required field is conflicting or invalid,
    # the rule cannot be conclusively evaluated.
    elif not all(known(n) for n in required):
        r1_status = "UNKNOWN"
        r1_reason = "Required fields contain invalid or conflicting values."

    else:
        # Retrieve the resolved values.
        business = field("business_name").value
        effective = field("requested_effective_date").value

        try:
            # Business name must be a nonempty string.
            valid_name = isinstance(business, str) and bool(business.strip())

            # Effective date must be a valid ISO date string.
            # Example: "2026-11-01".
            valid_date = (
                isinstance(effective, str)
                and date.fromisoformat(effective).isoformat() == effective
            )

        except ValueError:
            # An invalid date format fails validation.
            valid_date = False

        # PASS only when both required values are valid.
        r1_status = "PASS" if valid_name and valid_date else "UNKNOWN"

        r1_reason = (
            "Business name and effective date are valid."
            if r1_status == "PASS"
            else "Required field values are invalid."
        )

    # Save the R1 evaluation and supporting evidence.
    results.append(RuleResult(
        rule_id="R1",
        rule_name="Required Fields",
        status=r1_status,
        reason=r1_reason,
        evidence=evidence(*required),
    ))

    # ========================================================
    # RULE R2: VEHICLE COUNT RECONCILIATION
    # ========================================================

    # Compare the applicant's declared vehicle count
    # against the number of vehicles in the CSV schedule.
    declared = field("declared_vehicle_count")
    scheduled = field("schedule_vehicle_count")

    def valid_count(item):
        """
        Verify that a vehicle count:
        - Has state KNOWN.
        - Is an integer.
        - Is not negative.

        type(...) is int also excludes boolean values,
        because bool is a subclass of int in Python.
        """
        return (
            item.state == "KNOWN"
            and type(item.value) is int
            and item.value >= 0
        )

    # If either count is unavailable or invalid,
    # the rule cannot make a reliable comparison.
    if not valid_count(declared) or not valid_count(scheduled):
        r2_status = "UNKNOWN"
        r2_reason = "Vehicle counts are missing, invalid, or unresolved."

    # PASS when both vehicle counts match.
    elif declared.value == scheduled.value:
        r2_status = "PASS"
        r2_reason = f"Both sources report {declared.value} vehicles."

    else:
        # FLAG when the declared count and schedule count differ.
        r2_status = "FLAG"
        r2_reason = (
            f"Declared {declared.value} vehicles; "
            f"schedule contains {scheduled.value}."
        )

    # Save the R2 evaluation with evidence from both sources.
    results.append(RuleResult(
        rule_id="R2",
        rule_name="Vehicle Count Reconciliation",
        status=r2_status,
        reason=r2_reason,
        evidence=evidence(
            "declared_vehicle_count", "schedule_vehicle_count"
        ),
    ))

    # ========================================================
    # RULE R3: OPERATING RADIUS
    # ========================================================

    # Maximum permitted operating radius: 150 miles.
    # A radius greater than 150 miles must be flagged.
    radius = field("operating_radius_miles")

    # Validate that the radius:
    # - Has state KNOWN.
    # - Is numeric (integer or float).
    # - Is finite (not infinity or NaN).
    # - Is not negative.
    if (
        not known("operating_radius_miles")
        or type(radius.value) not in (int, float)
        or not isfinite(radius.value)
        or radius.value < 0
    ):
        r3_status = "UNKNOWN"
        r3_reason = "Operating radius is missing, invalid, or conflicting."

    # FLAG when operating radius exceeds 150 miles.
    elif radius.value > 150:
        r3_status = "FLAG"
        r3_reason = f"Operating radius {radius.value} exceeds 150 miles."

    else:
        # PASS when the radius is within the threshold.
        # Exactly 150 miles is allowed.
        r3_status = "PASS"
        r3_reason = f"Operating radius {radius.value} is within 150 miles."

    # Save the R3 evaluation.
    results.append(RuleResult(
        rule_id="R3",
        rule_name="Operating Radius",
        status=r3_status,
        reason=r3_reason,
        evidence=evidence("operating_radius_miles"),
    ))

    # ========================================================
    # RULE R4: HAZARDOUS MATERIALS
    # ========================================================

    # Determine whether the applicant transports
    # hazardous materials.
    hazmat = field("hazardous_materials")

    # UNKNOWN when the hazardous materials field
    # is missing, invalid, or conflicting.
    if not known("hazardous_materials"):
        r4_status = "UNKNOWN"
        r4_reason = "Hazardous materials status is unresolved."

    # FLAG when hazardous materials are explicitly reported.
    elif hazmat.value is True:
        r4_status = "FLAG"
        r4_reason = "Hazardous materials explicitly marked Yes."

    # PASS when hazardous materials are explicitly denied.
    elif hazmat.value is False:
        r4_status = "PASS"
        r4_reason = "Hazardous materials explicitly marked No."

    else:
        # Reject ambiguous or unexpected data types.
        r4_status = "UNKNOWN"
        r4_reason = "Hazardous materials answer is ambiguous."

    # Save the R4 evaluation.
    results.append(RuleResult(
        rule_id="R4",
        rule_name="Hazardous Materials",
        status=r4_status,
        reason=r4_reason,
        evidence=evidence("hazardous_materials"),
    ))

    # ========================================================
    # RULE R5: LOSS RUNS ATTACHMENT
    # ========================================================

    # Verify whether a readable loss runs report
    # was included with the submission.
    loss_runs = field("loss_runs_present")

    # UNKNOWN when attachment availability cannot be verified.
    if not known("loss_runs_present"):
        r5_status = "UNKNOWN"
        r5_reason = "Loss runs attachment cannot be verified."

    # PASS when a readable loss runs report is attached.
    elif loss_runs.value is True:
        r5_status = "PASS"
        r5_reason = "Readable loss runs report attached."

    # FLAG when the loss runs report is absent.
    elif loss_runs.value is False:
        r5_status = "FLAG"
        r5_reason = "Loss runs report is not attached."

    else:
        # UNKNOWN when the field contains an unexpected value.
        r5_status = "UNKNOWN"
        r5_reason = "Loss runs attachment state is invalid."

    # Save the R5 evaluation.
    results.append(RuleResult(
        rule_id="R5",
        rule_name="Loss Runs",
        status=r5_status,
        reason=r5_reason,
        evidence=evidence("loss_runs_present"),
    ))

    # ========================================================
    # FINAL UNDERWRITING DECISION
    # ========================================================

    # Determine whether every underwriting rule passed.
    #
    # all() returns True only if all five statuses are PASS.
    all_pass = all(r.status == "PASS" for r in results)

    # Create and return the complete underwriting decision.
    return UnderwritingDecision(

        # A submission is ready for human review only
        # when all five deterministic rules pass.
        overall_status=(
            "READY_FOR_REVIEW" if all_pass else "NEEDS_REVIEW"
        ),

        # Preserve each individual rule result.
        rules=results,

        # Count the number of passed rules.
        pass_count=sum(r.status == "PASS" for r in results),

        # Count the number of flagged rules.
        flag_count=sum(r.status == "FLAG" for r in results),

        # Count the number of rules with unresolved outcomes.
        unknown_count=sum(r.status == "UNKNOWN" for r in results),
    )