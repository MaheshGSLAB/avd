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
    from collections.abc import Callable
    from typing import TypeVar

    from typing_extensions import Self

    T_CliGeneratorSubclass = TypeVar("T_CliGeneratorSubclass", bound="CliGeneratorProtocol")


class CliModel:
    """
    Accumulator for a single named section of CLI configuration.

    Multi-line strings are automatically split on newlines. None values are ignored.
    Lines are appended via :meth:`extend` from :class:`CliSection` render results.
    """

    def __init__(self) -> None:
        self._lines: list[str] = []

    def extend(self, lines: list[str]) -> None:
        """Extend from a CliSection render result."""
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

    Each section is a :class:`CliModel` that generators write to via
    their ``_model`` property (e.g. ``return self.cli_config.router_bgp``).
    """

    def __init__(self) -> None:
        # Sections are declared in EOS config output order.
        self.config_comment = CliModel()
        self.boot = CliModel()
        self.ethernet_interfaces = CliModel()
        self.router_bgp = CliModel()

    def get_config(self) -> str:
        """Return all non-empty sections joined with newlines, in declaration order."""
        return "\n".join(section.get_config() for section in self.__dict__.values() if isinstance(section, CliModel) and section)

    def __bool__(self) -> bool:
        return any(isinstance(section, CliModel) and bool(section) for section in self.__dict__.values())

    def __str__(self) -> str:
        return self.get_config()


class CliSection:
    """
    Base class for self-contained CLI config sections.

    Each subclass renders one named block (e.g. ``vrf PROD``, ``address-family ipv4``)
    into a list of strings via :meth:`render`. The caller can compose sections by
    calling :meth:`_sub` inside :meth:`_generate`, which renders a child section at
    the next indent level and appends its lines.

    By default (:attr:`separator` is ``True``) a ``!`` line is prepended when the
    section produces any output — identical to EOS behaviour where each top-level or
    sub-block gets a ``!`` separator only when it exists. Set ``separator = False``
    for sections that must not emit a ``!`` prefix.

    Usage::

        class RouterBgpVrf(CliSection):
            def __init__(self, vrf: ...) -> None:
                self.vrf = vrf

            def _generate(self) -> None:
                self._header(f"vrf {self.vrf.name}")
                self._add("rd {}", self.vrf.rd)
                self._sub(RouterBgpVrfAddressFamilyIpv4(self.vrf))


        # caller inside RouterBgpGenerator:
        for vrf in vrfs:
            self._model.extend(RouterBgpVrf(vrf).render(indent=1))
    """

    separator: bool = True
    _INDENT_STR: str = "   "

    def render(self, indent: int = 0) -> list[str]:
        """
        Execute :meth:`_generate` and return lines, optionally prefixed with ``!``.

        Args:
            indent: The indent level at which this section's header is written.
                    Body lines are written at ``indent + 1``; sub-sections start
                    at ``indent + 1`` (their own headers) with bodies at ``indent + 2``.
        """
        self._output_lines: list[str] = []
        self._indent = indent
        self._generate()
        result = self._output_lines
        if result and self.separator:
            return [self._INDENT_STR * indent + "!", *result]
        return result

    def _generate(self) -> None:
        """Override to build output using :meth:`_header`, :meth:`_add`, :meth:`_sub`."""
        raise NotImplementedError

    def _header(self, text: str) -> None:
        """Write the section header line at :attr:`_indent`."""
        self._output_lines.append(f"{self._INDENT_STR * self._indent}{text}")

    def _add(self, template: str | None, /, *values: object) -> None:
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

    def _sub(self, section: CliSection) -> None:
        """Render *section* at ``_indent + 1`` and extend :attr:`_out`."""
        self._output_lines.extend(section.render(self._indent + 1))


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

    def decorator(contributor: Callable[[T_CliGeneratorSubclass], None]) -> Callable[[T_CliGeneratorSubclass], None]:
        contributor._is_cli_config_contributor = True  # pyright: ignore [reportFunctionMemberAccess]

        if toggle_and_value is None:
            return contributor

        toggle, toggle_value = toggle_and_value

        @wraps(contributor)
        def wrapped_contributor(self: T_CliGeneratorSubclass) -> None:
            if get_v2(self.data, toggle, default=None) == toggle_value:
                return contributor(self)

            return None

        return wrapped_contributor

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
            self.data = EosCliConfigGen._from_dict(structured_config)
        else:
            self.data = structured_config

        self.cli_config = CliConfig()
