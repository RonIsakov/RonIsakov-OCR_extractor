"""
Pydantic models for validation reports.

This module defines models for tracking the delta between GPT-4o raw extraction
and Pydantic validated output, providing accuracy and completeness metrics.
"""

from typing import List, Optional
from pydantic import BaseModel, Field


class FieldCorrection(BaseModel):
    """
    Represents a single field that was auto-corrected by Pydantic validation.

    Tracks the difference between raw GPT-4o extraction and validated output,
    helping users understand what was automatically fixed.
    """

    field: str = Field(description="Field name that was corrected")
    raw_value: str = Field(description="Original value from GPT-4o extraction")
    validated_value: str = Field(description="Corrected value after Pydantic validation")
    reason: str = Field(description="Explanation of why correction was needed")
    auto_corrected: bool = Field(default=True, description="Whether field was auto-corrected")
    issue_type: str = Field(
        default="correction",
        description="Type of issue: 'correction' (auto-fixed) or 'quality' (not fixable)"
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
    Complete validation report comparing raw extraction vs validated output.

    Provides:
    - Accuracy: How many fields GPT-4o extracted correctly (no corrections needed)
    - Completeness: Percentage of fields that are filled
    - Corrections list: What Pydantic auto-fixed
    """

    is_valid: bool = Field(
        description="Overall validation status (True if Pydantic accepted the data)"
    )

    accuracy_score: float = Field(
        ge=0, le=100,
        description="Accuracy percentage: (unchanged fields / total non-empty fields) × 100"
    )

    completeness_score: float = Field(
        ge=0, le=100,
        description="Completeness percentage: (filled fields / total fields) × 100"
    )

    corrections: List[FieldCorrection] = Field(
        default_factory=list,
        description="List of fields that were auto-corrected by Pydantic"
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
                "is_valid": True,
                "accuracy_score": 94.4,
                "completeness_score": 85.7,
                "corrections": [
                    {
                        "field": "mobilePhone",
                        "raw_value": "6502474947",
                        "validated_value": "0502474947",
                        "reason": "Israeli mobile phone numbers must start with 05",
                        "auto_corrected": True
                    }
                ],
                "filled_count": 18,
                "total_count": 21,
                "missing_fields": ["landlinePhone", "entrance", "poBox"],
                "summary": "Validation passed. 18/21 fields filled (85.7%). 17/18 data fields accurate (94.4%). 1 field auto-corrected."
            }
        }