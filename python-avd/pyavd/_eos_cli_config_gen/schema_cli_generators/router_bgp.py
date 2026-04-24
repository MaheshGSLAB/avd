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

The :meth:`RouterBgpBlock.render` method drives the complete output in the same
order as the Jinja2 template (``j2templates/eos/router-bgp.j2`` lines 1-737).
"""

from __future__ import annotations

from typing import Any

from pyavd.j2filters import hide_passwords as _hide_passwords
from pyavd.j2filters import natural_sort

from .base import render_schema_field

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
        bgp:                   The ``router_bgp`` data dict.
        hide_passwords_enabled: When *True*, password values are masked.
    """

    def __init__(self, bgp_schema: dict, bgp: dict, hide_passwords_enabled: bool = False) -> None:
        self._schema_keys: dict = bgp_schema.get("keys") or {}
        self._bgp = bgp
        self._hide_passwords = hide_passwords_enabled

    # ------------------------------------------------------------------
    # Public entry point
    # ------------------------------------------------------------------

    def render(self, indent: int = 0) -> list[str]:
        """Return CLI lines for the ``router bgp`` block in j2 template order."""
        bgp_as = self._bgp.get("as")
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
        lines += self._render_bgp_default_flags(b)                  # custom: True/False branches
        lines += self._render_timers(b)                             # custom: multi-field assembly
        lines += self._render_distance(b)                           # custom: multi-field assembly
        lines += self._render_graceful_restart(b)                   # custom: ordered sub-lines
        lines += self._schema_field("bgp_cluster_id", b)            # schema: line
        lines += self._render_graceful_restart_helper(b)            # custom: enabled/disabled branches
        lines += self._render_route_reflector_preserve(b)           # custom: optional 'always'
        lines += self._render_maximum_paths(b)                      # custom: optional ecmp
        lines += self._schema_field("bgp_defaults", b)              # schema: item_lines {_item}
        lines += self._render_additional_paths(b)                   # schema receive + custom send
        lines += self._render_listen_ranges(b)                      # custom: conditional peer-filter/remote-as
        lines += self._render_bgp_bestpath(b)                       # schema: bool_true_line
        lines += self._render_neighbor_default_send_community(b)    # custom: 'all' vs value

        # --- Per-entity sections (j2 lines 151-499) ---
        lines += self._render_peer_groups(b)
        lines += self._render_neighbors(b)

        # --- Global redistribute-internal (j2 line 500-503) ---
        lines += self._render_redistribute_internal(b)              # schema: bool_true/false_line

        # --- Aggregate addresses (j2 lines 505-526) ---
        lines += self._render_aggregate_addresses(b)                # custom: multi-flag assembly

        # --- Redistribute (j2 lines 527-688) ---
        lines += self._render_redistribute(b)                       # custom: per-protocol logic

        # --- Neighbor interfaces (j2 lines 690-696) ---
        lines += self._schema_field("neighbor_interfaces", b)       # schema: item_lines

        # --- VLANs (j2 lines 697-737) ---
        lines += self._render_vlans(b)                              # custom: nested section-in-list

        return lines

    # ------------------------------------------------------------------
    # Schema-field dispatcher
    # ------------------------------------------------------------------

    def _schema_field(self, key: str, indent: int) -> list[str]:
        """Render a top-level ``router_bgp`` key via its schema ``cli`` annotation."""
        child_schema = self._schema_keys.get(key) or {}
        data = self._bgp.get(key)
        if data is None:
            return []
        return render_schema_field(child_schema, key, data, self._bgp, indent)

    # ------------------------------------------------------------------
    # Custom methods — global settings
    # ------------------------------------------------------------------

    def _render_labeled_unicast_rib(self, indent: int) -> list[str]:
        """``bgp labeled-unicast rib [ip [route-map X]] [tunnel [route-map Y]]`` (j2 lines 13-28)."""
        rib = ((self._bgp.get("bgp") or {}).get("labeled_unicast") or {}).get("rib") or {}
        ip = rib.get("ip") or {}
        tunnel = rib.get("tunnel") or {}
        if ip.get("enabled") is not True and tunnel.get("enabled") is not True:
            return []
        cmd = "bgp labeled-unicast rib"
        if ip.get("enabled") is True:
            cmd += " ip"
            if ip.get("route_map"):
                cmd += f" route-map {ip['route_map']}"
        if tunnel.get("enabled") is True:
            cmd += " tunnel"
            if tunnel.get("route_map"):
                cmd += f" route-map {tunnel['route_map']}"
        return [_INDENT * indent + cmd]

    def _render_bgp_default_flags(self, indent: int) -> list[str]:
        """``bgp default ipv4-unicast`` and ``bgp default ipv4-unicast transport ipv6`` (j2 lines 38-47).

        Schema carries ``bool_true_line``/``bool_false_line`` annotations on these fields,
        but they live inside a nested dict (``bgp.default``) rendered at a different j2
        position than the containing ``bgp`` key, so a custom method is used to place them
        in the correct order.
        """
        default = ((self._bgp.get("bgp") or {}).get("default") or {})
        lines: list[str] = []
        pref = _INDENT * indent
        if default.get("ipv4_unicast") is True:
            lines.append(pref + "bgp default ipv4-unicast")
        elif default.get("ipv4_unicast") is False:
            lines.append(pref + "no bgp default ipv4-unicast")
        if default.get("ipv4_unicast_transport_ipv6") is True:
            lines.append(pref + "bgp default ipv4-unicast transport ipv6")
        elif default.get("ipv4_unicast_transport_ipv6") is False:
            lines.append(pref + "no bgp default ipv4-unicast transport ipv6")
        return lines

    def _render_timers(self, indent: int) -> list[str]:
        """``timers bgp keepalive hold [min-hold-time X] [send-failure hold-time Y]`` (j2 lines 48-62)."""
        timers = self._bgp.get("timers") or {}
        keepalive = timers.get("keepalive_time")
        hold = timers.get("hold_time")
        min_hold = timers.get("min_hold_time")
        send_failure = timers.get("send_failure_hold_time")
        if keepalive is None and hold is None and min_hold is None and send_failure is None:
            return []
        cmd = "timers bgp"
        if keepalive is not None and hold is not None:
            cmd += f" {keepalive} {hold}"
        if min_hold is not None:
            cmd += f" min-hold-time {min_hold}"
        if send_failure is not None:
            cmd += f" send-failure hold-time {send_failure}"
        return [_INDENT * indent + cmd]

    def _render_distance(self, indent: int) -> list[str]:
        """``distance bgp external [internal local]`` (j2 lines 63-69)."""
        distance = self._bgp.get("distance") or {}
        ext = distance.get("external_routes")
        if ext is None:
            return []
        cmd = f"distance bgp {ext}"
        internal = distance.get("internal_routes")
        local = distance.get("local_routes")
        if internal is not None and local is not None:
            cmd += f" {internal} {local}"
        return [_INDENT * indent + cmd]

    def _render_graceful_restart(self, indent: int) -> list[str]:
        """``graceful-restart`` timers then enable command (j2 lines 70-78).

        Timers must precede the enable command in EOS CLI.
        """
        gr = self._bgp.get("graceful_restart") or {}
        if gr.get("enabled") is not True:
            return []
        pref = _INDENT * indent
        lines: list[str] = []
        if gr.get("restart_time") is not None:
            lines.append(pref + f"graceful-restart restart-time {gr['restart_time']}")
        if gr.get("stalepath_time") is not None:
            lines.append(pref + f"graceful-restart stalepath-time {gr['stalepath_time']}")
        lines.append(pref + "graceful-restart")
        return lines

    def _render_graceful_restart_helper(self, indent: int) -> list[str]:
        """``graceful-restart-helper`` or its negation (j2 lines 82-90)."""
        grh = self._bgp.get("graceful_restart_helper") or {}
        pref = _INDENT * indent
        if grh.get("enabled") is False:
            return [pref + "no graceful-restart-helper"]
        if grh.get("enabled") is True:
            if grh.get("restart_time") is not None:
                return [pref + f"graceful-restart-helper restart-time {grh['restart_time']}"]
            if grh.get("long_lived") is True:
                return [pref + "graceful-restart-helper long-lived"]
        return []

    def _render_route_reflector_preserve(self, indent: int) -> list[str]:
        """``bgp route-reflector preserve-attributes [always]`` (j2 lines 91-97)."""
        rr = ((self._bgp.get("bgp") or {}).get("route_reflector_preserve_attributes") or {})
        if rr.get("enabled") is not True:
            return []
        cmd = "bgp route-reflector preserve-attributes"
        if rr.get("always") is True:
            cmd += " always"
        return [_INDENT * indent + cmd]

    def _render_maximum_paths(self, indent: int) -> list[str]:
        """``maximum-paths X [ecmp Y]`` (j2 lines 98-103)."""
        mp = self._bgp.get("maximum_paths") or {}
        paths = mp.get("paths")
        if paths is None:
            return []
        cmd = f"maximum-paths {paths}"
        if mp.get("ecmp") is not None:
            cmd += f" ecmp {mp['ecmp']}"
        return [_INDENT * indent + cmd]

    def _render_additional_paths(self, indent: int) -> list[str]:
        """``bgp additional-paths receive`` (schema) and ``send ...`` (custom) (j2 lines 108-126)."""
        ap = (self._bgp.get("bgp") or {}).get("additional_paths") or {}
        pref = _INDENT * indent
        lines: list[str] = []

        # receive — schema carries bool_true_line/bool_false_line; replicate here for ordering
        receive = ap.get("receive")
        if receive is True:
            lines.append(pref + "bgp additional-paths receive")
        elif receive is False:
            lines.append(pref + "no bgp additional-paths receive")

        # send — complex switch; no schema annotation possible
        send = ap.get("send")
        send_limit = ap.get("send_limit")
        if send is None:
            return lines
        if send == "disabled":
            lines.append(pref + "no bgp additional-paths send")
        elif send == "ecmp" and send_limit is not None:
            lines.append(pref + f"bgp additional-paths send ecmp limit {send_limit}")
        elif send == "limit" and send_limit is not None:
            lines.append(pref + f"bgp additional-paths send limit {send_limit}")
        else:
            lines.append(pref + f"bgp additional-paths send {send}")
        return lines

    def _render_listen_ranges(self, indent: int) -> list[str]:
        """``bgp listen range`` entries (j2 lines 127-142)."""
        lines: list[str] = []
        pref = _INDENT * indent
        for lr in natural_sort(self._bgp.get("listen_ranges") or [], sort_key="peer_group"):
            if lr.get("peer_group") is None or lr.get("prefix") is None:
                continue
            if lr.get("peer_filter") is None and lr.get("remote_as") is None:
                continue
            cmd = f"bgp listen range {lr['prefix']}"
            if lr.get("peer_id_include_router_id") is True:
                cmd += " peer-id include router-id"
            cmd += f" peer-group {lr['peer_group']}"
            if lr.get("peer_filter") is not None:
                cmd += f" peer-filter {lr['peer_filter']}"
            elif lr.get("remote_as") is not None:
                cmd += f" remote-as {lr['remote_as']}"
            lines.append(pref + cmd)
        return lines

    def _render_bgp_bestpath(self, indent: int) -> list[str]:
        """``bgp bestpath d-path`` (j2 line 143-144) — schema carries bool_true_line."""
        d_path = ((self._bgp.get("bgp") or {}).get("bestpath") or {}).get("d_path")
        if d_path is True:
            return [_INDENT * indent + "bgp bestpath d-path"]
        return []

    def _render_neighbor_default_send_community(self, indent: int) -> list[str]:
        """``neighbor default send-community [value]`` (j2 lines 146-149).

        When ``send_community`` is ``'all'``, EOS omits the trailing keyword.
        """
        sc = (self._bgp.get("neighbor_default") or {}).get("send_community")
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
        for pg in natural_sort(self._bgp.get("peer_groups") or [], sort_key="name"):
            lines += self._render_peer_group(pg, indent)
        return lines

    def _render_peer_group(self, pg: dict, indent: int) -> list[str]:
        """Render one peer-group block in j2 output order."""
        name = pg.get("name")
        if name is None:
            return []

        pref = _INDENT * indent
        lines: list[str] = [pref + f"neighbor {name} peer group"]

        def add(line: str) -> None:
            lines.append(pref + line)

        if pg.get("remote_as") is not None:
            add(f"neighbor {name} remote-as {pg['remote_as']}")
        if pg.get("next_hop_self") is True:
            add(f"neighbor {name} next-hop-self")
        if pg.get("next_hop_peer") is True:
            add(f"neighbor {name} next-hop-peer")
        if pg.get("next_hop_unchanged") is True:
            add(f"neighbor {name} next-hop-unchanged")
        if pg.get("shutdown") is True:
            add(f"neighbor {name} shutdown")

        lines += self._render_remove_private_as(name, pg.get("remove_private_as") or {}, indent)

        as_path = pg.get("as_path") or {}
        if as_path.get("prepend_own_disabled") is True:
            add(f"neighbor {name} as-path prepend-own disabled")
        if as_path.get("remote_as_replace_out") is True:
            add(f"neighbor {name} as-path remote-as replace out")

        if pg.get("local_as") is not None:
            add(f"neighbor {name} local-as {pg['local_as']} no-prepend replace-as")
        if pg.get("weight") is not None:
            add(f"neighbor {name} weight {pg['weight']}")
        if pg.get("passive") is True:
            add(f"neighbor {name} passive")
        if pg.get("update_source") is not None:
            add(f"neighbor {name} update-source {pg['update_source']}")

        lines += self._render_bfd(name, pg.get("bfd"), pg.get("bfd_timers") or {}, indent)

        if pg.get("description") is not None:
            add(f"neighbor {name} description {pg['description']}")

        lines += self._render_allowas_in(name, pg.get("allowas_in") or {}, indent)
        lines += self._render_rib_in_pre_policy_retain(name, pg.get("rib_in_pre_policy_retain") or {}, indent)

        if pg.get("ebgp_multihop") is not None:
            add(f"neighbor {name} ebgp-multihop {pg['ebgp_multihop']}")
        if pg.get("ttl_maximum_hops") is not None:
            add(f"neighbor {name} ttl maximum-hops {pg['ttl_maximum_hops']}")
        if pg.get("route_reflector_client") is True:
            add(f"neighbor {name} route-reflector-client")
        if pg.get("session_tracker") is not None:
            add(f"neighbor {name} session tracker {pg['session_tracker']}")
        if pg.get("timers") is not None:
            add(f"neighbor {name} timers {pg['timers']}")
        if pg.get("route_map_in") is not None:
            add(f"neighbor {name} route-map {pg['route_map_in']} in")
        if pg.get("route_map_out") is not None:
            add(f"neighbor {name} route-map {pg['route_map_out']} out")

        # password key before shared-secret for peer-groups (j2 ordering)
        lines += self._render_password_key(name, pg.get("password"), pg.get("password_type"), indent)
        lines += self._render_shared_secret(name, pg.get("shared_secret") or {}, indent)

        lines += self._render_default_originate(name, pg.get("default_originate") or {}, indent)
        lines += self._render_send_community(name, pg.get("send_community"), indent)
        lines += self._render_maximum_routes(
            name,
            pg.get("maximum_routes"),
            pg.get("maximum_routes_warning_limit"),
            pg.get("maximum_routes_warning_only"),
            indent,
        )
        lines += self._render_missing_policy(name, pg.get("missing_policy") or {}, indent)

        if pg.get("peer_tag_in") is not None:
            add(f"neighbor {name} peer-tag in {pg['peer_tag_in']}")
        if pg.get("peer_tag_out_discard") is not None:
            add(f"neighbor {name} peer-tag out discard {pg['peer_tag_out_discard']}")

        lines += self._render_link_bandwidth(name, pg.get("link_bandwidth") or {}, indent)
        lines += self._render_remove_private_as_ingress(name, pg.get("remove_private_as_ingress") or {}, indent)

        return lines

    # ------------------------------------------------------------------
    # Neighbors (j2 lines 324-499)
    # ------------------------------------------------------------------

    def _render_neighbors(self, indent: int) -> list[str]:
        lines: list[str] = []
        for nb in natural_sort(self._bgp.get("neighbors") or [], sort_key="ip_address"):
            lines += self._render_neighbor(nb, indent)
        return lines

    def _render_neighbor(self, nb: dict, indent: int) -> list[str]:
        """Render one neighbor block in j2 output order.

        Differences from peer-groups:
        - ``no neighbor X bfd`` is valid (peer-group BFD can be overridden).
        - ``no neighbor X route-reflector-client`` is valid.
        - ``no neighbor X rib-in pre-policy retain`` is valid.
        - shared-secret is rendered *before* password key (j2 ordering).
        """
        ip = nb.get("ip_address")
        if ip is None:
            return []

        pref = _INDENT * indent
        lines: list[str] = []

        def add(line: str) -> None:
            lines.append(pref + line)

        if nb.get("peer_group") is not None:
            add(f"neighbor {ip} peer group {nb['peer_group']}")
        if nb.get("remote_as") is not None:
            add(f"neighbor {ip} remote-as {nb['remote_as']}")
        if nb.get("next_hop_self") is True:
            add(f"neighbor {ip} next-hop-self")
        if nb.get("next_hop_peer") is True:
            add(f"neighbor {ip} next-hop-peer")
        if nb.get("shutdown") is True:
            add(f"neighbor {ip} shutdown")

        lines += self._render_remove_private_as(ip, nb.get("remove_private_as") or {}, indent)

        as_path = nb.get("as_path") or {}
        if as_path.get("prepend_own_disabled") is True:
            add(f"neighbor {ip} as-path prepend-own disabled")
        if as_path.get("remote_as_replace_out") is True:
            add(f"neighbor {ip} as-path remote-as replace out")

        if nb.get("local_as") is not None:
            add(f"neighbor {ip} local-as {nb['local_as']} no-prepend replace-as")
        if nb.get("weight") is not None:
            add(f"neighbor {ip} weight {nb['weight']}")
        if nb.get("passive") is True:
            add(f"neighbor {ip} passive")
        if nb.get("update_source") is not None:
            add(f"neighbor {ip} update-source {nb['update_source']}")

        # Neighbors can disable BFD inherited from a peer-group; peer-groups cannot
        lines += self._render_bfd(ip, nb.get("bfd"), nb.get("bfd_timers") or {}, indent, allow_negation=nb.get("peer_group") is not None)

        if nb.get("description") is not None:
            add(f"neighbor {ip} description {nb['description']}")

        lines += self._render_allowas_in(ip, nb.get("allowas_in") or {}, indent)
        lines += self._render_rib_in_pre_policy_retain(ip, nb.get("rib_in_pre_policy_retain") or {}, indent)

        if nb.get("ebgp_multihop") is not None:
            add(f"neighbor {ip} ebgp-multihop {nb['ebgp_multihop']}")
        if nb.get("ttl_maximum_hops") is not None:
            add(f"neighbor {ip} ttl maximum-hops {nb['ttl_maximum_hops']}")

        # Neighbors support negation; peer-groups do not
        if nb.get("route_reflector_client") is True:
            add(f"neighbor {ip} route-reflector-client")
        elif nb.get("route_reflector_client") is False:
            add(f"no neighbor {ip} route-reflector-client")

        if nb.get("session_tracker") is not None:
            add(f"neighbor {ip} session tracker {nb['session_tracker']}")
        if nb.get("timers") is not None:
            add(f"neighbor {ip} timers {nb['timers']}")
        if nb.get("route_map_in") is not None:
            add(f"neighbor {ip} route-map {nb['route_map_in']} in")
        if nb.get("route_map_out") is not None:
            add(f"neighbor {ip} route-map {nb['route_map_out']} out")

        # shared-secret before password key for neighbors (j2 ordering)
        lines += self._render_shared_secret(ip, nb.get("shared_secret") or {}, indent)
        lines += self._render_password_key(ip, nb.get("password"), nb.get("password_type"), indent)

        lines += self._render_default_originate(ip, nb.get("default_originate") or {}, indent)
        lines += self._render_send_community(ip, nb.get("send_community"), indent)
        lines += self._render_maximum_routes(
            ip,
            nb.get("maximum_routes"),
            nb.get("maximum_routes_warning_limit"),
            nb.get("maximum_routes_warning_only"),
            indent,
        )
        lines += self._render_missing_policy(ip, nb.get("missing_policy") or {}, indent)

        if nb.get("peer_tag_in") is not None:
            add(f"neighbor {ip} peer-tag in {nb['peer_tag_in']}")
        if nb.get("peer_tag_out_discard") is not None:
            add(f"neighbor {ip} peer-tag out discard {nb['peer_tag_out_discard']}")

        lines += self._render_link_bandwidth(ip, nb.get("link_bandwidth") or {}, indent)
        lines += self._render_remove_private_as_ingress(ip, nb.get("remove_private_as_ingress") or {}, indent)

        return lines

    # ------------------------------------------------------------------
    # Shared per-entity helpers (peer-groups and neighbors)
    # ------------------------------------------------------------------

    def _render_remove_private_as(self, entity_id: str, rpa: dict, indent: int) -> list[str]:
        """``remove-private-as [all [replace-as]]`` or its negation."""
        pref = _INDENT * indent
        if rpa.get("enabled") is True:
            cmd = f"neighbor {entity_id} remove-private-as"
            if rpa.get("all") is True:
                cmd += " all"
                if rpa.get("replace_as") is True:
                    cmd += " replace-as"
            return [pref + cmd]
        if rpa.get("enabled") is False:
            return [pref + f"no neighbor {entity_id} remove-private-as"]
        return []

    def _render_bfd(
        self,
        entity_id: str,
        bfd: bool | None,
        bfd_timers: dict,
        indent: int,
        *,
        allow_negation: bool = False,
    ) -> list[str]:
        """``bfd`` and optional ``bfd interval`` line; ``no bfd`` when *allow_negation* is set."""
        pref = _INDENT * indent
        if bfd is True:
            lines = [pref + f"neighbor {entity_id} bfd"]
            interval = bfd_timers.get("interval")
            min_rx = bfd_timers.get("min_rx")
            multiplier = bfd_timers.get("multiplier")
            if interval is not None and min_rx is not None and multiplier is not None:
                lines.append(pref + f"neighbor {entity_id} bfd interval {interval} min-rx {min_rx} multiplier {multiplier}")
            return lines
        if bfd is False and allow_negation:
            return [pref + f"no neighbor {entity_id} bfd"]
        return []

    def _render_allowas_in(self, entity_id: str, allowas_in: dict, indent: int) -> list[str]:
        """``allowas-in [N]``."""
        if allowas_in.get("enabled") is not True:
            return []
        cmd = f"neighbor {entity_id} allowas-in"
        if allowas_in.get("times") is not None:
            cmd += f" {allowas_in['times']}"
        return [_INDENT * indent + cmd]

    def _render_rib_in_pre_policy_retain(self, entity_id: str, rib_in: dict, indent: int) -> list[str]:
        """``rib-in pre-policy retain [all]`` or its negation."""
        pref = _INDENT * indent
        if rib_in.get("enabled") is True:
            cmd = f"neighbor {entity_id} rib-in pre-policy retain"
            if rib_in.get("all") is True:
                cmd += " all"
            return [pref + cmd]
        if rib_in.get("enabled") is False:
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

    def _render_shared_secret(self, entity_id: str, shared_secret: dict, indent: int) -> list[str]:
        """``neighbor X password shared-secret profile P algorithm A``."""
        profile = shared_secret.get("profile")
        algo = shared_secret.get("hash_algorithm")
        if profile is not None and algo is not None:
            return [_INDENT * indent + f"neighbor {entity_id} password shared-secret profile {profile} algorithm {algo}"]
        return []

    def _render_default_originate(self, entity_id: str, do: dict, indent: int) -> list[str]:
        """``default-originate [route-map X] [always]``."""
        if do.get("enabled") is not True:
            return []
        cmd = f"neighbor {entity_id} default-originate"
        if do.get("route_map") is not None:
            cmd += f" route-map {do['route_map']}"
        if do.get("always") is True:
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
        warning_limit: Any,
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

    def _render_missing_policy(self, entity_id: str, missing_policy: dict, indent: int) -> list[str]:
        """``missing-policy address-family all [include ...] direction {in|out} action X``."""
        pref = _INDENT * indent
        lines: list[str] = []
        for direction in ("in", "out"):
            policy = missing_policy.get(f"direction_{direction}") or {}
            if not policy.get("action"):
                continue
            cmd = f"neighbor {entity_id} missing-policy address-family all"
            includes: list[str] = []
            if policy.get("include_community_list") is True:
                includes.append("community-list")
            if policy.get("include_prefix_list") is True:
                includes.append("prefix-list")
            if policy.get("include_sub_route_map") is True:
                includes.append("sub-route-map")
            if includes:
                cmd += " include " + " ".join(includes)
            cmd += f" direction {direction} action {policy['action']}"
            lines.append(pref + cmd)
        return lines

    def _render_link_bandwidth(self, entity_id: str, lb: dict, indent: int) -> list[str]:
        """``link-bandwidth [default X]``."""
        if lb.get("enabled") is not True:
            return []
        cmd = f"neighbor {entity_id} link-bandwidth"
        if lb.get("default") is not None:
            cmd += f" default {lb['default']}"
        return [_INDENT * indent + cmd]

    def _render_remove_private_as_ingress(self, entity_id: str, rpai: dict, indent: int) -> list[str]:
        """``remove-private-as ingress [replace-as]`` or its negation."""
        pref = _INDENT * indent
        if rpai.get("enabled") is True:
            cmd = f"neighbor {entity_id} remove-private-as ingress"
            if rpai.get("replace_as") is True:
                cmd += " replace-as"
            return [pref + cmd]
        if rpai.get("enabled") is False:
            return [pref + f"no neighbor {entity_id} remove-private-as ingress"]
        return []

    # ------------------------------------------------------------------
    # Redistribute-internal (j2 lines 500-503)
    # ------------------------------------------------------------------

    def _render_redistribute_internal(self, indent: int) -> list[str]:
        """``bgp redistribute-internal`` or its negation — schema carries bool_true/false_line."""
        ri = (self._bgp.get("bgp") or {}).get("redistribute_internal")
        if ri is True:
            return [_INDENT * indent + "bgp redistribute-internal"]
        if ri is False:
            return [_INDENT * indent + "no bgp redistribute-internal"]
        return []

    # ------------------------------------------------------------------
    # Aggregate addresses (j2 lines 505-526)
    # ------------------------------------------------------------------

    def _render_aggregate_addresses(self, indent: int) -> list[str]:
        """``aggregate-address prefix [as-set] [summary-only] [attribute-map X] ...``."""
        pref = _INDENT * indent
        lines: list[str] = []
        for agg in natural_sort(self._bgp.get("aggregate_addresses") or [], sort_key="prefix"):
            cmd = f"aggregate-address {agg['prefix']}"
            if agg.get("as_set") is True:
                cmd += " as-set"
            if agg.get("summary_only") is True:
                cmd += " summary-only"
            if agg.get("attribute_map") is not None:
                cmd += f" attribute-map {agg['attribute_map']}"
            if (agg.get("attribute") or {}).get("rcf") is not None:
                cmd += f" attribute rcf {agg['attribute']['rcf']}"
            if agg.get("match_map") is not None:
                cmd += f" match-map {agg['match_map']}"
            if agg.get("advertise_only") is True:
                cmd += " advertise-only"
            lines.append(pref + cmd)
        return lines

    # ------------------------------------------------------------------
    # Redistribute (j2 lines 527-688)
    # ------------------------------------------------------------------

    def _render_redistribute(self, indent: int) -> list[str]:  # noqa: PLR0912
        """Render all ``redistribute`` entries in j2 template order."""
        redist = self._bgp.get("redistribute") or {}
        pref = _INDENT * indent
        lines: list[str] = []

        conn = redist.get("connected") or {}
        if conn.get("enabled") is True:
            cli = "redistribute connected"
            if conn.get("include_leaked") is True:
                cli += " include leaked"
            if conn.get("route_map"):
                cli += f" route-map {conn['route_map']}"
            elif conn.get("rcf"):
                cli += f" rcf {conn['rcf']}"
            lines.append(pref + cli)

        isis = redist.get("isis") or {}
        if isis.get("enabled") is True:
            cli = "redistribute isis"
            if isis.get("isis_level"):
                cli += f" {isis['isis_level']}"
            if isis.get("include_leaked") is True:
                cli += " include leaked"
            if isis.get("route_map"):
                cli += f" route-map {isis['route_map']}"
            elif isis.get("rcf"):
                cli += f" rcf {isis['rcf']}"
            lines.append(pref + cli)

        ospf = redist.get("ospf") or {}
        if ospf.get("enabled") is True:
            cli = "redistribute ospf"
            if ospf.get("include_leaked") is True:
                cli += " include leaked"
            if ospf.get("route_map"):
                cli += f" route-map {ospf['route_map']}"
            lines.append(pref + cli)
        elif (ospf.get("match_internal") or {}).get("enabled") is True:
            mi = ospf["match_internal"]
            cli = "redistribute ospf match internal"
            if mi.get("include_leaked") is True:
                cli += " include leaked"
            if mi.get("route_map"):
                cli += f" route-map {mi['route_map']}"
            lines.append(pref + cli)

        me = ospf.get("match_external") or {}
        if me.get("enabled") is True:
            cli = "redistribute ospf match external"
            if me.get("include_leaked") is True:
                cli += " include leaked"
            if me.get("route_map"):
                cli += f" route-map {me['route_map']}"
            lines.append(pref + cli)

        mn = ospf.get("match_nssa_external") or {}
        if mn.get("enabled") is True:
            cli = "redistribute ospf match nssa-external"
            if mn.get("nssa_type") is not None:
                cli += f" {mn['nssa_type']}"
            if mn.get("include_leaked") is True:
                cli += " include leaked"
            if mn.get("route_map"):
                cli += f" route-map {mn['route_map']}"
            lines.append(pref + cli)

        ospfv3 = redist.get("ospfv3") or {}
        if ospfv3.get("enabled") is True:
            cli = "redistribute ospfv3"
            if ospfv3.get("include_leaked") is True:
                cli += " include leaked"
            if ospfv3.get("route_map"):
                cli += f" route-map {ospfv3['route_map']}"
            lines.append(pref + cli)
        elif (ospfv3.get("match_internal") or {}).get("enabled") is True:
            mi3 = ospfv3["match_internal"]
            cli = "redistribute ospfv3 match internal"
            if mi3.get("include_leaked") is True:
                cli += " include leaked"
            if mi3.get("route_map"):
                cli += f" route-map {mi3['route_map']}"
            lines.append(pref + cli)

        me3 = ospfv3.get("match_external") or {}
        if me3.get("enabled") is True:
            cli = "redistribute ospfv3 match external"
            if me3.get("include_leaked") is True:
                cli += " include leaked"
            if me3.get("route_map"):
                cli += f" route-map {me3['route_map']}"
            lines.append(pref + cli)

        mn3 = ospfv3.get("match_nssa_external") or {}
        if mn3.get("enabled") is True:
            cli = "redistribute ospfv3 match nssa-external"
            if mn3.get("nssa_type") is not None:
                cli += f" {mn3['nssa_type']}"
            if mn3.get("include_leaked") is True:
                cli += " include leaked"
            if mn3.get("route_map"):
                cli += f" route-map {mn3['route_map']}"
            lines.append(pref + cli)

        static = redist.get("static") or {}
        if static.get("enabled") is True:
            cli = "redistribute static"
            if static.get("include_leaked") is True:
                cli += " include leaked"
            if static.get("route_map"):
                cli += f" route-map {static['route_map']}"
            elif static.get("rcf"):
                cli += f" rcf {static['rcf']}"
            lines.append(pref + cli)

        rip = redist.get("rip") or {}
        if rip.get("enabled") is True:
            cli = "redistribute rip"
            if rip.get("route_map"):
                cli += f" route-map {rip['route_map']}"
            lines.append(pref + cli)

        attached_host = redist.get("attached_host") or {}
        if attached_host.get("enabled") is True:
            cli = "redistribute attached-host"
            if attached_host.get("route_map"):
                cli += f" route-map {attached_host['route_map']}"
            lines.append(pref + cli)

        dynamic = redist.get("dynamic") or {}
        if dynamic.get("enabled") is True:
            cli = "redistribute dynamic"
            if dynamic.get("route_map"):
                cli += f" route-map {dynamic['route_map']}"
            elif dynamic.get("rcf"):
                cli += f" rcf {dynamic['rcf']}"
            lines.append(pref + cli)

        bgp_redist = redist.get("bgp") or {}
        if bgp_redist.get("enabled") is True:
            cli = "redistribute bgp leaked"
            if bgp_redist.get("route_map"):
                cli += f" route-map {bgp_redist['route_map']}"
            lines.append(pref + cli)

        user = redist.get("user") or {}
        if user.get("enabled") is True:
            cli = "redistribute user"
            if user.get("rcf"):
                cli += f" rcf {user['rcf']}"
            lines.append(pref + cli)

        return lines

    # ------------------------------------------------------------------
    # VLANs (j2 lines 697-737)
    # ------------------------------------------------------------------

    def _render_vlans(self, indent: int) -> list[str]:
        lines: list[str] = []
        for vlan in natural_sort(self._bgp.get("vlans") or [], sort_key="id"):
            lines += self._render_vlan(vlan, indent)
        return lines

    def _render_vlan(self, vlan: dict, indent: int) -> list[str]:
        """Render one ``vlan X`` sub-block inside ``router bgp``."""
        vlan_id = vlan.get("id")
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

        if vlan.get("rd") is not None:
            sub(f"rd {vlan['rd']}")

        rd_evpn = vlan.get("rd_evpn_domain") or {}
        if rd_evpn.get("domain") is not None and rd_evpn.get("rd") is not None:
            sub(f"rd evpn domain {rd_evpn['domain']} {rd_evpn['rd']}")

        rt = vlan.get("route_targets") or {}
        for route_target in natural_sort(rt.get("both") or []):
            sub(f"route-target both {route_target}")
        for route_target in natural_sort(rt.get("import") or []):
            sub(f"route-target import {route_target}")
        for route_target in natural_sort(rt.get("export") or []):
            sub(f"route-target export {route_target}")
        for entry in natural_sort(rt.get("import_evpn_domains") or [], sort_key="domain"):
            sub(f"route-target import evpn domain {entry['domain']} {entry['route_target']}")
        for entry in natural_sort(rt.get("export_evpn_domains") or [], sort_key="domain"):
            sub(f"route-target export evpn domain {entry['domain']} {entry['route_target']}")
        for entry in natural_sort(rt.get("import_export_evpn_domains") or [], sort_key="domain"):
            sub(f"route-target import export evpn domain {entry['domain']} {entry['route_target']}")

        for route in natural_sort(vlan.get("redistribute_routes") or []):
            sub(f"redistribute {route}")
        for route in natural_sort(vlan.get("no_redistribute_routes") or []):
            sub(f"no redistribute {route}")

        eos_cli = vlan.get("eos_cli")
        if eos_cli is not None:
            sub("!")
            for line in eos_cli.splitlines():
                sub(line)

        return lines
