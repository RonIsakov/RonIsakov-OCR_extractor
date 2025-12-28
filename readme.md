# Form 283 Extraction System

AI-powered system for extracting and validating structured data from Israeli National Insurance Form 283 (workplace injury forms) using Azure Document Intelligence and GPT-4o.

![Python Version](https://img.shields.io/badge/python-3.10%2B-blue)
![Azure](https://img.shields.io/badge/Azure-Document_Intelligence-0089D6)
![Azure](https://img.shields.io/badge/Azure-OpenAI_GPT--4o-0089D6)

## Features

- **Multi-language Support**: Processes forms filled in Hebrew, English, or mixed languages
- **Azure Document Intelligence OCR**: Extracts text from PDF documents using prebuilt-layout model
- **GPT-4o Field Extraction**: Structured data extraction with JSON mode for reliable output
- **Pydantic Schema Validation**: Type-safe data models with Hebrew field aliases
- **Quality Validation**: Automated accuracy and completeness scoring with Israeli format validation
- **Web Interface**: User-friendly Streamlit UI for document upload and result visualization
- **Structured Logging**: Comprehensive logging with structlog (console and file output)
- **Error Handling**: Graceful handling of OCR errors and missing fields

## Table of Contents

- [Prerequisites](#prerequisites)
- [Installation](#installation)
- [Configuration](#configuration)
- [Usage](#usage)
  - [Streamlit Web UI](#streamlit-web-ui)
  - [Python API](#python-api)
- [Project Structure](#project-structure)
- [Architecture](#architecture)
- [Output Format](#output-format)
- [Quality Validation](#quality-validation)
- [Testing](#testing)
- [Logging](#logging)
- [Known Limitations](#known-limitations)

## Prerequisites

- **Python**: 3.10 or higher
- **Azure Resources**:
  - Azure Document Intelligence instance with prebuilt-layout model support
  - Azure OpenAI instance with GPT-4o deployment
  - API version: `2024-02-15-preview` or later
- **Git**: For cloning the repository (optional)

## Installation

```bash
# 1. Clone the repository
git clone <repository-url>
cd to the cloned directory


# 2. Create and activate virtual environment
python -m venv venv

# On Windows:
venv\Scripts\activate
venv\Scripts\activate

# On macOS/Linux:
source venv/bin/activate
source venv/bin/activate

# 3. Install dependencies
pip install -r requirements.txt
```

## Configuration

### Step 1: Create `.env` File

Create a `.env` file in the project root directory:

```env
# Azure Document Intelligence Configuration
AZURE_DI_ENDPOINT=https://<your-resource>.cognitiveservices.azure.com/
AZURE_DI_KEY=<your_document_intelligence_key>

# Azure OpenAI Configuration
AZURE_OPENAI_ENDPOINT=https://<your-resource>.openai.azure.com/
AZURE_OPENAI_KEY=<your_openai_key>
AZURE_OPENAI_API_VERSION=2024-02-15-preview
AZURE_OPENAI_DEPLOYMENT_NAME=gpt-4o

# Optional Application Settings (defaults shown)
LOG_LEVEL=INFO
MAX_FILE_SIZE_MB=10
DATA_INPUT_DIR=data/input
DATA_OUTPUT_DIR=data/output
LOGS_DIR=logs
```

## Usage

### Streamlit Web UI

The way to use the system:

```bash
streamlit run src/ui/streamlit_app.py
```

Then:
1. Open your browser to `http://localhost:8501`
2. Upload a PDF file (max 10MB)
3. Click "Process Document"
4. View the results:
   - Extracted JSON with all form fields
   - Validation report with accuracy and completeness scores
   - Quality issues detected (if any)
   - Missing fields list
5. Download outputs (JSON, validation report, OCR text)

### Python API

For programmatic usage:

```python
from src.main import FormProcessor

# Initialize processor
processor = FormProcessor()

# Process a document
form_data, metadata, validation_report = processor.process_document(
    file_path="path/to/form283.pdf",
    save_output=True,
    output_dir="data/output"
)

# Access validation metrics
print(f"Completeness: {validation_report.completeness_score:.1f}%")
print(f"Accuracy: {validation_report.accuracy_score:.1f}%")
print(f"Quality issues: {len(validation_report.corrections)}")
print(f"Total tokens used: {metadata['total_tokens']}")

# Access extracted data with English field names
print(f"Last Name: {form_data.lastName}")
print(f"ID Number: {form_data.idNumber}")

# Access with Hebrew field names
hebrew_data = form_data.model_dump(by_alias=True)
print(f"שם משפחה: {hebrew_data['שם משפחה']}")
```

## Project Structure

```
Home-Assignment-GenAI-KPMG/
├── src/
│   ├── config/
│   │   ├── settings.py          # Pydantic settings management
│   │   └── prompts.py           # GPT-4o extraction prompts
│   ├── services/
│   │   ├── document_intelligence.py  # Azure DI OCR service
│   │   ├── openai_service.py        # Azure OpenAI field extraction
│   │   └── validation_service.py    # Quality validation & scoring
│   ├── models/
│   │   ├── schemas.py           # Form283Data Pydantic models
│   │   └── validation.py        # ValidationReport models
│   ├── ui/
│   │   └── streamlit_app.py     # Web interface
│   ├── utils/
│   │   └── logger.py            # Structured logging setup
│   └── main.py                  # FormProcessor orchestrator
├── tests/                        # Integration and unit tests
├── data/
│   ├── input/                   # Upload directory
│   └── output/
│       ├── ocr_text/            # Extracted OCR text
│       ├── extracted_json/      # Form data JSON
│       └── validation_reports/  # Validation reports
├── logs/                         # Application logs
├── requirements.txt             # Python dependencies
├── .env                         # Azure credentials (not in git)
└── README.md                    # This file
```

### Core Components

- **[FormProcessor](src/main.py)**: Main orchestrator that coordinates the entire pipeline
- **[DocumentIntelligenceService](src/services/document_intelligence.py)**: PDF OCR extraction using Azure Document Intelligence prebuilt-layout model
- **[OpenAIService](src/services/openai_service.py)**: Field extraction from OCR text using GPT-4o with JSON mode
- **[ValidationService](src/services/validation_service.py)**: Quality checking for Israeli-specific format rules
- **[Form283Data](src/models/schemas.py)**: Pydantic model with 20+ fields and Hebrew aliases

## Architecture

### Processing Pipeline

```
┌─────────────┐
│ PDF Upload  │
└──────┬──────┘
       │
       ▼
┌─────────────────────────────┐
│ Document Intelligence (OCR) │  ← Azure DI prebuilt-layout
└──────────┬──────────────────┘
           │ Raw OCR Text
           ▼
┌─────────────────────────────┐
│   GPT-4o Field Extraction   │  ← Azure OpenAI JSON mode
└──────────┬──────────────────┘
           │ Raw JSON
           ▼
┌─────────────────────────────┐
│   Pydantic Validation       │  ← Schema enforcement
└──────────┬──────────────────┘
           │ Validated Form283Data
           ▼
┌─────────────────────────────┐
│   Quality Validation        │  ← Format checks, scoring
└──────────┬──────────────────┘
           │
           ▼
┌─────────────────────────────┐
│  Output Generation          │  ← JSON, reports, OCR text
└─────────────────────────────┘
```

### Data Models

**Form283Data**: Main form structure with nested models
- `DateField`: day/month/year components (יום, חודש, שנה)
- `AddressField`: Israeli address structure (רחוב, מספר בית, כניסה, דירה, ישוב, מיקוד, תא דואר)
- `MedicalFields`: Medical institution data (חבר בקופת חולים, מהות התאונה, אבחנות רפואיות)

**ValidationReport**: Quality metrics
- `accuracy_score`: Percentage of filled fields without quality issues
- `completeness_score`: Percentage of total fields that are filled
- `corrections`: List of FieldCorrection objects
- `missing_fields`: List of empty field names
- `summary`: Human-readable validation summary

**FieldCorrection**: Quality issue tracking
- `field`: Field name with quality issue
- `value`: Field value that has the issue
- `reason`: Description of the quality issue

## Output Format

The system generates three types of output files:

### 1. OCR Text (`data/output/ocr_text/{filename}_extracted.txt`)

Raw OCR-extracted text with metadata header:
```
=== Document OCR Extraction ===
File: form283_sample.pdf
Extracted at: 2025-01-15 14:30:45
Pages: 2
Text length: 1,847 characters
===

[OCR text content...]
```

### 2. Form Data (`data/output/extracted_json/{filename}_form_data.json`)

Structured JSON with Hebrew field names:
```json
{
  "שם משפחה": "כהן",
  "שם פרטי": "דוד",
  "מספר זהות": "123456789",
  "תאריך לידה": {
    "יום": "15",
    "חודש": "03",
    "שנה": "1985"
  },
  "כתובת": {
    "רחוב": "הרצל",
    "מספר בית": "25",
    "ישוב": "תל אביב",
    "מיקוד": "6473301"
  },
  "טלפון נייד": "0501234567"
}
```

### 3. Validation Report (`data/output/validation_reports/{filename}_validation.json`)

Quality metrics and issue tracking:
```json
{
  "accuracy_score": 95.5,
  "completeness_score": 78.3,
  "filled_count": 18,
  "total_count": 23,
  "corrections": [
    {
      "field": "טלפון נייד",
      "value": "650-123-4567",
      "reason": "Israeli phone numbers should start with 0"
    }
  ],
  "missing_fields": [
    "תאריך קבלת הטופס בקופה",
    "למילוי ע\"י המוסד הרפואי.אבחנות רפואיות"
  ],
  "summary": "Validation passed. 18/23 fields filled (78.3%). 21/22 data fields accurate (95.5%). 1 quality issue(s) detected."
}
```

## Logging

The system uses `structlog` for structured logging:

- **Console Output**: Formatted for readability during development
- **File Output**: JSON format in `logs/app_{YYYY-MM-DD}.log`
- **Log Levels**: DEBUG, INFO, WARNING, ERROR (configurable via `LOG_LEVEL` env var)
- **Metadata Included**: Timestamps, service names, file names, token counts, error details

Example log entry:
```json
{
  "event": "Document analysis completed",
  "level": "info",
  "timestamp": "2025-01-15T14:30:45.123456Z",
  "logger": "src.services.document_intelligence",
  "file_name": "form283_sample.pdf",
  "pages": 2,
  "text_length": 1847
}
```

## Known Limitations

- **File Format**: Supports PDF files only (no JPG/PNG)
- **File Size**: Maximum 10MB per document
- **Azure Dependency**: Requires active Azure subscriptions with sufficient quotas
- **OCR Quality**: Best results with high-quality scanned documents; poor scans may affect accuracy
- **GPT-4o Variability**: Field extraction accuracy depends on OCR quality and form legibility

## Dependencies

Core dependencies (see [requirements.txt](requirements.txt) for complete list):

- `azure-ai-documentintelligence>=1.0.0b1` - Azure Document Intelligence SDK
- `openai>=1.12.0` - Azure OpenAI SDK
- `pydantic>=2.5.0` - Data validation and serialization
- `streamlit>=1.30.0` - Web UI framework
- `structlog>=24.0.0` - Structured logging
- `python-dotenv>=1.0.0` - Environment variable management

---
