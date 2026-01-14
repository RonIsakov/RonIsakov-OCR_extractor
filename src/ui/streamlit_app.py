"""
Streamlit UI for Form 283 Document Extraction System.

This app provides a user-friendly interface for:
- Uploading PDF documents
- Extracting structured data with AI
- Viewing validation reports
- Downloading results as JSON
"""

import streamlit as st
import json
import sys
from pathlib import Path
from io import BytesIO

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.main import FormProcessor
from src.models.schemas import Form283Data
from src.models.validation import ValidationReport
from src.utils.logger import setup_logging
from src.config.settings import get_settings

# Initialize logging
settings = get_settings()
setup_logging(log_level=settings.LOG_LEVEL, logs_dir=settings.LOGS_DIR)


# Page configuration
st.set_page_config(
    page_title="Form 283 Extractor",
    page_icon="📄",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for Hebrew text and styling
st.markdown("""
<style>
    .hebrew-text {
        direction: rtl;
        text-align: right;
        font-family: Arial, sans-serif;
    }

    .upload-box {
        border: 2px dashed #cccccc;
        border-radius: 10px;
        padding: 40px;
        text-align: center;
        background-color: #f9f9f9;
    }

    .metric-card {
        background-color: #f0f2f6;
        padding: 20px;
        border-radius: 10px;
        margin: 10px 0;
    }

    .success-box {
        background-color: #d4edda;
        border: 1px solid #c3e6cb;
        color: #155724;
        padding: 15px;
        border-radius: 5px;
        margin: 10px 0;
    }

    .warning-box {
        background-color: #fff3cd;
        border: 1px solid #ffeaa7;
        color: #856404;
        padding: 15px;
        border-radius: 5px;
        margin: 10px 0;
    }

    .error-box {
        background-color: #f8d7da;
        border: 1px solid #f5c6cb;
        color: #721c24;
        padding: 15px;
        border-radius: 5px;
        margin: 10px 0;
    }

    .stDownloadButton button {
        background-color: #4285f4;
        color: white;
        border-radius: 5px;
    }
</style>
""", unsafe_allow_html=True)


def initialize_session_state():
    """Initialize session state variables."""
    if 'processed' not in st.session_state:
        st.session_state.processed = False
    if 'form_data' not in st.session_state:
        st.session_state.form_data = None
    if 'validation_report' not in st.session_state:
        st.session_state.validation_report = None
    if 'metadata' not in st.session_state:
        st.session_state.metadata = None


def render_header():
    """Render the application header."""
    st.title("📄 Form 283 To JSON")
    st.markdown("""
    ### Convert PDF documents into JSON instantly
    Extract PDF data to structured JSON format instantly with AI-powered extraction
    """)


def render_sidebar():
    """Render the sidebar with information and instructions."""
    with st.sidebar:
        st.header("ℹ️ About")
        st.markdown("""
        This tool extracts structured data from Israeli National Insurance Form 283.

        **Supported formats:**
        - PDF documents
        """)

        st.header("📋 Instructions")
        st.markdown("""
        1. Upload a Form 283 document (PDF)
        2. Click "Process Document"
        3. Review extracted data and validation report
        4. Download JSON results

        **Note:** Processing takes 15-30 seconds depending on document complexity.
        """)


def save_uploaded_file(uploaded_file) -> Path:
    """Save uploaded file to temporary location."""
    temp_dir = Path("data/temp")
    temp_dir.mkdir(parents=True, exist_ok=True)

    temp_file_path = temp_dir / uploaded_file.name
    with open(temp_file_path, "wb") as f:
        f.write(uploaded_file.getbuffer())

    return temp_file_path


def render_validation_summary(validation_report: ValidationReport):
    """Render validation summary metrics."""
    st.markdown("### 📊 Validation Summary")

    col1, col2, col3 = st.columns(3)

    with col1:
        accuracy_color = "🟢" if validation_report.accuracy_score >= 95 else "🟡" if validation_report.accuracy_score >= 80 else "🔴"
        st.metric(
            label="Accuracy Score",
            value=f"{validation_report.accuracy_score:.1f}%",
            delta=f"{accuracy_color}"
        )

    with col2:
        completeness_color = "🟢" if validation_report.completeness_score >= 80 else "🟡" if validation_report.completeness_score >= 60 else "🔴"
        st.metric(
            label="Completeness Score",
            value=f"{validation_report.completeness_score:.1f}%",
            delta=f"{completeness_color}"
        )

    with col3:
        st.metric(
            label="Fields Filled",
            value=f"{validation_report.filled_count}/{validation_report.total_count}"
        )

    # Summary message
    if validation_report.accuracy_score >= 95 and validation_report.completeness_score >= 80:
        st.markdown(f'<div class="success-box">✅ {validation_report.summary}</div>', unsafe_allow_html=True)
    elif validation_report.accuracy_score >= 80 or validation_report.completeness_score >= 60:
        st.markdown(f'<div class="warning-box">⚠️ {validation_report.summary}</div>', unsafe_allow_html=True)
    else:
        st.markdown(f'<div class="warning-box">⚠️ {validation_report.summary}</div>', unsafe_allow_html=True)


def render_quality_issues(validation_report: ValidationReport):
    """Render quality issues if any."""
    if len(validation_report.corrections) > 0:
        st.markdown("### ⚠️ Quality Issues Detected")

        for i, issue in enumerate(validation_report.corrections, 1):
            with st.expander(f"Issue #{i}: {issue.field}"):
                st.markdown(f"**Field:** `{issue.field}`")
                st.markdown(f"**Value:** `{issue.value}`")
                st.markdown(f"**Issue:** {issue.reason}")

    if len(validation_report.missing_fields) > 0:
        with st.expander(f"📝 Missing Fields ({len(validation_report.missing_fields)})"):
            for field in validation_report.missing_fields:
                st.markdown(f"- {field}")


def render_raw_json(form_data: Form283Data):
    """Render raw JSON viewer."""
    st.markdown("### 🔍 Raw JSON Output")

    form_dict = form_data.model_dump(by_alias=True)
    json_str = json.dumps(form_dict, ensure_ascii=False, indent=2)

    st.code(json_str, language="json")


def render_download_buttons(form_data: Form283Data, validation_report: ValidationReport, metadata: dict):
    """Render download buttons for JSON files."""
    st.markdown("### 💾 Download Results")

    col1, col2 = st.columns(2)

    # Extracted data JSON
    with col1:
        form_dict = form_data.model_dump(by_alias=True)
        json_str = json.dumps(form_dict, ensure_ascii=False, indent=2)

        st.download_button(
            label="📥 Download Form Data (JSON)",
            data=json_str,
            file_name="form_283_extracted_data.json",
            mime="application/json"
        )

    # Validation report JSON
    with col2:
        report_dict = {
            "processing_metadata": metadata,
            "validation_report": validation_report.model_dump()
        }
        report_str = json.dumps(report_dict, ensure_ascii=False, indent=2)

        st.download_button(
            label="📥 Download Validation Report (JSON)",
            data=report_str,
            file_name="form_283_validation_report.json",
            mime="application/json"
        )


def main():
    """Main application logic."""
    initialize_session_state()
    render_header()
    render_sidebar()

    # File uploader section
    st.markdown("---")
    st.markdown("### 📤 Upload Document")

    uploaded_file = st.file_uploader(
        "Drag and drop or click to upload",
        type=["pdf"],
        help="PDF format only"
    )

    if uploaded_file is not None:
        # Display file info
        file_size_mb = uploaded_file.size / (1024 * 1024)
        st.info(f"📄 File: {uploaded_file.name} ({file_size_mb:.2f} MB)")

        # Check file size
        if file_size_mb > 10:
            st.error("❌ File size exceeds 10MB limit. Please upload a smaller file.")
            return

        # Process button
        if st.button("Process Document", type="primary"):
            try:
                # Save uploaded file
                temp_file_path = save_uploaded_file(uploaded_file)

                # Initialize processor
                with st.spinner("Initializing services..."):
                    processor = FormProcessor()

                # Process document
                with st.spinner("Processing document... This may take 15-30 seconds."):
                    form_data, metadata, validation_report = processor.process_document(
                        file_path=str(temp_file_path),
                        save_output=True
                    )

                # Store in session state
                st.session_state.processed = True
                st.session_state.form_data = form_data
                st.session_state.validation_report = validation_report
                st.session_state.metadata = metadata

                # Clean up temp file
                temp_file_path.unlink()

                st.success("Document processed successfully!")

            except Exception as e:
                st.error(f"Processing failed: {str(e)}")
                import traceback
                with st.expander("Error Details"):
                    st.code(traceback.format_exc())

    # Display results if processed
    if st.session_state.processed:
        st.markdown("---")

        # Extracted JSON
        render_raw_json(st.session_state.form_data)

        st.markdown("---")

        # Quality Issues
        render_quality_issues(st.session_state.validation_report)

        st.markdown("---")

        # Validation Summary
        render_validation_summary(st.session_state.validation_report)

        st.markdown("---")

        # Download Buttons
        render_download_buttons(
            st.session_state.form_data,
            st.session_state.validation_report,
            st.session_state.metadata
        )

        # Processing metadata
        with st.expander("📈 Processing Metadata"):
            st.json(st.session_state.metadata)


if __name__ == "__main__":
    main()