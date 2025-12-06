"""EventBus implementations."""

import asyncio
from collections.abc import Awaitable, Callable

from raw_runtime.events import Event, EventType

SyncHandler = Callable[[Event], None]
AsyncHandler = Callable[[Event], Awaitable[None]]


class LocalEventBus:
    """Synchronous in-process event bus for `raw run`.

    Ephemeral bus that lives for a single workflow execution.
    Handlers are called synchronously in registration order.
    """

    def __init__(self) -> None:
        self._handlers: list[tuple[SyncHandler, list[EventType] | None]] = []

    def emit(self, event: Event) -> None:
        """Emit an event to all matching handlers."""
        for handler, event_types in self._handlers:
            if event_types is None or event.event_type in event_types:
                handler(event)

    def subscribe(
        self,
        handler: SyncHandler,
        event_types: list[EventType] | None = None,
    ) -> None:
        """Subscribe a handler to events."""
        self._handlers.append((handler, event_types))

    def unsubscribe(self, handler: SyncHandler) -> None:
        """Unsubscribe a handler from events."""
        self._handlers = [(h, et) for h, et in self._handlers if h != handler]

    def clear(self) -> None:
        """Remove all handlers."""
        self._handlers.clear()


class NullEventBus:
    """No-op event bus for testing or when events are disabled."""

    def emit(self, event: Event) -> None:
        """Discard event."""
        pass

    def subscribe(
        self,
        handler: SyncHandler,
        event_types: list[EventType] | None = None,
    ) -> None:
        """No-op."""
        pass

    def unsubscribe(self, handler: SyncHandler) -> None:
        """No-op."""
        pass


class AsyncEventBus:
    """Async-native event bus using asyncio.Queue.

    Designed for `raw serve` daemon mode with FastAPI integration.
    Events are pushed to a queue and processed by async handlers.

    Usage:
        bus = AsyncEventBus()

        async def my_handler(event: Event) -> None:
            print(f"Received: {event}")

        bus.subscribe(my_handler)

        # Start processing (runs until stopped)
        task = asyncio.create_task(bus.start())

        # Emit events
        await bus.emit_async(event)

        # Stop processing
        await bus.stop()
    """

    def __init__(self, maxsize: int = 0) -> None:
        self._queue: asyncio.Queue[Event | None] = asyncio.Queue(maxsize=maxsize)
        self._handlers: list[tuple[AsyncHandler, list[EventType] | None]] = []
        self._sync_handlers: list[tuple[SyncHandler, list[EventType] | None]] = []
        self._running = False
        self._task: asyncio.Task[None] | None = None

    async def emit_async(self, event: Event) -> None:
        """Emit an event asynchronously (adds to queue)."""
        await self._queue.put(event)

    def emit(self, event: Event) -> None:
        """Emit an event synchronously (for compatibility).

        If called from within an async context, schedules the emit.
        Otherwise, processes handlers directly.
        """
        try:
            loop = asyncio.get_running_loop()
            loop.call_soon(lambda: self._queue.put_now_wait(event))
        except RuntimeError:
            self._process_sync(event)

    def _process_sync(self, event: Event) -> None:
        """Process event with sync handlers only."""
        for handler, event_types in self._sync_handlers:
            if event_types is None or event.event_type in event_types:
                handler(event)

    def subscribe(
        self,
        handler: SyncHandler,
        event_types: list[EventType] | None = None,
    ) -> None:
        """Subscribe a synchronous handler."""
        self._sync_handlers.append((handler, event_types))

    def subscribe_async(
        self,
        handler: AsyncHandler,
        event_types: list[EventType] | None = None,
    ) -> None:
        """Subscribe an asynchronous handler."""
        self._handlers.append((handler, event_types))

    def unsubscribe(self, handler: SyncHandler) -> None:
        """Unsubscribe a synchronous handler."""
        self._sync_handlers = [(h, et) for h, et in self._sync_handlers if h != handler]

    def unsubscribe_async(self, handler: AsyncHandler) -> None:
        """Unsubscribe an asynchronous handler."""
        self._handlers = [(h, et) for h, et in self._handlers if h != handler]

    async def start(self) -> None:
        """Start processing events from the queue."""
        self._running = True
        while self._running:
            event = await self._queue.get()
            if event is None:
                break
            await self._dispatch(event)
            self._queue.task_done()

    async def _dispatch(self, event: Event) -> None:
        """Dispatch event to all matching handlers."""
        for sync_handler, event_types in self._sync_handlers:
            if event_types is None or event.event_type in event_types:
                sync_handler(event)

        tasks: list[Awaitable[None]] = []
        for async_handler, event_types in self._handlers:
            if event_types is None or event.event_type in event_types:
                tasks.append(async_handler(event))
        if tasks:
            await asyncio.gather(*tasks)

    async def stop(self) -> None:
        """Stop processing events."""
        self._running = False
        await self._queue.put(None)  # Sentinel to unblock the loop

    def clear(self) -> None:
        """Remove all handlers."""
        self._handlers.clear()
        self._sync_handlers.clear()
