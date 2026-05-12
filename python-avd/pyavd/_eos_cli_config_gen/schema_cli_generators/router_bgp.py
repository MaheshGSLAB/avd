# Copyright (c) 2023-2026 Arista Networks, Inc.
# Use of this source code is governed by the Apache License 2.0
# that can be found in the LICENSE file.
"""
Schema-driven CLI generator for ``router bgp``.

Every field is rendered through its ``cli:`` annotation in the schema —
:meth:`RouterBgpBlock.render` only orchestrates the output order to match
``j2templates/eos/router-bgp.j2`` (lines 1-737). Input data is read via
attribute access on :class:`~pyavd._eos_cli_config_gen.schema.EosCliConfigGen`;
renamed schema keys (e.g. ``as`` → ``field_as``) are resolved through the
model's ``_key_to_field_map``.

Password masking flows through the ``hide_passwords`` template filter that
:meth:`__init__` registers with the runtime toggle baked in.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from pyavd.j2filters import hide_passwords as _hide_passwords

from .base import _model_get, register_template_filter, render_schema_field

if TYPE_CHECKING:
    from pyavd._eos_cli_config_gen.schema import EosCliConfigGen

_INDENT = "   "


class RouterBgpBlock:
    """
    Renders the ``router bgp X`` block covering j2 template lines 1-737.

    For each field the renderer first tries the schema annotation
    (``render_schema_field``).  Custom methods are added only where schema
    annotations cannot express the required logic.

    Args:
        bgp_schema:            The ``router_bgp`` sub-schema dict
                               (i.e. ``root_schema["keys"]["router_bgp"]``).
        bgp:                   The ``router_bgp`` model instance.
        hide_passwords_enabled: When *True*, password values are masked.
    """

    def __init__(
        self,
        bgp_schema: dict,
        bgp: EosCliConfigGen.RouterBgp,
        hide_passwords_enabled: bool = False,
    ) -> None:
        self._schema_keys: dict = bgp_schema.get("keys") or {}
        self._bgp = bgp
        self._hide_passwords = hide_passwords_enabled
        # Schema-driven password masking: route `{password|hide_passwords}` placeholders
        # through the runtime toggle. Registry is module-global; if multiple blocks render
        # with different settings, the most recent wins.
        register_template_filter("hide_passwords", lambda v: _hide_passwords(v, hide_passwords_enabled))

    # ------------------------------------------------------------------
    # Public entry point
    # ------------------------------------------------------------------

    def render(self, indent: int = 0) -> list[str]:
        """Return CLI lines for the ``router bgp`` block in j2 template order."""
        bgp_as = self._bgp.field_as
        if bgp_as is None:
            return []

        i = indent      # section header indent level
        b = indent + 1  # body line indent level

        lines: list[str] = [
            _INDENT * i + "!",
            _INDENT * i + f"router bgp {bgp_as}",
        ]

        # --- Global settings (j2 lines 10-149) ---
        lines += self._schema_field("as_notation", b)               # schema: line
        lines += self._schema_field("bgp.labeled_unicast.rib", b)   # schema: gate + line_fragments
        lines += self._schema_field("router_id", b)                 # schema: line
        lines += self._schema_field("updates", b)                   # schema: bool_true_line children
        lines += self._schema_field("bgp.default", b)               # schema: bool_true/false_line children
        lines += self._schema_field("timers", b)                    # schema: line_fragments
        lines += self._schema_field("distance", b)                  # schema: line_fragments
        lines += self._schema_field("graceful_restart", b)          # schema: gate + lines
        lines += self._schema_field("bgp_cluster_id", b)            # schema: line
        lines += self._schema_field("graceful_restart_helper", b)   # schema: lines + equality guards
        lines += self._schema_field("bgp.route_reflector_preserve_attributes", b)  # schema: gate + line_fragments
        lines += self._schema_field("maximum_paths", b)             # schema: line_fragments
        lines += self._schema_field("bgp_defaults", b)              # schema: item_lines {_item}
        lines += self._schema_field("bgp.additional_paths", b)      # schema: bool_true/false_line (receive) + line_switch (send)
        lines += self._schema_field("listen_ranges", b)             # schema: sort_key + item_gate + item_line_fragments
        lines += self._schema_field("bgp.bestpath.d_path", b)       # schema: bool_true_line
        lines += self._schema_field("neighbor_default", b)          # schema: lines + equality guards

        # --- Per-entity sections (j2 lines 151-499) ---
        lines += self._schema_field("peer_groups", b)               # schema: items.cli.lines (composite + guards)
        lines += self._schema_field("neighbors", b)                 # schema: items.cli.lines (composite + guards)

        # --- Global redistribute-internal (j2 line 500-503) ---
        lines += self._schema_field("bgp.redistribute_internal", b)  # schema: bool_true/false_line

        # --- Aggregate addresses (j2 lines 505-526) ---
        lines += self._schema_field("aggregate_addresses", b)       # schema: item_line_fragments

        # --- Redistribute (j2 lines 527-688) ---
        lines += self._render_redistribute(b)                       # schema: gate + line_fragments per protocol (+ small ospf elif)

        # --- Neighbor interfaces (j2 lines 690-696) ---
        lines += self._schema_field("neighbor_interfaces", b)       # schema: item_lines

        # --- VLANs (j2 lines 697-737) ---
        lines += self._schema_field("vlans", b)                     # schema: items.cli with section + lines + raw_lines

        return lines

    # ------------------------------------------------------------------
    # Schema-field dispatcher
    # ------------------------------------------------------------------

    def _schema_field(self, path: str, indent: int) -> list[str]:
        """
        Render a ``router_bgp`` field by key or dotted path via its schema ``cli`` annotation.

        ``path`` may target a top-level key (``"router_id"``), a nested sub-model
        whose children render at the given indent (``"bgp.default"``), or a deep
        leaf field whose ``cli`` annotation drives one line (``"bgp.bestpath.d_path"``).
        """
        schema_node: dict = {"keys": self._schema_keys}
        data: Any = self._bgp
        parent: Any = self._bgp
        for part in path.split("."):
            schema_node = (schema_node.get("keys") or {}).get(part) or {}
            if not schema_node:
                return []
            parent = data
            data = _model_get(data, part)
            if data is None:
                return []
        # Skip empty AvdModel / AvdList — no fields set, nothing to render.
        if not isinstance(data, (bool, int, str)) and hasattr(data, "__bool__") and not data:
            return []
        return render_schema_field(schema_node, data, parent, indent)

    # ------------------------------------------------------------------
    # Redistribute (j2 lines 527-688)
    # ------------------------------------------------------------------

    _REDISTRIBUTE_PATHS: tuple[str, ...] = (
        "redistribute.connected",
        "redistribute.isis",
        "redistribute.ospf",
        "redistribute.ospf.match_internal",
        "redistribute.ospf.match_external",
        "redistribute.ospf.match_nssa_external",
        "redistribute.ospfv3",
        "redistribute.ospfv3.match_internal",
        "redistribute.ospfv3.match_external",
        "redistribute.ospfv3.match_nssa_external",
        "redistribute.static",
        "redistribute.rip",
        "redistribute.attached_host",
        "redistribute.dynamic",
        "redistribute.bgp",
        "redistribute.user",
    )

    def _render_redistribute(self, indent: int) -> list[str]:
        """
        Render all ``redistribute`` entries in j2 template order.

        Fully schema-driven — each protocol's gate + line_fragments live on
        the schema. The ``match_internal`` blocks use a parent-aware gate
        (``["enabled", "!^enabled"]``) so they only render when their own
        ``enabled`` is True AND the parent's ``enabled`` is not.
        """
        lines: list[str] = []
        for path in self._REDISTRIBUTE_PATHS:
            lines += self._schema_field(path, indent)
        return lines

