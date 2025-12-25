"""
Validation service for comparing raw GPT-4o extraction vs Pydantic validated output.

This module provides simple delta comparison to track accuracy and completeness.
"""

from typing import Dict, Any, List
from src.models.schemas import Form283Data
from src.models.validation import ValidationReport, FieldCorrection
from src.utils.logger import get_logger

logger = get_logger(__name__)


class ValidationService:
    """
    Service for comparing raw extraction vs validated output.

    Calculates:
    - Accuracy: Percentage of fields GPT-4o extracted correctly (no corrections)
    - Completeness: Percentage of fields filled
    - Corrections: List of fields that Pydantic auto-corrected
    """

    def validate(
        self,
        raw_extracted: Dict[str, Any],
        validated_form: Form283Data
    ) -> ValidationReport:
        """
        Compare raw GPT-4o output with Pydantic validated output.

        Args:
            raw_extracted: Raw JSON from GPT-4o (before Pydantic validation)
            validated_form: Validated Form283Data instance

        Returns:
            ValidationReport with accuracy, completeness, and corrections
        """
        logger.info("Starting validation delta comparison")

        # Get validated data as dict (using aliases for Hebrew field names)
        validated_dict = validated_form.model_dump(by_alias=True)

        # Find corrections from Pydantic auto-corrections
        corrections = self._find_corrections(raw_extracted, validated_dict)

        # Add quality issues (fields that don't meet format rules)
        quality_issues = self._check_field_quality(validated_dict)
        corrections.extend(quality_issues)  # Combine both types

        # Calculate accuracy
        total_fields = self._count_non_empty_fields(validated_dict)
        unchanged_fields = total_fields - len(corrections)
        accuracy_score = (unchanged_fields / total_fields * 100) if total_fields > 0 else 100.0

        # Get completeness from existing methods
        filled_count, total_count = validated_form.get_filled_fields_count()
        completeness_score = validated_form.get_completeness_percentage()

        # Calculate missing fields
        missing_fields = self._get_missing_fields(validated_dict)

        # Generate summary
        auto_corrections_count = len([c for c in corrections if c.auto_corrected])
        quality_issues_count = len([c for c in corrections if not c.auto_corrected])

        summary = (
            f"Validation passed. {filled_count}/{total_count} fields filled ({completeness_score:.1f}%). "
            f"{unchanged_fields}/{total_fields} data fields accurate ({accuracy_score:.1f}%). "
            f"{auto_corrections_count} field(s) auto-corrected, {quality_issues_count} quality issue(s) detected."
        )

        logger.info(
            "Validation complete",
            accuracy=accuracy_score,
            completeness=completeness_score,
            corrections_count=len(corrections)
        )

        return ValidationReport(
            is_valid=True,  # If we got here, Pydantic accepted the data
            accuracy_score=accuracy_score,
            completeness_score=completeness_score,
            corrections=corrections,
            filled_count=filled_count,
            total_count=total_count,
            missing_fields=missing_fields,
            summary=summary
        )

    def _find_corrections(
        self,
        raw_dict: Dict[str, Any],
        validated_dict: Dict[str, Any]
    ) -> List[FieldCorrection]:
        """
        Find fields that were corrected by Pydantic validation.

        Args:
            raw_dict: Raw GPT-4o output
            validated_dict: Pydantic validated output

        Returns:
            List of FieldCorrection objects
        """
        corrections = []

        # Compare all fields
        for key in validated_dict.keys():
            raw_value = raw_dict.get(key)
            validated_value = validated_dict.get(key)

            # Skip if both are None or empty
            if not raw_value and not validated_value:
                continue

            # Handle nested dicts (dates, address, medical fields)
            if isinstance(validated_value, dict):
                nested_corrections = self._compare_nested(key, raw_value, validated_value)
                corrections.extend(nested_corrections)
            # Handle simple values
            elif str(raw_value) != str(validated_value):
                corrections.append(
                    FieldCorrection(
                        field=key,
                        raw_value=str(raw_value) if raw_value else "",
                        validated_value=str(validated_value) if validated_value else "",
                        reason=self._get_reason(key, raw_value, validated_value),
                        auto_corrected=True
                    )
                )

        return corrections

    def _compare_nested(
        self,
        parent_key: str,
        raw_value: Any,
        validated_value: Dict[str, Any]
    ) -> List[FieldCorrection]:
        """Compare nested dictionary fields."""
        corrections = []

        if not isinstance(raw_value, dict):
            return corrections

        for nested_key, validated_nested in validated_value.items():
            raw_nested = raw_value.get(nested_key)

            if str(raw_nested) != str(validated_nested):
                full_key = f"{parent_key}.{nested_key}"
                corrections.append(
                    FieldCorrection(
                        field=full_key,
                        raw_value=str(raw_nested) if raw_nested else "",
                        validated_value=str(validated_nested) if validated_nested else "",
                        reason=self._get_reason(full_key, raw_nested, validated_nested),
                        auto_corrected=True
                    )
                )

        return corrections

    def _get_reason(self, field: str, raw_value: Any, validated_value: Any) -> str:
        """Generate human-readable reason for correction."""
        # Phone number corrections
        if "טלפון" in field or "Phone" in field:
            if "נייד" in field or "mobile" in field.lower():
                return "Israeli mobile phone numbers must start with 05"
            return "Phone number format corrected"

        # ID number corrections
        if "זהות" in field or "idNumber" in field:
            return "Israeli ID number normalized to 9 digits"

        # Date corrections
        if "תאריך" in field or "date" in field.lower():
            return "Date format normalized"

        # Address corrections
        if "כתובת" in field or "address" in field.lower():
            return "Address field normalized"

        # Generic
        return "Field value normalized during validation"

    def _count_non_empty_fields(self, data_dict: Dict[str, Any]) -> int:
        """Count total non-empty fields in the data (including nested)."""
        count = 0

        for value in data_dict.values():
            if isinstance(value, dict):
                # Count nested fields
                count += self._count_non_empty_fields(value)
            elif value:  # Non-empty value
                count += 1

        return count

    def _get_missing_fields(self, data_dict: Dict[str, Any], prefix: str = "") -> List[str]:
        """Get list of missing (empty) field names."""
        missing = []

        for key, value in data_dict.items():
            full_key = f"{prefix}.{key}" if prefix else key

            if isinstance(value, dict):
                # Check nested fields
                nested_missing = self._get_missing_fields(value, full_key)
                missing.extend(nested_missing)
            elif not value:  # Empty value
                missing.append(full_key)

        return missing

    def _check_field_quality(
        self,
        validated_dict: Dict[str, Any]
    ) -> List[FieldCorrection]:
        """
        Check validated data for quality issues.

        These are issues that Pydantic couldn't auto-correct,
        like non-numeric characters in numeric fields.

        Returns:
            List of quality issues (marked as issue_type='quality')
        """
        quality_issues = []

        # Check ID number quality
        id_number = validated_dict.get("מספר זהות", "")
        if id_number:
            # Strip separators for checking (but keep original value in report)
            cleaned_id = id_number.replace(" ", "").replace("-", "")

            if not cleaned_id.isdigit():
                quality_issues.append(
                    FieldCorrection(
                        field="מספר זהות",
                        raw_value=id_number,
                        validated_value=id_number,
                        reason="ID number contains non-numeric characters",
                        auto_corrected=False,
                        issue_type="quality"
                    )
                )
            elif len(cleaned_id) != 9:
                quality_issues.append(
                    FieldCorrection(
                        field="מספר זהות",
                        raw_value=id_number,
                        validated_value=id_number,
                        reason=f"ID number should be 9 digits, got {len(cleaned_id)}",
                        auto_corrected=False,
                        issue_type="quality"
                    )
                )

        # Check mobile phone quality
        mobile = validated_dict.get("טלפון נייד", "")
        if mobile:
            # Strip separators for checking (but keep original value in report)
            cleaned_mobile = mobile.replace("-", "").replace(" ", "").replace("(", "").replace(")", "")

            if not cleaned_mobile.isdigit():
                quality_issues.append(
                    FieldCorrection(
                        field="טלפון נייד",
                        raw_value=mobile,
                        validated_value=mobile,
                        reason="Phone number contains non-numeric characters",
                        auto_corrected=False,
                        issue_type="quality"
                    )
                )
            elif not cleaned_mobile.startswith("0"):
                quality_issues.append(
                    FieldCorrection(
                        field="טלפון נייד",
                        raw_value=mobile,
                        validated_value=mobile,
                        reason="Israeli phone numbers should start with 0",
                        auto_corrected=False,
                        issue_type="quality"
                    )
                )
            elif cleaned_mobile.startswith("05") and len(cleaned_mobile) != 10:
                quality_issues.append(
                    FieldCorrection(
                        field="טלפון נייד",
                        raw_value=mobile,
                        validated_value=mobile,
                        reason=f"Mobile phone should be 10 digits, got {len(cleaned_mobile)}",
                        auto_corrected=False,
                        issue_type="quality"
                    )
                )

        # Check landline phone quality
        landline = validated_dict.get("טלפון קווי", "")
        if landline:
            # Strip separators for checking (but keep original value in report)
            cleaned_landline = landline.replace("-", "").replace(" ", "").replace("(", "").replace(")", "")

            if not cleaned_landline.isdigit():
                quality_issues.append(
                    FieldCorrection(
                        field="טלפון קווי",
                        raw_value=landline,
                        validated_value=landline,
                        reason="Phone number contains non-numeric characters",
                        auto_corrected=False,
                        issue_type="quality"
                    )
                )
            elif not cleaned_landline.startswith("0"):
                quality_issues.append(
                    FieldCorrection(
                        field="טלפון קווי",
                        raw_value=landline,
                        validated_value=landline,
                        reason="Israeli phone numbers should start with 0",
                        auto_corrected=False,
                        issue_type="quality"
                    )
                )
            elif not cleaned_landline.startswith("05") and cleaned_landline.startswith("0") and len(cleaned_landline) != 9:
                quality_issues.append(
                    FieldCorrection(
                        field="טלפון קווי",
                        raw_value=landline,
                        validated_value=landline,
                        reason=f"Landline phone should be 9 digits, got {len(cleaned_landline)}",
                        auto_corrected=False,
                        issue_type="quality"
                    )
                )

        # Check date field quality
        for date_field_name in ["תאריך לידה", "תאריך הפגיעה", "תאריך מילוי הטופס", "תאריך קבלת הטופס בקופה"]:
            date_field = validated_dict.get(date_field_name, {})
            if isinstance(date_field, dict):
                # Check day
                day = date_field.get("יום", "")
                if day and not day.isdigit():
                    quality_issues.append(
                        FieldCorrection(
                            field=f"{date_field_name}.יום",
                            raw_value=day,
                            validated_value=day,
                            reason="Day must be numeric",
                            auto_corrected=False,
                            issue_type="quality"
                        )
                    )
                elif day and day.isdigit() and not (1 <= int(day) <= 31):
                    quality_issues.append(
                        FieldCorrection(
                            field=f"{date_field_name}.יום",
                            raw_value=day,
                            validated_value=day,
                            reason=f"Day must be 1-31, got {day}",
                            auto_corrected=False,
                            issue_type="quality"
                        )
                    )

                # Check month
                month = date_field.get("חודש", "")
                if month and not month.isdigit():
                    quality_issues.append(
                        FieldCorrection(
                            field=f"{date_field_name}.חודש",
                            raw_value=month,
                            validated_value=month,
                            reason="Month must be numeric",
                            auto_corrected=False,
                            issue_type="quality"
                        )
                    )
                elif month and month.isdigit() and not (1 <= int(month) <= 12):
                    quality_issues.append(
                        FieldCorrection(
                            field=f"{date_field_name}.חודש",
                            raw_value=month,
                            validated_value=month,
                            reason=f"Month must be 1-12, got {month}",
                            auto_corrected=False,
                            issue_type="quality"
                        )
                    )

                # Check year
                year = date_field.get("שנה", "")
                if year and not year.isdigit():
                    quality_issues.append(
                        FieldCorrection(
                            field=f"{date_field_name}.שנה",
                            raw_value=year,
                            validated_value=year,
                            reason="Year must be numeric",
                            auto_corrected=False,
                            issue_type="quality"
                        )
                    )
                elif year and year.isdigit():
                    year_int = int(year)
                    current_year = 2025  # Could use datetime.now().year but keeping simple
                    if not (1900 <= year_int <= current_year + 1):
                        quality_issues.append(
                            FieldCorrection(
                                field=f"{date_field_name}.שנה",
                                raw_value=year,
                                validated_value=year,
                                reason=f"Year should be 1900-{current_year+1}, got {year}",
                                auto_corrected=False,
                                issue_type="quality"
                            )
                        )

        # Check postal code quality
        address = validated_dict.get("כתובת", {})
        if isinstance(address, dict):
            postal_code = address.get("מיקוד", "")
            if postal_code:
                # Strip separators for checking (but keep original value in report)
                cleaned_postal = postal_code.replace(" ", "").replace("-", "")

                if not cleaned_postal.isdigit():
                    quality_issues.append(
                        FieldCorrection(
                            field="כתובת.מיקוד",
                            raw_value=postal_code,
                            validated_value=postal_code,
                            reason="Postal code must be numeric",
                            auto_corrected=False,
                            issue_type="quality"
                        )
                    )
                elif not (5 <= len(cleaned_postal) <= 7):
                    quality_issues.append(
                        FieldCorrection(
                            field="כתובת.מיקוד",
                            raw_value=postal_code,
                            validated_value=postal_code,
                            reason=f"Postal code should be 5-7 digits, got {len(cleaned_postal)}",
                            auto_corrected=False,
                            issue_type="quality"
                        )
                    )

        return quality_issues
