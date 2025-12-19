"""Pre-defined tools for RAW workflows.

These tools provide access to common external services with a uniform interface.

Available tools:
    - converse: AI conversation handling
    - email: Email sending
    - slack: Slack messaging
    - sms: SMS/MMS messaging
    - voice: Voice calls
    - database: Database operations
    - spreadsheet: Spreadsheet operations
    - storage: File storage
    - crm: CRM integration
    - payment: Payment processing
    - calendar: Calendar operations
    - scraper: Web scraping
    - http: HTTP requests
    - pdf: PDF generation/processing
    - ocr: Optical character recognition
    - translate: Text translation
    - summarize: Text summarization
    - classify: Text classification
    - search: Web search
    - notify: Push notifications
"""

from raw_runtime.tools.builtin.calendar import CalendarTool
from raw_runtime.tools.builtin.classify import ClassifyTool
from raw_runtime.tools.builtin.converse import ConverseTool
from raw_runtime.tools.builtin.crm import CrmTool
from raw_runtime.tools.builtin.database import DatabaseTool
from raw_runtime.tools.builtin.email import EmailTool
from raw_runtime.tools.builtin.http import HttpTool
from raw_runtime.tools.builtin.notify import NotifyTool
from raw_runtime.tools.builtin.ocr import OcrTool
from raw_runtime.tools.builtin.payment import PaymentTool
from raw_runtime.tools.builtin.pdf import PdfTool
from raw_runtime.tools.builtin.scraper import ScraperTool
from raw_runtime.tools.builtin.search import SearchTool
from raw_runtime.tools.builtin.slack import SlackTool
from raw_runtime.tools.builtin.sms import SmsTool
from raw_runtime.tools.builtin.spreadsheet import SpreadsheetTool
from raw_runtime.tools.builtin.storage import StorageTool
from raw_runtime.tools.builtin.summarize import SummarizeTool
from raw_runtime.tools.builtin.translate import TranslateTool
from raw_runtime.tools.builtin.voice import VoiceTool
from raw_runtime.tools.registry import register_tool


def register_all_builtin_tools() -> None:
    """Register all pre-defined tools in the global registry."""
    tools = [
        ConverseTool(),
        EmailTool(),
        SlackTool(),
        SmsTool(),
        VoiceTool(),
        DatabaseTool(),
        SpreadsheetTool(),
        StorageTool(),
        CrmTool(),
        PaymentTool(),
        CalendarTool(),
        ScraperTool(),
        HttpTool(),
        PdfTool(),
        OcrTool(),
        TranslateTool(),
        SummarizeTool(),
        ClassifyTool(),
        SearchTool(),
        NotifyTool(),
    ]
    for t in tools:
        register_tool(t)


__all__ = [
    "register_all_builtin_tools",
    "ConverseTool",
    "EmailTool",
    "SlackTool",
    "SmsTool",
    "VoiceTool",
    "DatabaseTool",
    "SpreadsheetTool",
    "StorageTool",
    "CrmTool",
    "PaymentTool",
    "CalendarTool",
    "ScraperTool",
    "HttpTool",
    "PdfTool",
    "OcrTool",
    "TranslateTool",
    "SummarizeTool",
    "ClassifyTool",
    "SearchTool",
    "NotifyTool",
]
