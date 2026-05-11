# Copyright (c) 2023-2026 Arista Networks, Inc.
# Use of this source code is governed by the Apache License 2.0
# that can be found in the LICENSE file.
"""
Base classes and helpers for CLI configuration generators.

Two complementary layers live here:

1. **Class-based scaffolding** (:class:`CliGenerator`, :class:`CliConfig`,
   :class:`CliModel`, :class:`CliSection`, :func:`cli_config_contributor`).
   Generators subclass :class:`CliGenerator`, decorate methods with
   ``@cli_config_contributor``, and append rendered lines to ``self.cli_config``.

2. **Schema-driven rendering** (:func:`render_schema_field`,
   :func:`render_from_schema`, :func:`resolve_template`).
   These walk the ``cli`` annotations embedded in the schema and render lines
   straight from an :class:`~pyavd._schema.models.avd_model.AvdModel` instance —
   so the schema stays the single source of truth for fields whose CLI shape can
   be expressed declaratively. Manual contributor methods can mix in
   schema-driven output for the simple fields and only hand-write the cases
   schema annotations cannot express.

All input data is read via attribute access on ``AvdModel`` (and iteration over
``AvdList`` / ``AvdIndexedList``) — never via dict ``.get()`` — so renamed fields
like ``as`` → ``field_as`` resolve through the model's ``_key_to_field_map``.

Supported ``cli`` annotation keys
---------------------------------
``section``                 Dict → named CLI block header (``section: "router bgp {as}"``)
``line``                    Any → single body line resolved from the *parent* model
``lines``                   Dict → multiple body lines, each template independently
                            resolved from the dict's own data. A line is rendered
                            only if all its placeholders resolve; supports the
                            ``?field_path`` truthy-guard suffix from ``item_lines``.
``line_fragments``          Dict → one composite line built from an ordered list of
                            fragments. The first fragment is the anchor: if it has
                            ``{placeholders}`` and they don't resolve, the whole line
                            is skipped. Subsequent fragments are concatenated only
                            when all their placeholders resolve. Each fragment may
                            also carry a ``?field_path`` truthy-guard suffix; the
                            fragment is skipped when the guard is falsy. If the
                            anchor has no placeholders / no guard and no data
                            fragment resolves, skip the line — unless ``cli.gate``
                            is set, in which case the anchor renders alone.
``gate``                    Any → one expression or a list of expressions; the
                            field renders only if all evaluate truthy. Each
                            expression is a field path that may be prefixed with
                            ``!`` to negate the truthy check and/or ``^`` to
                            evaluate against the *parent* data context.
                            Examples: ``enabled``, ``!enabled``, ``^enabled``,
                            ``!^enabled``, ``[enabled, !^enabled]``.
``bool_true_line``          Bool → fixed line when value is ``True``
``bool_false_line``         Bool → fixed line when value is ``False``
``item_lines``              List → one or more line templates per item
``item_line_fragments``     List → one composite line per item (per-item version
                            of ``line_fragments`` — same anchor + optional
                            fragments + ``?guard`` semantics).
``item_gate``               List → per-item gate (same syntax as ``cli.gate``,
                            including ``!``/``^``/``||``). Items where the gate
                            fails are skipped entirely.
``sort_key``                List → field name; items are natural-sorted by this
                            field before rendering. ``AvdIndexedList`` items are
                            always sorted by their primary key.
``separator``               Emit ``!`` before section header (default ``True``)
``section_only_if_content`` Skip header when no children rendered (default ``True``)

Template variables
------------------
``{var}``           — references a field on the current model
``{parent.child}``  — dot-notation traversal across nested models
A line is skipped if any referenced variable resolves to ``None``/``Undefined``.

For ``item_lines`` / ``lines`` / ``line_fragments``, the suffix ``?field_path``
acts as a boolean guard: the template is skipped unless the named field
(dot-notation supported) is truthy on the current context. The negated form
``?!field_path`` skips the template when the field IS truthy. Either suffix is
stripped from the rendered output.

Example schema::

    router_bgp:
      type: dict
      cli:
        section: "router bgp {as}"
        section_only_if_content: false
      keys:
        as_notation:
          type: str
          cli: { line: "bgp asn notation {as_notation}" }
        peer_groups:
          type: list
          cli:
            item_lines:
              - "neighbor {name} peer group"
              - "neighbor {name} remote-as {remote_as}"
              - "neighbor {name} shutdown?shutdown"
"""

from __future__ import annotations

import re
from functools import wraps
from typing import TYPE_CHECKING, Any, Protocol, overload

from pyavd._eos_cli_config_gen.schema import EosCliConfigGen
from pyavd._schema.models.avd_indexed_list import AvdIndexedList
from pyavd._schema.models.avd_list import AvdList
from pyavd._schema.models.avd_model import AvdModel
from pyavd._utils.get import get_v2

if TYPE_CHECKING:
    from collections.abc import Callable
    from typing import TypeVar

    from typing_extensions import Self

    T_CliGeneratorSubclass = TypeVar("T_CliGeneratorSubclass", bound="CliGeneratorProtocol")


# ---------------------------------------------------------------------------
# Class-based scaffolding
# ---------------------------------------------------------------------------


class CliModel:
    """
    Accumulator for a single named section of CLI configuration.

    Lines are appended via :meth:`extend` from :class:`CliSection` render results
    (or directly from contributor methods).
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
        """Render *section* at ``_indent + 1`` and extend output."""
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


# ---------------------------------------------------------------------------
# Schema-driven rendering (operates on AvdModel attribute access)
# ---------------------------------------------------------------------------


_INDENT = CliSection._INDENT_STR
# Supports plain {var} and dot-notation {parent.child}
_TEMPLATE_VAR_RE = re.compile(r"\{([\w.]+)\}")
# Matches an optional boolean guard suffix like "?shutdown" (truthy) or "?!shutdown"
# (negated — skip when truthy). Path supports dot-notation: "?bfd_timers.interval".
_CONDITION_SUFFIX_RE = re.compile(r"\?(!?)([\w][\w.]*)\s*$")


def _evaluate_gates(gate_spec: str | list[str], data: Any, parent_data: Any) -> bool:
    """
    Evaluate one or more gate expressions; return True only if all pass.

    Each expression is a field path with optional ``!`` (negate) and ``^``
    (parent context) prefixes — e.g. ``enabled``, ``!enabled``, ``^enabled``,
    ``!^enabled``. Multiple paths joined with ``||`` form an OR group: the
    expression passes if any alternative evaluates truthy. The list-level
    semantics is AND: every expression must pass for the gate to open.
    """
    expressions = [gate_spec] if isinstance(gate_spec, str) else gate_spec
    for expr in expressions:
        alternatives = [a.strip() for a in expr.split("||")]
        if not any(_evaluate_single_gate(a, data, parent_data) for a in alternatives):
            return False
    return True


def _evaluate_single_gate(expr: str, data: Any, parent_data: Any) -> bool:
    """Evaluate one gate path with optional ``!`` and ``^`` prefixes."""
    negate = expr.startswith("!")
    if negate:
        expr = expr[1:]
    if expr.startswith("^"):
        context = parent_data
        expr = expr[1:]
    else:
        context = data
    value = bool(_resolve_path(context, expr))
    return value != negate


def _model_get(context: Any, key: str) -> Any:
    """
    Read one segment from *context* using attribute access.

    For :class:`AvdModel`, applies the schema's ``_key_to_field_map`` so renamed
    fields (e.g. ``as`` → ``field_as``) resolve from the original schema key.
    Returns ``None`` when the field is unknown or unset.
    """
    if context is None:
        return None
    if isinstance(context, AvdModel):
        field_name = type(context)._key_to_field_map.get(key, key)
        if field_name not in type(context)._fields:
            return None
        # __getattr__ resolves the field default for unset fields, which is
        # None for scalars and an empty model/list for nested types — both are
        # treated as "no value" by callers below.
        return getattr(context, field_name, None)
    # Fallback for plain dicts (e.g. {"_item": value} synthetic context for scalars).
    if isinstance(context, dict):
        return context.get(key)
    return None


def _resolve_path(context: Any, path: str) -> Any:
    """
    Traverse a dot-notation path through nested models / dicts.

    Returns ``None`` if any segment is absent or resolves to a falsy empty model.
    """
    current = context
    for part in path.split("."):
        current = _model_get(current, part)
        if current is None:
            return None
        # An empty AvdModel is falsy — treat as missing so templates skip cleanly.
        if isinstance(current, AvdModel) and not current:
            return None
    return current


def resolve_template(template: str, context: Any) -> str | None:
    """
    Resolve ``{var}`` (and ``{parent.child}``) placeholders from *context*.

    Returns ``None`` if any referenced variable is absent or ``None`` so that
    callers can skip rendering incomplete lines.
    """
    variables = _TEMPLATE_VAR_RE.findall(template)
    result = template
    for var in variables:
        val = _resolve_path(context, var)
        if val is None:
            return None
        result = result.replace("{" + var + "}", str(val), 1)
    return result


def render_schema_field(
    schema: dict,
    data: Any,
    parent_data: Any,
    indent: int,
) -> list[str]:
    """
    Render one schema field according to its ``cli`` annotation.

    Args:
        schema:      Schema dict for this field.
        data:        Data value for this field — typically an :class:`AvdModel`,
                     :class:`AvdList`, :class:`AvdIndexedList`, or scalar.
        parent_data: The parent model, used as the resolution context for
                     ``cli.line`` templates (gives access to sibling fields).
        indent:      Current indentation level (0 = top-level).

    Returns:
        A list of CLI output lines (empty list = nothing to render).
    """
    cli: dict = schema.get("cli") or {}
    schema_type: str = schema.get("type", "")

    # --- cli.gate: one or more truthy guards on the current/parent data ---
    if "gate" in cli and not _evaluate_gates(cli["gate"], data, parent_data):
        return []

    # --- Bool: bool_true_line / bool_false_line ---
    if schema_type == "bool":
        if data is True and "bool_true_line" in cli:
            return [_INDENT * indent + cli["bool_true_line"]]
        if data is False and "bool_false_line" in cli:
            return [_INDENT * indent + cli["bool_false_line"]]
        return []

    # --- cli.line: single body line resolved from parent context ---
    if "line" in cli:
        rendered = resolve_template(cli["line"], parent_data)
        if rendered is None:
            return []
        return [_INDENT * indent + rendered]

    # --- cli.line_fragments: one composite line + recurse into annotated children ---
    if "line_fragments" in cli and isinstance(data, AvdModel):
        own = _render_line_fragments(cli["line_fragments"], data, indent, has_gate="gate" in cli)
        return own + _render_dict_children(schema, data, indent)

    # --- cli.lines: multiple body lines + recurse into annotated children ---
    if "lines" in cli and isinstance(data, AvdModel):
        return _render_lines(cli["lines"], data, indent) + _render_dict_children(schema, data, indent)

    # --- List with item_lines: one or more lines per list item ---
    if schema_type == "list" and "item_lines" in cli and isinstance(data, (AvdList, AvdIndexedList, list)):
        return _render_list_items(cli["item_lines"], _sort_items(data, cli.get("sort_key")), indent, item_gate=cli.get("item_gate"))

    # --- List with item_line_fragments: one composite line per list item ---
    if schema_type == "list" and "item_line_fragments" in cli and isinstance(data, (AvdList, AvdIndexedList, list)):
        return _render_list_item_fragments(
            cli["item_line_fragments"], _sort_items(data, cli.get("sort_key")), indent, item_gate=cli.get("item_gate")
        )

    # --- Dict with section: named CLI block with indented children ---
    if "section" in cli and schema_type == "dict" and isinstance(data, AvdModel):
        return _render_section(schema, cli, data, indent)

    # --- Dict without CLI section: recurse transparently at same indent ---
    if schema_type == "dict" and isinstance(data, AvdModel):
        return _render_dict_children(schema, data, indent)

    # Scalar with no applicable cli annotation — not rendered by this system
    return []


def _apply_item_template(template: str, context: Any) -> str | None:
    """
    Apply one item_lines template to a context (model or scalar).

    Strips an optional ``?field_path`` (truthy-required) or ``?!field_path``
    (truthy-forbidden) guard suffix before resolving ``{var}`` placeholders.
    Returns ``None`` when the guard fails or any placeholder doesn't resolve.
    """
    m = _CONDITION_SUFFIX_RE.search(template)
    if m:
        negate, path = m.group(1), m.group(2)
        value = _resolve_path(context, path)
        if negate and value:
            return None
        if not negate and not value:
            return None
        template = template[: m.start()]
    return resolve_template(template, context)


def _sort_items(items: Any, sort_key: str | None) -> Any:
    """
    Natural-sort a list-typed value before rendering.

    ``AvdIndexedList`` always sorts by its primary key (``sort_key`` is ignored).
    ``AvdList`` sorts by *sort_key* when provided, else by item value (works for
    scalar lists). Plain Python ``list`` is returned as-is.
    """
    if isinstance(items, AvdIndexedList):
        return items._natural_sorted()
    if isinstance(items, AvdList):
        return items._natural_sorted(sort_key=sort_key) if sort_key else items._natural_sorted()
    return items


def _list_item_context(item: Any) -> Any | None:
    """Wrap a list item into a render context. Returns None if the item should be skipped."""
    if isinstance(item, (AvdModel, dict)):
        return item
    if item is None:
        return None
    return {"_item": str(item)}


def _render_list_items(
    item_line_templates: list[str],
    items: Any,
    indent: int,
    *,
    item_gate: str | list[str] | None = None,
) -> list[str]:
    """
    Render each item in a list using the provided line templates.

    For :class:`AvdModel` items, variables in templates are resolved from the
    item via attribute access. For scalar items (``AvdList[str]`` etc.), the
    special variable ``{_item}`` expands to the item value. A template line is
    emitted only if all its variable references resolve.

    A ``?field_path`` suffix acts as a boolean guard: the line is skipped unless
    that field (dot-notation supported) is truthy on the item context, and the
    suffix is stripped from the rendered output.

    If *item_gate* is provided, an item is skipped entirely when its gates fail.
    """
    lines: list[str] = []
    for item in items:
        context = _list_item_context(item)
        if context is None:
            continue
        if item_gate is not None and not _evaluate_gates(item_gate, context, None):
            continue
        for tpl in item_line_templates:
            rendered = _apply_item_template(tpl, context)
            if rendered is not None:
                lines.append(_INDENT * indent + rendered)
    return lines


def _render_list_item_fragments(
    fragments: list[str],
    items: Any,
    indent: int,
    *,
    item_gate: str | list[str] | None = None,
) -> list[str]:
    """
    Render one composite line per list item from the provided fragment list.

    Each item becomes a render context; ``_render_line_fragments`` runs against
    it. Per-item ``cli.item_gate`` skips items whose gates fail. The line-level
    ``has_gate=True`` flag is set when ``item_gate`` is present so the bare
    anchor renders even if no data fragment resolves.
    """
    lines: list[str] = []
    has_gate = item_gate is not None
    for item in items:
        context = _list_item_context(item)
        if context is None:
            continue
        if item_gate is not None and not _evaluate_gates(item_gate, context, None):
            continue
        lines.extend(_render_line_fragments(fragments, context, indent, has_gate=has_gate))
    return lines


def _render_lines(line_templates: list[str], context: AvdModel, indent: int) -> list[str]:
    """
    Render multiple body lines from one dict's own data.

    Each template is resolved independently from *context*; a line is emitted
    only if all its placeholders resolve. Templates may carry the
    ``?field_path`` truthy-guard suffix (same syntax as ``item_lines``).
    """
    lines: list[str] = []
    for tpl in line_templates:
        rendered = _apply_item_template(tpl, context)
        if rendered is not None:
            lines.append(_INDENT * indent + rendered)
    return lines


def _is_data_fragment(template: str) -> bool:
    """A fragment is 'data' if it carries a {placeholder} or a ?guard suffix."""
    return bool(_TEMPLATE_VAR_RE.search(template) or _CONDITION_SUFFIX_RE.search(template))


def _render_line_fragments(fragments: list[str], context: AvdModel, indent: int, *, has_gate: bool = False) -> list[str]:
    """
    Render one composite line built from an ordered list of fragments.

    The first fragment is the *anchor*: if it carries ``{placeholders}`` or a
    ``?guard`` that fails, the entire line is skipped. Subsequent fragments are
    concatenated only when all their placeholders resolve and any guard is
    truthy. If the anchor is purely literal (no ``{}``/``?``) and no data
    fragment resolves, the line is skipped — unless *has_gate* is set, meaning
    a ``cli.gate`` already decided we should render, so the anchor renders alone.
    """
    if not fragments:
        return []

    anchor = fragments[0]
    rendered_anchor = _apply_item_template(anchor, context)
    if rendered_anchor is None:
        return []
    parts: list[str] = [rendered_anchor]
    any_data_fragment = _is_data_fragment(anchor)

    for fragment in fragments[1:]:
        rendered = _apply_item_template(fragment, context)
        if rendered is None:
            continue
        parts.append(rendered)
        if _is_data_fragment(fragment):
            any_data_fragment = True

    if not has_gate and not any_data_fragment:
        return []
    return [_INDENT * indent + "".join(parts)]


def _render_section(schema: dict, cli: dict, data: AvdModel, indent: int) -> list[str]:
    """Render a model field as a CLI section block."""
    separator: bool = cli.get("separator", True)
    section_only_if_content: bool = cli.get("section_only_if_content", True)

    header = resolve_template(cli["section"], data)
    if header is None:
        return []

    children = _render_dict_children(schema, data, indent + 1)

    if not children and section_only_if_content:
        return []

    lines: list[str] = []
    if separator:
        lines.append(_INDENT * indent + "!")
    lines.append(_INDENT * indent + header)
    lines.extend(children)
    return lines


def _render_dict_children(schema: dict, data: AvdModel, indent: int) -> list[str]:
    """Render annotated children of a dict schema using attribute access."""
    lines: list[str] = []
    keys_schema: dict = schema.get("keys") or {}

    for child_key, child_schema in keys_schema.items():
        child_data = _model_get(data, child_key)
        if child_data is None:
            continue
        # Skip empty nested models / empty lists so we don't recurse pointlessly.
        if isinstance(child_data, (AvdModel, AvdList, AvdIndexedList)) and not child_data:
            continue
        lines.extend(render_schema_field(child_schema, child_data, data, indent))

    return lines


def render_from_schema(schema: dict, data: AvdModel) -> list[str]:
    """
    Render CLI config from a schema dict and an :class:`AvdModel` instance.

    Iterates the schema's top-level keys and renders any that carry ``cli``
    annotations and have matching data on the model.

    Args:
        schema: Root schema dict (must have a ``"keys"`` mapping at top level).
        data:   Structured config data as an ``AvdModel`` instance
                (e.g. an :class:`EosCliConfigGen`).

    Returns:
        Ordered list of CLI output lines.
    """
    return _render_dict_children(schema, data, indent=0)


class SchemaCliGenerator:
    """
    Schema-driven CLI generator.

    Generates EOS CLI configuration from schema-embedded ``cli`` annotations
    by walking attributes on an :class:`AvdModel` — without requiring per-feature
    Python rendering code.

    Runs parallel to the manual :class:`CliGenerator` / :class:`CliSection`
    pattern. Use it for features whose CLI output can be fully described by
    schema annotations; keep the manual generators for complex logic that
    schema cannot easily express (optional suffixes, switch-case, boolean
    conditions inside list items, etc.).
    """

    def __init__(self, schema: dict, data: EosCliConfigGen | AvdModel | dict) -> None:
        """
        Initialize with a schema dict and structured config data.

        Args:
            schema: Root schema dict from the schema store (``store["eos_cli_config_gen"]``).
            data:   ``AvdModel`` instance or raw dict (converted to ``EosCliConfigGen``).
        """
        self._schema = schema
        if isinstance(data, dict):
            self._data: AvdModel = EosCliConfigGen._from_dict(data)
        else:
            self._data = data

    def render(self) -> list[str]:
        """Return rendered CLI lines derived from schema annotations."""
        return render_from_schema(self._schema, self._data)

    def get_config(self) -> str:
        """Return rendered config as a newline-joined string."""
        return "\n".join(self.render())
