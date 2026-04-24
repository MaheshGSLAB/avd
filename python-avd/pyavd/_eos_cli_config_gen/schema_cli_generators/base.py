# Copyright (c) 2023-2026 Arista Networks, Inc.
# Use of this source code is governed by the Apache License 2.0
# that can be found in the LICENSE file.
"""
Schema-driven CLI generator.

This module provides a way to generate EOS CLI configuration directly from
schema annotations, without writing per-feature Python rendering code.

Schema fields annotated with a ``cli`` key drive rendering:

``cli.section`` (dict only)
    Template for the block header line. Variables like ``{as}`` are resolved
    from the dict's own data. Example: ``section: "router bgp {as}"``

``cli.line`` (any type)
    Template for a single CLI body line. Variables are resolved from the
    *parent* dict's data (sibling keys). Example: ``line: "router-id {router_id}"``

``cli.bool_true_line`` (bool only)
    Fixed CLI line emitted verbatim when the field value is ``True``.
    Example: ``bool_true_line: "update wait-for-convergence"``

``cli.bool_false_line`` (bool only)
    Fixed CLI line emitted verbatim when the field value is ``False``.
    Example: ``bool_false_line: "no bgp default ipv4-unicast"``

``cli.item_lines`` (list only)
    List of line templates. For each item in the list field, each template is
    attempted and rendered if all its variable references resolve (are present
    and non-None) in the item dict.  For lists of scalars, use the special
    variable ``{_item}`` which expands to the item value itself.

    A template may end with ``?field_path`` to add a boolean guard: the line is
    skipped unless the named field (supports dot-notation) is truthy in the item
    context.  The ``?field_path`` suffix is stripped from the rendered output.

    Example::

        peer_groups:
          type: list
          cli:
            item_lines:
              - "neighbor {name} peer group"
              - "neighbor {name} remote-as {remote_as}"
              - "neighbor {name} shutdown?shutdown"
              - "neighbor {name} bfd interval {bfd_timers.interval} min-rx {bfd_timers.min_rx} multiplier {bfd_timers.multiplier}?bfd"

``cli.separator`` (bool, default ``True``)
    Emit a ``!`` line before the section header.

``cli.section_only_if_content`` (bool, default ``True``)
    Skip the section header if no child lines were rendered.

Variable syntax
    ``{var}`` references a key in the current context dict.
    ``{parent.child}`` uses dot-notation to traverse nested dicts.
    A line is skipped entirely if any referenced variable is absent or ``None``.

Example schema::

    router_bgp:
      type: dict
      cli:
        separator: true
        section: "router bgp {as}"
        section_only_if_content: false
      keys:
        as:
          type: str
        as_notation:
          type: str
          cli:
            line: "bgp asn notation {as_notation}"
        updates:
          type: dict
          keys:
            wait_for_convergence:
              type: bool
              cli:
                bool_true_line: "update wait-for-convergence"
        peer_groups:
          type: list
          cli:
            item_lines:
              - "neighbor {name} peer group"
              - "neighbor {name} remote-as {remote_as}"
"""

from __future__ import annotations

import re
from typing import Any

_INDENT = "   "
# Supports plain {var} and dot-notation {parent.child}
_TEMPLATE_VAR_RE = re.compile(r"\{([\w.]+)\}")
# Matches an optional boolean guard suffix like "?shutdown" or "?bfd_timers.interval"
_CONDITION_SUFFIX_RE = re.compile(r"\?([\w][\w.]*)\s*$")


def _resolve_path(context: Any, path: str) -> Any:
    """
    Traverse a dot-notation path through nested dicts.

    Returns ``None`` if any segment is absent or the context is not a dict.
    """
    current = context
    for part in path.split("."):
        if not isinstance(current, dict):
            return None
        current = current.get(part)
        if current is None:
            return None
    return current


def resolve_template(template: str, context: dict) -> str | None:
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
    key: str,
    data: Any,
    parent_data: dict,
    indent: int,
) -> list[str]:
    """
    Render one schema field according to its ``cli`` annotation.

    Args:
        schema:      Schema dict for this field.
        key:         Key name of this field inside its parent dict.
        data:        Data value for this field.
        parent_data: The parent dict's data, used as the resolution context for
                     ``cli.line`` templates (gives access to sibling keys).
        indent:      Current indentation level (0 = top-level).

    Returns:
        A list of CLI output lines (empty list = nothing to render).
    """
    cli: dict = schema.get("cli") or {}
    schema_type: str = schema.get("type", "")

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

    # --- List with item_lines: one or more lines per list item ---
    if schema_type == "list" and "item_lines" in cli and isinstance(data, list):
        return _render_list_items(cli["item_lines"], data, indent)

    # --- Dict with section: named CLI block with indented children ---
    if "section" in cli and schema_type == "dict" and isinstance(data, dict):
        return _render_section(schema, cli, data, indent)

    # --- Dict without CLI section: recurse transparently at same indent ---
    if schema_type == "dict" and isinstance(data, dict):
        return _render_dict_children(schema, data, indent)

    # Scalar with no applicable cli annotation — not rendered by this system
    return []


def _apply_item_template(template: str, context: dict) -> str | None:
    """
    Apply one item_lines template to a context dict.

    Strips a ``?field_path`` boolean guard suffix (skips when falsy) before
    resolving ``{var}`` placeholders.  Returns ``None`` when the line should be
    skipped.
    """
    m = _CONDITION_SUFFIX_RE.search(template)
    if m:
        if not _resolve_path(context, m.group(1)):
            return None
        template = template[: m.start()]
    return resolve_template(template, context)


def _render_list_items(item_line_templates: list[str], items: list, indent: int) -> list[str]:
    """
    Render each item in a list using the provided line templates.

    For dict items, variables in templates are resolved from the item dict.
    For scalar items, the special variable ``{_item}`` expands to the item value.
    A template line is emitted only if all its variable references resolve.

    A ``?field_path`` suffix acts as a boolean guard: the line is skipped unless
    that field (dot-notation supported) is truthy in the item context, and the
    suffix is stripped from the rendered output.
    """
    lines: list[str] = []
    for item in items:
        if isinstance(item, dict):
            context = item
        elif item is not None:
            context = {"_item": str(item)}
        else:
            continue
        for tpl in item_line_templates:
            rendered = _apply_item_template(tpl, context)
            if rendered is not None:
                lines.append(_INDENT * indent + rendered)
    return lines


def _render_section(schema: dict, cli: dict, data: dict, indent: int) -> list[str]:
    """Render a dict field as a CLI section block."""
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


def _render_dict_children(schema: dict, data: dict, indent: int) -> list[str]:
    """Render annotated children of a dict schema."""
    lines: list[str] = []
    keys_schema: dict = schema.get("keys") or {}

    for child_key, child_schema in keys_schema.items():
        child_data = data.get(child_key)
        if child_data is None:
            continue
        lines.extend(render_schema_field(child_schema, child_key, child_data, data, indent))

    return lines


def render_from_schema(schema: dict, data: dict) -> list[str]:
    """
    Render CLI config from a schema dict and a data dict.

    Iterates the schema's top-level keys and renders any that carry ``cli``
    annotations and have matching data.

    Args:
        schema: Root schema dict (must have a ``"keys"`` mapping at top level).
        data:   Structured config data dict.

    Returns:
        Ordered list of CLI output lines.

    Example::

        from schema_tools.store import create_store

        store = create_store()
        schema = store["eos_cli_config_gen"]
        data = {
            "router_bgp": {
                "as": "65001",
                "as_notation": "asplain",
                "router_id": "1.2.3.4",
                "updates": {"wait_for_convergence": True},
                "peer_groups": [{"name": "EVPN-OVERLAY", "remote_as": "65000"}],
            }
        }
        print("\\n".join(render_from_schema(schema, data)))
    """
    return _render_dict_children(schema, data, indent=0)


class SchemaCliGenerator:
    """
    Schema-driven CLI generator.

    Generates EOS CLI configuration from schema-embedded ``cli`` annotations
    without requiring per-feature Python rendering code.

    This runs parallel to the manual
    :class:`~pyavd._eos_cli_config_gen.cli_generators.base.CliGenerator` /
    :class:`~pyavd._eos_cli_config_gen.cli_generators.base.CliSection` pattern.
    Use it for features where the CLI output can be fully described by schema
    annotations; keep the manual generators for complex logic that schema
    cannot easily express (optional suffixes, switch-case, boolean conditions
    inside list items, etc.).

    Supported ``cli`` annotation keys
    ----------------------------------
    ``section``                 Dict → named CLI block header
    ``line``                    Any → single body line (resolved from parent dict)
    ``bool_true_line``          Bool → fixed line when value is True
    ``bool_false_line``         Bool → fixed line when value is False
    ``item_lines``              List → one or more line templates per item
    ``separator``               Emit ``!`` before section header (default True)
    ``section_only_if_content`` Skip header when no children rendered (default True)

    Usage::

        from schema_tools.store import create_store
        from pyavd._eos_cli_config_gen.schema_cli_generators import SchemaCliGenerator

        store = create_store()
        schema = store["eos_cli_config_gen"]
        data = {"router_bgp": {"as": "65001", "router_id": "1.2.3.4"}}

        gen = SchemaCliGenerator(schema, data)
        print(gen.get_config())
    """

    def __init__(self, schema: dict, data: dict) -> None:
        """
        Initialize with a schema dict and a data dict.

        Args:
            schema: Root schema dict from the schema store (``store["eos_cli_config_gen"]``).
            data:   Structured config data dict.
        """
        self._schema = schema
        self._data = data

    def render(self) -> list[str]:
        """Return rendered CLI lines derived from schema annotations."""
        return render_from_schema(self._schema, self._data)

    def get_config(self) -> str:
        """Return rendered config as a newline-joined string."""
        return "\n".join(self.render())
