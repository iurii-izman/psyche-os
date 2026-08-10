"""Validate the PSYCHE OS v2 research-documentation foundation.

The checks are intentionally repository/document focused. They do not claim that a
future product is secure, clinically valid, legally compliant, or ready for real
data. PyYAML is the sole non-stdlib dependency and is already required by the
source-registry build helper.
"""

from __future__ import annotations

import re
import sys
from collections import Counter, defaultdict
from pathlib import Path
from urllib.parse import urlparse

import yaml


ROOT = Path(__file__).resolve().parents[1]
REQUIRED = (
    "docs/PSYCHE_OS_MASTER_SPEC_v2.0_FINAL.md",
    "docs/research/PSYCHE_OS_RESEARCH_DOSSIER_2026.md",
    "docs/research/SOURCE_REGISTRY.yaml",
    "docs/research/EXECUTION_PLAN.md",
    "docs/reviews/V1_CRITICAL_AUDIT.md",
    "docs/reviews/INDEPENDENT_REBUILD.md",
    "docs/reviews/RED_TEAM_REPORT.md",
    "docs/DECISION_LOG.md",
    "CONSTITUTION.md",
    "docs/SCIENTIFIC_GOVERNANCE.md",
    "docs/architecture/DATA_MODEL.md",
    "docs/architecture/SYSTEM_ARCHITECTURE.md",
    "docs/architecture/PRIVACY_SECURITY_MODEL.md",
    "docs/architecture/MENTAL_HEALTH_AI_SAFETY.md",
    "docs/architecture/THREAT_MODEL.md",
    "ontology/psyche_domains.yaml",
    "docs/ROADMAP.md",
    "docs/prompts/F0_IMPLEMENTATION_PROMPT.md",
    "docs/FINAL_RESEARCH_REPORT.md",
)
EXTRA_REQUIRED = ("docs/architecture/REAL_DATA_GATE.yaml",)
SOURCE_ID_RE = re.compile(r"\b(?:ARCH|CLIN|MEAS)-\d{3}\b")
SOURCE_RANGE_RE = re.compile(r"\b(ARCH|CLIN|MEAS)-(\d{3})\s*[–—-]\s*(?:(ARCH|CLIN|MEAS)-)?(\d{3})\b")
LINK_RE = re.compile(r"(?<!!)\[[^\]]*\]\(([^)]+)\)")
HEADING_RE = re.compile(r"^(#{1,6})\s+(.+?)\s*$", re.MULTILINE)
URL_SCHEMES = {"http", "https"}
FORBIDDEN_SUFFIXES = {
    ".db",
    ".sqlite",
    ".sqlite3",
    ".psychebackup",
    ".pem",
    ".p12",
    ".pfx",
    ".key",
    ".env",
}
SOURCE_REQUIRED_FIELDS = {
    "id",
    "title",
    "authors_or_organization",
    "type",
    "publication",
    "publication_date",
    "url",
    "accessed_at",
    "evidence_tier",
    "domains",
    "currentness",
    "project_implications",
    "limitations",
    "rights_notes",
    "superseded",
    "review_due",
}


class Result:
    def __init__(self) -> None:
        self.errors: list[str] = []
        self.warnings: list[str] = []
        self.facts: list[str] = []

    def error(self, message: str) -> None:
        self.errors.append(message)

    def warn(self, message: str) -> None:
        self.warnings.append(message)

    def fact(self, message: str) -> None:
        self.facts.append(message)


def load_yaml(relative: str, result: Result):
    path = ROOT / relative
    try:
        return yaml.safe_load(path.read_text(encoding="utf-8"))
    except Exception as exc:  # validation boundary
        result.error(f"YAML parse failed for {relative}: {exc}")
        return None


def markdown_files() -> list[Path]:
    return sorted(path for path in ROOT.rglob("*.md") if ".git" not in path.parts)


def validate_required(result: Result) -> None:
    for relative in (*REQUIRED, *EXTRA_REQUIRED):
        path = ROOT / relative
        if not path.is_file() or path.stat().st_size == 0:
            result.error(f"Required artifact missing or empty: {relative}")
    result.fact(f"required_artifacts={sum((ROOT / p).is_file() for p in REQUIRED)}/{len(REQUIRED)}")


def validate_sources(result: Result) -> set[str]:
    payload = load_yaml("docs/research/SOURCE_REGISTRY.yaml", result)
    if not isinstance(payload, dict) or not isinstance(payload.get("sources"), list):
        result.error("SOURCE_REGISTRY must be a mapping with a sources list")
        return set()

    sources = payload["sources"]
    ids: list[str] = []
    by_url: dict[str, list[dict]] = defaultdict(list)
    for index, source in enumerate(sources):
        if not isinstance(source, dict):
            result.error(f"Source at index {index} is not a mapping")
            continue
        missing = SOURCE_REQUIRED_FIELDS - source.keys()
        if missing:
            result.error(f"{source.get('id', index)} missing source fields: {sorted(missing)}")
        source_id = str(source.get("id", ""))
        if not SOURCE_ID_RE.fullmatch(source_id):
            result.error(f"Invalid source ID: {source_id!r}")
        ids.append(source_id)
        url = str(source.get("url", ""))
        if urlparse(url).scheme not in URL_SCHEMES or not urlparse(url).netloc:
            result.error(f"Invalid source URL for {source_id}: {url}")
        by_url[url].append(source)
        if source.get("accessed_at") != "2026-08-10":
            result.warn(f"{source_id} accessed_at is not snapshot date: {source.get('accessed_at')}")
        for field in ("domains", "project_implications", "limitations"):
            if not isinstance(source.get(field), list) or not source.get(field):
                result.error(f"{source_id} {field} must be a non-empty list")
        for field in ("currentness", "rights_notes", "review_due"):
            if not str(source.get(field, "")).strip():
                result.error(f"{source_id} {field} is empty")

    duplicates = [item for item, count in Counter(ids).items() if count > 1]
    if duplicates:
        result.error(f"Duplicate source IDs: {duplicates}")
    for url, records in by_url.items():
        if len(records) < 2:
            continue
        record_ids = {record["id"] for record in records}
        for record in records:
            aliases = set(record.get("same_source_as", []))
            if aliases != record_ids - {record["id"]}:
                result.error(f"Duplicate URL aliases are not reciprocal for {record['id']}: {url}")

    declared_records = payload.get("source_record_count")
    declared_unique = payload.get("unique_source_count")
    if declared_records != len(sources):
        result.error(f"source_record_count={declared_records}, actual={len(sources)}")
    if declared_unique != len(by_url):
        result.error(f"unique_source_count={declared_unique}, actual={len(by_url)}")
    if len(by_url) < 100:
        result.error(f"Evidence saturation threshold not met: {len(by_url)} unique sources")
    result.fact(f"source_records={len(sources)} unique_sources={len(by_url)} unique_ids={len(set(ids))}")
    return set(ids)


def validate_citations(source_ids: set[str], result: Result) -> None:
    cited: set[str] = set()
    scanned = 0
    ranges_checked = 0
    for path in sorted((*markdown_files(), *(ROOT / "ontology").glob("*.yaml"))):
        text = path.read_text(encoding="utf-8")
        found = set(SOURCE_ID_RE.findall(text))
        cited.update(found)
        scanned += len(found)
        unknown = found - source_ids
        if unknown:
            result.error(f"Unknown source IDs in {path.relative_to(ROOT)}: {sorted(unknown)}")
        for match in SOURCE_RANGE_RE.finditer(text):
            first_prefix, first_number, second_prefix, second_number = match.groups()
            second_prefix = second_prefix or first_prefix
            start, end = int(first_number), int(second_number)
            ranges_checked += 1
            if first_prefix != second_prefix or start > end:
                result.error(f"Invalid source range in {path.relative_to(ROOT)}: {match.group(0)}")
                continue
            expected = {f"{first_prefix}-{number:03d}" for number in range(start, end + 1)}
            missing = expected - source_ids
            if missing:
                result.error(f"Source range has unregistered members in {path.relative_to(ROOT)}: {sorted(missing)}")
            cited.update(expected)
    result.fact(
        f"citation_occurrence_sets={scanned} citation_ranges_checked={ranges_checked} "
        f"unique_cited_source_ids={len(cited)} unknown=0"
    )


def validate_ontology(source_ids: set[str], result: Result) -> None:
    payload = load_yaml("ontology/psyche_domains.yaml", result)
    if not isinstance(payload, dict):
        return
    registry = payload.get("registry", {})
    if registry.get("completeness_claim") is not False:
        result.error("Ontology must declare completeness_claim: false")
    if registry.get("change_policy", {}).get("real_data_gate") != "CLOSED":
        result.error("Ontology real_data_gate must be CLOSED")
    domains = payload.get("domains")
    if not isinstance(domains, list):
        result.error("Ontology domains must be a list")
        return
    ids = [domain.get("id") for domain in domains]
    if len(ids) != len(set(ids)):
        result.error("Ontology domain IDs are not unique")
    allowed_layers = set(payload.get("enums", {}).get("layer_id", []))
    allowed_evidence = set(payload.get("enums", {}).get("evidence_kind", []))
    allowed_claims = set(payload.get("enums", {}).get("claim_type", []))
    for domain in domains:
        missing = set(payload.get("schema_contract", {}).get("required_domain_fields", [])) - domain.keys()
        if missing:
            result.error(f"Ontology {domain.get('id')} missing fields: {sorted(missing)}")
        if domain.get("layer") not in allowed_layers:
            result.error(f"Ontology {domain.get('id')} has invalid layer: {domain.get('layer')}")
        if not set(domain.get("allowed_evidence_kinds", [])) <= allowed_evidence:
            result.error(f"Ontology {domain.get('id')} has invalid evidence kinds")
        if not set(domain.get("allowed_claim_types", [])) <= allowed_claims:
            result.error(f"Ontology {domain.get('id')} has invalid claim types")
        refs = set(domain.get("review", {}).get("source_ids", []))
        if not refs <= source_ids:
            result.error(f"Ontology {domain.get('id')} has unknown sources: {sorted(refs - source_ids)}")
    relation_targets = set(ids)
    for relation in payload.get("domain_relations", []):
        endpoints = {relation.get("from"), relation.get("to")}
        if not endpoints <= relation_targets:
            result.error(f"Ontology relation has unknown endpoint: {relation}")
    result.fact(
        f"ontology_domains={len(domains)} layers={len(payload.get('layer_contracts', []))} "
        f"evidence_contracts={len(payload.get('evidence_kind_contracts', []))} relations={len(payload.get('domain_relations', []))}"
    )


def validate_gate(result: Result) -> None:
    gate = load_yaml("docs/architecture/REAL_DATA_GATE.yaml", result)
    if not isinstance(gate, dict):
        return
    if gate.get("status") != "CLOSED" or gate.get("production_implementation_exists") is not False:
        result.error("REAL_DATA_GATE must be CLOSED with no production implementation")
    requirements = gate.get("requirements", [])
    if not requirements or any(item.get("state") != "UNSATISFIED" or item.get("evidence") is not None for item in requirements):
        result.error("Every real-data requirement must remain UNSATISFIED with null evidence")
    if gate.get("opening_rule", {}).get("automatic_opening_forbidden") is not True:
        result.error("Automatic real-data opening must be forbidden")
    result.fact(f"real_data_gate={gate.get('status')} requirements={len(requirements)} satisfied=0")


def normalize_heading(value: str) -> str:
    value = re.sub(r"`([^`]*)`", r"\1", value)
    value = re.sub(r"[*_#]", "", value)
    return re.sub(r"\s+", " ", value.strip().lower())


def validate_markdown(result: Result) -> None:
    link_count = 0
    duplicate_count = 0
    for path in markdown_files():
        text = path.read_text(encoding="utf-8")
        fence_lines = [line for line in text.splitlines() if line.lstrip().startswith("```")]
        if len(fence_lines) % 2:
            result.error(f"Unbalanced Markdown code fences in {path.relative_to(ROOT)}")
        headings = [normalize_heading(match.group(2)) for match in HEADING_RE.finditer(text)]
        duplicates = [heading for heading, count in Counter(headings).items() if count > 1]
        if duplicates:
            duplicate_count += len(duplicates)
            result.warn(f"Duplicate headings in {path.relative_to(ROOT)}: {duplicates}")
        for match in LINK_RE.finditer(text):
            target = match.group(1).strip().strip("<>")
            if target.startswith(("http://", "https://", "mailto:", "#")):
                continue
            target = target.split("#", 1)[0]
            if not target:
                continue
            candidate = (path.parent / target).resolve()
            link_count += 1
            if not candidate.exists():
                result.error(f"Broken local Markdown link in {path.relative_to(ROOT)}: {match.group(1)}")
    result.fact(f"local_markdown_links_checked={link_count} duplicate_heading_warnings={duplicate_count}")


def validate_status_and_f0(result: Result) -> None:
    plan = (ROOT / "docs/research/EXECUTION_PLAN.md").read_text(encoding="utf-8")
    if "**Status:** complete" not in plan or "| Pending |" in plan or "| In progress |" in plan:
        result.error("Execution plan is not in a fully completed state")
    if plan.count("- [x]") < 19 or "- [ ]" in plan:
        result.error("Execution plan artifact checklist is incomplete")

    f0 = (ROOT / "docs/prompts/F0_IMPLEMENTATION_PROMPT.md").read_text(encoding="utf-8")
    required_terms = (
        "Python 3.12+",
        "synthetic",
        "SQLCipher",
        "Argon2id",
        "NEVER_CLOUD",
        "localhost listener",
        "REAL_DATA_GATE",
        "CLOSED",
        "Definition of Done",
        "docs/architecture/REAL_DATA_GATE.yaml",
    )
    missing = [term for term in required_terms if term not in f0]
    if missing:
        result.error(f"F0 prompt missing required contract terms: {missing}")
    for forbidden_scope in ("LLM", "FHIR", "real data", "graph/vector"):
        if forbidden_scope not in f0:
            result.error(f"F0 prompt does not explicitly address forbidden scope: {forbidden_scope}")
    result.fact("execution_plan=complete f0_scope_contract=present")


def validate_master_and_threat(result: Result) -> None:
    master = (ROOT / REQUIRED[0]).read_text(encoding="utf-8")
    required_master_terms = (
        "RESEARCH_CONVERGED",
        "REAL_DATA_GATE",
        "Personal Evidence & Reflection System",
        "MemoryReport",
        "ContradictionSet",
        "KnowledgeSnapshot",
        "NEVER_CLOUD",
        "# IMPLEMENTATION CONTRACT",
        "C6_replicated_n_of_1_or_trial",
        "40",
    )
    missing = [term for term in required_master_terms if term not in master]
    if missing:
        result.error(f"Master spec missing required terms: {missing}")
    if not master.rstrip().endswith("Completion authorizes only synthetic Phase 2 assurance. It does not authorize production use or the first real personal record."):
        result.error("Master spec must end with the implementation contract's closed-gate statement")

    threat = (ROOT / "docs/architecture/THREAT_MODEL.md").read_text(encoding="utf-8")
    for heading in (
        "## Overview",
        "## Threat Model, Trust Boundaries, and Assumptions",
        "## Attack Surface, Mitigations, and Attacker Stories",
        "## Severity Calibration (Critical, High, Medium, Low)",
    ):
        if heading not in threat:
            result.error(f"Threat model missing required heading: {heading}")
    lines = threat.rstrip().splitlines()
    if len(lines) < 2 or lines[-2] != "Repository: C:/Dev/psyche-os" or not lines[-1].startswith("Version: sha256:"):
        result.error("Threat model repository/version footer is missing or not final")


def validate_repo_hygiene(result: Result) -> None:
    dangerous: list[str] = []
    for path in ROOT.rglob("*"):
        if not path.is_file() or ".git" in path.parts:
            continue
        relative = path.relative_to(ROOT).as_posix()
        if path.suffix.lower() in FORBIDDEN_SUFFIXES or path.name.lower() in {".env", "id_rsa", "id_ed25519"}:
            dangerous.append(relative)
    if dangerous:
        result.error(f"Forbidden sensitive/binary artifact types present: {dangerous}")

    secret_patterns = (
        re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
        re.compile(r"\bsk-(?:proj-)?[A-Za-z0-9_-]{20,}\b"),
        re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
    )
    matches: list[str] = []
    for path in ROOT.rglob("*"):
        if not path.is_file() or ".git" in path.parts or path.suffix.lower() not in {".md", ".yaml", ".yml", ".py"}:
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        if any(pattern.search(text) for pattern in secret_patterns):
            matches.append(path.relative_to(ROOT).as_posix())
    if matches:
        result.error(f"Potential plaintext secrets detected: {matches}")
    result.fact(f"forbidden_sensitive_file_types={len(dangerous)} potential_secret_matches={len(matches)}")


def main() -> int:
    result = Result()
    validate_required(result)
    source_ids = validate_sources(result)
    validate_citations(source_ids, result)
    validate_ontology(source_ids, result)
    validate_gate(result)
    validate_markdown(result)
    validate_status_and_f0(result)
    validate_master_and_threat(result)
    validate_repo_hygiene(result)

    print("PSYCHE OS v2 research foundation validation")
    for fact in result.facts:
        print(f"FACT: {fact}")
    for warning in result.warnings:
        print(f"WARN: {warning}")
    for error in result.errors:
        print(f"ERROR: {error}")
    print(f"RESULT: errors={len(result.errors)} warnings={len(result.warnings)}")
    return 1 if result.errors else 0


if __name__ == "__main__":
    sys.exit(main())
