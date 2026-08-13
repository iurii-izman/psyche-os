"""E04 integration tests for registry history and read/status paths."""

from dataclasses import replace

import pytest

from psyche_os.domain.assessments import AssessmentLifecycle, GateOutcome
from psyche_os.knowledge import AssessmentRegistry


@pytest.mark.integration
def test_package_fixture_is_available_only_as_blocked_metadata() -> None:
    registry = AssessmentRegistry()

    assert registry.count() == 1
    status = registry.status("fictional_orchid_metadata", "1.0.0-metadata")
    assert status is not None
    assert status.outcome is GateOutcome.RIGHTS_BLOCKED
    assert status.scientific_claims_enabled is False
    assert all(not decision.allowed for decision in status.capabilities)


@pytest.mark.integration
def test_duplicate_and_unlinked_versions_do_not_mutate_history() -> None:
    registry = AssessmentRegistry()
    original = registry.list_all()[0]

    with pytest.raises(ValueError, match="already exists"):
        registry.register(original)

    unlinked = replace(
        original,
        identity=replace(original.identity, definition_version="1.1.0-metadata"),
    )
    with pytest.raises(ValueError, match="existing predecessor"):
        registry.register(unlinked)

    assert registry.list_all() == (original,)


@pytest.mark.integration
def test_linked_successor_appends_without_rewriting_prior_decision() -> None:
    registry = AssessmentRegistry()
    original = registry.list_all()[0]
    successor = replace(
        original,
        identity=replace(original.identity, definition_version="1.1.0-metadata"),
        supersedes_definition_version=original.definition_version,
    )

    status = registry.register(successor)

    assert status.outcome is GateOutcome.RIGHTS_BLOCKED
    assert registry.count() == 2
    assert registry.get(original.registry_id, original.definition_version) is original
    assert registry.get(successor.registry_id, successor.definition_version) is successor
    assert original.supersedes_definition_version is None


@pytest.mark.integration
def test_lifecycle_jump_and_branching_history_fail_before_mutation() -> None:
    empty_registry = AssessmentRegistry(include_fixture=False)
    original = AssessmentRegistry().list_all()[0]
    with pytest.raises(ValueError, match="must start"):
        empty_registry.register(replace(original, lifecycle=AssessmentLifecycle.REVOKED))

    registry = AssessmentRegistry()
    first_successor = replace(
        original,
        identity=replace(original.identity, definition_version="1.1.0-metadata"),
        supersedes_definition_version=original.definition_version,
    )
    registry.register(first_successor)
    branching_successor = replace(
        original,
        identity=replace(original.identity, definition_version="1.2.0-metadata"),
        supersedes_definition_version=original.definition_version,
    )
    with pytest.raises(ValueError, match="already has a successor"):
        registry.register(branching_successor)

    assert registry.count() == 2
