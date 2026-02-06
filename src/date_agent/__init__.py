"""
High-Precision Date Reasoning Agent for Financial Operations.

This package provides a date reasoning agent that converts natural language
temporal queries into precise date ranges for financial operations.

Core Principle: The agent handles SEMANTIC UNDERSTANDING only.
All date calculations are performed by deterministic TOOLS.
"""

from date_agent.core.config import DateAgentConfig
from date_agent.agent.date_agent import DateReasoningAgent

__version__ = "0.1.0"
__all__ = ["DateAgentConfig", "DateReasoningAgent", "__version__"]
