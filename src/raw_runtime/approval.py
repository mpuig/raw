"""Human-in-the-loop approval for RAW workflows.

Provides blocking approval mechanisms for workflows that require human
intervention before continuing. Supports different modes:

- Console mode (raw run): Prompts user via input()
- Web mode (raw serve): Waits for API call via asyncio.Future

Uses asyncio.Future for async blocking waits in daemon mode.

Note: Protocol is in raw_runtime.protocols.approval,
      Implementations are in raw_runtime.drivers.approval.
      This module re-exports for backwards compatibility.
"""

import asyncio
from typing import TYPE_CHECKING, Any

from rich.console import Console

from raw_runtime.context import get_workflow_context
from raw_runtime.drivers.approval import AutoApprovalHandler, ConsoleApprovalHandler
from raw_runtime.events import (
    ApprovalReceivedEvent,
    ApprovalRequestedEvent,
    ApprovalTimeoutEvent,
)
from raw_runtime.protocols.approval import ApprovalHandler

if TYPE_CHECKING:
    from raw_runtime.bus import ApprovalRegistry


# Global approval handler (set based on execution mode)
_approval_handler: ApprovalHandler | None = None


def set_approval_handler(handler: ApprovalHandler | None) -> None:
    """Set the global approval handler."""
    global _approval_handler
    _approval_handler = handler


def get_approval_handler() -> ApprovalHandler:
    """Get the current approval handler (defaults to console)."""
    if _approval_handler is None:
        return ConsoleApprovalHandler()
    return _approval_handler


def wait_for_approval(
    prompt: str,
    step_name: str | None = None,
    options: list[str] | None = None,
    context: dict[str, Any] | None = None,
    timeout_seconds: float | None = None,
) -> str:
    """Block until human approval is received.

    In connected mode (RAW_SERVER_URL set), this polls the server for
    approval decisions. In local mode, prompts the user via console.

    Args:
        prompt: Question to ask the user
        step_name: Name of the step requiring approval (auto-detected if None)
        options: Available choices (default: ["approve", "reject"])
        context: Additional context to show the user
        timeout_seconds: Maximum time to wait (default: 300s in connected mode)

    Returns:
        The user's decision (one of the options)

    Raises:
        TimeoutError: If timeout is exceeded

    Usage:
        @raw_step("deploy")
        def deploy(self):
            decision = wait_for_approval(
                prompt="Deploy to production?",
                context={"version": "1.2.3", "environment": "prod"},
            )
            if decision == "approve":
                do_deploy()
            else:
                print("Deployment cancelled")
    """
    from raw_runtime.connection import get_connection

    workflow_context = get_workflow_context()

    if options is None:
        options = ["approve", "reject"]
    if context is None:
        context = {}
    if step_name is None:
        step_name = "approval"

    if workflow_context:
        workflow_context.emit(
            ApprovalRequestedEvent(
                workflow_id=workflow_context.workflow_id,
                run_id=workflow_context.run_id,
                step_name=step_name,
                prompt=prompt,
                options=options,
                timeout_seconds=timeout_seconds,
                context=context,
            )
        )

    connection = get_connection()
    if connection and connection.is_connected:
        console = Console()
        console.print()
        console.print(f"[bold yellow]⏸[/] [bold]Waiting for approval:[/] {step_name}")
        console.print(f"  {prompt}")
        if context:
            console.print("[dim]Context:[/]")
            for key, value in context.items():
                console.print(f"  [dim]{key}:[/] {value}")
        console.print(f"[dim]Options: {', '.join(options)}[/]")
        console.print("[dim]Approval can be granted via: POST /approve/{run_id}/{step}[/]")

        try:
            event = connection.wait_for_event(
                event_type="approval",
                step_name=step_name,
                prompt=prompt,
                options=options,
                context=context,
                timeout_seconds=timeout_seconds or 300,
            )
            decision = event.get("decision", "reject")
            console.print(f"[green]✓[/] Received approval: {decision}")
        except TimeoutError:
            console.print("[red]✗[/] Approval timeout")
            raise
    else:
        handler = get_approval_handler()
        decision = handler.request_approval(
            step_name=step_name,
            prompt=prompt,
            options=options,
            context=context,
            timeout_seconds=timeout_seconds,
        )

    if workflow_context:
        workflow_context.emit(
            ApprovalReceivedEvent(
                workflow_id=workflow_context.workflow_id,
                run_id=workflow_context.run_id,
                step_name=step_name,
                decision=decision,
            )
        )

    return decision


# Global approval registry for daemon mode
_approval_registry: "ApprovalRegistry | None" = None


def set_approval_registry(registry: "ApprovalRegistry | None") -> None:
    """Set the global approval registry for daemon mode."""
    global _approval_registry
    _approval_registry = registry


def get_approval_registry() -> "ApprovalRegistry | None":
    """Get the current approval registry."""
    return _approval_registry


async def wait_for_approval_async(
    prompt: str,
    step_name: str | None = None,
    options: list[str] | None = None,
    context: dict[str, Any] | None = None,
    timeout_seconds: float | None = None,
) -> str:
    """Async version of wait_for_approval for `raw serve`.

    In daemon mode with ApprovalRegistry, this awaits a Future that gets
    resolved when approval is received via API. Without a registry, it
    falls back to the sync handler in a thread pool.

    The Future-based approach allows:
    - Non-blocking wait in the async event loop
    - External resolution via HTTP API (FastAPI endpoint)
    - Proper timeout handling with asyncio.wait_for
    """
    workflow_context = get_workflow_context()

    if options is None:
        options = ["approve", "reject"]
    if context is None:
        context = {}
    if step_name is None:
        step_name = "approval"

    workflow_id = workflow_context.workflow_id if workflow_context else "unknown"

    if workflow_context:
        workflow_context.emit(
            ApprovalRequestedEvent(
                workflow_id=workflow_id,
                run_id=workflow_context.run_id,
                step_name=step_name,
                prompt=prompt,
                options=options,
                timeout_seconds=timeout_seconds,
                context=context,
            )
        )

    run_id = workflow_context.run_id if workflow_context else None

    registry = get_approval_registry()
    if registry is not None:
        future = registry.request(workflow_id, step_name, run_id)
        try:
            if timeout_seconds:
                decision = await asyncio.wait_for(future, timeout=timeout_seconds)
            else:
                decision = await future
        except asyncio.TimeoutError:
            registry.cancel(workflow_id, step_name, "Timeout", run_id)
            if workflow_context:
                workflow_context.emit(
                    ApprovalTimeoutEvent(
                        workflow_id=workflow_id,
                        run_id=workflow_context.run_id,
                        step_name=step_name,
                        timeout_seconds=timeout_seconds or 0,
                    )
                )
            raise TimeoutError(f"Approval timeout after {timeout_seconds}s") from None
    else:
        handler = get_approval_handler()
        loop = asyncio.get_running_loop()

        if timeout_seconds:
            try:
                decision = await asyncio.wait_for(
                    loop.run_in_executor(
                        None,
                        lambda: handler.request_approval(
                            step_name, prompt, options, context, timeout_seconds
                        ),
                    ),
                    timeout=timeout_seconds,
                )
            except asyncio.TimeoutError:
                if workflow_context:
                    workflow_context.emit(
                        ApprovalTimeoutEvent(
                            workflow_id=workflow_id,
                            run_id=workflow_context.run_id,
                            step_name=step_name,
                            timeout_seconds=timeout_seconds,
                        )
                    )
                raise TimeoutError(f"Approval timeout after {timeout_seconds}s") from None
        else:
            decision = await loop.run_in_executor(
                None,
                lambda: handler.request_approval(
                    step_name, prompt, options, context, timeout_seconds
                ),
            )

    if workflow_context:
        workflow_context.emit(
            ApprovalReceivedEvent(
                workflow_id=workflow_id,
                run_id=workflow_context.run_id,
                step_name=step_name,
                decision=decision,
            )
        )

    return decision


def wait_for_webhook(
    step_name: str,
    timeout_seconds: float = 300,
) -> dict[str, Any]:
    """Wait for an external webhook payload. Requires connected mode.

    This function blocks until an external system sends a webhook to the
    RAW server, which routes the payload to this waiting workflow.

    Args:
        step_name: Unique identifier for this webhook wait point
        timeout_seconds: Maximum wait time (default: 5 minutes)

    Returns:
        The webhook payload dict

    Raises:
        RuntimeError: If not connected to RAW server
        TimeoutError: If no webhook received within timeout

    Usage:
        @step("wait_external")
        def wait_for_data(self) -> dict:
            payload = wait_for_webhook("external_data")
            return payload
    """
    from raw_runtime.connection import get_connection

    connection = get_connection()
    if not connection or not connection.is_connected:
        raise RuntimeError(
            "Cannot wait for webhook: not connected to RAW server. "
            "Set RAW_SERVER_URL environment variable and ensure server is running."
        )

    console = Console()
    console.print()
    console.print(f"[bold yellow]⏸[/] [bold]Waiting for webhook:[/] {step_name}")
    console.print(
        f"[dim]Webhook can be sent via: POST /webhook/{{workflow_id}} with run_id={connection.run_id}[/]"
    )

    try:
        event = connection.wait_for_event(
            event_type="webhook",
            step_name=step_name,
            timeout_seconds=timeout_seconds,
        )
        console.print("[green]✓[/] Received webhook")
        return event
    except TimeoutError:
        console.print(f"[red]✗[/] Webhook timeout after {timeout_seconds}s")
        raise


__all__ = [
    "ApprovalHandler",
    "ConsoleApprovalHandler",
    "AutoApprovalHandler",
    "get_approval_handler",
    "set_approval_handler",
    "wait_for_approval",
    "wait_for_approval_async",
    "wait_for_webhook",
    "get_approval_registry",
    "set_approval_registry",
]
