"""Tests for SAML SP cert-rotation primitives (S610)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from loop_control_plane.saml_certs import (
    DEFAULT_GRACE,
    CertificateBundle,
    CertRotationError,
    promote_pending,
    rollback_pending,
    stage_certificate,
    trust_set,
)

PEM_A = "-----BEGIN CERTIFICATE-----\nAAA\n-----END CERTIFICATE-----"
PEM_B = "-----BEGIN CERTIFICATE-----\nBBB\n-----END CERTIFICATE-----"
PEM_C = "-----BEGIN CERTIFICATE-----\nCCC\n-----END CERTIFICATE-----"
T0 = datetime(2026, 1, 1, 0, 0, tzinfo=UTC)


def test_trust_set_active_only() -> None:
    bundle = CertificateBundle(active_pem=PEM_A)
    assert trust_set(bundle, T0) == (PEM_A,)


def test_stage_certificate_puts_both_in_trust_set_during_grace() -> None:
    bundle = CertificateBundle(active_pem=PEM_A)
    staged = stage_certificate(bundle, PEM_B, T0)
    assert staged.pending_pem == PEM_B
    assert staged.grace_until == T0 + DEFAULT_GRACE
    # Inside grace, both certs trusted (so SAML responses signed with
    # either one verify without redeploy).
    assert trust_set(staged, T0 + timedelta(days=3)) == (PEM_A, PEM_B)


def test_trust_set_drops_pending_after_grace_expires() -> None:
    bundle = CertificateBundle(active_pem=PEM_A)
    staged = stage_certificate(bundle, PEM_B, T0, grace=timedelta(hours=1))
    after = T0 + timedelta(hours=2)
    assert trust_set(staged, after) == (PEM_A,)


def test_stage_rejects_duplicate_pending() -> None:
    bundle = CertificateBundle(active_pem=PEM_A)
    staged = stage_certificate(bundle, PEM_B, T0)
    with pytest.raises(CertRotationError, match="already staged"):
        stage_certificate(staged, PEM_C, T0 + timedelta(hours=1))


def test_stage_rejects_pem_identical_to_active() -> None:
    bundle = CertificateBundle(active_pem=PEM_A)
    with pytest.raises(CertRotationError, match="identical"):
        stage_certificate(bundle, PEM_A, T0)


def test_stage_rejects_empty_pem() -> None:
    bundle = CertificateBundle(active_pem=PEM_A)
    with pytest.raises(CertRotationError, match="empty"):
        stage_certificate(bundle, "   \n", T0)


def test_promote_pending_moves_active_to_history() -> None:
    bundle = CertificateBundle(active_pem=PEM_A)
    staged = stage_certificate(bundle, PEM_B, T0)
    promoted = promote_pending(staged)
    assert promoted.active_pem == PEM_B
    assert promoted.pending_pem is None
    assert promoted.history == (PEM_A,)
    assert promoted.grace_until is None


def test_promote_without_pending_errors() -> None:
    bundle = CertificateBundle(active_pem=PEM_A)
    with pytest.raises(CertRotationError, match="no pending"):
        promote_pending(bundle)


def test_history_capped_at_five_entries() -> None:
    pems = [f"PEM-{i}" for i in range(8)]
    bundle = CertificateBundle(active_pem=pems[0])
    for next_pem in pems[1:]:
        staged = stage_certificate(bundle, next_pem, T0)
        bundle = promote_pending(staged)
    # Bundle now has pems[7] active and the previous five (pems[2..6]) in history.
    assert bundle.active_pem == pems[7]
    assert len(bundle.history) == 5
    assert bundle.history[0] == pems[6]


def test_rollback_pending_clears_staging_metadata() -> None:
    bundle = CertificateBundle(active_pem=PEM_A)
    staged = stage_certificate(bundle, PEM_B, T0)
    rolled = rollback_pending(staged)
    assert rolled.active_pem == PEM_A
    assert rolled.pending_pem is None
    assert rolled.staged_at is None
    assert rolled.grace_until is None


def test_rollback_without_pending_errors() -> None:
    bundle = CertificateBundle(active_pem=PEM_A)
    with pytest.raises(CertRotationError, match="no pending"):
        rollback_pending(bundle)
