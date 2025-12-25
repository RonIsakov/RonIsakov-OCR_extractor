"""
Prompt templates for Azure OpenAI field extraction.

This module contains carefully engineered prompts for extracting structured data
from Israeli National Insurance Form 283 OCR text.
"""

# System message for the extraction model
SYSTEM_MESSAGE = """You are an expert at extracting structured data from Hebrew and English forms.
You specialize in processing Israeli National Insurance forms with high accuracy.

Your task is to:
1. Read OCR-extracted text from Form 283 (Israeli workplace injury form)
2. Extract all fields into the exact JSON structure provided
3. Preserve Hebrew text exactly as it appears in the OCR
4. Use empty strings ("") for any missing or unreadable fields
5. Handle OCR errors gracefully (minor typos are acceptable)
6. Format dates as separate day/month/year fields
7. Clean phone numbers (remove dashes/spaces but preserve digits)

Important rules:
- NEVER invent data that's not in the OCR text
- If a field is unclear or missing, use empty string ""
- Preserve Hebrew characters exactly (do not transliterate)
- Return ONLY valid JSON matching the schema provided"""


def get_extraction_prompt(ocr_text: str) -> str:
    """
    Generate the complete extraction prompt for GPT-4o.

    Args:
        ocr_text: The OCR-extracted text from Form 283

    Returns:
        Complete prompt with schema, rules, and OCR text
    """

    # Complete JSON schema with Hebrew field names (matching Pydantic aliases)
    json_schema = """{
  "שם משפחה": "",
  "שם פרטי": "",
  "מספר זהות": "",
  "מין": "",
  "תאריך לידה": {
    "יום": "",
    "חודש": "",
    "שנה": ""
  },
  "כתובת": {
    "רחוב": "",
    "מספר בית": "",
    "כניסה": "",
    "דירה": "",
    "ישוב": "",
    "מיקוד": "",
    "תא דואר": ""
  },
  "טלפון קווי": "",
  "טלפון נייד": "",
  "סוג העבודה": "",
  "תאריך הפגיעה": {
    "יום": "",
    "חודש": "",
    "שנה": ""
  },
  "שעת הפגיעה": "",
  "מקום התאונה": "",
  "כתובת מקום התאונה": "",
  "תיאור התאונה": "",
  "האיבר שנפגע": "",
  "חתימה": "",
  "תאריך מילוי הטופס": {
    "יום": "",
    "חודש": "",
    "שנה": ""
  },
  "תאריך קבלת הטופס בקופה": {
    "יום": "",
    "חודש": "",
    "שנה": ""
  },
  "למילוי ע\\"י המוסד הרפואי": {
    "חבר בקופת חולים": "",
    "מהות התאונה": "",
    "אבחנות רפואיות": ""
  }
}"""

    # Field extraction rules and context
    extraction_rules = """
LANGUAGE HANDLING (CRITICAL):
- Form 283 may be filled in HEBREW, ENGLISH, or MIXED (both languages)
- OCR text may contain field labels and values in either language
- ALWAYS output JSON with Hebrew field names (as shown in schema above)
- Preserve field VALUES in their original language from the OCR
  Examples:
    • "Last Name: Cohen" → "שם משפחה": "Cohen"
    • "שם משפחה: כהן" → "שם משפחה": "כהן"
    • "firstName: David" → "שם פרטי": "David"

FIELD LABEL VARIATIONS:
You may encounter field labels in multiple formats. Map ALL variations to Hebrew JSON keys:
- Hebrew: "שם משפחה", "תאריך לידה", "כתובת", "מספר זהות"
- English: "Last Name", "Date of Birth", "Address", "ID Number"
- CamelCase: "lastName", "firstName", "dateOfBirth", "idNumber"
- Mixed: "last name", "First Name", etc.

Regardless of label language or format, map to Hebrew JSON keys shown in schema.

FIELD EXTRACTION RULES:

1. **Personal Information (פרטי התובע / Personal Details)**:
   - שם משפחה (lastName / Last Name): Last name in original language
   - שם פרטי (firstName / First Name): First name in original language
   - מספר זהות (idNumber / ID Number): Israeli ID number (9 digits, may appear as 9 or 10 digits in OCR)
   - מין (gender / Gender): Either "זכר" (male) / "נקבה" (female) OR "Male" / "Female"
   - תאריך לידה (dateOfBirth / Date of Birth): Birth date as {יום/day, חודש/month, שנה/year}

2. **Address (כתובת / Address)**:
   - רחוב (street / Street): Street name in original language
   - מספר בית (houseNumber / House Number): House number
   - כניסה (entrance / Entrance): Entrance number (if applicable)
   - דירה (apartment / Apartment): Apartment number (if applicable)
   - ישוב (city / City): City/settlement name in original language
   - מיקוד (postalCode / Postal Code): Postal code (6 digits)
   - תא דואר (poBox / PO Box): PO Box (if applicable, usually empty)

3. **Contact Information (פרטי קשר / Contact Details)**:
   - טלפון קווי (landlinePhone / Landline Phone): Landline phone (9 digits, starts with 0)
   - טלפון נייד (mobilePhone / Mobile Phone): Mobile phone (10 digits, starts with 05)
   - Remove dashes and spaces from phone numbers

4. **Injury Details (פרטי התאונה / Accident Details)**:
   - סוג העבודה (jobType / Job Type): Type of work/occupation in original language
   - תאריך הפגיעה (dateOfInjury / Date of Injury): Injury date as {יום/day, חודש/month, שנה/year}
   - שעת הפגיעה (timeOfInjury / Time of Injury): Time of injury (HH:MM format)
   - מקום התאונה (accidentLocation / Accident Location): Location type
     Hebrew: "במפעל" (at factory), "ת. דרכים בעבודה" (traffic accident), "אחר" (other)
     English: "At workplace", "Traffic accident", "Other"
   - כתובת מקום התאונה (accidentAddress / Accident Address): Full address where accident occurred
   - תיאור התאונה (accidentDescription / Accident Description): Description in original language
   - האיבר שנפגע (injuredBodyPart / Injured Body Part): Body part in original language

5. **Declaration (הצהרה / Declaration)**:
   - חתימה (signature / Signature): Name of person signing (usually same as applicant name)

6. **Form Metadata (מטא-דאטה של הטופס / Form Metadata)**:
   - תאריך מילוי הטופס (formFillingDate / Form Filling Date): Date form was filled
   - תאריך קבלת הטופס בקופה (formReceiptDateAtClinic / Form Receipt Date): Date received at clinic

7. **Medical Institution Fields (למילוי ע"י המוסד הרפואי / Medical Institution Fields)**:
   - חבר בקופת חולים (healthFundMember / Health Fund): One of:
     Hebrew: "כללית", "מכבי", "מאוחדת", "לאומית"
     English: "Clalit", "Maccabi", "Meuhedet", "Leumit"
   - מהות התאונה (natureOfAccident / Nature of Accident): Type of accident
   - אבחנות רפואיות (medicalDiagnoses / Medical Diagnoses): Medical diagnoses (often empty)

DATE FORMAT RULES:
- Dates in OCR appear in various formats: "DDMMYYYY", "DD.MM.YYYY", "DD/MM/YYYY", or separate fields
- Extract to separate fields: {"יום": "DD", "חודש": "MM", "שנה": "YYYY"}
- Keep leading zeros (e.g., "02" not "2")
- If date is missing or unclear, use empty strings for all three fields
- Accept both Hebrew and English month names (convert to numbers)

FORM 283 LAYOUT CONTEXT:
- Form has 2 pages (page 1 has data, page 2 has instructions in Hebrew)
- Hebrew text reads right-to-left
- OCR may include labels like "שם משפחה", "ת. ז." (ID), "תאריך לידה", etc.
- English forms may have "Last Name", "ID Number", "Date of Birth", etc.
- Look for the actual data VALUES, not the field LABELS
- Selected checkboxes appear as ":selected:", unselected as ":unselected:"

CRITICAL RULES:
- Use empty string "" for missing fields, NOT null or undefined
- Preserve text in original language (Hebrew stays Hebrew, English stays English)
- If OCR has obvious errors but meaning is clear, extract the intended value
- Do not add explanatory text or comments in the JSON output
- Accept bilingual forms (some fields Hebrew, some English) - extract each in its original language
"""

    # Construct the final prompt
    prompt = f"""Extract all fields from the following Israeli National Insurance Form 283 OCR text.
This form may be in HEBREW, ENGLISH, or MIXED languages.

**REQUIRED JSON SCHEMA** (use this exact structure with Hebrew keys):
{json_schema}

{extraction_rules}

**OCR TEXT TO PROCESS**:
---
{ocr_text}
---

Return ONLY the JSON object with extracted data. Use empty strings ("") for missing fields.
Remember: Hebrew field names in output, but preserve VALUE language from OCR."""

    return prompt


# Example usage documentation
USAGE_EXAMPLE = """
# How to use these prompts with Azure OpenAI:

from openai import AzureOpenAI
from src.config.prompts import SYSTEM_MESSAGE, get_extraction_prompt

client = AzureOpenAI(
    api_key="your_key",
    api_version="2024-02-15-preview",
    azure_endpoint="your_endpoint"
)

# Extract OCR text first
ocr_text = "... extracted text from Form 283 ..."

# Call GPT-4o with JSON mode
response = client.chat.completions.create(
    model="gpt-4o",
    messages=[
        {"role": "system", "content": SYSTEM_MESSAGE},
        {"role": "user", "content": get_extraction_prompt(ocr_text)}
    ],
    response_format={"type": "json_object"},  # Enable JSON mode
    temperature=0.1  # Low temperature for consistency
)

# Get extracted JSON
extracted_json = response.choices[0].message.content

# Parse and validate with Pydantic
import json
from src.models.schemas import Form283Data

data_dict = json.loads(extracted_json)
form_data = Form283Data(**data_dict)  # Validates against schema
"""
