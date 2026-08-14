"""Exact frozen-profile proofs for the E08 standard-library parser."""

from __future__ import annotations

from dataclasses import replace

import pytest

from psyche_os.application.e08_imports import E08BoundaryError, E08ErrorCode
from psyche_os.imports.model import PLAIN_TEXT_PROFILE, PlainTextResourceProfile
from psyche_os.imports.plain_text import INCOMPATIBLE_SIGNATURES, PlainTextParser


def parse_bytes(
    value: bytes, profile: PlainTextResourceProfile = PLAIN_TEXT_PROFILE
):  # type: ignore[no-untyped-def]
    return PlainTextParser().parse(
        value,
        quarantine_id="q-synthetic",
        source_candidate_id="source-synthetic",
        source_version_id="source-synthetic-v1",
        protected_digest_ref="protected-reference",
        policy_lineage_id="e08-local-never-cloud-v1",
        profile=profile,
        rejection=lambda code: E08BoundaryError(E08ErrorCode(code)),
    )


def test_strict_utf8_bom_unicode_and_exact_newline_locators() -> None:
    raw = b"\xef\xbb\xbfalpha\r\n\xce\xb2eta\rthird\nfourth"
    candidate = parse_bytes(raw)

    assert candidate.bom is True
    assert candidate.transformations == ("removed-leading-utf8-bom",)
    assert [item.newline for item in candidate.segments] == ["\r\n", "\r", "\n", ""]
    assert [raw[item.byte_start : item.byte_end].decode() for item in candidate.segments] == [
        "alpha",
        "βeta",
        "third",
        "fourth",
    ]
    assert [(item.character_start, item.character_end) for item in candidate.segments] == [
        (0, 5),
        (7, 11),
        (12, 17),
        (18, 24),
    ]


@pytest.mark.parametrize("signature", [item[0] for item in INCOMPATIBLE_SIGNATURES])
def test_every_frozen_incompatible_signature_rejects(signature: bytes) -> None:
    with pytest.raises(E08BoundaryError) as caught:
        parse_bytes(signature + b" fictional")
    assert caught.value.code == E08ErrorCode.INCOMPATIBLE_SIGNATURE


@pytest.mark.parametrize(
    ("value", "code"),
    [
        (b"\xff", E08ErrorCode.INVALID_UTF8),
        (b"fictional\x00note", E08ErrorCode.DISALLOWED_CONTROL),
        (b"fictional\x7fnote", E08ErrorCode.DISALLOWED_CONTROL),
        (b" \t\r\n", E08ErrorCode.EMPTY_CANDIDATE),
    ],
)
def test_invalid_encoding_controls_and_empty_input_fail_closed(
    value: bytes, code: E08ErrorCode
) -> None:
    with pytest.raises(E08BoundaryError) as caught:
        parse_bytes(value)
    assert caught.value.code == code


def test_byte_limit_exact_boundary_and_one_over() -> None:
    profile = replace(
        PLAIN_TEXT_PROFILE,
        maximum_original_bytes=8,
        maximum_code_points=8,
        maximum_line_code_points=8,
    )
    assert parse_bytes(b"abcdefgh", profile).byte_count == 8
    with pytest.raises(E08BoundaryError) as caught:
        parse_bytes(b"abcdefghi", profile)
    assert caught.value.code == E08ErrorCode.BYTE_LIMIT_EXCEEDED


def test_character_limit_exact_boundary_and_one_over() -> None:
    profile = replace(PLAIN_TEXT_PROFILE, maximum_code_points=4)
    assert parse_bytes("αβγδ".encode(), profile).character_count == 4
    with pytest.raises(E08BoundaryError) as caught:
        parse_bytes("αβγδε".encode(), profile)
    assert caught.value.code == E08ErrorCode.CHARACTER_LIMIT_EXCEEDED


def test_line_and_segment_limit_exact_boundary_and_one_over() -> None:
    profile = replace(PLAIN_TEXT_PROFILE, maximum_physical_lines=3, maximum_segments=3)
    assert parse_bytes(b"a\nb\nc\n", profile).segment_count == 3
    with pytest.raises(E08BoundaryError) as caught:
        parse_bytes(b"a\nb\nc\nd\n", profile)
    assert caught.value.code == E08ErrorCode.LINE_LIMIT_EXCEEDED


def test_line_length_exact_boundary_and_one_over() -> None:
    profile = replace(PLAIN_TEXT_PROFILE, maximum_line_code_points=4)
    assert parse_bytes("αβγδ".encode(), profile).segment_count == 1
    with pytest.raises(E08BoundaryError) as caught:
        parse_bytes("αβγδε".encode(), profile)
    assert caught.value.code == E08ErrorCode.LINE_LENGTH_EXCEEDED


def test_candidate_identity_changes_with_security_relevant_input() -> None:
    first = parse_bytes(b"repeated fictional line")
    second = parse_bytes(b"repeated fictional line\n")
    other_profile = replace(PLAIN_TEXT_PROFILE, maximum_segments=4_095)
    third = parse_bytes(b"repeated fictional line", other_profile)
    assert len({first.candidate_id, second.candidate_id, third.candidate_id}) == 3


def test_frozen_numeric_boundaries_pass_exactly_and_fail_one_unit_over() -> None:
    million_characters = ("x" * 243 + "\n") * 4_095 + "x" * 820
    assert len(million_characters) == 1_000_000
    exact_characters = parse_bytes(million_characters.encode())
    assert exact_characters.character_count == 1_000_000
    assert exact_characters.physical_line_count == 4_096
    with pytest.raises(E08BoundaryError) as character_over:
        parse_bytes((million_characters + "x").encode())
    assert character_over.value.code == E08ErrorCode.CHARACTER_LIMIT_EXCEEDED

    exact_bytes = (("é" * 127 + "\n") * 4_095 + "é" * 2_175 + "x").encode()
    assert len(exact_bytes) == 1_048_576
    assert parse_bytes(exact_bytes).byte_count == 1_048_576
    with pytest.raises(E08BoundaryError) as byte_over:
        parse_bytes(exact_bytes + b"x")
    assert byte_over.value.code == E08ErrorCode.BYTE_LIMIT_EXCEEDED

    assert parse_bytes(("x" * 16_384).encode()).segment_count == 1
    with pytest.raises(E08BoundaryError) as line_over:
        parse_bytes(("x" * 16_385).encode())
    assert line_over.value.code == E08ErrorCode.LINE_LENGTH_EXCEEDED
