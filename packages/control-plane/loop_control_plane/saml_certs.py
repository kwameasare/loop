"""SAML IdP signing-certificate rotation primitives (S610).

Per ``engineering/SSO_SAML.md``, every tenant SSO record carries the
IdP's signing certificate (or chain). Production IdPs rotate those
certs on a schedule, and the SP must accept assertions signed by
**either** the active cert or a pending cert during a grace window
so login doesn't break at the rotation instant.

This module models that bundle and the rotation primitives. It is
deliberately a pure-data layer (no XML, no crypto): the actual
signature verification happens inside the
:class:`~loop_control_plane.saml.SamlValidator` implementation, which
takes a :class:`CertificateBundle` and walks :func:`trust_set` to know
which PEMs to try.

Usage
-----

1. Operator drops a new IdP cert PEM into Studio → Settings → SSO.
2. cp-api calls :func:`stage_certificate` to record the pending cert
   alongside the still-active one. ``staged_at`` and ``grace_until``
   are set; both certs are now in :func:`trust_set`.
3. After the grace window, a daily job calls :func:`promote_pending`
   which moves the pending cert to active and clears staging metadata.
4. If the IdP rolls back, :func:`rollback_pending` drops the staged
   cert without touching the active one.
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from datetime import datetime, timedelta


class CertRotationError(ValueError):
    """Raised on illegal cert-bundle state transitions."""


DEFAULT_GRACE = timedelta(days=7)


@dataclass(frozen=True, slots=True)
class CertificateBundle:
    """Active + (optional) pending IdP signing certificate.

    PEM strings are stored as-is; this module never parses them. The
    consuming validator does that.
    """

    active_pem: str
    """Currently-trusted IdP signing certificate (PEM)."""

    pending_pem: str | None = None
    """Newly-staged certificate; trusted alongside ``active`` until
    ``grace_until``."""

    staged_at: datetime | None = None
    """When the pending cert was staged."""

    grace_until: datetime | None = None
    """Last instant the pending cert is in :func:`trust_set` alongside
    the active cert. After this, callers should call
    :func:`promote_pending`."""

    history: tuple[str, ...] = field(default_factory=tuple)
    """Previously-active cert PEMs (most-recent first), kept for
    incident forensics. Capped at 5."""


_HISTORY_DEPTH = 5


def trust_set(bundle: CertificateBundle, now: datetime) -> tuple[str, ...]:
    """The set of PEMs the SAML validator should try in order.

    During the grace window: ``(active, pending)``.
    After grace expires: ``(active,)`` only — caller is responsible
    for invoking :func:`promote_pending` shortly thereafter.
    """
    if bundle.pending_pem is None:
        return (bundle.active_pem,) if bundle.active_pem else ()
    if bundle.grace_until is None or now > bundle.grace_until:
        return (bundle.active_pem,)
    return (bundle.active_pem, bundle.pending_pem)


def stage_certificate(
    bundle: CertificateBundle,
    new_pem: str,
    now: datetime,
    grace: timedelta = DEFAULT_GRACE,
) -> CertificateBundle:
    """Stage a new IdP cert. Returns a new bundle with ``pending`` set."""
    if not new_pem.strip():
        raise CertRotationError("cannot stage an empty PEM")
    if bundle.pending_pem is not None:
        raise CertRotationError(
            "a pending cert is already staged; rollback or promote it first"
        )
    if new_pem == bundle.active_pem:
        raise CertRotationError("staged cert is identical to the active cert")
    return replace(
        bundle,
        pending_pem=new_pem,
        staged_at=now,
        grace_until=now + grace,
    )


def promote_pending(bundle: CertificateBundle) -> CertificateBundle:
    """Move ``pending`` to ``active``. Old active goes to history."""
    if bundle.pending_pem is None:
        raise CertRotationError("no pending cert to promote")
    new_history = (bundle.active_pem, *bundle.history)[:_HISTORY_DEPTH]
    return CertificateBundle(
        active_pem=bundle.pending_pem,
        pending_pem=None,
        staged_at=None,
        grace_until=None,
        history=new_history,
    )


def rollback_pending(bundle: CertificateBundle) -> CertificateBundle:
    """Drop the pending cert, leave active untouched."""
    if bundle.pending_pem is None:
        raise CertRotationError("no pending cert to rollback")
    return replace(bundle, pending_pem=None, staged_at=None, grace_until=None)
