# Channels

A channel is the transport that carries user messages into your agent and
agent responses back out. Loop ships adapters for the channels most
products need; you can add your own by implementing the `Channel` protocol.

## Built-in channels

| Channel | Inbound | Outbound | Streaming | Status |
| --- | --- | --- | --- | --- |
| `web-widget` | yes | yes | SSE | GA |
| `slack` | yes | yes | webhooks | GA |
| `whatsapp-cloud` | yes | yes | webhooks | GA |
| `sms-twilio` | yes | yes | no | GA |
| `voice-webrtc` | yes | yes | bidi audio | beta |
| `email-imap` | yes | yes | no | beta |

## Channel responsibilities

A `Channel` adapter is responsible for **only** transport: parsing the
provider's payload into a `ChannelMessage`, handing it to the runtime,
and serialising the agent's `AgentResponse` back into the provider's
format. It does not own routing, auth, or retries; those live in the
gateway.

```python
class Channel(Protocol):
    name: str

    async def receive(self, request: Request) -> ChannelMessage: ...
    async def send(self, message: ChannelMessage) -> None: ...
```

See `packages/channels/` for reference implementations.

## Adding a new channel

1. Implement the protocol in `packages/channels/loop_channels/<name>.py`.
2. Add a smoke test that round-trips a fixture payload.
3. Register it in `loop_channels.__init__`.
4. Document it on this page.

The control plane will pick it up automatically on the next deploy.
