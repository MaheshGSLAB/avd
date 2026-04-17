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
    from collections.abc import Callable, Iterator
    from contextlib import AbstractContextManager
    from typing import TypeVar

    from typing_extensions import Self

    T_CliGeneratorSubclass = TypeVar("T_CliGeneratorSubclass", bound="CliGeneratorProtocol")


class CliModel:
    """
    Accumulator for a single named section of CLI configuration.

    Multi-line strings are automatically split on newlines. None values are ignored.
    Use :meth:`append_at` with the current indent level, or drive indentation
    automatically via :meth:`CliGenerator._block_into`.
    """

    _INDENT: str = "   "

    def __init__(self) -> None:
        self._lines: list[str] = []

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
        this together with :meth:`CliGenerator._block_into` so that render methods
        never need to hard-code an indent level.
        """
        prefix = self._INDENT * level
        if values:
            if any(not v for v in values):
                return
            self.append(f"{prefix}{template.format(*values)}")  # type: ignore[arg-type]
        elif template:
            self.append(f"{prefix}{template}")

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
        return any(isinstance(v, CliModel) and bool(v) for v in self.__dict__.values())

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


class CliWriter:
    """
    Mixin that provides CLI writing primitives for generator classes.

    Tracks the current indent level and writes CLI lines into a :class:`CliModel`
    via :meth:`_add` and :meth:`_block`. Subclasses must supply :attr:`_model`
    (the target section) and set ``self._block_level = 0`` in ``__init__``.
    """

    _block_level: int
    _EXCLAMATION: str = "!"  # written before each block header when exclamation=True

    @property
    def _model(self) -> CliModel:
        """
        The :class:`CliModel` this writer targets.

        Subclasses must override to return the appropriate section from
        ``self.cli_config``, e.g. ``return self.cli_config.router_bgp``.
        """
        raise NotImplementedError

    def _add(self, template: str | None, /, *values: object) -> None:
        """Add a single CLI line at the current indent level into :attr:`_model`."""
        self._model.append_at(self._block_level, template, *values)

    def _block(self, header: str | None = None, /, *values: object, exclamation: bool = True) -> AbstractContextManager[None]:
        """
        Context manager: open a CLI block in :attr:`_model`.

        Writes an optional ``!`` separator (when *exclamation* is ``True``), writes
        *header* at the current indent level, then increments the level for the body.
        Decrements on exit.

        Usage::

            with self._block(f"router bgp {bgp_as}"):
                self._add("router-id {}", bgp.router_id)

            with self._block(f"vrf {vrf.name}"):
                self._add("rd {}", vrf.rd)
                with self._block("address-family ipv4"):
                    self._add("neighbor {} activate", ip)

            with self._block("encapsulation vlan", exclamation=False):
                self._add("client dot1q {} network dot1q {}", c_vlan, n_vlan)
        """
        return self._block_into(self._model, header, *values, exclamation=exclamation)

    @contextmanager
    def _block_into(self, model: CliModel, header: str | None = None, /, *values: object, exclamation: bool = True) -> Iterator[None]:  # type: ignore[misc]
        """
        Context manager: open a CLI block writing into an explicit *model*.

        Identical to :meth:`_block` but targets *model* instead of :attr:`_model`.
        Used internally by :meth:`_block`; call directly only when writing to a
        section other than the default.

        The *header* / *values* pair follows the same falsy-skip convention as
        :meth:`CliModel.append_at`: if any value is falsy the header line is
        silently omitted but the indent still increments.
        """
        if exclamation:
            model.append_at(self._block_level, self._EXCLAMATION)
        if header is not None:
            model.append_at(self._block_level, header, *values)
        self._block_level += 1
        try:
            yield
        finally:
            self._block_level -= 1


class CliGenerator(CliWriter, CliGeneratorProtocol):
    """
    Base class for CLI configuration generators.

    Combines :class:`CliWriter` (writing primitives) with :class:`CliGeneratorProtocol`
    (render loop). Subclasses define methods decorated with ``@cli_config_contributor`` that
    call :meth:`_add` / :meth:`_block` to build config, then expose it via
    :meth:`render`.
    """

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
        self._block_level = 0
