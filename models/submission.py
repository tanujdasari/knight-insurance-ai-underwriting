# ============================================================
# IMPORTS
# ============================================================

# Any allows a field to store different data types,
# such as strings, integers, booleans, or None.
#
# Literal restricts a field to a predefined set of values.
from typing import Any, Literal

# BaseModel provides structured data validation using Pydantic.
#
# Field allows us to configure model attributes,
# including default values and default factories.
from pydantic import BaseModel, Field


# ============================================================
# FIELD NAMES
# ============================================================

# List of business fields that the AI extraction process
# is expected to identify from submitted insurance documents.
#
# These fields are used during underwriting review
# and deterministic rule evaluation (R1–R5).
#
# The first eight represent business information.
# schedule_vehicle_count is derived from the vehicle schedule.
FIELD_NAMES = [
    "business_name",              # Name of the business requesting insurance.
    "requested_effective_date",   # Requested insurance policy start date.
    "garaging_state",             # State where the vehicles are primarily garaged.
    "operations_description",     # Description of the business operations.
    "declared_vehicle_count",     # Number of vehicles declared by the applicant.
    "operating_radius_miles",     # Maximum operating radius in miles.
    "hazardous_materials",        # Whether the business transports hazardous materials.
    "loss_runs_present",          # Whether historical loss-run documents are provided.
    "schedule_vehicle_count",     # Vehicle count determined from the submitted schedule.
]


# ============================================================
# EVIDENCE MODEL
# ============================================================

# Stores the original source information supporting
# an extracted field or underwriting rule.
#
# Evidence helps underwriters trace AI-generated values
# back to the documents from which they were extracted.
class Evidence(BaseModel):

    # Name of the source document containing the information.
    # Example: "broker_email.txt" or "vehicle_schedule.csv".
    source_file: str

    # Location of the information within the source document.
    # Example: "Page 2", "Row 4", or "Email body".
    locator: str

    # Exact text excerpt or observation supporting the value.
    # This allows reviewers to verify the extracted information.
    excerpt_or_observation: str


# ============================================================
# CANDIDATE MODEL
# ============================================================

# Represents one possible value extracted for a business field.
#
# Multiple candidates may exist when different documents
# provide different values for the same field.
#
# Example:
# Broker email: Operating radius = 80 miles.
# Application: Operating radius = 180 miles.
#
# Both values can be preserved as candidates
# so the conflict can be reviewed by an underwriter.
class Candidate(BaseModel):

    # Original value extracted from the source document.
    # Stored as text to preserve the source representation.
    raw_value: str

    # Evidence identifying where this candidate originated.
    evidence: Evidence


# ============================================================
# FIELD RESULT MODEL
# ============================================================

# Represents the extraction result for one business field.
#
# Stores the resolved value, extraction state,
# supporting evidence, candidate values, and review notes.
class FieldResult(BaseModel):

    # Final extracted or human-corrected value.
    #
    # Any supports different data types:
    # business_name            -> string
    # declared_vehicle_count   -> integer
    # hazardous_materials      -> boolean
    #
    # Defaults to None when no value is available.
    value: Any = None

    # Current extraction state of the field.
    #
    # KNOWN    = A usable value has been identified.
    # MISSING  = No value was found.
    # CONFLICT = Multiple sources provide conflicting values.
    # INVALID  = A value was found but is not valid.
    #
    # Literal ensures only these four states are accepted.
    #
    # The default state is MISSING.
    state: Literal[
        "KNOWN", "MISSING", "CONFLICT", "INVALID"
    ] = "MISSING"

    # Stores all candidate values identified for this field.
    #
    # Useful for detecting and investigating conflicting values.
    #
    # default_factory=list ensures each FieldResult
    # receives its own independent list.
    candidates: list[Candidate] = Field(default_factory=list)

    # Stores supporting source evidence for this field.
    #
    # Evidence allows reviewers to verify where
    # the extracted information originated.
    evidence: list[Evidence] = Field(default_factory=list)

    # Stores additional extraction notes or warnings.
    #
    # Examples:
    # - "Conflicting values found in two documents."
    # - "Vehicle count could not be verified."
    notes: list[str] = Field(default_factory=list)

    # Indicates whether a human reviewer has overridden
    # the AI-extracted value.
    #
    # False = No human override has been recorded.
    # True  = A human override has been applied.
    #
    # The override workflow is responsible for updating
    # this flag and maintaining the associated audit history.
    human_override: bool = False


# ============================================================
# SUBMISSION EXTRACTION MODEL
# ============================================================

# Represents the complete AI extraction result
# for one commercial auto insurance submission.
#
# Combines all extracted business fields with information
# about the AI model and extraction status.
class SubmissionExtraction(BaseModel):

    # Dictionary containing the extraction result
    # for each business field.
    #
    # Key   = Business field name.
    # Value = FieldResult object.
    #
    # Example:
    # {
    #     "business_name": FieldResult(...),
    #     "operating_radius_miles": FieldResult(...)
    # }
    fields: dict[str, FieldResult]

    # Name of the AI model used during extraction.
    # Example: "gpt-4.1-mini".
    model_name: str

    # Status of the overall extraction operation.
    #
    # Example: "success".
    #
    # This is a string field; permitted values are not
    # restricted by this Pydantic model.
    extraction_status: str