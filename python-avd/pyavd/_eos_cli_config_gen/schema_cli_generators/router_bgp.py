# Copyright (c) 2023-2026 Arista Networks, Inc.
# Use of this source code is governed by the Apache License 2.0
# that can be found in the LICENSE file.
"""
Schema-driven + custom CLI generator for 'router bgp'.

Rendering strategy (per field):
  - Fields with a ``cli:`` annotation in the schema are rendered via
    :func:`render_schema_field` so the schema remains the single source of truth.
  - Fields whose rendering logic cannot be expressed as schema annotations
    (optional suffixes, multi-key strings, nested conditionals) use a dedicated
    custom method.

All input data is read via attribute access on the
:class:`~pyavd._eos_cli_config_gen.schema.EosCliConfigGen` model — never via
dict ``.get()``. Renamed schema keys (e.g. ``as`` → ``field_as``) are accessed
through the model's attribute names.

The :meth:`RouterBgpBlock.render` method drives the complete output in the same
order as the Jinja2 template (``j2templates/eos/router-bgp.j2`` lines 1-737).
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from pyavd.j2filters import hide_passwords as _hide_passwords

from .base import _model_get, render_schema_field

if TYPE_CHECKING:
    from pyavd._eos_cli_config_gen.schema import EosCliConfigGen

    RouterBgp = EosCliConfigGen.RouterBgp
    PeerGroupsItem = RouterBgp.PeerGroupsItem
    NeighborsItem = RouterBgp.NeighborsItem
    VlansItem = RouterBgp.VlansItem

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
        lines += self._render_labeled_unicast_rib(b)                # custom: optional ip/tunnel parts
        lines += self._schema_field("router_id", b)                 # schema: line
        lines += self._schema_field("updates", b)                   # schema: bool_true_line children
        lines += self._schema_field("bgp.default", b)               # schema: bool_true/false_line children
        lines += self._schema_field("timers", b)                    # schema: line_fragments
        lines += self._schema_field("distance", b)                  # schema: line_fragments
        lines += self._schema_field("graceful_restart", b)          # schema: gate + lines
        lines += self._schema_field("bgp_cluster_id", b)            # schema: line
        lines += self._render_graceful_restart_helper(b)            # custom: enabled/disabled branches
        lines += self._schema_field("bgp.route_reflector_preserve_attributes", b)  # schema: gate + line_fragments
        lines += self._schema_field("maximum_paths", b)             # schema: line_fragments
        lines += self._schema_field("bgp_defaults", b)              # schema: item_lines {_item}
        lines += self._schema_field("bgp.additional_paths.receive", b)  # schema: bool_true/false_line
        lines += self._render_additional_paths_send(b)              # custom: switch on send/send_limit
        lines += self._schema_field("listen_ranges", b)             # schema: sort_key + item_gate + item_line_fragments
        lines += self._schema_field("bgp.bestpath.d_path", b)       # schema: bool_true_line
        lines += self._render_neighbor_default_send_community(b)    # custom: 'all' vs value

        # --- Per-entity sections (j2 lines 151-499) ---
        lines += self._render_peer_groups(b)
        lines += self._render_neighbors(b)

        # --- Global redistribute-internal (j2 line 500-503) ---
        lines += self._schema_field("bgp.redistribute_internal", b)  # schema: bool_true/false_line

        # --- Aggregate addresses (j2 lines 505-526) ---
        lines += self._render_aggregate_addresses(b)                # custom: multi-flag assembly

        # --- Redistribute (j2 lines 527-688) ---
        lines += self._render_redistribute(b)                       # schema: gate + line_fragments per protocol (+ small ospf elif)

        # --- Neighbor interfaces (j2 lines 690-696) ---
        lines += self._schema_field("neighbor_interfaces", b)       # schema: item_lines

        # --- VLANs (j2 lines 697-737) ---
        lines += self._render_vlans(b)                              # custom: nested section-in-list

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
    # Custom methods — global settings
    # ------------------------------------------------------------------

    def _render_labeled_unicast_rib(self, indent: int) -> list[str]:
        """``bgp labeled-unicast rib [ip [route-map X]] [tunnel [route-map Y]]`` (j2 lines 13-28)."""
        rib = self._bgp.bgp.labeled_unicast.rib
        ip = rib.ip
        tunnel = rib.tunnel
        if ip.enabled is not True and tunnel.enabled is not True:
            return []
        cmd = "bgp labeled-unicast rib"
        if ip.enabled is True:
            cmd += " ip"
            if ip.route_map:
                cmd += f" route-map {ip.route_map}"
        if tunnel.enabled is True:
            cmd += " tunnel"
            if tunnel.route_map:
                cmd += f" route-map {tunnel.route_map}"
        return [_INDENT * indent + cmd]

    def _render_graceful_restart_helper(self, indent: int) -> list[str]:
        """``graceful-restart-helper`` or its negation (j2 lines 82-90)."""
        grh = self._bgp.graceful_restart_helper
        pref = _INDENT * indent
        if grh.enabled is False:
            return [pref + "no graceful-restart-helper"]
        if grh.enabled is True:
            if grh.restart_time is not None:
                return [pref + f"graceful-restart-helper restart-time {grh.restart_time}"]
            if grh.long_lived is True:
                return [pref + "graceful-restart-helper long-lived"]
        return []

    def _render_additional_paths_send(self, indent: int) -> list[str]:
        """``bgp additional-paths send ...`` (j2 lines 113-126) — switch on send/send_limit."""
        ap = self._bgp.bgp.additional_paths
        send = ap.send
        if send is None:
            return []
        pref = _INDENT * indent
        send_limit = ap.send_limit
        if send == "disabled":
            return [pref + "no bgp additional-paths send"]
        if send == "ecmp" and send_limit is not None:
            return [pref + f"bgp additional-paths send ecmp limit {send_limit}"]
        if send == "limit" and send_limit is not None:
            return [pref + f"bgp additional-paths send limit {send_limit}"]
        return [pref + f"bgp additional-paths send {send}"]

    def _render_neighbor_default_send_community(self, indent: int) -> list[str]:
        """``neighbor default send-community [value]`` (j2 lines 146-149).

        When ``send_community`` is ``'all'``, EOS omits the trailing keyword.
        """
        sc = self._bgp.neighbor_default.send_community
        if sc == "all":
            return [_INDENT * indent + "neighbor default send-community"]
        if sc is not None:
            return [_INDENT * indent + f"neighbor default send-community {sc}"]
        return []

    # ------------------------------------------------------------------
    # Peer groups (j2 lines 151-323)
    # ------------------------------------------------------------------

    def _render_peer_groups(self, indent: int) -> list[str]:
        lines: list[str] = []
        peer_groups = self._bgp.peer_groups
        if not peer_groups:
            return lines
        for pg in peer_groups._natural_sorted():
            lines += self._render_peer_group(pg, indent)
        return lines

    def _render_peer_group(self, pg: PeerGroupsItem, indent: int) -> list[str]:
        """Render one peer-group block in j2 output order."""
        name = pg.name
        if name is None:
            return []

        pref = _INDENT * indent
        lines: list[str] = [pref + f"neighbor {name} peer group"]

        def add(line: str) -> None:
            lines.append(pref + line)

        if pg.remote_as is not None:
            add(f"neighbor {name} remote-as {pg.remote_as}")
        if pg.next_hop_self is True:
            add(f"neighbor {name} next-hop-self")
        if pg.next_hop_peer is True:
            add(f"neighbor {name} next-hop-peer")
        if pg.next_hop_unchanged is True:
            add(f"neighbor {name} next-hop-unchanged")
        if pg.shutdown is True:
            add(f"neighbor {name} shutdown")

        lines += self._render_remove_private_as(name, pg.remove_private_as, indent)

        as_path = pg.as_path
        if as_path.prepend_own_disabled is True:
            add(f"neighbor {name} as-path prepend-own disabled")
        if as_path.remote_as_replace_out is True:
            add(f"neighbor {name} as-path remote-as replace out")

        if pg.local_as is not None:
            add(f"neighbor {name} local-as {pg.local_as} no-prepend replace-as")
        if pg.weight is not None:
            add(f"neighbor {name} weight {pg.weight}")
        if pg.passive is True:
            add(f"neighbor {name} passive")
        if pg.update_source is not None:
            add(f"neighbor {name} update-source {pg.update_source}")

        lines += self._render_bfd(name, pg.bfd, pg.bfd_timers, indent)

        if pg.description is not None:
            add(f"neighbor {name} description {pg.description}")

        lines += self._render_allowas_in(name, pg.allowas_in, indent)
        lines += self._render_rib_in_pre_policy_retain(name, pg.rib_in_pre_policy_retain, indent)

        if pg.ebgp_multihop is not None:
            add(f"neighbor {name} ebgp-multihop {pg.ebgp_multihop}")
        if pg.ttl_maximum_hops is not None:
            add(f"neighbor {name} ttl maximum-hops {pg.ttl_maximum_hops}")
        if pg.route_reflector_client is True:
            add(f"neighbor {name} route-reflector-client")
        if pg.session_tracker is not None:
            add(f"neighbor {name} session tracker {pg.session_tracker}")
        if pg.timers is not None:
            add(f"neighbor {name} timers {pg.timers}")
        if pg.route_map_in is not None:
            add(f"neighbor {name} route-map {pg.route_map_in} in")
        if pg.route_map_out is not None:
            add(f"neighbor {name} route-map {pg.route_map_out} out")

        # password key before shared-secret for peer-groups (j2 ordering)
        lines += self._render_password_key(name, pg.password, pg.password_type, indent)
        lines += self._render_shared_secret(name, pg.shared_secret, indent)

        lines += self._render_default_originate(name, pg.default_originate, indent)
        lines += self._render_send_community(name, pg.send_community, indent)
        lines += self._render_maximum_routes(
            name,
            pg.maximum_routes,
            pg.maximum_routes_warning_limit,
            pg.maximum_routes_warning_only,
            indent,
        )
        lines += self._render_missing_policy(name, pg.missing_policy, indent)

        if pg.peer_tag_in is not None:
            add(f"neighbor {name} peer-tag in {pg.peer_tag_in}")
        if pg.peer_tag_out_discard is not None:
            add(f"neighbor {name} peer-tag out discard {pg.peer_tag_out_discard}")

        lines += self._render_link_bandwidth(name, pg.link_bandwidth, indent)
        lines += self._render_remove_private_as_ingress(name, pg.remove_private_as_ingress, indent)

        return lines

    # ------------------------------------------------------------------
    # Neighbors (j2 lines 324-499)
    # ------------------------------------------------------------------

    def _render_neighbors(self, indent: int) -> list[str]:
        lines: list[str] = []
        neighbors = self._bgp.neighbors
        if not neighbors:
            return lines
        for nb in neighbors._natural_sorted():
            lines += self._render_neighbor(nb, indent)
        return lines

    def _render_neighbor(self, nb: NeighborsItem, indent: int) -> list[str]:
        """Render one neighbor block in j2 output order.

        Differences from peer-groups:
        - ``no neighbor X bfd`` is valid (peer-group BFD can be overridden).
        - ``no neighbor X route-reflector-client`` is valid.
        - ``no neighbor X rib-in pre-policy retain`` is valid.
        - shared-secret is rendered *before* password key (j2 ordering).
        """
        ip = nb.ip_address
        if ip is None:
            return []

        pref = _INDENT * indent
        lines: list[str] = []

        def add(line: str) -> None:
            lines.append(pref + line)

        if nb.peer_group is not None:
            add(f"neighbor {ip} peer group {nb.peer_group}")
        if nb.remote_as is not None:
            add(f"neighbor {ip} remote-as {nb.remote_as}")
        if nb.next_hop_self is True:
            add(f"neighbor {ip} next-hop-self")
        if nb.next_hop_peer is True:
            add(f"neighbor {ip} next-hop-peer")
        if nb.shutdown is True:
            add(f"neighbor {ip} shutdown")

        lines += self._render_remove_private_as(ip, nb.remove_private_as, indent)

        as_path = nb.as_path
        if as_path.prepend_own_disabled is True:
            add(f"neighbor {ip} as-path prepend-own disabled")
        if as_path.remote_as_replace_out is True:
            add(f"neighbor {ip} as-path remote-as replace out")

        if nb.local_as is not None:
            add(f"neighbor {ip} local-as {nb.local_as} no-prepend replace-as")
        if nb.weight is not None:
            add(f"neighbor {ip} weight {nb.weight}")
        if nb.passive is True:
            add(f"neighbor {ip} passive")
        if nb.update_source is not None:
            add(f"neighbor {ip} update-source {nb.update_source}")

        # Neighbors can disable BFD inherited from a peer-group; peer-groups cannot
        lines += self._render_bfd(ip, nb.bfd, nb.bfd_timers, indent, allow_negation=nb.peer_group is not None)

        if nb.description is not None:
            add(f"neighbor {ip} description {nb.description}")

        lines += self._render_allowas_in(ip, nb.allowas_in, indent)
        lines += self._render_rib_in_pre_policy_retain(ip, nb.rib_in_pre_policy_retain, indent)

        if nb.ebgp_multihop is not None:
            add(f"neighbor {ip} ebgp-multihop {nb.ebgp_multihop}")
        if nb.ttl_maximum_hops is not None:
            add(f"neighbor {ip} ttl maximum-hops {nb.ttl_maximum_hops}")

        # Neighbors support negation; peer-groups do not
        if nb.route_reflector_client is True:
            add(f"neighbor {ip} route-reflector-client")
        elif nb.route_reflector_client is False:
            add(f"no neighbor {ip} route-reflector-client")

        if nb.session_tracker is not None:
            add(f"neighbor {ip} session tracker {nb.session_tracker}")
        if nb.timers is not None:
            add(f"neighbor {ip} timers {nb.timers}")
        if nb.route_map_in is not None:
            add(f"neighbor {ip} route-map {nb.route_map_in} in")
        if nb.route_map_out is not None:
            add(f"neighbor {ip} route-map {nb.route_map_out} out")

        # shared-secret before password key for neighbors (j2 ordering)
        lines += self._render_shared_secret(ip, nb.shared_secret, indent)
        lines += self._render_password_key(ip, nb.password, nb.password_type, indent)

        lines += self._render_default_originate(ip, nb.default_originate, indent)
        lines += self._render_send_community(ip, nb.send_community, indent)
        lines += self._render_maximum_routes(
            ip,
            nb.maximum_routes,
            nb.maximum_routes_warning_limit,
            nb.maximum_routes_warning_only,
            indent,
        )
        lines += self._render_missing_policy(ip, nb.missing_policy, indent)

        if nb.peer_tag_in is not None:
            add(f"neighbor {ip} peer-tag in {nb.peer_tag_in}")
        if nb.peer_tag_out_discard is not None:
            add(f"neighbor {ip} peer-tag out discard {nb.peer_tag_out_discard}")

        lines += self._render_link_bandwidth(ip, nb.link_bandwidth, indent)
        lines += self._render_remove_private_as_ingress(ip, nb.remove_private_as_ingress, indent)

        return lines

    # ------------------------------------------------------------------
    # Shared per-entity helpers (peer-groups and neighbors)
    # ------------------------------------------------------------------

    def _render_remove_private_as(self, entity_id: str, rpa: Any, indent: int) -> list[str]:
        """``remove-private-as [all [replace-as]]`` or its negation."""
        pref = _INDENT * indent
        if rpa.enabled is True:
            cmd = f"neighbor {entity_id} remove-private-as"
            if rpa.all is True:
                cmd += " all"
                if rpa.replace_as is True:
                    cmd += " replace-as"
            return [pref + cmd]
        if rpa.enabled is False:
            return [pref + f"no neighbor {entity_id} remove-private-as"]
        return []

    def _render_bfd(
        self,
        entity_id: str,
        bfd: bool | None,
        bfd_timers: Any,
        indent: int,
        *,
        allow_negation: bool = False,
    ) -> list[str]:
        """``bfd`` and optional ``bfd interval`` line; ``no bfd`` when *allow_negation* is set."""
        pref = _INDENT * indent
        if bfd is True:
            lines = [pref + f"neighbor {entity_id} bfd"]
            interval = bfd_timers.interval
            min_rx = bfd_timers.min_rx
            multiplier = bfd_timers.multiplier
            if interval is not None and min_rx is not None and multiplier is not None:
                lines.append(pref + f"neighbor {entity_id} bfd interval {interval} min-rx {min_rx} multiplier {multiplier}")
            return lines
        if bfd is False and allow_negation:
            return [pref + f"no neighbor {entity_id} bfd"]
        return []

    def _render_allowas_in(self, entity_id: str, allowas_in: Any, indent: int) -> list[str]:
        """``allowas-in [N]``."""
        if allowas_in.enabled is not True:
            return []
        cmd = f"neighbor {entity_id} allowas-in"
        if allowas_in.times is not None:
            cmd += f" {allowas_in.times}"
        return [_INDENT * indent + cmd]

    def _render_rib_in_pre_policy_retain(self, entity_id: str, rib_in: Any, indent: int) -> list[str]:
        """``rib-in pre-policy retain [all]`` or its negation."""
        pref = _INDENT * indent
        if rib_in.enabled is True:
            cmd = f"neighbor {entity_id} rib-in pre-policy retain"
            if rib_in.all is True:
                cmd += " all"
            return [pref + cmd]
        if rib_in.enabled is False:
            return [pref + f"no neighbor {entity_id} rib-in pre-policy retain"]
        return []

    def _render_password_key(
        self,
        entity_id: str,
        password: str | None,
        password_type: str | None,
        indent: int,
    ) -> list[str]:
        """``neighbor X password [type] key`` (type defaults to 7)."""
        if password is None:
            return []
        pw_type = password_type if password_type is not None else "7"
        hashed = _hide_passwords(password, self._hide_passwords)
        return [_INDENT * indent + f"neighbor {entity_id} password {pw_type} {hashed}"]

    def _render_shared_secret(self, entity_id: str, shared_secret: Any, indent: int) -> list[str]:
        """``neighbor X password shared-secret profile P algorithm A``."""
        profile = shared_secret.profile
        algo = shared_secret.hash_algorithm
        if profile is not None and algo is not None:
            return [_INDENT * indent + f"neighbor {entity_id} password shared-secret profile {profile} algorithm {algo}"]
        return []

    def _render_default_originate(self, entity_id: str, do: Any, indent: int) -> list[str]:
        """``default-originate [route-map X] [always]``."""
        if do.enabled is not True:
            return []
        cmd = f"neighbor {entity_id} default-originate"
        if do.route_map is not None:
            cmd += f" route-map {do.route_map}"
        if do.always is True:
            cmd += " always"
        return [_INDENT * indent + cmd]

    def _render_send_community(self, entity_id: str, send_community: str | None, indent: int) -> list[str]:
        """``send-community`` — 'all' omits the trailing keyword in EOS CLI."""
        if send_community == "all":
            return [_INDENT * indent + f"neighbor {entity_id} send-community"]
        if send_community is not None:
            return [_INDENT * indent + f"neighbor {entity_id} send-community {send_community}"]
        return []

    def _render_maximum_routes(
        self,
        entity_id: str,
        max_routes: int | None,
        warning_limit: int | None,
        warning_only: bool | None,
        indent: int,
    ) -> list[str]:
        """``maximum-routes N [warning-limit M] [warning-only]``."""
        if max_routes is None:
            return []
        cmd = f"neighbor {entity_id} maximum-routes {max_routes}"
        if warning_limit is not None:
            cmd += f" warning-limit {warning_limit}"
        if warning_only is True:
            cmd += " warning-only"
        return [_INDENT * indent + cmd]

    def _render_missing_policy(self, entity_id: str, missing_policy: Any, indent: int) -> list[str]:
        """``missing-policy address-family all [include ...] direction {in|out} action X``."""
        pref = _INDENT * indent
        lines: list[str] = []
        for direction, policy in (("in", missing_policy.direction_in), ("out", missing_policy.direction_out)):
            if not policy.action:
                continue
            cmd = f"neighbor {entity_id} missing-policy address-family all"
            includes: list[str] = []
            if policy.include_community_list is True:
                includes.append("community-list")
            if policy.include_prefix_list is True:
                includes.append("prefix-list")
            if policy.include_sub_route_map is True:
                includes.append("sub-route-map")
            if includes:
                cmd += " include " + " ".join(includes)
            cmd += f" direction {direction} action {policy.action}"
            lines.append(pref + cmd)
        return lines

    def _render_link_bandwidth(self, entity_id: str, lb: Any, indent: int) -> list[str]:
        """``link-bandwidth [default X]``."""
        if lb.enabled is not True:
            return []
        cmd = f"neighbor {entity_id} link-bandwidth"
        if lb.default is not None:
            cmd += f" default {lb.default}"
        return [_INDENT * indent + cmd]

    def _render_remove_private_as_ingress(self, entity_id: str, rpai: Any, indent: int) -> list[str]:
        """``remove-private-as ingress [replace-as]`` or its negation."""
        pref = _INDENT * indent
        if rpai.enabled is True:
            cmd = f"neighbor {entity_id} remove-private-as ingress"
            if rpai.replace_as is True:
                cmd += " replace-as"
            return [pref + cmd]
        if rpai.enabled is False:
            return [pref + f"no neighbor {entity_id} remove-private-as ingress"]
        return []

    # ------------------------------------------------------------------
    # Aggregate addresses (j2 lines 505-526)
    # ------------------------------------------------------------------

    def _render_aggregate_addresses(self, indent: int) -> list[str]:
        """``aggregate-address prefix [as-set] [summary-only] [attribute-map X] ...``."""
        pref = _INDENT * indent
        lines: list[str] = []
        aggregates = self._bgp.aggregate_addresses
        if not aggregates:
            return lines
        for agg in aggregates._natural_sorted():
            cmd = f"aggregate-address {agg.prefix}"
            if agg.as_set is True:
                cmd += " as-set"
            if agg.summary_only is True:
                cmd += " summary-only"
            if agg.attribute_map is not None:
                cmd += f" attribute-map {agg.attribute_map}"
            if agg.attribute.rcf is not None:
                cmd += f" attribute rcf {agg.attribute.rcf}"
            if agg.match_map is not None:
                cmd += f" match-map {agg.match_map}"
            if agg.advertise_only is True:
                cmd += " advertise-only"
            lines.append(pref + cmd)
        return lines

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

    # ------------------------------------------------------------------
    # VLANs (j2 lines 697-737)
    # ------------------------------------------------------------------

    def _render_vlans(self, indent: int) -> list[str]:
        lines: list[str] = []
        vlans = self._bgp.vlans
        if not vlans:
            return lines
        for vlan in vlans._natural_sorted():
            lines += self._render_vlan(vlan, indent)
        return lines

    def _render_vlan(self, vlan: VlansItem, indent: int) -> list[str]:
        """Render one ``vlan X`` sub-block inside ``router bgp``."""
        vlan_id = vlan.id
        if vlan_id is None:
            return []

        pref_hdr = _INDENT * indent
        pref_body = _INDENT * (indent + 1)
        lines: list[str] = [
            pref_hdr + "!",
            pref_hdr + f"vlan {vlan_id}",
        ]

        def sub(line: str) -> None:
            lines.append(pref_body + line)

        if vlan.rd is not None:
            sub(f"rd {vlan.rd}")

        rd_evpn = vlan.rd_evpn_domain
        if rd_evpn.domain is not None and rd_evpn.rd is not None:
            sub(f"rd evpn domain {rd_evpn.domain} {rd_evpn.rd}")

        rt = vlan.route_targets
        # `import` is a Python keyword so the field is renamed to `field_import` on the model.
        for route_target in rt.both._natural_sorted():
            sub(f"route-target both {route_target}")
        for route_target in rt.field_import._natural_sorted():
            sub(f"route-target import {route_target}")
        for route_target in rt.export._natural_sorted():
            sub(f"route-target export {route_target}")
        for entry in rt.import_evpn_domains._natural_sorted(sort_key="domain"):
            sub(f"route-target import evpn domain {entry.domain} {entry.route_target}")
        for entry in rt.export_evpn_domains._natural_sorted(sort_key="domain"):
            sub(f"route-target export evpn domain {entry.domain} {entry.route_target}")
        for entry in rt.import_export_evpn_domains._natural_sorted(sort_key="domain"):
            sub(f"route-target import export evpn domain {entry.domain} {entry.route_target}")

        for route in vlan.redistribute_routes._natural_sorted():
            sub(f"redistribute {route}")
        for route in vlan.no_redistribute_routes._natural_sorted():
            sub(f"no redistribute {route}")

        eos_cli = vlan.eos_cli
        if eos_cli is not None:
            sub("!")
            for line in eos_cli.splitlines():
                sub(line)

        return lines
