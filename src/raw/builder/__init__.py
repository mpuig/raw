"""RAW Builder - Agentic workflow development loop.

The Builder implements a plan → execute → verify → iterate loop for workflow development.
It emulates coding-agent behavior while maintaining deterministic quality gates.

Core Components:
- Loop Controller: Orchestrates plan/execute cycles with budget enforcement
- Mode Enforcement: Read-only plan mode vs full-access execute mode
- Gate Runner: Validates workflows (validate, dry, tests, lint)
- Skill Discovery: Finds and injects repo-local builder skills
- Journal: Append-only event log for debugging and resume
"""

from raw.builder.entrypoint import build_workflow

__all__ = ["build_workflow"]
