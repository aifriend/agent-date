"""Configuration for the feedback system."""

import os
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class FeedbackConfig:
    """Configuration for the autonomous feedback loop."""

    # Azure OpenAI
    azure_openai_endpoint: Optional[str] = None
    azure_openai_api_key: Optional[str] = None
    azure_openai_api_version: str = "2025-01-01-preview"
    azure_openai_deployment: str = "gpt-4.1m-aicg"

    # Stopping criteria
    target_consecutive_successes: int = 1000
    max_total_queries: int = 5000
    max_fix_attempts_per_query: int = 3

    # Reference date (same as test suite)
    reference_date: str = "2024-07-15"

    # Paths
    state_file: str = "feedback_state.json"
    log_dir: str = "feedback_logs"

    # Challenger settings
    batch_size: int = 50
    llm_query_ratio: float = 0.3  # 30% LLM-generated, 70% template

    # Auto-fixer settings
    auto_fix_enabled: bool = True
    run_regression_tests: bool = True
    test_command: str = "PYTHONPATH=src .venv/bin/python -m pytest tests/ -v --tb=short -x"
    max_test_timeout_seconds: int = 120

    # Files the auto-fixer is allowed to modify
    modifiable_files: list = field(default_factory=lambda: [
        "src/date_agent/agent/semantic_parser.py",
        "src/date_agent/tools/resolve_period_tool.py",
        "src/date_agent/localization/spanish.py",
        "src/date_agent/localization/english.py",
        "src/date_agent/agent/query_decomposer.py",
        "src/date_agent/core/constants.py",
    ])

    def __post_init__(self) -> None:
        """Load from environment variables if not provided."""
        if self.azure_openai_endpoint is None:
            self.azure_openai_endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
        if self.azure_openai_api_key is None:
            self.azure_openai_api_key = os.getenv("AZURE_OPENAI_API_KEY")
        if os.getenv("AZURE_OPENAI_API_VERSION"):
            self.azure_openai_api_version = os.getenv("AZURE_OPENAI_API_VERSION")
        if os.getenv("AZURE_OPENAI_DEPLOYMENT"):
            self.azure_openai_deployment = os.getenv("AZURE_OPENAI_DEPLOYMENT")
