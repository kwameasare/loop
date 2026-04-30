"""EmailChannel: SES-backed surface adapter."""

from __future__ import annotations

import asyncio
from typing import Any
from uuid import UUID, uuid4

from loop_channels_core import ChannelDispatcher

from loop_channels_email.messages import to_send_email_body
from loop_channels_email.parser import parse_ses_inbound


class EmailConversationIndex:
    """Maps an RFC-822 thread-id to a stable conversation UUID.

    Persistent storage is left to the host service; this in-memory
    impl matches the WhatsApp / Slack pattern and is good enough for
    tests + a single-replica dev runner.
    """

    def __init__(self) -> None:
        self._by_thread: dict[str, UUID] = {}
        self._lock = asyncio.Lock()

    async def get_or_create(self, *, thread_id: str) -> UUID:
        async with self._lock:
            existing = self._by_thread.get(thread_id)
            if existing is not None:
                return existing
            new = uuid4()
            self._by_thread[thread_id] = new
            return new

    async def get(self, *, thread_id: str) -> UUID | None:
        async with self._lock:
            return self._by_thread.get(thread_id)


class EmailChannel:
    """Bridges an SES inbound payload to the runtime dispatcher.

    ``handle_event`` returns the list of SES SendEmail request bodies
    the host should POST to the SES API; the host owns transport.
    """

    name: str = "email"

    def __init__(
        self,
        *,
        workspace_id: UUID,
        agent_id: UUID,
        sender: str,
        conversations: EmailConversationIndex | None = None,
    ) -> None:
        self._workspace_id = workspace_id
        self._agent_id = agent_id
        self._sender = sender
        self._conversations = conversations or EmailConversationIndex()
        self._dispatcher: ChannelDispatcher | None = None

    async def start(self, dispatcher: ChannelDispatcher) -> None:
        self._dispatcher = dispatcher

    async def stop(self) -> None:
        self._dispatcher = None

    async def handle_event(self, payload: dict[str, Any]) -> list[dict[str, Any]]:
        if self._dispatcher is None:
            raise RuntimeError("EmailChannel.start() not called")

        thread_id = _peek_thread_id(payload)
        if thread_id is None:
            return []

        conversation_id = await self._conversations.get_or_create(thread_id=thread_id)
        parsed = parse_ses_inbound(
            payload,
            workspace_id=self._workspace_id,
            agent_id=self._agent_id,
            conversation_id=conversation_id,
        )
        if parsed is None:
            return []
        event, recipient = parsed
        subject = event.metadata.get("subject", "")
        in_reply_to = event.metadata.get("message_id")

        out: list[dict[str, Any]] = []
        async for frame in self._dispatcher.dispatch(event):
            body = to_send_email_body(
                frame,
                to=recipient,
                sender=self._sender,
                subject=subject,
                in_reply_to=in_reply_to,
            )
            if body is not None:
                out.append(body)
        return out


def _peek_thread_id(payload: dict[str, Any]) -> str | None:
    """Lightweight peek at the thread-id without parsing the whole event.

    The full parser computes the canonical thread root, but the
    channel layer needs the thread-id *first* to allocate the
    conversation UUID. Order of preference: References[0] ->
    Message-Id header -> SES messageId.
    """
    mail = payload.get("mail") or {}
    if not isinstance(mail, dict):
        return None
    common = mail.get("commonHeaders") or {}
    refs = common.get("references")
    if isinstance(refs, list) and refs:
        return str(refs[0])
    if isinstance(refs, str) and refs.strip():
        return refs.strip().split()[0]
    headers = mail.get("headers")
    if isinstance(headers, list):
        for header in headers:
            if str(header.get("name", "")).lower() == "message-id":
                value = header.get("value")
                if value:
                    return str(value)
    msg_id = mail.get("messageId")
    return str(msg_id) if msg_id else None


__all__ = ["EmailChannel", "EmailConversationIndex"]
