"""Loop SMS channel adapter for Twilio-compatible providers."""

from loop_channels_sms.compliance import (
    ComplianceDecision,
    ComplianceKeywordHandler,
    InMemorySmsConsentStore,
    SmsConsentStore,
)
from loop_channels_sms.connect import (
    TwilioConnectFlow,
    TwilioConnectRequest,
    TwilioConnectResult,
    TwilioNumberCandidate,
)
from loop_channels_sms.twilio import (
    SmsInboundParser,
    SmsOutboundMessage,
    TwilioSendResult,
    TwilioSmsAdapter,
    TwilioSmsClient,
)
from loop_channels_sms.verify import (
    TwilioSignatureError,
    verify_twilio_signature,
)

__all__ = [
    "ComplianceDecision",
    "ComplianceKeywordHandler",
    "InMemorySmsConsentStore",
    "SmsConsentStore",
    "SmsInboundParser",
    "SmsOutboundMessage",
    "TwilioConnectFlow",
    "TwilioConnectRequest",
    "TwilioConnectResult",
    "TwilioNumberCandidate",
    "TwilioSendResult",
    "TwilioSignatureError",
    "TwilioSmsAdapter",
    "TwilioSmsClient",
    "verify_twilio_signature",
]
