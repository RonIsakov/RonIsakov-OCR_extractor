"""
Validation service for quality checking and accuracy tracking.

Validates Pydantic-validated form data for quality issues (format violations,
Israeli-specific rules) without blocking. Calculates accuracy and completeness scores.
"""

from datetime import datetime
from typing import Dict, Any, List
from src.models.schemas import Form283Data
from src.models.validation import ValidationReport, FieldCorrection
from src.utils.logger import get_logger

logger = get_logger(__name__)


class ValidationService:
    """
    Service for validating Pydantic-validated form data.

    Calculates:
    - Accuracy: Percentage of fields that pass quality checks
    - Completeness: Percentage of fields filled
    - Quality Issues: List of fields that don't meet format requirements
    """

    def validate(
        self,
        validated_form: Form283Data
    ) -> ValidationReport:
        """
        Validate Pydantic-validated form data for quality issues.

        Args:
            validated_form: Validated Form283Data instance

        Returns:
            ValidationReport with accuracy, completeness, and quality issues
        """
        logger.info("Starting quality validation")

        validated_dict = validated_form.model_dump(by_alias=True)
        quality_issues = self._check_field_quality(validated_dict)

        total_filled = self._count_non_empty_fields(validated_dict)
        fields_with_issues = len(quality_issues)
        fields_without_issues = total_filled - fields_with_issues
        accuracy_score = (fields_without_issues / total_filled * 100) if total_filled > 0 else 100.0

        filled_count, total_count = validated_form.get_filled_fields_count()
        completeness_score = validated_form.get_completeness_percentage()
        missing_fields = self._get_missing_fields(validated_dict)

        summary = (
            f"Validation passed. {filled_count}/{total_count} fields filled ({completeness_score:.1f}%). "
            f"{fields_without_issues}/{total_filled} data fields accurate ({accuracy_score:.1f}%). "
            f"{fields_with_issues} quality issue(s) detected."
        )

        logger.info(
            "Validation complete",
            accuracy=accuracy_score,
            completeness=completeness_score,
            quality_issues_count=fields_with_issues
        )

        return ValidationReport(
            accuracy_score=accuracy_score,
            completeness_score=completeness_score,
            corrections=quality_issues,
            filled_count=filled_count,
            total_count=total_count,
            missing_fields=missing_fields,
            summary=summary
        )

    def _count_non_empty_fields(self, data_dict: Dict[str, Any]) -> int:
        """Count total non-empty fields in the data (including nested)."""
        count = 0

        for value in data_dict.values():
            if isinstance(value, dict):
                count += self._count_non_empty_fields(value)
            elif value:
                count += 1

        return count

    def _get_missing_fields(self, data_dict: Dict[str, Any], prefix: str = "") -> List[str]:
        """Get list of missing (empty) field names."""
        missing = []

        for key, value in data_dict.items():
            full_key = f"{prefix}.{key}" if prefix else key

            if isinstance(value, dict):
                nested_missing = self._get_missing_fields(value, full_key)
                missing.extend(nested_missing)
            elif not value:
                missing.append(full_key)

        return missing

    def _check_field_quality(
        self,
        validated_dict: Dict[str, Any]
    ) -> List[FieldCorrection]:
        """
        Check validated data for quality issues.

        Checks format violations
        (non-numeric characters, wrong lengths, invalid ranges, OCR failures).

        Returns:
            List of quality issues
        """
        quality_issues = []

        id_number = validated_dict.get("מספר זהות", "")
        if id_number:
            cleaned_id = id_number.replace(" ", "").replace("-", "")

            if not cleaned_id.isdigit():
                quality_issues.append(
                    FieldCorrection(
                        field="מספר זהות",
                        value=id_number,
                        reason="ID number contains non-numeric characters"
                    )
                )
            elif len(cleaned_id) != 9:
                quality_issues.append(
                    FieldCorrection(
                        field="מספר זהות",
                        value=id_number,
                        reason=f"ID number should be 9 digits, got {len(cleaned_id)}"
                    )
                )

        # Check last name for OCR failure pattern
        last_name = validated_dict.get("שם משפחה", "")
        if last_name and "ס״ב" in last_name:
            quality_issues.append(
                FieldCorrection(
                    field="שם משפחה",
                    value=last_name,
                    reason="OCR failed to read last name - detected 'ס״ב' marker instead of actual name"
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
                        value=mobile,
                        reason="Phone number contains non-numeric characters"
                    )
                )
            elif not cleaned_mobile.startswith("0"):
                quality_issues.append(
                    FieldCorrection(
                        field="טלפון נייד",
                        value=mobile,
                        reason="Israeli phone numbers should start with 0"
                    )
                )
            elif cleaned_mobile.startswith("05") and len(cleaned_mobile) != 10:
                quality_issues.append(
                    FieldCorrection(
                        field="טלפון נייד",
                        value=mobile,
                        reason=f"Mobile phone should be 10 digits, got {len(cleaned_mobile)}"
                    )
                )

        # Check landline phone quality
        landline = validated_dict.get("טלפון קווי", "")
        if landline:
            cleaned_landline = landline.replace("-", "").replace(" ", "").replace("(", "").replace(")", "")

            if not cleaned_landline.isdigit():
                quality_issues.append(
                    FieldCorrection(
                        field="טלפון קווי",
                        value=landline,
                        reason="Phone number contains non-numeric characters"
                    )
                )
            elif not cleaned_landline.startswith("0"):
                quality_issues.append(
                    FieldCorrection(
                        field="טלפון קווי",
                        value=landline,
                        reason="Israeli phone numbers should start with 0"
                    )
                )
            elif not cleaned_landline.startswith("05") and cleaned_landline.startswith("0") and len(cleaned_landline) != 9:
                quality_issues.append(
                    FieldCorrection(
                        field="טלפון קווי",
                        value=landline,
                        reason=f"Landline phone should be 9 digits, got {len(cleaned_landline)}"
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
                            value=day,
                            reason="Day must be numeric"
                        )
                    )
                elif day and day.isdigit() and not (1 <= int(day) <= 31):
                    quality_issues.append(
                        FieldCorrection(
                            field=f"{date_field_name}.יום",
                            value=day,
                            reason=f"Day must be 1-31, got {day}"
                        )
                    )

                # Check month
                month = date_field.get("חודש", "")
                if month and not month.isdigit():
                    quality_issues.append(
                        FieldCorrection(
                            field=f"{date_field_name}.חודש",
                            value=month,
                            reason="Month must be numeric"
                        )
                    )
                elif month and month.isdigit() and not (1 <= int(month) <= 12):
                    quality_issues.append(
                        FieldCorrection(
                            field=f"{date_field_name}.חודש",
                            value=month,
                            reason=f"Month must be 1-12, got {month}"
                        )
                    )

                # Check year
                year = date_field.get("שנה", "")
                if year and not year.isdigit():
                    quality_issues.append(
                        FieldCorrection(
                            field=f"{date_field_name}.שנה",
                            value=year,
                            reason="Year must be numeric"
                        )
                    )
                elif year and year.isdigit():
                    year_int = int(year)
                    current_year = datetime.now().year
                    if not (1900 <= year_int <= current_year + 1):
                        quality_issues.append(
                            FieldCorrection(
                                field=f"{date_field_name}.שנה",
                                value=year,
                                reason=f"Year should be 1900-{current_year+1}, got {year}"
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
                            value=postal_code,
                            reason="Postal code must be numeric"
                        )
                    )
                elif not (5 <= len(cleaned_postal) <= 7):
                    quality_issues.append(
                        FieldCorrection(
                            field="כתובת.מיקוד",
                            value=postal_code,
                            reason=f"Postal code should be 5-7 digits, got {len(cleaned_postal)}"
                        )
                    )

        return quality_issues