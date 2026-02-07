"""CLI entry point for the feedback system."""

import argparse
import asyncio
import logging
import os
import sys


def main():
    parser = argparse.ArgumentParser(
        description="Date Agent Autonomous Feedback System",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Full autonomous run (target 1000 consecutive successes)
  PYTHONPATH=src python -m date_agent.feedback.cli --target 1000

  # Resume from previous run
  PYTHONPATH=src python -m date_agent.feedback.cli --resume feedback_state.json

  # Validation only (no auto-fix)
  PYTHONPATH=src python -m date_agent.feedback.cli --no-auto-fix --target 100

  # Quick smoke test
  PYTHONPATH=src python -m date_agent.feedback.cli --target 10 --batch-size 10
        """,
    )
    parser.add_argument(
        "--target",
        type=int,
        default=1000,
        help="Target consecutive successes (default: 1000)",
    )
    parser.add_argument(
        "--max-queries",
        type=int,
        default=5000,
        help="Maximum total queries (safety cap, default: 5000)",
    )
    parser.add_argument(
        "--resume",
        type=str,
        default=None,
        help="Path to state file to resume from",
    )
    parser.add_argument(
        "--reference-date",
        type=str,
        default="2024-07-15",
        help="Reference date for ground truth (YYYY-MM-DD, default: 2024-07-15)",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=50,
        help="Queries per generation batch (default: 50)",
    )
    parser.add_argument(
        "--log-level",
        type=str,
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
    )
    parser.add_argument(
        "--no-auto-fix",
        action="store_true",
        help="Disable auto-fixing (validation only)",
    )
    parser.add_argument(
        "--no-regression-tests",
        action="store_true",
        help="Skip regression tests after fixes (faster but riskier)",
    )
    parser.add_argument(
        "--state-file",
        type=str,
        default="feedback_state.json",
        help="Path to state file (default: feedback_state.json)",
    )
    parser.add_argument(
        "--log-dir",
        type=str,
        default="feedback_logs",
        help="Directory for reports (default: feedback_logs)",
    )

    args = parser.parse_args()

    # Setup logging
    logging.basicConfig(
        level=getattr(logging, args.log_level),
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
        handlers=[
            logging.StreamHandler(sys.stdout),
        ],
    )

    # Build config
    from date_agent.feedback.config import FeedbackConfig

    config = FeedbackConfig(
        target_consecutive_successes=args.target,
        max_total_queries=args.max_queries,
        reference_date=args.reference_date,
        batch_size=args.batch_size,
        auto_fix_enabled=not args.no_auto_fix,
        run_regression_tests=not args.no_regression_tests,
        state_file=args.state_file,
        log_dir=args.log_dir,
    )

    # Run
    from date_agent.feedback.orchestrator import FeedbackOrchestrator

    orchestrator = FeedbackOrchestrator(config)
    state = asyncio.run(orchestrator.run(resume_from=args.resume))

    # Print summary
    print(f"\n{'=' * 60}")
    print(f"Feedback Loop Complete")
    print(f"{'=' * 60}")
    print(f"Total queries:         {state.total_queries_processed}")
    print(f"Passes:                {state.total_passes}")
    print(f"Fixes applied:         {state.total_fixes_applied}")
    print(f"Skipped:               {state.total_skipped}")
    print(f"Consecutive successes: {state.consecutive_successes}")
    print(f"Max consecutive:       {state.max_consecutive_achieved}")
    print(f"Target reached:        {state.consecutive_successes >= args.target}")
    print(f"Reason:                {state.completion_reason}")
    print(f"{'=' * 60}")


if __name__ == "__main__":
    main()
