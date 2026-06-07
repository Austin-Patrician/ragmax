from collections.abc import Mapping
from dataclasses import dataclass, field

from ragmax.application.indexing.dtos import SourceInput
from ragmax.application.indexing.ports import SourceParser
from ragmax.core.exceptions import InvalidRequestError
from ragmax.domain.indexing.profiles import IndexingProfile


@dataclass(frozen=True)
class ParserSpec:
    name: str
    description: str
    supported_extensions: tuple[str, ...] = field(default_factory=tuple)
    supported_media_types: tuple[str, ...] = field(default_factory=tuple)
    requires_api_key: bool = False
    is_default: bool = False
    is_internal: bool = False

    def to_dict(self) -> dict[str, object]:
        return {
            "name": self.name,
            "description": self.description,
            "supported_extensions": list(self.supported_extensions),
            "supported_media_types": list(self.supported_media_types),
            "requires_api_key": self.requires_api_key,
            "is_default": self.is_default,
            "is_internal": self.is_internal,
        }


@dataclass(frozen=True)
class ResolvedParser:
    name: str
    parser: SourceParser
    spec: ParserSpec


class SourceParserRegistry:
    def __init__(
        self,
        *,
        parsers: Mapping[str, SourceParser],
        specs: tuple[ParserSpec, ...],
        default_file_parser: str,
        inline_parser: str,
    ) -> None:
        self._parsers = dict(parsers)
        self._specs = {spec.name: spec for spec in specs}
        self._default_file_parser = default_file_parser
        self._inline_parser = inline_parser

    def list(self, *, include_internal: bool = False) -> tuple[ParserSpec, ...]:
        specs = tuple(self._specs.values())
        if include_internal:
            return specs
        return tuple(spec for spec in specs if not spec.is_internal)

    def resolve(
        self,
        *,
        source: SourceInput,
        requested_parser: str | None,
        requested_profile: IndexingProfile | None,
    ) -> ResolvedParser:
        parser_name = self._resolve_name(
            source=source,
            requested_parser=requested_parser,
            requested_profile=requested_profile,
        )
        parser = self._parsers.get(parser_name)
        spec = self._specs.get(parser_name)
        if parser is None or spec is None:
            raise InvalidRequestError(f"Unknown source parser: {parser_name}")

        self._validate_source_supported(source, spec)
        return ResolvedParser(name=parser_name, parser=parser, spec=spec)

    def _resolve_name(
        self,
        *,
        source: SourceInput,
        requested_parser: str | None,
        requested_profile: IndexingProfile | None,
    ) -> str:
        if requested_parser:
            return requested_parser
        if source.text or source.blocks:
            return self._inline_parser
        if requested_profile is not None:
            return requested_profile.parser
        return self._default_file_parser

    def _validate_source_supported(self, source: SourceInput, spec: ParserSpec) -> None:
        if spec.is_internal:
            return
        if not source.file_path:
            raise InvalidRequestError(f"Parser '{spec.name}' requires an uploaded file source.")

        extension = _extension_from_filename(source.filename)
        if spec.supported_extensions and extension not in spec.supported_extensions:
            raise InvalidRequestError(
                f"Parser '{spec.name}' does not support file extension '{extension}'."
            )


def _extension_from_filename(filename: str) -> str:
    suffix = filename.rsplit(".", maxsplit=1)
    if len(suffix) != 2 or not suffix[1]:
        return ""
    return f".{suffix[1].lower()}"
