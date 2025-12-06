# Changelog

All notable changes to the RAW project will be documented in this file.


## [Unreleased]

### Added
- **Registry**: `ToolRegistry` protocol for centralized tool discovery.
- **Git Support**: `raw install <url>` to fetch remote tools from git repos.

### Changed
- **Refactor**: Complete migration of `src/raw_runtime` to Clean Architecture (`protocols/` vs `drivers/`).
- **Refactor**: Split monolithic `src/raw` into domain modules (`engine/`, `discovery/`, `scaffold/`).

## [0.7.0] - 2025-12-08

### Added
- **Unified Tools**: New architecture standardizing on a single `tools/` directory for both local code and managed dependencies.
- **Migration**: Logic to treat tools as standard Python packages.

### Removed
- **Legacy**: Deleted `raw_tools/` and `examples/` directories to enforce the new Unified Tools pattern.

## [0.6.0] - 2025-12-08

### Added
- **Connected Mode**: "Mothership" architecture allowing workflows to register with a central server.
- **Orchestrator Protocol**: Abstraction for triggering workflows via subprocess (`Local`) or HTTP (`Http`).
- **External Events**: `wait_for_webhook()` function to pause workflows until an external signal is received.

## [0.5.0] - 2025-12-07

### Added
- **Control Plane**: `raw serve` command (FastAPI) providing a daemon for webhooks and monitoring.
- **Dashboard**: Professional HTML5/Tailwind/Alpine.js web interface for `raw serve`.
- **Approvals API**: HTTP endpoints to list pending approvals and submit decisions remotely.

### Fixed
- **Concurrency**: Race conditions in `ApprovalRegistry` fixed by keying approvals with `run_id`.

## [0.4.0] - 2025-12-07

### Added
- **Agent Experience**: `raw hooks install` command to inject `raw prime` context into Claude Code sessions automatically.
- **Human Interface**: `HumanInterface` protocol abstracting console vs. remote user interactions.

## [0.3.0] - 2025-12-07

### Added
- **Observability**: `TelemetrySink` protocol with `Console` and `JsonFile` drivers.
- **Storage**: `StorageBackend` protocol with `FileSystem` and `Memory` drivers.
- **Secrets**: `SecretProvider` protocol supporting environment variables and `.env` files.

## [0.2.0] - 2025-12-06

### Added
- **Prompt-First Creation**: `raw create --intent "..."` command to scaffold workflows from natural language.
- **Dry Run**: `raw run --dry` command with mock data generation capabilities.
- **Publishing**: `raw publish` command to freeze workflows and pin tool versions (Immutability).

### Changed
- **DX**: Default workflow path moved to `runs/<timestamp>/` for better history tracking.

## [0.1.0] - 2025-12-06

### Added
- **Core**: Initial release of RAW framework.
- **Runtime**: `BaseWorkflow` with `@step`, `@retry`, `@cache_step`.
- **CLI**: Basic `raw init`, `raw run`, `raw list` commands.
- **Event Bus**: Foundational event-driven architecture.

