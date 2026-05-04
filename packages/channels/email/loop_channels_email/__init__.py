"""Loop Email (SES) channel.

Translates SES inbound notifications (delivered to an SQS queue or
SNS topic) into :class:`InboundEvent` envelopes, and translates the
runtime's :class:`OutboundFrame` stream into SES ``SendEmail``
request bodies.

The adapter is HTTP-framework-agnostic -- the host service owns the
queue consumer and SES client; we only handle wire-shape translation
and conversation indexing.
"""

from loop_channels_email.channel import EmailChannel, EmailConversationIndex
from loop_channels_email.dkim_inbound import (
    DnsTxtLookup,
    InboundDkimResult,
    InboundDkimStatus,
    verify_dkim_inbound,
)
from loop_channels_email.messages import to_send_email_body
from loop_channels_email.parser import parse_ses_inbound
from loop_channels_email.sns_verify import (
    SigningCertFetcher,
    SnsSignatureError,
    verify_sns_signature,
)

__all__ = [
    "DnsTxtLookup",
    "EmailChannel",
    "EmailConversationIndex",
    "InboundDkimResult",
    "InboundDkimStatus",
    "SigningCertFetcher",
    "SnsSignatureError",
    "parse_ses_inbound",
    "to_send_email_body",
    "verify_dkim_inbound",
    "verify_sns_signature",
]
