"""Feedback loop orchestrator - main loop with auto-fix cycle."""

import importlib
import logging
import os
import uuid
from datetime import date, datetime

from date_agent.feedback.config import FeedbackConfig
from date_agent.feedback.models import QueryResult, ValidationResult
from date_agent.feedback.state import RunState

logger = logging.getLogger("Orchestrator")


class FeedbackOrchestrator:
    """Main feedback loop orchestrator.

    Algorithm:
    1. Generate a batch of queries (ChallengerAgent)
    2. For each query:
       a. Run through the date agent (Validator)
       b. If PASS: increment consecutive_successes
       c. If FAIL: attempt auto-fix (up to N attempts)
    3. Check stopping criteria (target consecutive successes)
    4. Repeat
    5. Generate final report
    """

    def __init__(self, config: FeedbackConfig):
        self.config = config
        self.ref_date = date.fromisoformat(config.reference_date)

        # Azure OpenAI client (shared)
        self.openai_client = None
        self._init_openai()

        # Date agent (system under test)
        self._init_agent()

        # Sub-components
        from date_agent.feedback.challenger import ChallengerAgent
        from date_agent.feedback.auto_fixer import AutoFixer
        from date_agent.feedback.report import ReportGenerator

        self.challenger = ChallengerAgent(
            self.ref_date, config, self.openai_client
        )
        self.auto_fixer = AutoFixer(config, self.openai_client)
        self.report_gen = ReportGenerator()

    def _init_openai(self):
        """Initialize Azure OpenAI client if credentials available."""
        if self.config.azure_openai_endpoint and self.config.azure_openai_api_key:
            try:
                from openai import AsyncAzureOpenAI

                self.openai_client = AsyncAzureOpenAI(
                    azure_endpoint=self.config.azure_openai_endpoint,
                    api_key=self.config.azure_openai_api_key,
                    api_version=self.config.azure_openai_api_version,
                )
            except ImportError:
                logger.warning("openai package not installed, LLM features disabled")

    def _init_agent(self):
        """Initialize the date agent and validator."""
        from date_agent.agent.date_agent import DateReasoningAgent
        from date_agent.core.config import DateAgentConfig
        from date_agent.feedback.validator import Validator

        self.agent_config = DateAgentConfig(
            azure_openai_endpoint=self.config.azure_openai_endpoint,
            azure_openai_api_key=self.config.azure_openai_api_key,
            azure_openai_api_version=self.config.azure_openai_api_version,
            azure_openai_deployment=self.config.azure_openai_deployment,
            default_timezone="America/Lima",
            default_locale="es",
            enable_audit_trail=False,
        )
        self.agent = DateReasoningAgent(self.agent_config)
        self.validator = Validator(self.agent)

    async def run(self, resume_from: str = None) -> RunState:
        """Execute the feedback loop.

        Args:
            resume_from: Path to a state file to resume from.

        Returns:
            Final RunState with complete results.
        """
        # Initialize or resume state
        if resume_from and os.path.exists(resume_from):
            state = RunState.load(resume_from)
            logger.info(
                f"Resuming: {state.total_queries_processed} processed, "
                f"{state.consecutive_successes} consecutive"
            )
        else:
            state = RunState(
                run_id=str(uuid.uuid4()),
                started_at=datetime.now().isoformat(),
                reference_date=self.config.reference_date,
            )

        logger.info(
            f"Starting feedback loop (target: {self.config.target_consecutive_successes} "
            f"consecutive, max: {self.config.max_total_queries})"
        )

        try:
            while not self._should_stop(state):
                batch = self.challenger.generate_batch(self.config.batch_size)
                logger.info(
                    f"Batch of {len(batch)} queries "
                    f"(total: {state.total_queries_processed}, "
                    f"consecutive: {state.consecutive_successes})"
                )

                for query in batch:
                    if self._should_stop(state):
                        break

                    # Validate
                    validation = await self.validator.validate(query)

                    if validation.result == ValidationResult.PASS:
                        qr = QueryResult(
                            query=query,
                            validation=validation,
                            final_status="passed",
                        )
                        state.record_pass(qr)
                        if state.consecutive_successes % 50 == 0:
                            logger.info(
                                f"Consecutive: {state.consecutive_successes} "
                                f"(total: {state.total_queries_processed})"
                            )
                    else:
                        logger.warning(
                            f"FAIL [{validation.result.value}]: "
                            f"{query.query_text[:60]}..."
                        )
                        if self.config.auto_fix_enabled:
                            await self._handle_failure(query, validation, state)
                        else:
                            qr = QueryResult(
                                query=query,
                                validation=validation,
                                final_status="skipped",
                            )
                            state.record_skip(qr)

                    # Save state periodically
                    if state.total_queries_processed % 10 == 0:
                        state.save(self.config.state_file)

        except KeyboardInterrupt:
            logger.info("Interrupted by user")
            state.completion_reason = "manual_stop"

        # Finalize
        state.completed = True
        state.completed_at = datetime.now().isoformat()
        if not state.completion_reason:
            if state.consecutive_successes >= self.config.target_consecutive_successes:
                state.completion_reason = "target_reached"
            else:
                state.completion_reason = "max_queries"

        state.save(self.config.state_file)

        # Generate report
        os.makedirs(self.config.log_dir, exist_ok=True)
        self.report_gen.generate(state, self.config.log_dir)

        return state

    async def _handle_failure(self, query, validation, state) -> None:
        """Handle a failing query: attempt fix, verify, or skip."""
        fix_attempts = []

        for attempt in range(1, self.config.max_fix_attempts_per_query + 1):
            logger.info(
                f"Fix attempt {attempt}/{self.config.max_fix_attempts_per_query}"
            )

            fix = await self.auto_fixer.attempt_fix(query, validation, attempt)
            fix_attempts.append(fix)

            if not fix.fix_applied or not fix.regression_test_passed:
                logger.warning(f"Fix attempt {attempt} failed: {fix.error_message}")
                continue

            # Reload agent modules after code change
            self._reload_agent()

            # Re-validate
            re_validation = await self.validator.validate(query)

            if re_validation.result == ValidationResult.PASS:
                fix.fix_verified = True
                qr = QueryResult(
                    query=query,
                    validation=re_validation,
                    fix_attempts=fix_attempts,
                    final_status="fixed",
                )
                state.record_fix(qr)
                logger.info(f"FIX VERIFIED: {fix.fix_description}")
                return
            else:
                logger.warning(
                    f"Fix did not resolve: {re_validation.result.value}"
                )
                validation = re_validation

        # All attempts exhausted
        qr = QueryResult(
            query=query,
            validation=validation,
            fix_attempts=fix_attempts,
            final_status="skipped",
        )
        state.record_skip(qr)
        logger.error(
            f"SKIPPED after {len(fix_attempts)} attempts: "
            f"{query.query_text[:60]}"
        )

    def _reload_agent(self) -> None:
        """Reload date agent modules after a code change.

        Reload order follows the dependency chain:
        1. localization (leaf modules)
        2. semantic_parser (depends on localization)
        3. resolve_period_tool (depends on localization)
        4. query_decomposer
        5. date_agent (depends on all above)
        """
        import date_agent.localization.spanish
        import date_agent.localization.english
        import date_agent.agent.semantic_parser
        import date_agent.tools.resolve_period_tool
        import date_agent.agent.query_decomposer
        import date_agent.agent.date_agent as da_module

        importlib.reload(date_agent.localization.spanish)
        importlib.reload(date_agent.localization.english)
        importlib.reload(date_agent.agent.semantic_parser)
        importlib.reload(date_agent.tools.resolve_period_tool)
        importlib.reload(date_agent.agent.query_decomposer)
        importlib.reload(da_module)

        # Re-create agent and validator with reloaded modules
        self._init_agent()
        logger.info("Agent modules reloaded")

    def _should_stop(self, state: RunState) -> bool:
        """Check if the loop should stop."""
        if state.consecutive_successes >= self.config.target_consecutive_successes:
            return True
        if state.total_queries_processed >= self.config.max_total_queries:
            return True
        return False
