# Copyright (c) 2023-2026 Arista Networks, Inc.
# Use of this source code is governed by the Apache License 2.0
# that can be found in the LICENSE file.
"""Base classes for documentation generators."""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol

from pyavd._eos_cli_config_gen.schema import EosCliConfigGen

if TYPE_CHECKING:
    from collections.abc import Callable
    from typing import TypeVar

    from typing_extensions import Self

    T_DocGeneratorSubclass = TypeVar("T_DocGeneratorSubclass", bound="DocGeneratorProtocol")


class DocSection:
    """
    Accumulator for a single named section of markdown documentation.

    Mirrors :class:`CliConfigSection` but emits GitHub-flavoured markdown
    instead of EOS CLI syntax.
    """

    def __init__(self) -> None:
        self._lines: list[str] = []

    def heading(self, level: int, text: str) -> None:
        """Add a markdown heading at *level* (1–6)."""
        self._lines.append(f"\n{'#' * level} {text}")

    def text(self, content: str) -> None:
        """Add a line of plain text."""
        if content:
            self._lines.append(content)

    def table(self, headers: list[str], rows: list[list[str]]) -> None:
        """
        Add a GitHub-flavoured markdown table.

        *headers* is the column header list.
        *rows* is a list of rows; each row must have the same length as *headers*.
        Empty *rows* still emits the header and separator so the section is
        clearly present in the output.
        """
        sep = ["-" * max(len(h), 3) for h in headers]
        self._lines.append("| " + " | ".join(headers) + " |")
        self._lines.append("| " + " | ".join(sep) + " |")
        for row in rows:
            self._lines.append("| " + " | ".join(str(c) for c in row) + " |")

    def code_block(self, content: str, lang: str = "eos") -> None:
        """Add a fenced code block."""
        self._lines.append(f"\n```{lang}\n{content}\n```")

    def get_markdown(self) -> str:
        """Return accumulated lines joined with newlines."""
        return "\n".join(self._lines)

    def __bool__(self) -> bool:
        return bool(self._lines)

    def __str__(self) -> str:
        return self.get_markdown()


class DocConfig:
    """
    Container of named documentation sections rendered in declaration order.

    Each section is a :class:`DocSection` accessible as an attribute.
    Mirrors :class:`CliConfig`.

    Sections are declared in the order they appear in the generated markdown file.
    Add a new ``DocSection()`` attribute here when a new doc generator is introduced.
    """

    def __init__(self) -> None:
        # Sections are declared in documentation output order.
        self.router_bgp = DocSection()

    def get_markdown(self) -> str:
        """Return all non-empty sections joined with newlines, in declaration order."""
        return "\n".join(section.get_markdown() for section in self.__dict__.values() if isinstance(section, DocSection) and section)

    def clear(self) -> None:
        """Reset all sections to empty."""
        for section in self.__dict__.values():
            if isinstance(section, DocSection):
                section._lines.clear()

    def __bool__(self) -> bool:
        return any(isinstance(v, DocSection) and bool(v) for v in self.__dict__.values())

    def __str__(self) -> str:
        return self.get_markdown()


def doc_contributor(func: Callable[[T_DocGeneratorSubclass], None]) -> Callable[[T_DocGeneratorSubclass], None]:
    """
    Mark a method as a documentation contributor called during :meth:`DocGeneratorProtocol.render`.

    Methods should write to ``self.doc_config`` via ``self._section`` instead of returning strings.

    Mirrors :func:`cli_config_contributor`.
    """
    func._is_doc_contributor = True  # pyright: ignore [reportFunctionMemberAccess]
    return func


class DocGeneratorProtocol(Protocol):
    """
    Protocol for documentation generators.

    Mirrors :class:`CliGeneratorProtocol`.
    """

    data: EosCliConfigGen
    """Structured configuration data."""

    doc_config: DocConfig
    """Documentation accumulator."""

    def render(self) -> str:
        """
        Execute all contributor methods and return generated markdown.

        Returns:
            Markdown text or empty string if not applicable.
        """
        for method in self.doc_methods():
            method(self)

        return self.doc_config.get_markdown()

    @classmethod
    def doc_methods(cls) -> list[Callable[[Self], None]]:
        """Return methods decorated with @doc_contributor."""
        return [method for key in cls._keys() if getattr(method := getattr(cls, key), "_is_doc_contributor", False)]

    @classmethod
    def _keys(cls) -> list[str]:
        """Return all attribute names. Override to customise contributor execution order."""
        return dir(cls)


class DocGenerator(DocGeneratorProtocol):
    """
    Base class for documentation generators.

    Subclasses define methods decorated with :func:`doc_contributor` that write
    markdown to ``self.doc_config``, then call :meth:`render` to get the final output.

    Mirrors :class:`CliGenerator`.
    """

    def __init__(self, structured_config: EosCliConfigGen | dict) -> None:
        """
        Initialise with structured config data.

        Args:
            structured_config: Dict or EosCliConfigGen model. Dicts are converted to the model.
        """
        if isinstance(structured_config, dict):
            self.data = EosCliConfigGen._from_dict(structured_config)
        else:
            self.data = structured_config

        self.doc_config = DocConfig()

    @property
    def _section(self) -> DocSection:
        """
        The :class:`DocSection` this generator writes to.

        Subclasses must override this to return the appropriate section from
        :attr:`doc_config`, e.g. ``return self.doc_config.router_bgp``.
        """
        raise NotImplementedError

    @staticmethod
    def _default(*values: object, fallback: str = "-") -> str:
        """
        Return the first non-``None`` value as a string, or *fallback*.

        Replaces the ``| arista.avd.default(v1, v2, '-') |`` Jinja2 filter chain.

        Usage::

            self._default(neighbor.remote_as, inherited_remote_as)          # → first non-None, else "-"
            self._default(neighbor.vrf, inherited_vrf, fallback="default")  # → first non-None, else "default"
        """
        for v in values:
            if v is not None:
                return str(v)
        return fallback
