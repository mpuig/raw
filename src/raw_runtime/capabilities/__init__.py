"""Built-in capabilities for RAW workflows.

Capabilities provide access to external services with a uniform interface.
Each capability implements the Capability protocol, yielding events during
execution.

Available capabilities:
    - converse: AI conversation handling (Converse integration)
    - email: Email sending (SMTP, SendGrid, etc.)
    - slack: Slack messaging
    - sms: SMS/MMS messaging (Twilio, etc.)
    - voice: Voice calls (Twilio, etc.)
    - database: Database operations (PostgreSQL, MySQL, etc.)
    - spreadsheet: Spreadsheet operations (Google Sheets, Excel)
    - storage: File storage (S3, GCS, local)
    - crm: CRM integration (Salesforce, HubSpot, etc.)
    - payment: Payment processing (Stripe, etc.)
    - calendar: Calendar operations (Google Calendar, etc.)
    - scraper: Web scraping
    - http: HTTP requests
    - pdf: PDF generation and processing
    - ocr: Optical character recognition
    - translate: Text translation
    - summarize: Text summarization (LLM-based)
    - classify: Text classification (LLM-based)
    - search: Search engines (Google, Bing, etc.)
    - notify: Push notifications

Usage:
    from raw_runtime.capabilities import register_all_capabilities

    # Register all built-in capabilities
    register_all_capabilities()

    # In a workflow
    result = await self.capability("email").call(
        to="user@example.com",
        subject="Hello",
        body="World",
    )
"""

from raw_runtime.capabilities.calendar import CalendarCapability
from raw_runtime.capabilities.classify import ClassifyCapability
from raw_runtime.capabilities.converse import ConverseCapability
from raw_runtime.capabilities.crm import CrmCapability
from raw_runtime.capabilities.database import DatabaseCapability
from raw_runtime.capabilities.email import EmailCapability
from raw_runtime.capabilities.http import HttpCapability
from raw_runtime.capabilities.notify import NotifyCapability
from raw_runtime.capabilities.ocr import OcrCapability
from raw_runtime.capabilities.payment import PaymentCapability
from raw_runtime.capabilities.pdf import PdfCapability
from raw_runtime.capabilities.scraper import ScraperCapability
from raw_runtime.capabilities.search import SearchCapability
from raw_runtime.capabilities.slack import SlackCapability
from raw_runtime.capabilities.sms import SmsCapability
from raw_runtime.capabilities.spreadsheet import SpreadsheetCapability
from raw_runtime.capabilities.storage import StorageCapability
from raw_runtime.capabilities.summarize import SummarizeCapability
from raw_runtime.capabilities.translate import TranslateCapability
from raw_runtime.capabilities.voice import VoiceCapability
from raw_runtime.capability import register_capability


def register_all_capabilities() -> None:
    """Register all built-in capabilities in the global registry."""
    capabilities = [
        ConverseCapability(),
        EmailCapability(),
        SlackCapability(),
        SmsCapability(),
        VoiceCapability(),
        DatabaseCapability(),
        SpreadsheetCapability(),
        StorageCapability(),
        CrmCapability(),
        PaymentCapability(),
        CalendarCapability(),
        ScraperCapability(),
        HttpCapability(),
        PdfCapability(),
        OcrCapability(),
        TranslateCapability(),
        SummarizeCapability(),
        ClassifyCapability(),
        SearchCapability(),
        NotifyCapability(),
    ]
    for cap in capabilities:
        register_capability(cap)


__all__ = [
    "register_all_capabilities",
    "ConverseCapability",
    "EmailCapability",
    "SlackCapability",
    "SmsCapability",
    "VoiceCapability",
    "DatabaseCapability",
    "SpreadsheetCapability",
    "StorageCapability",
    "CrmCapability",
    "PaymentCapability",
    "CalendarCapability",
    "ScraperCapability",
    "HttpCapability",
    "PdfCapability",
    "OcrCapability",
    "TranslateCapability",
    "SummarizeCapability",
    "ClassifyCapability",
    "SearchCapability",
    "NotifyCapability",
]
