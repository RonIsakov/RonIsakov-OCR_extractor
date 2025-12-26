"""
Main processing pipeline for Form 283 extraction.

This module orchestrates the entire document processing workflow:
1. OCR extraction with Azure Document Intelligence
2. Field extraction with Azure OpenAI GPT-4o
3. Pydantic schema validation
4. Quality validation
5. JSON output generation
"""

import json
from pathlib import Path
from typing import Dict, Any, Tuple

from src.services.document_intelligence import DocumentIntelligenceService
from src.services.openai_service import OpenAIService
from src.models.schemas import Form283Data
from src.models.validation import ValidationReport
from src.config.settings import get_settings
from src.utils.logger import get_logger

logger = get_logger(__name__)


class FormProcessor:
    """
    Main processor for Form 283 document extraction pipeline.

    Orchestrates:
    - OCR extraction (Azure Document Intelligence)
    - Field extraction (Azure OpenAI GPT-4o)
    - Schema validation (Pydantic)
    - Quality validation (ValidationService)
    """

    def __init__(self):
        """Initialize all required services."""
        settings = get_settings()

        # Initialize Document Intelligence service
        self.di_service = DocumentIntelligenceService(
            endpoint=settings.AZURE_DI_ENDPOINT,
            key=settings.AZURE_DI_KEY
        )

        # Initialize OpenAI service
        self.openai_service = OpenAIService()

        logger.info("FormProcessor initialized with all services")

    def process_document(
        self,
        file_path: str,
        save_output: bool = True,
        output_dir: str = "data/output"
    ) -> Tuple[Form283Data, Dict[str, Any], ValidationReport]:
        """
        Process a Form 283 document end-to-end.

        Pipeline:
        1. OCR with Azure Document Intelligence
        2. Field extraction with GPT-4o
        3. Pydantic schema validation
        4. Quality validation
        5. Save JSON outputs (optional)

        Args:
            file_path: Path to PDF/image file
            save_output: Whether to save JSON outputs
            output_dir: Directory to save outputs

        Returns:
            Tuple of:
                - form_data: Validated Form283Data instance
                - metadata: Processing metadata (tokens, model info)
                - validation_report: Quality validation report

        Raises:
            FileNotFoundError: If input file doesn't exist
            Exception: If any processing step fails
        """
        file_path_obj = Path(file_path)

        # Validate input file exists
        if not file_path_obj.exists():
            raise FileNotFoundError(f"Input file not found: {file_path}")

        logger.info(
            "Starting document processing",
            file_path=str(file_path_obj),
            file_size_bytes=file_path_obj.stat().st_size
        )

        try:
            # Step 1: OCR with Document Intelligence
            logger.info("Step 1/4: Running OCR with Azure Document Intelligence")
            ocr_result = self.di_service.analyze_document(str(file_path_obj))
            ocr_text = self.di_service.extract_text_content(ocr_result)

            logger.info(
                "OCR extraction complete",
                text_length=len(ocr_text),
                pages=len(ocr_result.pages) if hasattr(ocr_result, 'pages') else 1
            )

            # Step 2-4: Extract fields, validate with Pydantic, run quality checks
            logger.info("Step 2/4: Extracting fields with GPT-4o")
            logger.info("Step 3/4: Validating with Pydantic schema")
            logger.info("Step 4/4: Running quality validation")

            form_data, metadata, validation_report = self.openai_service.extract_and_validate(ocr_text)

            logger.info(
                "Processing complete",
                accuracy=validation_report.accuracy_score,
                completeness=validation_report.completeness_score,
                quality_issues=len(validation_report.corrections)
            )

            # Step 5: Save outputs (optional)
            if save_output:
                self._save_outputs(
                    file_path_obj=file_path_obj,
                    ocr_text=ocr_text,
                    form_data=form_data,
                    metadata=metadata,
                    validation_report=validation_report,
                    output_dir=output_dir
                )

            return form_data, metadata, validation_report

        except Exception as e:
            logger.error(
                "Document processing failed",
                file_path=str(file_path_obj),
                error=str(e),
                error_type=type(e).__name__
            )
            raise

    def _save_outputs(
        self,
        file_path_obj: Path,
        ocr_text: str,
        form_data: Form283Data,
        metadata: Dict[str, Any],
        validation_report: ValidationReport,
        output_dir: str
    ):
        """
        Save all processing outputs to JSON files.

        Saves:
        - OCR text
        - Extracted form data (with Hebrew field names)
        - Validation report
        - Processing metadata

        Args:
            file_path_obj: Input file path
            ocr_text: Extracted OCR text
            form_data: Validated form data
            metadata: Processing metadata
            validation_report: Validation report
            output_dir: Output directory
        """
        # Create output directories
        output_path = Path(output_dir)
        ocr_dir = output_path / "ocr_text"
        json_dir = output_path / "extracted_json"
        validation_dir = output_path / "validation_reports"

        for directory in [ocr_dir, json_dir, validation_dir]:
            directory.mkdir(parents=True, exist_ok=True)

        # Generate base filename
        base_name = file_path_obj.stem

        # Save OCR text
        ocr_file = ocr_dir / f"{base_name}_extracted.txt"
        with open(ocr_file, 'w', encoding='utf-8') as f:
            f.write(f"FILE: {file_path_obj.name}\n")
            f.write(f"{'='*70}\n\n")
            f.write("EXTRACTED TEXT:\n")
            f.write(f"{'-'*70}\n")
            f.write(ocr_text)

        logger.info(f"OCR text saved to {ocr_file}")

        # Save extracted form data (with Hebrew field names)
        json_file = json_dir / f"{base_name}_form_data.json"
        with open(json_file, 'w', encoding='utf-8') as f:
            json.dump(
                form_data.model_dump(by_alias=True),  # Use Hebrew aliases
                f,
                ensure_ascii=False,
                indent=2
            )

        logger.info(f"Form data saved to {json_file}")

        # Save validation report
        validation_file = validation_dir / f"{base_name}_validation.json"
        validation_data = {
            "file": file_path_obj.name,
            "processing_metadata": metadata,
            "validation_report": validation_report.model_dump()
        }

        with open(validation_file, 'w', encoding='utf-8') as f:
            json.dump(validation_data, f, ensure_ascii=False, indent=2)

        logger.info(f"Validation report saved to {validation_file}")

        logger.info(
            "All outputs saved successfully",
            output_directory=str(output_path)
        )
