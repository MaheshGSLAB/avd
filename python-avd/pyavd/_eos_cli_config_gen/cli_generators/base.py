# Copyright (c) 2023-2026 Arista Networks, Inc.
# Use of this source code is governed by the Apache License 2.0
# that can be found in the LICENSE file.
"""Base classes for CLI configuration generators."""

from __future__ import annotations

from functools import wraps
from typing import TYPE_CHECKING, Protocol, overload

from pyavd._eos_cli_config_gen.schema import EosCliConfigGen
from pyavd._utils.get import get_v2

if TYPE_CHECKING:
    from collections.abc import Callable, Iterable
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


class _IndentedSection:
    """Proxy that prepends a fixed indentation prefix to every :meth:`append` call."""

    __slots__ = ("_prefix", "_section")

    def __init__(self, section: CliConfigSection, prefix: str) -> None:
        self._section = section
        self._prefix = prefix

    def append(self, line: str | None) -> None:
        """Append *line* prefixed with the configured indentation."""
        self._section.append(f"{self._prefix}{line}" if line else None)


class CliConfigSection:
    """
    Accumulator for a single named section of CLI configuration.

    Multi-line strings are automatically split on newlines. None values are ignored.
    Use ``append_l1`` … ``append_l4`` to prepend indentation automatically, or call
    :meth:`at` once per function to get an :class:`_IndentedSection` that applies a
    fixed indent level to every ``append`` call without repeating the level suffix.
    """

    _STEP: str = "   "
    _L1: str = _STEP
    _L2: str = _STEP * 2
    _L3: str = _STEP * 3
    _L4: str = _STEP * 4

    def __init__(self) -> None:
        self._lines: list[str] = []

    def at(self, level: int) -> _IndentedSection:
        """Return a writer that prepends *level* indentation steps to every :meth:`append` call."""
        return _IndentedSection(self, self._STEP * level)

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

    def append_l1(self, template: str | None, /, *values: object) -> None:
        """
        Append *template* with L1 indentation (3 spaces).

        When *values* are given, behaves like :meth:`CliLines.append`: skips the
        line silently if any value is falsy, otherwise formats and appends.
        """
        if values:
            if any(not v for v in values):
                return
            self.append(f"{self._L1}{template.format(*values)}")  # type: ignore[arg-type]
        elif template:
            self.append(f"{self._L1}{template}")

    def append_l2(self, template: str | None, /, *values: object) -> None:
        """
        Append *template* with L2 indentation (6 spaces).

        When *values* are given, behaves like :meth:`CliLines.append`: skips the
        line silently if any value is falsy, otherwise formats and appends.
        """
        if values:
            if any(not v for v in values):
                return
            self.append(f"{self._L2}{template.format(*values)}")  # type: ignore[arg-type]
        elif template:
            self.append(f"{self._L2}{template}")

    def append_l3(self, template: str | None, /, *values: object) -> None:
        """
        Append *template* with L3 indentation (9 spaces).

        When *values* are given, behaves like :meth:`CliLines.append`: skips the
        line silently if any value is falsy, otherwise formats and appends.
        """
        if values:
            if any(not v for v in values):
                return
            self.append(f"{self._L3}{template.format(*values)}")  # type: ignore[arg-type]
        elif template:
            self.append(f"{self._L3}{template}")

    def append_l4(self, template: str | None, /, *values: object) -> None:
        """
        Append *template* with L4 indentation (12 spaces).

        When *values* are given, behaves like :meth:`CliLines.append`: skips the
        line silently if any value is falsy, otherwise formats and appends.
        """
        if values:
            if any(not v for v in values):
                return
            self.append(f"{self._L4}{template.format(*values)}")  # type: ignore[arg-type]
        elif template:
            self.append(f"{self._L4}{template}")

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
    _SEP: str = "!"  # top-level section separator
    _L1: str = _STEP  # "   "
    _L2: str = _STEP * 2  # "      "
    _L3: str = _STEP * 3  # "         "
    _L4: str = _STEP * 4  # "            "
    _SEP_L1: str = _STEP + "!"  # "   !"
    _SEP_L2: str = _STEP * 2 + "!"  # "      !"
    _SEP_L3: str = _STEP * 3 + "!"  # "         !"

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
