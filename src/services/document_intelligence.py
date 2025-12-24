"""
Azure Document Intelligence Service for OCR extraction.
Handles PDF/image processing and text extraction using Azure DI prebuilt-layout model.
"""

from typing import Dict, List, Optional
from pathlib import Path
from azure.ai.documentintelligence import DocumentIntelligenceClient
from azure.ai.documentintelligence.models import AnalyzeResult
from azure.core.credentials import AzureKeyCredential
import structlog

logger = structlog.get_logger(__name__)


class DocumentIntelligenceService:
    """
    Service for extracting text and structure from documents using Azure Document Intelligence.
    Supports PDF, JPG, PNG, and other common document formats.
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
        Analyze a document using Azure Document Intelligence prebuilt-layout model.

        This model extracts:
        - Text content with reading order
        - Tables and their structure
        - Key-value pairs (form fields)
        - Selection marks (checkboxes)
        - Page layout information

        Args:
            file_path: Path to the document file (PDF, JPG, PNG, etc.)

        Returns:
            AnalyzeResult object containing all extracted information

        Raises:
            FileNotFoundError: If the file doesn't exist
            Exception: If the Azure API call fails
        """
        file_path_obj = Path(file_path)

        if not file_path_obj.exists():
            logger.error("File not found", file_path=file_path)
            raise FileNotFoundError(f"File not found: {file_path}")

        # Determine content type based on file extension
        extension = file_path_obj.suffix.lower()
        content_type_mapping = {
            '.pdf': 'application/pdf',
            '.jpg': 'image/jpeg',
            '.jpeg': 'image/jpeg',
            '.png': 'image/png',
            '.bmp': 'image/bmp',
            '.tiff': 'image/tiff',
            '.tif': 'image/tiff'
        }

        content_type = content_type_mapping.get(extension, 'application/octet-stream')

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
        Extract plain text content from the analysis result.

        The text is extracted in reading order, preserving the document's layout.

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

    def extract_key_value_pairs(self, result: AnalyzeResult) -> Dict[str, str]:
        """
        Extract key-value pairs (form fields) detected by Document Intelligence.

        These are automatically detected form fields like "Name: John Doe"

        Args:
            result: AnalyzeResult from analyze_document()

        Returns:
            Dictionary of key-value pairs
        """
        key_value_pairs = {}

        if not result or not hasattr(result, 'key_value_pairs'):
            logger.info("No key-value pairs detected")
            return key_value_pairs

        if result.key_value_pairs:
            for kv_pair in result.key_value_pairs:
                # Extract key
                key = kv_pair.key.content if kv_pair.key else ""

                # Extract value
                value = kv_pair.value.content if kv_pair.value else ""

                if key:
                    key_value_pairs[key] = value

            logger.info(
                "Key-value pairs extracted",
                pairs_count=len(key_value_pairs)
            )

        return key_value_pairs

    def extract_tables(self, result: AnalyzeResult) -> List[Dict]:
        """
        Extract tables detected in the document.

        Args:
            result: AnalyzeResult from analyze_document()

        Returns:
            List of tables, where each table is represented as a dict with:
            - row_count: Number of rows
            - column_count: Number of columns
            - cells: List of cell dictionaries
        """
        tables = []

        if not result or not hasattr(result, 'tables'):
            logger.info("No tables detected")
            return tables

        if result.tables:
            for table in result.tables:
                table_data = {
                    'row_count': table.row_count,
                    'column_count': table.column_count,
                    'cells': []
                }

                for cell in table.cells:
                    cell_data = {
                        'row_index': cell.row_index,
                        'column_index': cell.column_index,
                        'content': cell.content,
                        'row_span': getattr(cell, 'row_span', 1),
                        'column_span': getattr(cell, 'column_span', 1)
                    }
                    table_data['cells'].append(cell_data)

                tables.append(table_data)

            logger.info(
                "Tables extracted",
                tables_count=len(tables)
            )

        return tables

    def get_page_info(self, result: AnalyzeResult) -> List[Dict]:
        """
        Extract page-level information (dimensions, orientation, etc.).

        Args:
            result: AnalyzeResult from analyze_document()

        Returns:
            List of page information dictionaries
        """
        pages_info = []

        if not result or not hasattr(result, 'pages'):
            return pages_info

        if result.pages:
            for idx, page in enumerate(result.pages, 1):
                page_info = {
                    'page_number': idx,
                    'width': page.width if hasattr(page, 'width') else None,
                    'height': page.height if hasattr(page, 'height') else None,
                    'unit': page.unit if hasattr(page, 'unit') else None,
                    'angle': page.angle if hasattr(page, 'angle') else None,
                    'lines_count': len(page.lines) if hasattr(page, 'lines') and page.lines else 0
                }
                pages_info.append(page_info)

        return pages_info