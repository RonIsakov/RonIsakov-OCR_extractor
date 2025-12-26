"""
Pydantic models for validation reports.

This module defines models for quality validation of Pydantic-validated form data,
providing accuracy and completeness metrics based on format compliance.
"""

from typing import List, Optional
from pydantic import BaseModel, Field


class FieldCorrection(BaseModel):
    """
    Represents a quality issue detected in a validated field.

    Reports format violations (e.g., ID not 9 digits, phone missing leading zero,
    OCR failure patterns) without modifying the data.
    """

    field: str = Field(description="Field name with quality issue")
    value: str = Field(description="Field value that has the quality issue")
    reason: str = Field(description="Description of the quality issue")

    class Config:
        """Pydantic model configuration."""
        json_schema_extra = {
            "example": {
                "field": "טלפון נייד",
                "value": "502474947",
                "reason": "Israeli phone numbers should start with 0"
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
                        "value": "502474947",
                        "reason": "Israeli phone numbers should start with 0"
                    }
                ],
                "filled_count": 18,
                "total_count": 21,
                "missing_fields": ["טלפון קווי", "כניסה", "תא דואר"],
                "summary": "Validation passed. 18/21 fields filled (85.7%). 17/18 data fields accurate (94.4%). 1 quality issue(s) detected."
            }
        }