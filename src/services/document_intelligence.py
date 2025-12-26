"""
Azure Document Intelligence Service for OCR extraction.
Handles PDF/image processing and text extraction using Azure DI prebuilt-layout model.
"""

from pathlib import Path
from azure.ai.documentintelligence import DocumentIntelligenceClient
from azure.ai.documentintelligence.models import AnalyzeResult
from azure.core.credentials import AzureKeyCredential
import structlog

logger = structlog.get_logger(__name__)


class DocumentIntelligenceService:
    """
    Service for extracting text from documents using Azure Document Intelligence.
    Supports PDF.
    """

    def __init__(self, endpoint: str, key: str):
        """
        Initialize the Document Intelligence client.

        Args:
            endpoint: Azure Document Intelligence endpoint URL
            key: Azure Document Intelligence API key
        """
        self.client = DocumentIntelligenceClient(
            endpoint=endpoint,
            credential=AzureKeyCredential(key)
        )
        self.endpoint = endpoint
        logger.info("DocumentIntelligenceService initialized", endpoint=endpoint[:50])

    def analyze_document(self, file_path: str) -> AnalyzeResult:
        """
        Analyze a PDF document using Azure Document Intelligence prebuilt-layout model.

        Extracts text content with reading order and layout preservation.

        Args:
            file_path: Path to the PDF file

        Returns:
            AnalyzeResult object containing extracted text and metadata

        Raises:
            FileNotFoundError: If the file doesn't exist
            ValueError: If file is not a PDF
            Exception: If the Azure API call fails
        """
        file_path_obj = Path(file_path)

        if not file_path_obj.exists():
            logger.error("File not found", file_path=file_path)
            raise FileNotFoundError(f"File not found: {file_path}")

        # Validate PDF format
        if file_path_obj.suffix.lower() != '.pdf':
            raise ValueError(f"Only PDF files are supported, got {file_path_obj.suffix}")

        content_type = 'application/pdf'

        logger.info(
            "Starting document analysis",
            file_name=file_path_obj.name,
            file_size_mb=file_path_obj.stat().st_size / (1024 * 1024),
            content_type=content_type
        )

        try:
            # Read and send document to Azure DI
            with open(file_path, "rb") as f:
                poller = self.client.begin_analyze_document(
                    model_id="prebuilt-layout",
                    body=f,
                    content_type=content_type
                )

            # Wait for the analysis to complete
            result = poller.result()

            logger.info(
                "Document analysis completed",
                file_name=file_path_obj.name,
                pages=len(result.pages) if result.pages else 0,
                text_length=len(result.content) if result.content else 0
            )

            return result

        except Exception as e:
            logger.error(
                "Document analysis failed",
                file_name=file_path_obj.name,
                error=str(e)
            )
            raise

    def extract_text_content(self, result: AnalyzeResult) -> str:
        """
        Extract plain text content from the analysis result in reading order.

        Args:
            result: AnalyzeResult from analyze_document()

        Returns:
            Extracted text as a string
        """
        if not result or not hasattr(result, 'content'):
            logger.warning("No content found in analysis result")
            return ""

        text = result.content or ""

        logger.info(
            "Text content extracted",
            text_length=len(text),
            lines_count=text.count('\n')
        )

        return text