"""E10 professional handoff application service.

The service owns explicit selection, the exact local preview, single-use
non-transferable authorization, TOCTOU revalidation immediately before
generation, deterministic report/JSON-manifest construction, content-free
disclosure receipts and the narrow outer export adapter.  It never mutates
canonical data and never calls a model/provider or the network.
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
import re
import secrets
from typing import Any

from psyche_os.adapters.e10_filesystem import E10FileWriteError, ExportFileInfo
from psyche_os.reports.e10_professional import (
    EXPORT_RETENTION_NOTE,
    EXTERNAL_COPY_NOTICE,
    PENDING_REVIEW_ITEMS,
    REPORT_SECTIONS,
    E10ReportError,
    Exclusion,
    Redaction,
    ReportConfig,
    ReportPackage,
    ReportPreview,
    build_manifest,
    build_report_records,
    canonical_cutoff_of,
    collect_counterevidence_ids,
    compute_identity,
    manifest_bytes,
    policy_identity_of,
    render_markdown,
    report_id_of,
    resolve_record,
    transformation_identity,
)


@dataclass(frozen=True, slots=True)
class HandoffAuthorization:
    """Service-minted, exact-preview-bound, single-use capability."""

    authorization_id: str
    service_instance_id: str
    preview_digest: str
    single_use: bool = True

    def __repr__(self) -> str:
        return (
            f"HandoffAuthorization(authorization_id={self.authorization_id!r}, "
            f"service_instance_id={self.service_instance_id!r}, "
            f"single_use={self.single_use!r})"
        )


@dataclass(frozen=True, slots=True)
class DisclosureReceipt:
    """Content-free disclosure receipt; bounded audit metadata only."""

    receipt_id: str
    report_id: str
    report_version: str
    audience: str
    purpose: str
    disclosure_state: str
    selected_count: int
    counterevidence_count: int
    byte_count: int
    external_copy_limited: bool
    issued_at: str

    def __repr__(self) -> str:
        return (
            f"DisclosureReceipt(receipt_id={self.receipt_id!r}, "
            f"report_id={self.report_id!r}, report_version={self.report_version!r}, "
            f"disclosure_state={self.disclosure_state!r})"
        )


@dataclass(frozen=True, slots=True)
class DisclosureOutcome:
    """Result of one complete authorized disclosure action."""

    package: ReportPackage
    receipt: DisclosureReceipt

    def __repr__(self) -> str:
        return (
            f"DisclosureOutcome(report_id={self.package.identity.report_id!r}, "
            f"disclosure_state={self.receipt.disclosure_state!r})"
        )


def _normalise_selection(
    selection: Iterable[tuple[str, str]],
) -> tuple[tuple[str, str], ...]:
    pairs: set[tuple[str, str]] = set()
    for item in selection:
        if not isinstance(item, tuple) or len(item) != 2:
            raise E10ReportError("INVALID_SELECTION")
        rid, vid = item
        if not isinstance(rid, str) or not isinstance(vid, str) or not rid or not vid:
            raise E10ReportError("INVALID_SELECTION")
        pairs.add((rid, vid))
    if not pairs:
        raise E10ReportError("EMPTY_SELECTION")
    return tuple(sorted(pairs))


def _normalise_exclusions(
    exclusions: Iterable[Exclusion],
) -> tuple[Exclusion, ...]:
    seen: set[tuple[str, str]] = set()
    result: list[Exclusion] = []
    for exclusion in exclusions:
        key = (exclusion.record_id, exclusion.version_id)
        if key in seen:
            continue
        seen.add(key)
        result.append(exclusion)
    return tuple(sorted(result, key=lambda e: (e.record_id, e.version_id)))


def _validate_redactions(
    redactions: Iterable[Redaction],
    allowed_ids: frozenset[tuple[str, str]],
    known_fields: dict[tuple[str, str], frozenset[str]],
) -> tuple[Redaction, ...]:
    result: list[Redaction] = []
    for redaction in redactions:
        key = (redaction.record_id, redaction.version_id)
        if key not in allowed_ids:
            raise E10ReportError("INVALID_REDACTION")
        if redaction.field not in known_fields[key]:
            raise E10ReportError("INVALID_REDACTION")
        try:
            re.compile(redaction.pattern)
        except re.error:
            raise E10ReportError("INVALID_REDACTION") from None
        result.append(redaction)
    return tuple(sorted(result, key=lambda r: (r.record_id, r.version_id, r.field)))


def _policy_state(connection: Any, audience: str) -> str:
    """Export-policy gate: ``"missing"``, ``"blocked"`` or ``"ok"``.

    PS-01 / Master Spec §409: missing or ambiguous policy fails closed, so zero
    active policies is ``"missing"`` (never silently permissive).  Any active
    policy outside the local/no-cloud, audience-bounded export profile is
    ``"blocked"``.
    """
    if (
        connection.execute("SELECT 1 FROM data_policies WHERE is_active=1 LIMIT 1").fetchone()
        is None
    ):
        return "missing"
    violating = connection.execute(
        "SELECT 1 FROM data_policies WHERE is_active=1 AND "
        "(processing_location != 'local_only' OR cloud_policy != 'never_cloud' OR "
        "export_rule NOT IN ('allow','redact') OR "
        "(export_audience != '' AND export_audience != ?)) LIMIT 1",
        (audience,),
    ).fetchone()
    return "ok" if violating is None else "blocked"


def _validate_destination(destination: str) -> None:
    """Reject destinations that could escape the caller-owned base directory."""
    if not isinstance(destination, str) or not destination or "\x00" in destination:
        raise E10ReportError("INVALID_DESTINATION")
    candidate = Path(destination)
    # ``anchor`` covers absolute and drive/root-relative paths on any platform.
    if candidate.anchor or ".." in candidate.parts:
        raise E10ReportError("INVALID_DESTINATION")


class E10ProfessionalHandoffService:
    """One service instance; authorizations never cross instances."""

    def __init__(
        self,
        connection: Any,
        config: ReportConfig | None = None,
        instance_id: str | None = None,
    ) -> None:
        self.connection = connection
        self.config = config or ReportConfig()
        self._instance_id = instance_id or ("e10-instance-" + secrets.token_hex(8))
        self._authorization_states: dict[str, str] = {}

    @property
    def instance_id(self) -> str:
        return self._instance_id

    def build_preview(
        self,
        selection: Sequence[tuple[str, str]],
        exclusions: Sequence[Exclusion] = (),
        redactions: Sequence[Redaction] = (),
        destination: str = "handoff.md",
    ) -> ReportPreview:
        """Build the exact local preview over current canonical state.

        The destination is the exact authorized export target and is bound into
        the preview digest; it never enters the report bytes.
        """
        _validate_destination(destination)
        selected = _normalise_selection(selection)
        exclusions_norm = _normalise_exclusions(exclusions)
        excluded_keys = {(e.record_id, e.version_id) for e in exclusions_norm}
        # F3: exclusion is a transformation over the exact explicit selection;
        # fabricated/unselected IDs cannot appear as excluded metadata.
        for key in excluded_keys:
            if key not in selected:
                raise E10ReportError("INVALID_EXCLUSION")
        effective = tuple(pair for pair in selected if pair not in excluded_keys)
        if not effective:
            raise E10ReportError("EMPTY_SELECTION")
        state = _policy_state(self.connection, self.config.audience)
        if state == "missing":
            raise E10ReportError("POLICY_MISSING")
        if state == "blocked":
            raise E10ReportError("POLICY_BLOCKED")

        known_fields: dict[tuple[str, str], frozenset[str]] = {}
        selected_kinds: dict[tuple[str, str], str] = {}
        # Every explicitly selected version must exist and be available,
        # including ones excluded from this candidate.
        for rid, vid in selected:
            content = resolve_record(self.connection, rid, vid)
            if content is None:
                raise E10ReportError("RECORD_UNAVAILABLE")
            if (rid, vid) in effective:
                known_fields[(rid, vid)] = frozenset(label for label, _value in content.fields)
                selected_kinds[(rid, vid)] = content.kind

        counterevidence_ids = collect_counterevidence_ids(self.connection, effective)
        for rid, vid in counterevidence_ids:
            content = resolve_record(self.connection, rid, vid)
            if content is None:
                raise E10ReportError("COUNTEREVIDENCE_UNAVAILABLE")
            known_fields[(rid, vid)] = frozenset(label for label, _value in content.fields)

        redactions_norm = _validate_redactions(
            redactions,
            frozenset(effective) | frozenset(counterevidence_ids),
            known_fields,
        )
        return ReportPreview(
            audience=self.config.audience,
            purpose=self.config.purpose,
            profile=self.config.profile,
            selected_ids=effective,
            excluded_ids=tuple(pair for pair in excluded_keys),
            redactions=redactions_norm,
            counterevidence_ids=counterevidence_ids,
            section_names=REPORT_SECTIONS,
            uncertainty_record_count=sum(
                1 for key in effective if selected_kinds[key] == "unknown"
            ),
            output_format=self.config.output_format,
            destination=destination,
            retention_note=EXPORT_RETENTION_NOTE,
            external_copy_notice=EXTERNAL_COPY_NOTICE,
            builder_version=self.config.builder_version,
            config_version=self.config.config_version,
            policy_identity=policy_identity_of(self.connection),
            canonical_cutoff=canonical_cutoff_of(self.connection),
            pending_review_items=tuple(item for item, _label in PENDING_REVIEW_ITEMS),
        )

    def issue_authorization(self, preview: ReportPreview) -> HandoffAuthorization:
        """Mint a single-use, non-transferable, preview-bound capability."""
        authorization = HandoffAuthorization(
            authorization_id="e10-auth-" + secrets.token_hex(16),
            service_instance_id=self._instance_id,
            preview_digest=preview.digest,
            single_use=True,
        )
        self._authorization_states[authorization.authorization_id] = "issued"
        return authorization

    def _validate_authorization(
        self, authorization: HandoffAuthorization
    ) -> None:
        state = self._authorization_states.get(authorization.authorization_id)
        if state is None:
            raise E10ReportError("AUTHORIZATION_FABRICATED")
        if authorization.service_instance_id != self._instance_id:
            self._authorization_states[authorization.authorization_id] = "invalidated"
            raise E10ReportError("AUTHORIZATION_NON_TRANSFERABLE")
        if state == "consumed":
            raise E10ReportError("AUTHORIZATION_REPLAYED")
        if state == "invalidated":
            raise E10ReportError("AUTHORIZATION_INVALIDATED")

    def _revalidate(self, preview: ReportPreview) -> ReportPreview:
        """Recompute the exact preview from current canonical state."""
        return self.build_preview(
            selection=(*preview.selected_ids, *preview.excluded_ids),
            exclusions=tuple(Exclusion(rid, vid) for rid, vid in preview.excluded_ids),
            redactions=preview.redactions,
            destination=preview.destination,
        )

    def _build_package(self, current: ReportPreview) -> ReportPackage:
        """Deterministic report construction; destination never enters the bytes."""
        selected, counterevidence = build_report_records(self.connection, current)
        all_records = (*selected, *counterevidence)
        transformation = transformation_identity(
            tuple(Exclusion(rid, vid) for rid, vid in current.excluded_ids),
            current.redactions,
        )
        report_id = report_id_of(
            self.config,
            current.selected_ids,
            current.excluded_ids,
            current.counterevidence_ids,
            transformation,
            current.policy_identity,
        )
        markdown = render_markdown(
            selected, counterevidence, current, report_id, self.config.report_version
        )
        identity = compute_identity(
            self.config,
            current.selected_ids,
            current.excluded_ids,
            current.counterevidence_ids,
            transformation,
            current.policy_identity,
            current.canonical_cutoff,
            markdown,
        )
        manifest = build_manifest(identity, current, all_records)
        return ReportPackage(identity, current, markdown, manifest)

    def disclose(
        self,
        preview: ReportPreview,
        authorization: HandoffAuthorization,
        writer: Any,
        *,
        overwrite: bool = False,
    ) -> DisclosureOutcome:
        """The complete authorized disclosure action.

        The single-use capability covers revalidation, deterministic report
        construction AND the write to the exact authorized destination.  The
        write failure path invalidates the capability; it is never reusable.
        """
        self._validate_authorization(authorization)
        try:
            current = self._revalidate(preview)
        except E10ReportError:
            self._authorization_states[authorization.authorization_id] = "invalidated"
            raise E10ReportError("TOCTOU_INVALIDATION") from None
        if current.digest != authorization.preview_digest:
            self._authorization_states[authorization.authorization_id] = "invalidated"
            raise E10ReportError("TOCTOU_INVALIDATION")

        package = self._build_package(current)
        try:
            info: ExportFileInfo = writer.write(
                package.markdown, current.destination, overwrite=overwrite
            )
        except E10FileWriteError:
            self._authorization_states[authorization.authorization_id] = "invalidated"
            raise
        self._authorization_states[authorization.authorization_id] = "consumed"
        receipt = DisclosureReceipt(
            receipt_id="e10-receipt-" + secrets.token_hex(8),
            report_id=package.identity.report_id,
            report_version=package.identity.report_version,
            audience=package.identity.audience,
            purpose=package.identity.purpose,
            disclosure_state=package.identity.disclosure_state,
            selected_count=len(package.identity.selected_ids),
            counterevidence_count=len(package.preview.counterevidence_ids),
            byte_count=info.byte_count,
            external_copy_limited=True,
            issued_at=datetime.now(UTC).isoformat(),
        )
        return DisclosureOutcome(package, receipt)

    @staticmethod
    def manifest_bytes(package: ReportPackage) -> bytes:
        return manifest_bytes(package.manifest)
