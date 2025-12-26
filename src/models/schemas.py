"""
Pydantic models for Form 283 data validation and serialization.

This module defines the complete data structure for Israeli National Insurance
Form 283.
"""

from typing import Optional
from pydantic import BaseModel, Field, field_validator, model_validator


class DateField(BaseModel):
    """
    Represents a date in day/month/year format.

    All fields are strings to match the form's text-based input format.
    Empty strings are used for missing values.
    """
    day: str = Field(default="", alias="יום", description="Day (יום)")
    month: str = Field(default="", alias="חודש", description="Month (חודש)")
    year: str = Field(default="", alias="שנה", description="Year (שנה)")

    @field_validator('day', 'month', 'year', mode='before')
    @classmethod
    def convert_to_string(cls, v):
        """Convert numeric values to strings and handle None."""
        if v is None:
            return ""
        return str(v).strip()


    def is_empty(self) -> bool:
        """Check if all date fields are empty."""
        return self.day == "" and self.month == "" and self.year == ""

    def to_display_string(self) -> str:
        """Convert to display format (DD/MM/YYYY) or empty string."""
        if self.is_empty():
            return ""
        return f"{self.day}/{self.month}/{self.year}"

    class Config:
        """Pydantic model configuration."""
        populate_by_name = True  # Allow both alias and field name


class AddressField(BaseModel):
    """
    Represents a complete address in Israel.

    All fields are optional strings (empty strings for missing values).
    """
    street: str = Field(default="", alias="רחוב", description="Street name (רחוב)")
    houseNumber: str = Field(default="", alias="מספר בית", description="House number (מספר בית)")
    entrance: str = Field(default="", alias="כניסה", description="Entrance (כניסה)")
    apartment: str = Field(default="", alias="דירה", description="Apartment number (דירה)")
    city: str = Field(default="", alias="ישוב", description="City/Settlement (ישוב)")
    postalCode: str = Field(default="", alias="מיקוד", description="Postal code (מיקוד)")
    poBox: str = Field(default="", alias="תא דואר", description="PO Box (תא דואר)")

    @field_validator('*', mode='before')
    @classmethod
    def convert_to_string(cls, v):
        """Convert all values to strings and handle None."""
        if v is None:
            return ""
        return str(v).strip()

    def is_empty(self) -> bool:
        """Check if all address fields are empty."""
        return all([
            self.street == "",
            self.houseNumber == "",
            self.entrance == "",
            self.apartment == "",
            self.city == "",
            self.postalCode == "",
            self.poBox == ""
        ])

    def to_display_string(self) -> str:
        """Convert to display format."""
        if self.is_empty():
            return ""

        parts = []
        if self.street:
            street_part = self.street
            if self.houseNumber:
                street_part += f" {self.houseNumber}"
            if self.entrance:
                street_part += f" כניסה {self.entrance}"
            if self.apartment:
                street_part += f" דירה {self.apartment}"
            parts.append(street_part)

        if self.city:
            parts.append(self.city)

        if self.postalCode:
            parts.append(f"מיקוד {self.postalCode}")

        if self.poBox:
            parts.append(f"ת.ד. {self.poBox}")

        return ", ".join(parts)

    class Config:
        """Pydantic model configuration."""
        populate_by_name = True  # Allow both alias and field name


class MedicalInstitutionFields(BaseModel):
    """
    Fields filled by the medical institution (Part 5 of Form 283).
    """
    healthFundMember: str = Field(
        default="",
        alias="חבר בקופת חולים",
        description="Health fund membership (חבר בקופת חולים): כללית/מכבי/מאוחדת/לאומית"
    )
    natureOfAccident: str = Field(
        default="",
        alias="מהות התאונה",
        description="Nature of accident/location type (מהות התאונה)"
    )
    medicalDiagnoses: str = Field(
        default="",
        alias="אבחנות רפואיות",
        description="Medical diagnoses (אבחנות רפואיות)"
    )

    @field_validator('*', mode='before')
    @classmethod
    def convert_to_string(cls, v):
        """Convert all values to strings and handle None."""
        if v is None:
            return ""
        return str(v).strip()


class Form283Data(BaseModel):
    """
    Complete data model for Israeli National Insurance Form 283.

    This model represents the "Application for Medical Treatment for
    Self-Employed Work Injury" form used by the Israeli National Insurance Institute.

    All fields default to empty strings when not provided, as required by the specification.
    Hebrew field names are supported via aliases.
    """

    # Personal Information (Part 2)
    lastName: str = Field(
        default="",
        alias="שם משפחה",
        description="Last name (שם משפחה)"
    )
    firstName: str = Field(
        default="",
        alias="שם פרטי",
        description="First name (שם פרטי)"
    )
    idNumber: str = Field(
        default="",
        alias="מספר זהות",
        description="Israeli ID number (מספר זהות - 9 digits)"
    )
    gender: str = Field(
        default="",
        alias="מין",
        description="Gender (מין): זכר/נקבה"
    )
    dateOfBirth: DateField = Field(
        default_factory=DateField,
        alias="תאריך לידה",
        description="Date of birth (תאריך לידה)"
    )

    # Contact Information
    address: AddressField = Field(
        default_factory=AddressField,
        alias="כתובת",
        description="Full address (כתובת)"
    )
    landlinePhone: str = Field(
        default="",
        alias="טלפון קווי",
        description="Landline phone (טלפון קווי)"
    )
    mobilePhone: str = Field(
        default="",
        alias="טלפון נייד",
        description="Mobile phone (טלפון נייד)"
    )

    # Injury Details (Part 3)
    jobType: str = Field(
        default="",
        alias="סוג העבודה",
        description="Type of job/occupation (סוג העבודה)"
    )
    dateOfInjury: DateField = Field(
        default_factory=DateField,
        alias="תאריך הפגיעה",
        description="Date of injury (תאריך הפגיעה)"
    )
    timeOfInjury: str = Field(
        default="",
        alias="שעת הפגיעה",
        description="Time of injury (שעת הפגיעה)"
    )
    accidentLocation: str = Field(
        default="",
        alias="מקום התאונה",
        description="Accident location type (מקום התאונה): במפעל/ת. דרכים בעבודה/ת. דרכים בדרך לעבודה/מהעבודה/תאונה בדרך ללא רכב/אחר"
    )
    accidentAddress: str = Field(
        default="",
        alias="כתובת מקום התאונה",
        description="Address where accident occurred (כתובת מקום התאונה)"
    )
    accidentDescription: str = Field(
        default="",
        alias="תיאור התאונה",
        description="Description of circumstances (תיאור התאונה)"
    )
    injuredBodyPart: str = Field(
        default="",
        alias="האיבר שנפגע",
        description="Injured body part (האיבר שנפגע)"
    )

    # Declaration (Part 4)
    signature: str = Field(
        default="",
        alias="חתימה",
        description="Signature (חתימה)"
    )

    # Form Metadata
    formFillingDate: DateField = Field(
        default_factory=DateField,
        alias="תאריך מילוי הטופס",
        description="Date form was filled (תאריך מילוי הטופס)"
    )
    formReceiptDateAtClinic: DateField = Field(
        default_factory=DateField,
        alias="תאריך קבלת הטופס בקופה",
        description="Date form received at clinic (תאריך קבלת הטופס בקופה)"
    )

    # Medical Institution Fields (Part 5)
    medicalInstitutionFields: MedicalInstitutionFields = Field(
        default_factory=MedicalInstitutionFields,
        alias='למילוי ע"י המוסד הרפואי',
        description="Fields completed by medical institution (למילוי ע\"י המוסד הרפואי)"
    )

    @field_validator('lastName', 'firstName', 'idNumber', 'gender', 'landlinePhone',
                     'mobilePhone', 'jobType', 'timeOfInjury', 'accidentLocation',
                     'accidentAddress', 'accidentDescription', 'injuredBodyPart', 'signature',
                     mode='before')
    @classmethod
    def convert_to_string(cls, v):
        """Convert all string fields to strings and handle None."""
        if v is None:
            return ""
        return str(v).strip()

    def get_filled_fields_count(self) -> tuple[int, int]:
        """
        Calculate how many fields are filled vs total fields.

        Returns:
            (filled_count, total_count) tuple
        """
        total = 0
        filled = 0

        # Simple string fields
        simple_fields = [
            self.lastName, self.firstName, self.idNumber, self.gender,
            self.landlinePhone, self.mobilePhone, self.jobType,
            self.timeOfInjury, self.accidentLocation, self.accidentAddress,
            self.accidentDescription, self.injuredBodyPart, self.signature
        ]

        for field in simple_fields:
            total += 1
            if field and field != "":
                filled += 1

        # Date fields (count as 1 unit each)
        date_fields = [self.dateOfBirth, self.dateOfInjury,
                      self.formFillingDate, self.formReceiptDateAtClinic]
        for date_field in date_fields:
            total += 1
            if not date_field.is_empty():
                filled += 1

        # Address (count as 1 unit)
        total += 1
        if not self.address.is_empty():
            filled += 1

        # Medical institution fields (count individually)
        medical_fields = [
            self.medicalInstitutionFields.healthFundMember,
            self.medicalInstitutionFields.natureOfAccident,
            self.medicalInstitutionFields.medicalDiagnoses
        ]
        for field in medical_fields:
            total += 1
            if field and field != "":
                filled += 1

        return filled, total

    def get_completeness_percentage(self) -> float:
        """Calculate percentage of filled fields (0-100)."""
        filled, total = self.get_filled_fields_count()
        if total == 0:
            return 0.0
        return (filled / total) * 100

    class Config:
        """Pydantic model configuration."""
        populate_by_name = True  # Allow both alias and field name
        str_strip_whitespace = True  # Strip whitespace from strings
        validate_assignment = True  # Validate on assignment
        json_schema_extra = {
            "example": {
                "lastName": "טננבאום",
                "firstName": "יהודה",
                "idNumber": "877524563",
                "gender": "זכר",
                "dateOfBirth": {"day": "02", "month": "02", "year": "1995"},
                "address": {
                    "street": "הרמבם",
                    "houseNumber": "16",
                    "entrance": "1",
                    "apartment": "12",
                    "city": "אבן יהודה",
                    "postalCode": "312422",
                    "poBox": ""
                },
                "landlinePhone": "",
                "mobilePhone": "0502474947",
                "jobType": "מלצרות",
                "dateOfInjury": {"day": "16", "month": "04", "year": "2022"},
                "timeOfInjury": "19:00",
                "accidentLocation": "במפעל",
                "accidentAddress": "הורדים 8, תל אביב",
                "accidentDescription": "החלקתי בגלל שהרצפה הייתה רטובה ולא היה שום שלט שמזהיר",
                "injuredBodyPart": "יד שמאל",
                "signature": "טננבאום יהודה",
                "formFillingDate": {"day": "25", "month": "01", "year": "2023"},
                "formReceiptDateAtClinic": {"day": "02", "month": "02", "year": "1999"},
                "medicalInstitutionFields": {
                    "healthFundMember": "מכבי",
                    "natureOfAccident": "במפעל",
                    "medicalDiagnoses": ""
                }
            }
        }