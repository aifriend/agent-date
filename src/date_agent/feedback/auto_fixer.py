"""Auto-Fixer - LLM-based diagnosis and code patching."""

import logging
import os
import re
import subprocess
from typing import Optional, Tuple

from date_agent.feedback.config import FeedbackConfig
from date_agent.feedback.models import (
    ChallengerQuery,
    FixAttempt,
    ValidationReport,
    ValidationResult,
)

logger = logging.getLogger("AutoFixer")

AUTO_FIXER_SYSTEM_PROMPT = """You are a Python debugging specialist for a Date Reasoning Agent.

The agent converts natural language date queries (in Spanish and English) to concrete date ranges.

Architecture:
- SemanticParser: pattern-matching + LLM fallback to extract period type from query text
- ResolvePeriodTool: deterministic date math, converts period types to (start_date, end_date)
- Localization modules: regex patterns for Spanish and English period expressions

Common bug categories:
1. Missing regex pattern in semantic_parser._extract_period_from_query()
2. Missing normalization mapping in semantic_parser._normalize_period_type()
3. Missing period handling in resolve_period_tool._resolve_to_dates()
4. Missing normalization in resolve_period_tool._normalize_period()
5. Incorrect date arithmetic (off-by-one, wrong month/quarter boundary)
6. Missing event query pattern in semantic_parser._is_event_query()

When proposing fixes:
- Use EXACT code from the source file in the ORIGINAL block (copy-paste precision)
- Keep fixes minimal - add patterns, not rewrite functions
- Follow existing code style and conventions
- Never break existing functionality
- Prefer adding to existing pattern lists over changing logic
"""


class AutoFixer:
    """Uses LLM to diagnose and fix date agent bugs.

    Workflow:
    1. Collect error context (query, expected, actual, traceback)
    2. Read relevant source file(s)
    3. Ask LLM to diagnose the root cause
    4. Ask LLM to propose a minimal fix
    5. Validate fix syntax with compile()
    6. Apply fix (backup original first)
    7. Run regression tests
    8. Rollback if tests fail
    """

    def __init__(self, config: FeedbackConfig, openai_client=None):
        self.config = config
        self.client = openai_client
        self.project_root = self._find_project_root()

    def _find_project_root(self) -> str:
        """Find the project root directory."""
        # Walk up from this file until we find pyproject.toml
        current = os.path.dirname(os.path.abspath(__file__))
        for _ in range(10):
            if os.path.exists(os.path.join(current, "pyproject.toml")):
                return current
            current = os.path.dirname(current)
        return os.getcwd()

    async def attempt_fix(
        self,
        query: ChallengerQuery,
        validation: ValidationReport,
        attempt_number: int,
    ) -> FixAttempt:
        """Attempt to fix the date agent for a failing query."""
        if not self.client:
            return FixAttempt(
                attempt_number=attempt_number,
                file_path="",
                original_code="",
                proposed_fix="",
                fix_description="No OpenAI client configured",
                fix_applied=False,
                fix_verified=False,
                regression_test_passed=False,
                error_message="No LLM available for auto-fix",
            )

        # Step 1: Gather context
        error_context = self._build_error_context(query, validation)

        # Step 2: Identify candidate files
        candidate_files = self._identify_candidate_files(validation)
        logger.info(f"Candidate files: {candidate_files}")

        # Step 3: Read source code
        source_contents = {}
        for fpath in candidate_files:
            full_path = os.path.join(self.project_root, fpath)
            if os.path.exists(full_path):
                with open(full_path, "r") as f:
                    source_contents[fpath] = f.read()

        # Step 4: Ask LLM to diagnose and propose fix
        diagnosis_prompt = self._build_diagnosis_prompt(
            error_context, source_contents, attempt_number
        )

        try:
            response = await self.client.chat.completions.create(
                model=self.config.azure_openai_deployment,
                messages=[
                    {"role": "system", "content": AUTO_FIXER_SYSTEM_PROMPT},
                    {"role": "user", "content": diagnosis_prompt},
                ],
                temperature=0.2,
                max_tokens=4000,
            )
            fix_content = response.choices[0].message.content
        except Exception as e:
            logger.error(f"LLM diagnosis failed: {e}")
            return FixAttempt(
                attempt_number=attempt_number,
                file_path="",
                original_code="",
                proposed_fix="",
                fix_description="LLM call failed",
                fix_applied=False,
                fix_verified=False,
                regression_test_passed=False,
                error_message=str(e),
            )

        # Step 5: Parse the proposed fix
        parsed = self._parse_fix(fix_content)
        if parsed is None:
            return FixAttempt(
                attempt_number=attempt_number,
                file_path="",
                original_code="",
                proposed_fix="",
                fix_description="Could not parse LLM fix proposal",
                fix_applied=False,
                fix_verified=False,
                regression_test_passed=False,
                error_message="Invalid fix format from LLM",
            )

        file_path, original_code, new_code, description = parsed

        # Verify file is modifiable
        if file_path not in self.config.modifiable_files:
            return FixAttempt(
                attempt_number=attempt_number,
                file_path=file_path,
                original_code=original_code,
                proposed_fix=new_code,
                fix_description=description,
                fix_applied=False,
                fix_verified=False,
                regression_test_passed=False,
                error_message=f"File not in modifiable list: {file_path}",
            )

        # Step 6: Validate syntax
        full_path = os.path.join(self.project_root, file_path)
        backup = source_contents.get(file_path, "")
        if not backup:
            try:
                with open(full_path, "r") as f:
                    backup = f.read()
            except Exception:
                pass

        new_full_content = backup.replace(original_code, new_code, 1)
        if new_full_content == backup:
            return FixAttempt(
                attempt_number=attempt_number,
                file_path=file_path,
                original_code=original_code,
                proposed_fix=new_code,
                fix_description=description,
                fix_applied=False,
                fix_verified=False,
                regression_test_passed=False,
                error_message="ORIGINAL code block not found in file",
            )

        try:
            compile(new_full_content, file_path, "exec")
        except SyntaxError as e:
            return FixAttempt(
                attempt_number=attempt_number,
                file_path=file_path,
                original_code=original_code,
                proposed_fix=new_code,
                fix_description=description,
                fix_applied=False,
                fix_verified=False,
                regression_test_passed=False,
                error_message=f"Syntax error in proposed fix: {e}",
            )

        # Step 7: Apply the fix
        try:
            with open(full_path, "w") as f:
                f.write(new_full_content)
            logger.info(f"Applied fix to {file_path}: {description}")
        except Exception as e:
            return FixAttempt(
                attempt_number=attempt_number,
                file_path=file_path,
                original_code=original_code,
                proposed_fix=new_code,
                fix_description=description,
                fix_applied=False,
                fix_verified=False,
                regression_test_passed=False,
                error_message=f"Failed to write fix: {e}",
            )

        # Step 8: Run regression tests
        regression_passed = True
        if self.config.run_regression_tests:
            regression_passed = self._run_regression_tests()

        if not regression_passed:
            logger.warning(f"Regression tests failed, rolling back {file_path}")
            self._rollback(full_path, backup)
            return FixAttempt(
                attempt_number=attempt_number,
                file_path=file_path,
                original_code=original_code,
                proposed_fix=new_code,
                fix_description=description,
                fix_applied=True,
                fix_verified=False,
                regression_test_passed=False,
                error_message="Regression tests failed, fix rolled back",
            )

        return FixAttempt(
            attempt_number=attempt_number,
            file_path=file_path,
            original_code=original_code,
            proposed_fix=new_code,
            fix_description=description,
            fix_applied=True,
            fix_verified=False,  # Verified by orchestrator after re-validation
            regression_test_passed=True,
        )

    def _build_error_context(
        self, query: ChallengerQuery, validation: ValidationReport
    ) -> str:
        """Build error context string for the LLM."""
        lines = [
            f"Query: {query.query_text}",
            f"Language: {query.language}",
            f"Category: {query.category.value}",
            f"Reference date: {query.reference_date.isoformat()}",
            f"",
            f"Expected:",
            f"  success: {query.expected_success}",
            f"  start_date: {query.expected_start_date}",
            f"  end_date: {query.expected_end_date}",
            f"  calendar_days: {query.expected_calendar_days}",
            f"  intent_type: {query.expected_intent_type}",
            f"",
            f"Actual agent output:",
        ]
        for k, v in validation.agent_output.items():
            lines.append(f"  {k}: {v}")

        lines.append(f"")
        lines.append(f"Validation result: {validation.result.value}")
        lines.append(f"Mismatches:")
        for field, info in validation.mismatches.items():
            lines.append(f"  {field}: expected={info['expected']}, actual={info['actual']}")

        if validation.error_traceback:
            lines.append(f"")
            lines.append(f"Traceback:")
            lines.append(validation.error_traceback)

        return "\n".join(lines)

    def _identify_candidate_files(
        self, validation: ValidationReport
    ) -> list:
        """Determine which source files to examine based on failure type."""
        result = validation.result
        candidates = []

        if result in (
            ValidationResult.FAIL_START_DATE,
            ValidationResult.FAIL_END_DATE,
            ValidationResult.FAIL_CALENDAR_DAYS,
        ):
            candidates.append("src/date_agent/tools/resolve_period_tool.py")
            candidates.append("src/date_agent/agent/semantic_parser.py")
            candidates.append("src/date_agent/localization/spanish.py")

        elif result == ValidationResult.FAIL_INTENT_TYPE:
            candidates.append("src/date_agent/agent/semantic_parser.py")

        elif result == ValidationResult.FAIL_SUCCESS_FLAG:
            candidates.append("src/date_agent/agent/semantic_parser.py")
            candidates.append("src/date_agent/tools/resolve_period_tool.py")

        elif result == ValidationResult.FAIL_EXCEPTION:
            tb = validation.error_traceback or ""
            for modifiable in self.config.modifiable_files:
                if modifiable in tb:
                    candidates.append(modifiable)
            if not candidates:
                candidates.append("src/date_agent/agent/semantic_parser.py")
                candidates.append("src/date_agent/tools/resolve_period_tool.py")

        else:
            candidates.append("src/date_agent/agent/semantic_parser.py")

        return candidates[:3]

    def _build_diagnosis_prompt(
        self,
        error_context: str,
        source_contents: dict,
        attempt_number: int,
    ) -> str:
        """Build the diagnosis prompt for the LLM."""
        sources = ""
        for path, content in source_contents.items():
            sources += f"\n\n### FILE: {path}\n```python\n{content}\n```\n"

        return f"""## Error Context
{error_context}

## Source Code
{sources}

## Instructions
This is attempt #{attempt_number} to fix this bug.

Analyze the error and propose a MINIMAL fix. The fix should:
1. Fix the specific failing query without breaking other functionality
2. Follow existing code patterns and conventions
3. Be as small as possible (ideally < 10 lines changed)

Respond with:
### DIAGNOSIS
[What went wrong and why]

### FIX
FILE: [relative path to the file to modify]
ORIGINAL:
```python
[exact code to replace - must match the file exactly]
```
NEW:
```python
[replacement code]
```
DESCRIPTION: [one-line description of what the fix does]
"""

    def _parse_fix(
        self, content: str
    ) -> Optional[Tuple[str, str, str, str]]:
        """Parse the LLM's fix proposal.

        Returns (file_path, original_code, new_code, description) or None.
        """
        # Extract FILE
        file_match = re.search(r"FILE:\s*(.+?)(?:\n|$)", content)
        if not file_match:
            return None
        file_path = file_match.group(1).strip().strip("`")

        # Extract ORIGINAL code block
        orig_match = re.search(
            r"ORIGINAL:\s*\n```(?:python)?\n(.*?)```",
            content,
            re.DOTALL,
        )
        if not orig_match:
            return None
        original_code = orig_match.group(1).rstrip("\n")

        # Extract NEW code block
        new_match = re.search(
            r"NEW:\s*\n```(?:python)?\n(.*?)```",
            content,
            re.DOTALL,
        )
        if not new_match:
            return None
        new_code = new_match.group(1).rstrip("\n")

        # Extract DESCRIPTION
        desc_match = re.search(r"DESCRIPTION:\s*(.+?)(?:\n|$)", content)
        description = desc_match.group(1).strip() if desc_match else "LLM fix"

        if not original_code or not new_code or original_code == new_code:
            return None

        return file_path, original_code, new_code, description

    def _run_regression_tests(self) -> bool:
        """Run the existing test suite to check for regressions."""
        try:
            result = subprocess.run(
                self.config.test_command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=self.config.max_test_timeout_seconds,
                cwd=self.project_root,
            )
            if result.returncode != 0:
                logger.warning(
                    f"Regression tests failed:\n{result.stdout[-500:]}\n{result.stderr[-500:]}"
                )
            return result.returncode == 0
        except subprocess.TimeoutExpired:
            logger.warning("Regression tests timed out")
            return False
        except Exception as e:
            logger.warning(f"Failed to run regression tests: {e}")
            return False

    def _rollback(self, file_path: str, original_content: str) -> None:
        """Rollback a file to its original content."""
        with open(file_path, "w") as f:
            f.write(original_content)
        logger.info(f"Rolled back {file_path}")
