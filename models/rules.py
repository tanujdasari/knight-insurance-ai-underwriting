# Import Literal to restrict a field to specific allowed values.
from typing import Literal

# BaseModel provides data validation and structured data models.
# Field allows us to define default values for model attributes.
from pydantic import BaseModel, Field

# Import Evidence to track the source documents supporting rule results.
from models.submission import Evidence


# ============================================================
# RuleResult
# Represents the evaluation result of one underwriting rule.
# Each rule (R1–R5) produces its own result.
# ============================================================

class RuleResult(BaseModel):

    # Unique identifier of the underwriting rule.
    # Example: "R1", "R2", "R3", "R4", or "R5".
    rule_id: str

    # Human-readable name describing the underwriting rule.
    # Example: "Vehicle Count Validation".
    rule_name: str

    # Final evaluation status of the individual rule.
    # PASS    = Rule conditions are satisfied.
    # FLAG    = A problem or rule violation was identified.
    # UNKNOWN = Insufficient or unresolved information.
    # Literal ensures that only these three values are accepted.
    status: Literal["PASS", "FLAG", "UNKNOWN"]

    # Explanation of why the rule received its status.
    # Helps underwriters understand the evaluation outcome.
    reason: str

    # Supporting evidence used during rule evaluation.
    # May contain references to uploaded documents or source text.
    #
    # default_factory=list creates a separate empty list
    # for each RuleResult instance when no evidence is provided.
    evidence: list[Evidence] = Field(default_factory=list)


# ============================================================
# UnderwritingDecision
# Represents the overall underwriting review outcome.
# Combines all individual rule results into one decision.
# ============================================================

class UnderwritingDecision(BaseModel):

    # Overall submission review status.
    #
    # READY_FOR_REVIEW = All required underwriting rules passed.
    # NEEDS_REVIEW     = At least one rule was flagged or unknown.
    #
    # This status indicates review readiness,
    # NOT final insurance approval or rejection.
    overall_status: Literal[
        "READY_FOR_REVIEW", "NEEDS_REVIEW"
    ]

    # Collection of individual underwriting rule results.
    # Typically contains the results of rules R1 through R5.
    rules: list[RuleResult]

    # Total number of rules that returned PASS.
    pass_count: int

    # Total number of rules that returned FLAG.
    flag_count: int

    # Total number of rules that returned UNKNOWN.
    unknown_count: int