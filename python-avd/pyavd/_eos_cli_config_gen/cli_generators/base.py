# Copyright (c) 2023-2026 Arista Networks, Inc.
# Use of this source code is governed by the Apache License 2.0
# that can be found in the LICENSE file.
"""Base classes for CLI configuration generators."""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol

from pyavd._eos_cli_config_gen.schema import EosCliConfigGen

if TYPE_CHECKING:
    from collections.abc import Callable
    from typing import TypeVar

    from typing_extensions import Self

    T_CliGeneratorSubclass = TypeVar("T_CliGeneratorSubclass", bound="CliGeneratorProtocol")


class CliSection:
    """
    Base class for self-contained CLI config sections.

    Each subclass renders one named block (e.g. ``vrf PROD``, ``address-family ipv4``)
    into a list of strings via :meth:`render`. The caller can compose sections by
    calling :meth:`_sub_section` inside :meth:`_section`, which renders a child section at
    the next indent level and appends its lines.

    By default (:attr:`separator` is ``True``) a ``!`` line is prepended when the
    section produces any output — identical to EOS behaviour where each top-level or
    sub-block gets a ``!`` separator only when it exists. Set ``separator = False``
    for sections that must not emit a ``!`` prefix.

    Usage::

        class RouterBgpVrf(CliSection):
            def __init__(self, vrf: ...) -> None:
                self.vrf = vrf

            def _section(self) -> None:
                self._section_heading(f"vrf {self.vrf.name}")
                self._cli_line("rd {}", self.vrf.rd)
                self._sub_section(RouterBgpVrfAddressFamilyIpv4(self.vrf))


        # caller inside RouterBgpGenerator:
        for vrf in vrfs:
            self._model.extend(RouterBgpVrf(vrf).render(indent=1))
    """

    separator: bool = True
    _INDENT_STR: str = "   "

    def render(self, indent: int = 0, *, skip_separator: bool = False) -> list[str]:
        """
        Execute :meth:`_section` and return lines, optionally prefixed with ``!``.

        Args:
            indent: The indent level at which this section's header is written.
                    Body lines are written at ``indent + 1``; sub-sections start
                    at ``indent + 1`` (their own headers) with bodies at ``indent + 2``.
            skip_separator: If True, suppress the leading ``!`` for this render
                    call even when :attr:`separator` is True. Useful for the first
                    item in a sequence of repeated sub-sections that should be
                    separated by ``!`` between entries but not before the first.
        """
        self._output_lines: list[str] = []
        self._indent = indent
        self._section()
        result = self._output_lines
        if result and self.separator and not skip_separator:
            return [self._INDENT_STR * indent + "!", *result]
        return result

    def _section(self) -> None:
        """Override to build output using :meth:`_section_heading`, :meth:`_cli_line`, :meth:`_sub_section`."""
        raise NotImplementedError

    def _section_heading(self, text: str) -> None:
        """Write the section header line at :attr:`_indent`."""
        self._output_lines.append(f"{self._INDENT_STR * self._indent}{text}")

    def _cli_line(self, template: str | None, /, *values: object) -> None:
        """
        Write a body line at ``_indent + 1``.

        Skips silently if *template* is falsy or if any positional *value* is falsy.
        """
        prefix = self._INDENT_STR * (self._indent + 1)
        if values:
            if any(not v for v in values):
                return
            if template:
                self._output_lines.append(f"{prefix}{template.format(*values)}")
        elif template:
            self._output_lines.append(f"{prefix}{template}")

    def _sub_section(self, section: CliSection, *, skip_separator: bool = False) -> None:
        """
        Render *section* at ``_indent + 1`` and extend :attr:`_out`.

        Args:
            section: The child :class:`CliSection` to render.
            skip_separator: If True, suppress the leading ``!`` for this child render
                even when ``section.separator`` is True. Use this for the first item
                in a sequence of repeated sub-sections where ``!`` should appear
                *between* entries but not *before* the first.
        """
        self._output_lines.extend(section.render(self._indent + 1, skip_separator=skip_separator))


def cli_config_contributor(func: Callable[[T_CliGeneratorSubclass], None]) -> Callable[[T_CliGeneratorSubclass], None]:
    """
    Mark a method as a CLI config contributor called during :meth:`CliGeneratorProtocol.render`.

    Methods should append to ``self._model`` instead of returning strings.

    TODO: Store the functions in a class variable on CliGeneratorProtocol instead of modifying the func.
    """
    func._is_cli_config_contributor = True  # pyright: ignore [reportFunctionMemberAccess]
    return func


class CliGeneratorProtocol(Protocol):
    """
    Protocol for CLI generators.

    Generators render EOS config sections using contributor methods that append
    to ``self._model``. The :meth:`render` method executes all contributors and
    returns the final config string.
    """

    inputs: EosCliConfigGen
    """Structured configuration data."""

    _model: list[str]
    """Accumulator the generator writes lines into."""

    def render(self) -> str:
        """
        Execute all contributor methods and return generated config.

        Returns:
            CLI configuration text or empty string if not applicable.
        """
        for method in self.cli_config_methods():
            method(self)

        return "\n".join(self._model)

    @classmethod
    def cli_config_methods(cls) -> list[Callable[[Self], None]]:
        """Return methods decorated with @cli_config_contributor."""
        return [method for key in cls._keys() if getattr(method := getattr(cls, key), "_is_cli_config_contributor", False)]

    @classmethod
    def _keys(cls) -> list[str]:
        """Return all attribute names. Override to customize contributor execution order."""
        return dir(cls)


class CliGenerator(CliGeneratorProtocol):
    """
    Base class for CLI configuration generators.

    Subclasses define methods decorated with ``@cli_config_contributor`` that call
    ``self._model.extend(SomeSection(...).render(indent=N))`` to build config, then
    expose the result via :meth:`render`.
    """

    def __init__(self, structured_config: EosCliConfigGen | dict) -> None:
        """
        Initialize with structured config data.

        Args:
            structured_config: Dict or EosCliConfigGen model. Dicts are converted to the model.
        """
        if isinstance(structured_config, dict):
            self.inputs = EosCliConfigGen._from_dict(structured_config)
        else:
            self.inputs = structured_config

        self._model: list[str] = []
