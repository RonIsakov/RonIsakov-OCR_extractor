"""
Azure OpenAI service for field extraction from OCR text.

This module provides the OpenAIService class that uses GPT-4o to extract
structured data from Form 283 OCR text and return validated JSON.
"""

import json
from typing import Dict, Any, Tuple
from openai import AzureOpenAI
from openai.types.chat import ChatCompletion

from src.config.settings import get_settings
from src.config.prompts import SYSTEM_MESSAGE, get_extraction_prompt
from src.models.schemas import Form283Data
from src.models.validation import ValidationReport
from src.services.validation_service import ValidationService
from src.utils.logger import get_logger

logger = get_logger(__name__)


class OpenAIService:
    """
    Service for extracting structured data from OCR text using Azure OpenAI GPT-4o.

    This service takes raw OCR text and uses prompt engineering with GPT-4o
    to extract all fields from Form 283 into a structured JSON format.
    """

    def __init__(self):
        """Initialize the Azure OpenAI client with credentials from settings."""
        settings = get_settings()

        self.client = AzureOpenAI(
            api_key=settings.AZURE_OPENAI_KEY,
            api_version=settings.AZURE_OPENAI_API_VERSION,
            azure_endpoint=settings.AZURE_OPENAI_ENDPOINT
        )

        self.deployment_name = settings.AZURE_OPENAI_DEPLOYMENT_NAME
        self.temperature = 0.1  # Low temperature for consistency

        logger.info(
            "OpenAI service initialized",
            deployment=self.deployment_name,
            temperature=self.temperature
        )

    def extract_fields(self, ocr_text: str) -> Tuple[Dict[str, Any], Dict[str, Any]]:
        """
        Extract structured fields from OCR text using GPT-4o with JSON mode.

        Args:
            ocr_text: Raw OCR text extracted from Form 283

        Returns:
            Tuple of (extracted_data, metadata) where:
                - extracted_data: Parsed JSON with form fields
                - metadata: Token usage and model info

        Raises:
            ValueError: If JSON parsing fails
            Exception: If API call fails
        """
        logger.info("Starting field extraction", ocr_length=len(ocr_text))

        try:
            user_prompt = get_extraction_prompt(ocr_text)

            response: ChatCompletion = self.client.chat.completions.create(
                model=self.deployment_name,
                messages=[
                    {"role": "system", "content": SYSTEM_MESSAGE},
                    {"role": "user", "content": user_prompt}
                ],
                response_format={"type": "json_object"},
                temperature=self.temperature
            )

            raw_json = response.choices[0].message.content
            usage = response.usage
            logger.info(
                "OpenAI API call successful",
                prompt_tokens=usage.prompt_tokens,
                completion_tokens=usage.completion_tokens,
                total_tokens=usage.total_tokens,
                model=response.model
            )

            try:
                extracted_data = json.loads(raw_json)
            except json.JSONDecodeError as e:
                logger.error("Failed to parse JSON response", error=str(e), raw_response=raw_json[:500])
                raise ValueError(f"Invalid JSON response from GPT-4o: {e}")

            metadata = {
                "model": response.model,
                "prompt_tokens": usage.prompt_tokens,
                "completion_tokens": usage.completion_tokens,
                "total_tokens": usage.total_tokens,
                "temperature": self.temperature,
                "finish_reason": response.choices[0].finish_reason
            }

            logger.info(
                "Field extraction completed successfully",
                fields_extracted=len(extracted_data),
                total_tokens=usage.total_tokens
            )

            return extracted_data, metadata

        except Exception as e:
            logger.error("Field extraction failed", error=str(e), error_type=type(e).__name__)
            raise

    def extract_and_validate(
        self,
        ocr_text: str
    ) -> Tuple[Form283Data, Dict[str, Any], ValidationReport]:
        """
        Extract fields from OCR text and validate with Pydantic schema and quality checks.

        Args:
            ocr_text: Raw OCR text extracted from Form 283

        Returns:
            Tuple of (form_data, metadata, validation_report) where:
                - form_data: Validated Form283Data instance
                - metadata: Token usage and API metadata
                - validation_report: Accuracy and completeness metrics

        Raises:
            ValidationError: If extracted data doesn't match schema
            ValueError: If JSON parsing fails
            Exception: If API call fails
        """
        logger.info("Starting extraction with validation")

        raw_extracted_data, metadata = self.extract_fields(ocr_text)

        try:
            form_data = Form283Data(**raw_extracted_data)
            logger.info(
                "Pydantic validation successful",
                filled_fields=form_data.get_filled_fields_count()[0],
                total_fields=form_data.get_filled_fields_count()[1],
                completeness=form_data.get_completeness_percentage()
            )
        except Exception as e:
            logger.error(
                "Pydantic validation failed",
                error=str(e),
                error_type=type(e).__name__,
                extracted_data_keys=list(raw_extracted_data.keys())
            )
            raise

        validation_service = ValidationService()
        validation_report = validation_service.validate(form_data)

        logger.info(
            "Validation report generated",
            accuracy=validation_report.accuracy_score,
            completeness=validation_report.completeness_score,
            quality_issues=len(validation_report.corrections)
        )

        return form_data, metadata, validation_report

