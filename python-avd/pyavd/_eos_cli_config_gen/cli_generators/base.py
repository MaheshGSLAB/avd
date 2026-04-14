# Copyright (c) 2023-2026 Arista Networks, Inc.
# Use of this source code is governed by the Apache License 2.0
# that can be found in the LICENSE file.
"""Base classes for CLI configuration generators."""

from __future__ import annotations

from contextlib import contextmanager
from functools import wraps
from typing import TYPE_CHECKING, Protocol, overload

from pyavd._eos_cli_config_gen.schema import EosCliConfigGen
from pyavd._utils.get import get_v2

if TYPE_CHECKING:
    from collections.abc import Callable, Iterable, Iterator
    from contextlib import AbstractContextManager
    from typing import TypeVar

    from typing_extensions import Self

    T_CliGeneratorSubclass = TypeVar("T_CliGeneratorSubclass", bound="CliGeneratorProtocol")


class CliLines(list):
    """
    A ``list[str]`` subclass with a conditional format-append method.

    The overridden :meth:`append` accepts an optional sequence of *values*:

    * **No values** — appends *template* verbatim (no-op when falsy, so
      an empty string returned by :meth:`CliGenerator._cli` is safely ignored).
    * **With values** — if *any* value is falsy (``None``, ``False``, ``""``),
      the line is **silently skipped**; otherwise ``template.format(*values)``
      is appended.

    Usage::

        lines = CliLines()
        lines.append("bgp asn notation {}", bgp.as_notation)  # skipped when None
        lines.append("router-id {}", bgp.router_id)  # skipped when None
        lines.append("update wait-for-convergence", bgp.updates.wait_for_convergence)  # skipped when False/None
        lines.append("neighbor {} remote-as {}", ip, remote_as)  # skipped when either is falsy
        lines.append("!")  # always appended
    """

    def append(self, template: str | None, /, *values: object) -> None:  # type: ignore[override]
        if values:
            if any(not v for v in values):
                return
            super().append(template.format(*values))  # type: ignore[arg-type]
        elif template:
            super().append(template)


class CliConfigSection:
    """
    Accumulator for a single named section of CLI configuration.

    Multi-line strings are automatically split on newlines. None values are ignored.
    Use :meth:`append_at` with the current indent level, or drive indentation
    automatically via :meth:`CliGenerator._block`.
    """

    _STEP: str = "   "

    def __init__(self) -> None:
        self._lines: list[str] = []

    def extend_at(self, level: int, lines: Iterable[str] | None) -> None:
        """
        Extend with *lines*, prepending *level* indentation steps to each line.

        Accepts any iterable (list, generator, etc.) so callers can pass lazy
        sequences without materialising an intermediate list first.
        """
        if lines is None:
            return
        prefix = self._STEP * level
        self._lines.extend(f"{prefix}{line}" for line in lines)

    def append(self, line: str | None) -> None:
        """Append a CLI line or multi-line string."""
        if line:
            if "\n" in line:
                self._lines.extend(line.split("\n"))
            else:
                self._lines.append(line)

    def append_at(self, level: int, template: str | None, /, *values: object) -> None:
        """
        Append *template* with dynamic *level* indentation steps.

        Equivalent to ``append_l1`` / ``append_l2`` … but the indent level is
        supplied at call time instead of being baked into the method name.  Use
        this together with :meth:`CliGenerator._block` so that render methods
        never need to hard-code an indent level.
        """
        prefix = self._STEP * level
        if values:
            if any(not v for v in values):
                return
            self.append(f"{prefix}{template.format(*values)}")  # type: ignore[arg-type]
        elif template:
            self.append(f"{prefix}{template}")

    def extend(self, lines: list[str] | None) -> None:
        """Extend with multiple CLI lines."""
        if lines:
            self._lines.extend(lines)

    def get_config(self) -> str:
        """Return accumulated lines joined with newlines."""
        return "\n".join(self._lines)

    def __bool__(self) -> bool:
        return bool(self._lines)

    def __str__(self) -> str:
        return self.get_config()


class CliConfig:
    """
    Container of named CLI config sections rendered in declaration order.

    Each section is a :class:`CliConfigSection` accessible as an attribute::

        self.cli_config.boot.append("!")
        self.cli_config.config_comment.append("!comment")
    """

    def __init__(self) -> None:
        # Sections are declared in EOS config output order.
        self.config_comment = CliConfigSection()
        self.boot = CliConfigSection()
        self.router_bgp = CliConfigSection()

    def get_config(self) -> str:
        """Return all non-empty sections joined with newlines, in declaration order."""
        return "\n".join(section.get_config() for section in self.__dict__.values() if isinstance(section, CliConfigSection) and section)

    def clear(self) -> None:
        """Reset all sections to empty."""
        for section in self.__dict__.values():
            if isinstance(section, CliConfigSection):
                section._lines.clear()

    def __bool__(self) -> bool:
        return any(isinstance(v, CliConfigSection) and bool(v) for v in self.__dict__.values())

    def __str__(self) -> str:
        return self.get_config()


# Overload when assigned with args.
@overload
def cli_config_contributor(
    func: None = None, *, toggle_and_value: tuple[str, bool] | None = None
) -> Callable[[Callable[[T_CliGeneratorSubclass], None]], Callable[[T_CliGeneratorSubclass], None]]: ...


# Overload when assigned without args.
@overload
def cli_config_contributor(func: Callable[[T_CliGeneratorSubclass], None]) -> Callable[[T_CliGeneratorSubclass], None]: ...


def cli_config_contributor(
    func: Callable[[T_CliGeneratorSubclass], None] | None = None, *, toggle_and_value: tuple[str, bool] | None = None
) -> Callable[[T_CliGeneratorSubclass], None] | Callable[[Callable[[T_CliGeneratorSubclass], None]], Callable[[T_CliGeneratorSubclass], None]]:
    """
    Mark methods as CLI config contributors that get called during render().

    Methods should append to self.cli_config instead of returning strings.

    Args:
        func: The method to decorate.
        toggle_and_value: Optional (attribute_path, expected_value) tuple for conditional
            execution. Path can be nested like 'vlan_settings.enabled'. Method only runs
            if self.data.{path} == expected_value.

    TODO: Store the functions in a class variable on CliGeneratorProtocol instead of modifying the func.
    """

    def decorator(fnc: Callable[[T_CliGeneratorSubclass], None]) -> Callable[[T_CliGeneratorSubclass], None]:
        fnc._is_cli_config_contributor = True  # pyright: ignore [reportFunctionMemberAccess]

        if toggle_and_value is None:
            return fnc

        toggle, toggle_value = toggle_and_value

        @wraps(fnc)
        def wrapped_func(self: T_CliGeneratorSubclass) -> None:
            if get_v2(self.data, toggle, default=None) == toggle_value:
                return fnc(self)

            return None

        return wrapped_func

    if func is not None:
        return decorator(func)

    return decorator


class CliGeneratorProtocol(Protocol):
    """
    Protocol for CLI generators.

    Generators render EOS config sections using contributor methods that append
    to self.cli_config. The render() method executes all contributors and returns
    the final config string.
    """

    data: EosCliConfigGen
    """Structured configuration data."""

    cli_config: CliConfig
    """Config accumulator."""

    def render(self) -> str:
        """
        Execute all contributor methods and return generated config.

        Returns:
            CLI configuration text or empty string if not applicable.
        """
        for method in self.cli_config_methods():
            method(self)

        return self.cli_config.get_config()

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

    Subclasses define methods decorated with @cli_config_contributor that append
    config to self.cli_config, then call render() to get the final output.
    """

    _STEP: str = "   "  # single indent step (3 spaces)
    _SEP: str = "!"  # section separator

    @staticmethod
    def _cli(*parts: str | None) -> str:
        """
        Build a CLI command by joining non-falsy parts with a single space.

        Use Python's short-circuit ``and`` to express optional segments without
        explicit ``if`` blocks::

            self._cli(
                "redistribute isis",
                r.isis.isis_level,  # included when not None/False
                r.isis.include_leaked and "include leaked",  # included only when True
                r.isis.route_map and f"route-map {r.isis.route_map}" or r.isis.rcf and f"rcf {r.isis.rcf}",  # first truthy wins (elif)
            )
        """
        return " ".join(str(p) for p in parts if p)

    def __init__(self, structured_config: EosCliConfigGen | dict) -> None:
        """
        Initialize with structured config data.

        Args:
            structured_config: Dict or EosCliConfigGen model. Dicts are converted to the model.
        """
        if isinstance(structured_config, dict):
            self.data = EosCliConfigGen._from_dict(structured_config)
        else:
            self.data = structured_config

        self.cli_config = CliConfig()
        self._indent_level: int = 0

    @property
    def _section(self) -> CliConfigSection:
        """
        The default :class:`CliConfigSection` this generator writes to.

        Subclasses must override this to return the appropriate section from
        :attr:`cli_config`, e.g. ``return self.cli_config.router_bgp``.
        """
        raise NotImplementedError

    def _write(self, template: str | None, /, *values: object) -> None:
        """Write *template* at the current indent level to :attr:`_section`."""
        self._section.append_at(self._indent_level, template, *values)

    def _indent(self, header: str | None = None, /, *values: object, sep: bool = True) -> AbstractContextManager[None]:
        """
        Context manager: write optional *header* at the current indent level, then increment the indent level for the body.

        Decrements the indent level on exit.

        When *sep* is ``True``, a ``!`` separator is written at the current indent level before *header*.
        This replaces the two-line pattern ``self._write("!"); with self._indent(...)`` with a single
        ``with self._indent(..., sep=True):`` call.

        Usage::

            with self._indent(f"router bgp {bgp_as}", sep=True):
                self._write("router-id {}", bgp.router_id)  # indented one level in

            with self._indent(f"vrf {vrf.name}"):
                self._write("rd {}", vrf.rd)
                with self._indent("address-family ipv4", sep=True):
                    self._write("neighbor {} activate", ip)
        """
        return self._block(self._section, header, *values, sep=sep)

    @contextmanager
    def _block(self, section: CliConfigSection, header: str | None = None, /, *values: object, sep: bool = True) -> Iterator[None]:  # type: ignore[misc]
        """
        Context manager that optionally writes a block header then increments the indent level.

        When *sep* is ``True``, a ``!`` separator is written at the current indent level before
        *header*. This is the same separator written by ``self._write("!")``, but co-located with
        the block opening so callers need only one line instead of two.

        Usage::

            # Write "!" then "router bgp 65000" at level 0, execute body at level 1.
            with self._block(cfg, f"router bgp {bgp_as}", sep=True):
                self._render_global_settings(bgp)  # writes at level 1

            # Write "vrf PROD" at level 1, execute body at level 2.
            with self._block(cfg, f"vrf {vrf.name}"):
                cfg.append_at(self._indent_level, "rd {}", vrf.rd)

            # No header — just bump the indent level for a group of calls.
            with self._block(cfg):
                ...

        The *header* / *values* pair follows the same falsy-skip convention as
        :meth:`CliConfigSection.append_at`: if any value is falsy, the header line
        is silently omitted but the indent still increments.
        """
        if sep:
            section.append_at(self._indent_level, self._SEP)
        if header is not None:
            section.append_at(self._indent_level, header, *values)
        self._indent_level += 1
        try:
            yield
        finally:
            self._indent_level -= 1
