"""
Pydantic models for validation reports.

This module defines models for quality validation of Pydantic-validated form data,
providing accuracy and completeness metrics based on format compliance.
"""

from typing import List, Optional
from pydantic import BaseModel, Field


class FieldCorrection(BaseModel):
    """
    Represents a quality issue found in a field.

    Quality issues are format violations like non-numeric ID, wrong phone length, etc.
    """

    field: str = Field(description="Field name with quality issue")
    raw_value: str = Field(description="Field value")
    validated_value: str = Field(description="Field value (same as raw_value)")
    reason: str = Field(description="Explanation of quality issue")
    auto_corrected: bool = Field(default=False, description="Always False for quality issues")
    issue_type: str = Field(
        default="quality",
        description="Always 'quality'"
    )

    class Config:
        """Pydantic model configuration."""
        json_schema_extra = {
            "example": {
                "field": "mobilePhone",
                "raw_value": "6502474947",
                "validated_value": "0502474947",
                "reason": "Israeli mobile phone numbers must start with 05",
                "auto_corrected": True,
                "issue_type": "correction"
            }
        }


class ValidationReport(BaseModel):
    """
    Quality validation report for form data.

    Provides:
    - Accuracy: Percentage of filled fields without quality issues
    - Completeness: Percentage of fields that are filled
    - Corrections: List of quality issues found
    """

    accuracy_score: float = Field(
        ge=0, le=100,
        description="(fields without quality issues / total filled fields) * 100"
    )

    completeness_score: float = Field(
        ge=0, le=100,
        description="(filled fields / total fields) * 100"
    )

    corrections: List[FieldCorrection] = Field(
        default_factory=list,
        description="List of quality issues found"
    )

    filled_count: int = Field(
        description="Number of fields that have data"
    )

    total_count: int = Field(
        description="Total number of fields in the form"
    )

    missing_fields: List[str] = Field(
        default_factory=list,
        description="List of field names that are empty"
    )

    summary: str = Field(
        description="Human-readable summary of validation results"
    )

    class Config:
        """Pydantic model configuration."""
        json_schema_extra = {
            "example": {
                "accuracy_score": 94.4,
                "completeness_score": 85.7,
                "corrections": [
                    {
                        "field": "טלפון נייד",
                        "raw_value": "502474947",
                        "validated_value": "502474947",
                        "reason": "Israeli phone numbers should start with 0",
                        "auto_corrected": False,
                        "issue_type": "quality"
                    }
                ],
                "filled_count": 18,
                "total_count": 21,
                "missing_fields": ["טלפון קווי", "כניסה", "תא דואר"],
                "summary": "Validation passed. 18/21 fields filled (85.7%). 17/18 data fields accurate (94.4%). 1 quality issue(s) detected."
            }
        }