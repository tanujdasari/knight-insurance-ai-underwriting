# ============================================================
# IMPORTS
# ============================================================

# dataclass automatically creates an initializer for
# classes primarily used to store data.
from dataclasses import dataclass

# Import the final underwriting decision model.
from models.rules import UnderwritingDecision

# Import the structured AI extraction model.
from models.submission import SubmissionExtraction


# ============================================================
# 1. REVIEW CONTENT DATA MODEL
# ============================================================

@dataclass
class ReviewContent:
    """
    Stores the two outputs generated for an underwriting review.

    summary:
        Internal underwriting review summary.

    broker_email:
        Draft email requesting additional information
        or communicating the initial review status.
    """

    # Internal summary for the underwriting team.
    summary: str

    # Broker follow-up email draft.
    broker_email: str


# ============================================================
# 2. BUSINESS FIELD DISPLAY LABELS
# ============================================================

# Maps internal Python field names to readable labels.
#
# Example:
# "business_name" -> "Business name"
#
# These labels are used in the underwriting summary
# and broker follow-up email.
FIELD_LABELS = {
    "business_name": "Business name",
    "requested_effective_date": "Requested effective date",
    "garaging_state": "Garaging state",
    "operations_description": "Operations description",
    "declared_vehicle_count": "Declared vehicle count",
    "schedule_vehicle_count": "Scheduled vehicle count",
    "operating_radius_miles": "Operating radius",
    "hazardous_materials": "Hazardous materials",
    "loss_runs_present": "Loss runs",
}


# ============================================================
# 3. GENERATE UNDERWRITING REVIEW CONTENT
# ============================================================

def generate_review_content(
    extraction: SubmissionExtraction,
    decision: UnderwritingDecision,
) -> ReviewContent:
    """
    Generate the underwriting summary and broker email.

    Inputs:
        extraction:
            Structured field values produced by AI extraction
            and deterministic document processing.

        decision:
            Results of underwriting rules R1–R5.

    Processing:
        1. Read validated business information.
        2. Build the underwriting summary.
        3. Include all rule evaluation results.
        4. Identify unresolved extraction fields.
        5. Generate recommended next steps.
        6. Prepare a broker follow-up email.
        7. Avoid duplicate requests for the same issue.

    Returns:
        ReviewContent containing:
        - summary
        - broker_email

    Note:
        This function uses predefined Python templates.
        It does not make an additional LLM API call.
    """

    # Access the extracted business fields.
    fields = extraction.fields

    # --------------------------------------------------------
    # STEP 1: HELPER FUNCTION FOR DISPLAY VALUES
    # --------------------------------------------------------

    def known_value(name, default="Not confirmed"):
        """
        Return a readable value for a resolved field.

        If the field is unavailable, unresolved, or has
        no value, return the default text.

        Boolean values are converted to Yes or No.
        """

        # Retrieve the field without raising a KeyError
        # when the requested field does not exist.
        result = fields.get(name)

        if result is None:
            return default

        # Only display values that have been resolved.
        if result.state != "KNOWN":
            return default

        # Avoid displaying None as a valid business value.
        if result.value is None:
            return default

        # Convert boolean values into readable answers.
        if isinstance(result.value, bool):
            return "Yes" if result.value else "No"

        # Convert other validated values into strings.
        return str(result.value)

    # Retrieve the business name for the summary and email.
    business_name = known_value("business_name")

    # ========================================================
    # STEP 2: BUILD UNDERWRITING SUMMARY
    # ========================================================

    # Each list element represents one line of the summary.
    # Empty strings create blank lines for readability.
    summary_lines = [
        "COMMERCIAL AUTO UNDERWRITING SUMMARY",
        "",
        f"Business: {business_name}",
        f"Requested effective date: {known_value('requested_effective_date')}",
        f"Garaging state: {known_value('garaging_state')}",
        f"Operations: {known_value('operations_description')}",
        f"Declared vehicles: {known_value('declared_vehicle_count')}",
        f"Scheduled vehicles: {known_value('schedule_vehicle_count')}",
        f"Operating radius (miles): {known_value('operating_radius_miles')}",
        f"Hazardous materials: {known_value('hazardous_materials')}",
        f"Loss runs present: {known_value('loss_runs_present')}",
        "",
        f"Automated rule status: {decision.overall_status}",
        "",
        "UNDERWRITING RULE RESULTS",
    ]

    # --------------------------------------------------------
    # STEP 3: INCLUDE R1–R5 RULE RESULTS
    # --------------------------------------------------------

    # Add each rule's ID, name, status, and explanation.
    #
    # Example:
    # R3 - Operating Radius: FLAG -
    # Operating radius 180.0 exceeds 150 miles.
    for rule in decision.rules:
        summary_lines.append(
            f"{rule.rule_id} - {rule.rule_name}: "
            f"{rule.status} - {rule.reason}"
        )

    # Add the total number of PASS, FLAG, and UNKNOWN rules.
    summary_lines.extend([
        "",
        f"Passed: {decision.pass_count}",
        f"Flagged: {decision.flag_count}",
        f"Unknown: {decision.unknown_count}",
    ])

    # ========================================================
    # STEP 4: IDENTIFY UNRESOLVED EXTRACTION FIELDS
    # ========================================================

    # Store fields that require additional verification.
    unresolved_fields = []

    # Examine every field in the extracted submission.
    for field_name, result in fields.items():

        # Fields in these states are not fully resolved:
        #
        # CONFLICT = Different source documents disagree.
        # MISSING  = Required information was not found.
        # INVALID  = Extracted information failed validation.
        if result.state in ("CONFLICT", "MISSING", "INVALID"):
            unresolved_fields.append(
                (field_name, result)
            )

    # Add a separate section for field validation results.
    summary_lines.extend([
        "",
        "FIELD VALIDATION RESULTS",
    ])

    if unresolved_fields:

        # Include each unresolved field in the summary.
        for field_name, result in unresolved_fields:

            # Use a readable field label when available.
            # Otherwise, create one from the field name.
            label = FIELD_LABELS.get(
                field_name,
                field_name.replace("_", " ").title(),
            )

            summary_lines.append(
                f"- {label}: {result.state}"
            )

            # When sources conflict, preserve each candidate
            # value and its original document reference.
            if result.state == "CONFLICT":
                for candidate in result.candidates:
                    summary_lines.append(
                        f"  Candidate: {candidate.raw_value} "
                        f"(Source: {candidate.evidence.source_file}, "
                        f"{candidate.evidence.locator})"
                    )

    else:
        # Indicate that no extraction fields are unresolved.
        summary_lines.append(
            "- All extracted fields are resolved."
        )

    # ========================================================
    # STEP 5: GENERATE RECOMMENDED NEXT STEPS
    # ========================================================

    summary_lines.extend([
        "",
        "RECOMMENDED NEXT STEPS",
    ])

    # Collect rules that require additional attention.
    unresolved_rules = [
        rule
        for rule in decision.rules
        if rule.status in ("FLAG", "UNKNOWN")
    ]

    # Add recommendations based on unresolved rules.
    if unresolved_rules:
        for rule in unresolved_rules:
            summary_lines.append(
                f"- Review {rule.rule_id}: {rule.reason}"
            )

    # Add recommendations for unresolved extraction fields.
    if unresolved_fields:
        for field_name, result in unresolved_fields:

            label = FIELD_LABELS.get(
                field_name,
                field_name.replace("_", " ").title(),
            )

            summary_lines.append(
                f"- Resolve {label} ({result.state})."
            )

    # If all rules pass and all fields are resolved,
    # recommend proceeding with normal human review.
    if not unresolved_rules and not unresolved_fields:
        summary_lines.append(
            "- All automated rules passed and extracted "
            "fields are resolved. Proceed with normal "
            "human underwriting review."
        )

    else:
        # Outstanding issues must be reviewed by a human.
        summary_lines.append(
            "- Human review is required before "
            "outstanding issues can be considered resolved."
        )

    # ========================================================
    # STEP 6: CREATE BROKER FOLLOW-UP EMAIL
    # ========================================================

    # Prepare the email subject, greeting, and introduction.
    email_lines = [
        "Subject: Commercial Auto Submission - Information Request",
        "",
        "Hello,",
        "",
        "Thank you for submitting the commercial auto "
        "insurance application.",
    ]

    # Include the business name when it has been confirmed.
    if business_name != "Not confirmed":
        email_lines.append(
            f"We are reviewing the submission for {business_name}."
        )

    # ========================================================
    # STEP 7: REQUEST MISSING OR CONFLICTING INFORMATION
    # ========================================================

    if unresolved_rules or unresolved_fields:

        # Introduce the list of information requests.
        email_lines.extend([
            "",
            "To continue our review, please clarify "
            "the following items:",
            "",
        ])

        # Map underwriting rules to their underlying fields.
        #
        # This mapping prevents duplicate email requests.
        #
        # Example:
        # If R3 is UNKNOWN because operating_radius_miles
        # is CONFLICT, request clarification of the field
        # instead of listing the same issue twice.
        rule_fields = {
            "R1": {"business_name", "requested_effective_date"},
            "R2": {"declared_vehicle_count", "schedule_vehicle_count"},
            "R3": {"operating_radius_miles"},
            "R4": {"hazardous_materials"},
            "R5": {"loss_runs_present"},
        }

        # Create a set containing unresolved field names.
        # Sets allow efficient membership and overlap checks.
        unresolved_names = {name for name, _ in unresolved_fields}

        # Store the final requests to include in the email.
        requests = []

        # ----------------------------------------------------
        # STEP 7A: ADD RULE-LEVEL REQUESTS
        # ----------------------------------------------------

        for rule in unresolved_rules:

            # Identify the fields associated with this rule.
            covered = rule_fields.get(rule.rule_id, set())

            # Skip the rule-level request if an unresolved
            # field-level request already covers the issue.
            #
            # The rule remains visible in the internal summary.
            if covered & unresolved_names:
                continue

            # Add a rule-level request when no field-level
            # request covers the issue.
            requests.append(f"{rule.rule_name}: {rule.reason}")

        # ----------------------------------------------------
        # STEP 7B: ADD FIELD-LEVEL REQUESTS
        # ----------------------------------------------------

        for field_name, result in unresolved_fields:

            # Convert the field name into a readable label.
            label = FIELD_LABELS.get(
                field_name, field_name.replace("_", " ").title()
            )

            if result.state == "CONFLICT":
                # Request confirmation when source values disagree.
                request = (
                    f"Please confirm the correct {label.lower()} because "
                    "the submitted documents contain conflicting information."
                )

            elif result.state == "MISSING":
                # Request information that was not provided.
                request = f"Please provide the missing {label.lower()}."

            else:
                # Request a valid replacement for invalid information.
                request = f"Please provide a valid {label.lower()}."

            requests.append(request)

        # ----------------------------------------------------
        # STEP 7C: NUMBER THE EMAIL REQUESTS
        # ----------------------------------------------------

        # enumerate(..., 1) numbers requests starting at 1.
        #
        # Example:
        # 1. Please provide the missing garaging state.
        # 2. Please confirm the correct operating radius.
        for number, request in enumerate(requests, 1):
            email_lines.append(f"{number}. {request}")

        # Ask the broker for supporting documentation.
        email_lines.extend([
            "",
            "Please provide the relevant clarification "
            "or supporting documentation.",
        ])

    else:
        # When no issues are identified, explain that
        # the submission still requires human review.
        email_lines.extend([
            "",
            "Our initial automated checks did not identify "
            "any outstanding rule or field-validation issues. "
            "The submission remains subject to underwriter review.",
        ])

    # ========================================================
    # STEP 8: ADD EMAIL CLOSING
    # ========================================================

    email_lines.extend([
        "",
        "Thank you for your assistance.",
        "",
        "Best regards,",
        "Underwriting Team",
    ])

    # ========================================================
    # STEP 9: RETURN GENERATED REVIEW CONTENT
    # ========================================================

    # Join the summary lines using newline characters.
    # Join the email lines in the same way.
    #
    # Both outputs are returned in one ReviewContent object.
    return ReviewContent(
        summary="\n".join(summary_lines),
        broker_email="\n".join(email_lines),
    )