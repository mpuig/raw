"""Configuration management for call center solution.

Loads configuration from YAML files and environment variables with proper
validation and type safety using Pydantic.
"""

from pathlib import Path

import yaml
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class BotConfig(BaseModel):
    """Bot behavior configuration."""

    name: str = "customer-support"
    greeting_first: bool = True


class LLMConfig(BaseModel):
    """LLM provider configuration."""

    model: str = "claude-3-5-sonnet-20241022"
    temperature: float = 0.7
    max_tokens: int = 2000


class STTConfig(BaseModel):
    """Speech-to-Text configuration."""

    provider: str = "deepgram"
    model: str = "nova-2"
    language: str = "en-US"
    interim_results: bool = True
    punctuate: bool = True
    smart_format: bool = True


class TTSConfig(BaseModel):
    """Text-to-Speech configuration."""

    provider: str = "elevenlabs"
    voice_id: str = "21m00Tcm4TlvDq8ikWAM"  # Rachel
    model: str = "eleven_turbo_v2_5"
    stability: float = 0.5
    similarity_boost: float = 0.75
    optimize_streaming_latency: int = 3


class VoiceConfig(BaseModel):
    """Voice services configuration."""

    stt: STTConfig = Field(default_factory=STTConfig)
    tts: TTSConfig = Field(default_factory=TTSConfig)


class CORSConfig(BaseModel):
    """CORS configuration."""

    enabled: bool = True
    allow_origins: list[str] = Field(default_factory=lambda: ["http://localhost:3000"])
    allow_credentials: bool = True
    allow_methods: list[str] = Field(default_factory=lambda: ["GET", "POST", "PUT", "DELETE"])
    allow_headers: list[str] = Field(default_factory=lambda: ["*"])


class ServerConfig(BaseModel):
    """FastAPI server configuration."""

    host: str = "0.0.0.0"
    port: int = 8000
    log_level: str = "info"
    title: str = "Call Center API"
    description: str = "AI-powered customer support call center"
    version: str = "0.1.0"
    enable_docs: bool = True
    enable_metrics: bool = True
    cors: CORSConfig = Field(default_factory=CORSConfig)


class TwilioConfig(BaseModel):
    """Twilio integration configuration."""

    webhook_path: str = "/voice/twilio"
    status_callback_path: str = "/voice/status"
    record_calls: bool = False
    recording_status_callback: str = "/voice/recording"


class DatabaseConfig(BaseModel):
    """Database configuration."""

    enabled: bool = False
    url: str = ""
    pool_size: int = 20
    max_overflow: int = 10


class RedisConfig(BaseModel):
    """Redis configuration."""

    enabled: bool = False
    url: str = ""
    max_connections: int = 50


class StateConfig(BaseModel):
    """State management configuration."""

    backend: str = "memory"  # memory, redis, postgres
    ttl: int = 3600  # seconds


class TelemetryConfig(BaseModel):
    """Telemetry configuration."""

    enabled: bool = False
    service_name: str = "callcenter"
    exporter: str = "otlp"
    endpoint: str = "http://localhost:4317"
    sample_rate: float = 1.0


class PostCallWorkflowConfig(BaseModel):
    """Post-call workflow configuration."""

    enabled: bool = True
    summarize: bool = True
    update_crm: bool = True
    send_email: bool = False
    create_ticket_threshold: float = 0.6


class WorkflowsConfig(BaseModel):
    """Workflows configuration."""

    post_call: PostCallWorkflowConfig = Field(default_factory=PostCallWorkflowConfig)


class SkillConfig(BaseModel):
    """Individual skill configuration."""

    enabled: bool = True
    cache_ttl: int = 300
    mock_data: bool = False


class BusinessHoursConfig(BaseModel):
    """Business hours configuration."""

    start: str = "09:00"
    end: str = "17:00"
    timezone: str = "America/New_York"


class ScheduleCallbackConfig(BaseModel):
    """Schedule callback skill configuration."""

    enabled: bool = True
    business_hours: BusinessHoursConfig = Field(default_factory=BusinessHoursConfig)
    max_days_ahead: int = 30


class SkillsConfig(BaseModel):
    """Skills configuration."""

    lookup_customer: SkillConfig = Field(default_factory=SkillConfig)
    check_order_status: SkillConfig = Field(default_factory=SkillConfig)
    schedule_callback: ScheduleCallbackConfig = Field(default_factory=ScheduleCallbackConfig)


class EscalationConfig(BaseModel):
    """Escalation rules configuration."""

    keywords: list[str] = Field(
        default_factory=lambda: [
            "speak to manager",
            "supervisor",
            "cancel account",
            "legal action",
        ]
    )
    max_turns: int = 20
    sentiment_threshold: float = 0.3


class CallHandlingConfig(BaseModel):
    """Call handling rules configuration."""

    max_duration: int = 1800  # seconds
    silence_timeout: int = 30
    greeting_delay: float = 1.0


class BusinessRulesConfig(BaseModel):
    """Business rules configuration."""

    escalation: EscalationConfig = Field(default_factory=EscalationConfig)
    call: CallHandlingConfig = Field(default_factory=CallHandlingConfig)


class LoggingConfig(BaseModel):
    """Logging configuration."""

    level: str = "info"
    format: str = "json"
    output: str = "stdout"
    file_path: str = "logs/callcenter.log"


class FeaturesConfig(BaseModel):
    """Feature flags."""

    sentiment_analysis: bool = True
    call_recording: bool = False
    real_time_transcription: bool = True
    post_call_survey: bool = False


class CallCenterConfig(BaseSettings):
    """Main configuration for call center solution.

    Loads configuration from:
    1. config.yaml file
    2. Environment variables (override YAML)

    Why: Centralizes all configuration with proper validation and type safety.
    Supports both file-based config (for defaults) and env vars (for secrets).
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_nested_delimiter="__",
        case_sensitive=False,
        extra="allow",
    )

    # Core components
    bot: BotConfig = Field(default_factory=BotConfig)
    llm: LLMConfig = Field(default_factory=LLMConfig)
    voice: VoiceConfig = Field(default_factory=VoiceConfig)
    server: ServerConfig = Field(default_factory=ServerConfig)
    twilio: TwilioConfig = Field(default_factory=TwilioConfig)

    # Infrastructure
    database: DatabaseConfig = Field(default_factory=DatabaseConfig)
    redis: RedisConfig = Field(default_factory=RedisConfig)
    state: StateConfig = Field(default_factory=StateConfig)
    telemetry: TelemetryConfig = Field(default_factory=TelemetryConfig)

    # Application
    workflows: WorkflowsConfig = Field(default_factory=WorkflowsConfig)
    skills: SkillsConfig = Field(default_factory=SkillsConfig)
    business_rules: BusinessRulesConfig = Field(default_factory=BusinessRulesConfig)
    logging: LoggingConfig = Field(default_factory=LoggingConfig)
    features: FeaturesConfig = Field(default_factory=FeaturesConfig)

    # API Keys (loaded from environment)
    openai_api_key: str = Field(default="", alias="OPENAI_API_KEY")
    anthropic_api_key: str = Field(default="", alias="ANTHROPIC_API_KEY")
    deepgram_api_key: str = Field(default="", alias="DEEPGRAM_API_KEY")
    elevenlabs_api_key: str = Field(default="", alias="ELEVENLABS_API_KEY")
    twilio_account_sid: str = Field(default="", alias="TWILIO_ACCOUNT_SID")
    twilio_auth_token: str = Field(default="", alias="TWILIO_AUTH_TOKEN")
    twilio_phone_number: str = Field(default="", alias="TWILIO_PHONE_NUMBER")

    @classmethod
    def from_yaml(cls, path: str | Path = "config.yaml") -> "CallCenterConfig":
        """Load configuration from YAML file with env var overrides.

        Args:
            path: Path to YAML configuration file.

        Returns:
            Validated configuration instance.

        Why: Provides a clean API for loading config from files while still
        allowing environment variables to override values.
        """
        config_path = Path(path)

        if not config_path.exists():
            # If no config file, use defaults + env vars
            return cls()

        with open(config_path) as f:
            yaml_data = yaml.safe_load(f)

        # Environment variables will override YAML values
        # thanks to Pydantic's settings hierarchy
        return cls(**yaml_data)

    def validate_required_keys(self) -> list[str]:
        """Validate that required API keys are present.

        Returns:
            List of missing API key names.

        Why: Fail fast with clear error messages about missing credentials
        rather than waiting for runtime failures.
        """
        missing = []

        # Check LLM provider
        if not self.openai_api_key and not self.anthropic_api_key:
            missing.append("LLM provider (OPENAI_API_KEY or ANTHROPIC_API_KEY)")

        # Check voice services
        if not self.deepgram_api_key:
            missing.append("DEEPGRAM_API_KEY")
        if not self.elevenlabs_api_key:
            missing.append("ELEVENLABS_API_KEY")

        # Check Twilio
        if not self.twilio_account_sid:
            missing.append("TWILIO_ACCOUNT_SID")
        if not self.twilio_auth_token:
            missing.append("TWILIO_AUTH_TOKEN")

        return missing

    def get_llm_provider(self) -> str:
        """Determine which LLM provider to use based on available keys.

        Returns:
            Provider name: "openai" or "anthropic".

        Why: Auto-detect provider based on available credentials to simplify
        configuration for end users.
        """
        if self.anthropic_api_key:
            return "anthropic"
        elif self.openai_api_key:
            return "openai"
        else:
            raise ValueError("No LLM API key found")


def load_config(config_path: str | Path = "config.yaml") -> CallCenterConfig:
    """Load and validate call center configuration.

    Args:
        config_path: Path to YAML configuration file.

    Returns:
        Validated configuration instance.

    Raises:
        ValueError: If required API keys are missing.

    Why: Provides a simple entry point for loading configuration with
    validation and clear error messages.
    """
    config = CallCenterConfig.from_yaml(config_path)

    # Validate required keys
    missing_keys = config.validate_required_keys()
    if missing_keys:
        raise ValueError(
            f"Missing required configuration: {', '.join(missing_keys)}. "
            "Please set these environment variables or add them to .env file."
        )

    return config
