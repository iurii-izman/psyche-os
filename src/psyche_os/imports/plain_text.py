"""Strict standard-library parser for the frozen E08 UTF-8 profile."""

from __future__ import annotations

import codecs
from dataclasses import asdict
from typing import Final, Protocol

from psyche_os.imports.model import (
    ParsedImportCandidate,
    ParsedSegment,
    PlainTextResourceProfile,
    identity_digest,
)


class ImportRejection(Protocol):
    def __call__(self, code: str) -> Exception: ...


UTF8_BOM: Final = b"\xef\xbb\xbf"
INCOMPATIBLE_SIGNATURES: Final[tuple[tuple[bytes, str], ...]] = (
    (b"PK\x03\x04", "zip"),
    (b"PK\x05\x06", "zip"),
    (b"PK\x07\x08", "zip"),
    (b"\x1f\x8b", "gzip"),
    (b"7z\xbc\xaf\x27\x1c", "7z"),
    (b"Rar!\x1a\x07", "rar"),
    (b"%PDF-", "pdf"),
    (b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1", "ole"),
    (b"\x89PNG\r\n\x1a\n", "png"),
    (b"\xff\xd8\xff", "jpeg"),
    (b"\x7fELF", "elf"),
    (b"MZ", "pe"),
    (b"\xff\xfe", "utf16"),
    (b"\xfe\xff", "utf16"),
)


class PlainTextParser:
    name: Final = "psyche-os-stdlib-utf8"
    version: Final = "1.0.0"
    config_digest: Final = identity_digest(
        {
            "decoder": "strict-utf8",
            "bom": "optional-leading-only",
            "newlines": "preserve-cr-lf-crlf",
            "segments": "non-whitespace-physical-lines",
        }
    )

    def parse(
        self,
        bounded_bytes: bytes,
        *,
        quarantine_id: str,
        source_candidate_id: str,
        source_version_id: str,
        protected_digest_ref: str,
        policy_lineage_id: str,
        profile: PlainTextResourceProfile,
        rejection: ImportRejection,
    ) -> ParsedImportCandidate:
        if len(bounded_bytes) > profile.maximum_original_bytes:
            raise rejection("byte_limit_exceeded")
        for signature, _kind in INCOMPATIBLE_SIGNATURES:
            if bounded_bytes.startswith(signature):
                raise rejection("incompatible_signature")

        bom = bounded_bytes.startswith(UTF8_BOM)
        payload = bounded_bytes[len(UTF8_BOM) :] if bom else bounded_bytes
        decoder = codecs.getincrementaldecoder("utf-8")("strict")
        decoded_parts: list[str] = []
        decoded_count = 0
        try:
            for offset in range(0, len(payload), 16_384):
                part = decoder.decode(payload[offset : offset + 16_384], final=False)
                decoded_count += len(part)
                if decoded_count > profile.maximum_code_points:
                    raise rejection("character_limit_exceeded")
                decoded_parts.append(part)
            tail = decoder.decode(b"", final=True)
        except UnicodeDecodeError:
            raise rejection("invalid_utf8") from None
        decoded_count += len(tail)
        if decoded_count > profile.maximum_code_points:
            raise rejection("character_limit_exceeded")
        decoded_parts.append(tail)
        text = "".join(decoded_parts)
        if any(self._disallowed_control(character) for character in text):
            raise rejection("disallowed_control")

        lines = self._physical_lines(payload, text, len(UTF8_BOM) if bom else 0, rejection)
        if len(lines) > profile.maximum_physical_lines:
            raise rejection("line_limit_exceeded")
        segments: list[ParsedSegment] = []
        for number, (content, char_start, byte_start, byte_end, newline) in enumerate(lines, 1):
            if len(content) > profile.maximum_line_code_points:
                raise rejection("line_length_exceeded")
            if content.strip():
                if len(segments) >= profile.maximum_segments:
                    raise rejection("segment_limit_exceeded")
                segment_material = {
                    "source_version_id": source_version_id,
                    "line": number,
                    "character_start": char_start,
                    "character_end": char_start + len(content),
                    "byte_start": byte_start,
                    "byte_end": byte_end,
                    "newline": newline,
                    "text": content,
                }
                segments.append(
                    ParsedSegment(
                        identity_digest(segment_material),
                        source_version_id,
                        number,
                        char_start,
                        char_start + len(content),
                        byte_start,
                        byte_end,
                        newline,
                        content,
                    )
                )
        if not segments:
            raise rejection("empty_candidate")

        transformations = ("removed-leading-utf8-bom",) if bom else ()
        material = {
            "candidate_version": "1",
            "quarantine_id": quarantine_id,
            "source_candidate_id": source_candidate_id,
            "source_version_id": source_version_id,
            "protected_digest_ref": protected_digest_ref,
            "byte_count": len(bounded_bytes),
            "encoding": "utf-8",
            "bom": bom,
            "profile": asdict(profile),
            "parser": (self.name, self.version, self.config_digest),
            "character_count": decoded_count,
            "physical_line_count": len(lines),
            "transformations": transformations,
            "segments": [
                {
                    "segment_id": item.segment_id,
                    "line": item.physical_line,
                    "character_start": item.character_start,
                    "character_end": item.character_end,
                    "byte_start": item.byte_start,
                    "byte_end": item.byte_end,
                    "newline": item.newline,
                    "text": item.text,
                }
                for item in segments
            ],
            "policy_lineage_id": policy_lineage_id,
            "untrusted_content": True,
        }
        return ParsedImportCandidate(
            candidate_id=identity_digest(material),
            candidate_version="1",
            quarantine_id=quarantine_id,
            source_candidate_id=source_candidate_id,
            source_version_id=source_version_id,
            protected_digest_ref=protected_digest_ref,
            byte_count=len(bounded_bytes),
            encoding="utf-8",
            bom=bom,
            profile_id=profile.profile_id,
            profile_identity=profile.identity,
            parser_name=self.name,
            parser_version=self.version,
            parser_config_digest=self.config_digest,
            character_count=decoded_count,
            physical_line_count=len(lines),
            segment_count=len(segments),
            transformations=transformations,
            segments=tuple(segments),
            untrusted_content=True,
            policy_lineage_id=policy_lineage_id,
        )

    @staticmethod
    def _disallowed_control(character: str) -> bool:
        code = ord(character)
        return (code < 32 and character not in "\t\r\n") or 0x7F <= code <= 0x9F

    @staticmethod
    def _physical_lines(
        payload: bytes,
        text: str,
        bom_bytes: int,
        rejection: ImportRejection,
    ) -> list[tuple[str, int, int, int, str]]:
        """Split without normalization and retain absolute original byte ranges."""
        result: list[tuple[str, int, int, int, str]] = []
        char_cursor = 0
        byte_cursor = 0
        index = 0
        while index < len(text):
            if text[index] not in "\r\n":
                index += 1
                continue
            newline = text[index]
            width = 1
            if newline == "\r" and index + 1 < len(text) and text[index + 1] == "\n":
                newline = "\r\n"
                width = 2
            content = text[char_cursor:index]
            encoded = content.encode("utf-8")
            result.append(
                (content, char_cursor, bom_bytes + byte_cursor, bom_bytes + byte_cursor + len(encoded), newline)
            )
            byte_cursor += len(encoded) + width
            char_cursor = index + width
            index += width
        if char_cursor < len(text) or not result:
            content = text[char_cursor:]
            encoded = content.encode("utf-8")
            result.append(
                (content, char_cursor, bom_bytes + byte_cursor, bom_bytes + byte_cursor + len(encoded), "")
            )
        if byte_cursor > len(payload):
            raise rejection("malformed_resource")
        return result
