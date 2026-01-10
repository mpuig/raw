# RAW Overview

RAW is a local orchestration platform that turns agent-written code into **durable, runnable workflows**.

**Audience:** Business stakeholders, product leaders, engineering leads
**Type:** Overview

---

## The Problem RAW Solves

AI coding agents can generate workflows quickly, but the output is often:

- **Ephemeral**: runs once, then the “state of work” is lost
- **Hard to operate**: limited logs, weak provenance, unclear retry/caching behavior
- **Hard to iterate**: no built-in verification loop or quality gates

## What RAW Provides

RAW separates **intelligence** from **infrastructure**:

- **Agent (intelligence):** understands intent, designs logic, reacts to failures
- **RAW (infrastructure):** execution, state/logs, caching/retries, reproducibility, safety rails

At a glance:

- **Workflows** live in `.raw/workflows/<workflow-id>/`
- **Tools** are reusable libraries in `tools/<tool-name>/`
- **Runs** produce structured outputs and logs (including dry runs with mocks)

## Two Layers (High-Level)

- **Layer 1: Builder** (`raw build`)
  - Iterates plan → execute → verify using deterministic gates
  - Produces/updates workflow code (and tools, if needed)
  - Captures a durable build journal for resume and debugging
- **Layer 2: Runner** (`raw run`)
  - Executes workflows deterministically (optionally with selective agentic steps)
  - Produces run artifacts, logs, and execution metadata

This split is intentional: build-time work is iterative and agentic; run-time work is mostly deterministic and operational.

## Agent-Native Principles (What “Good” Looks Like)

- **Parity:** anything a human can do via CLI should be doable by an agent (CLI and SDK surfaces stay aligned).
- **Composability:** workflows are code + tools (small reusable libraries), not opaque graphs.
- **Verification loops:** workflows and tools are developed with gates (validate, dry runs, optional tests).
- **Durability:** work products are stored on disk (workflows/tools/runs) and can be resumed/debugged.

## Typical Use Cases

- “Build a workflow that…” (data ingestion, analysis, reporting, notifications)
- Tooling factories (“create a reusable tool for X, then use it in N workflows”)
- Repeatable operational jobs (cron/webhook-triggered workflows via daemon mode)

## Success Looks Like

- Agents can generate workflows **reliably** with an explicit verify loop
- Workflow runs are **observable** and **debuggable**
- Work products (tools, workflows, results) are **durable** and **reusable**

## Related Docs

- Getting started: [QUICKSTART.md](QUICKSTART.md), [GUIDE.md](GUIDE.md)
- Builder: [BUILDER.md](BUILDER.md)
- Reference: [REFERENCE.md](REFERENCE.md)
- Architecture: [ARCHITECTURE.md](ARCHITECTURE.md)
