# Copyright (c) 2023-2026 Arista Networks, Inc.
# Use of this source code is governed by the Apache License 2.0
# that can be found in the LICENSE file.
"""Router BGP documentation generator."""

from __future__ import annotations

from typing import TYPE_CHECKING

from pyavd.j2filters import natural_sort

from .base import DocGenerator, DocSection, doc_contributor

if TYPE_CHECKING:
    from pyavd._eos_cli_config_gen.schema import EosCliConfigGen


class RouterBgpDocGenerator(DocGenerator):
    """
    Generator for Router BGP documentation.

    Migrated from j2templates/documentation/router-bgp.j2
    """

    @property
    def _model(self) -> DocSection:
        return self.doc_config.router_bgp

    @doc_contributor
    def router_bgp(self) -> None:
        """Render all Router BGP documentation sections."""
        bgp = self.data.router_bgp
        if bgp is None:
            return

        self._model.heading(3, "Router BGP")
        self._render_bgp_neighbors(bgp)

    # ------------------------------------------------------------------
    # BGP Neighbors table
    # ------------------------------------------------------------------

    def _render_bgp_neighbors(self, bgp: EosCliConfigGen.RouterBgp) -> None:
        """
        Render the BGP Neighbors table.

        Covers both default-VRF neighbors (router_bgp.neighbors) and
        per-VRF neighbors (router_bgp.vrfs[*].neighbors) in a single table,
        matching the J2 template output exactly.
        """
        has_default_neighbors = bool(bgp.neighbors)
        has_vrf_neighbors = any(vrf.neighbors for vrf in (bgp.vrfs or []))
        if not has_default_neighbors and not has_vrf_neighbors:
            return

        self._model.heading(4, "BGP Neighbors")

        headers = [
            "Neighbor",
            "Remote AS",
            "VRF",
            "Shutdown",
            "Send-community",
            "Maximum-routes",
            "Allowas-in",
            "BFD",
            "RIB Pre-Policy Retain",
            "Route-Reflector Client",
            "Passive",
            "TTL Max Hops",
        ]

        rows: list[list[str]] = []

        # Default VRF neighbors — sorted by ip_address, TTL Max Hops resolved from data.
        for neighbor in natural_sort(bgp.neighbors or [], sort_key="ip_address"):
            inherited = self._peer_group_inherited(neighbor.peer_group, bgp, include_ttl=True)
            vrf = self._default(neighbor.vrf, inherited.get("vrf"), fallback="default")
            rows.append(self._neighbor_row(neighbor, inherited, vrf_name=vrf, include_ttl=True))

        # Per-VRF neighbors — VRF name comes from the outer vrf object, TTL always "-".
        for vrf in natural_sort(bgp.vrfs or [], sort_key="name"):
            for neighbor in vrf.neighbors or []:
                inherited = self._peer_group_inherited(neighbor.peer_group, bgp, include_ttl=False)
                rows.append(self._neighbor_row(neighbor, inherited, vrf_name=vrf.name, include_ttl=False))

        self._model.table(headers, rows)

    def _peer_group_inherited(
        self,
        peer_group_name: str | None,
        bgp: EosCliConfigGen.RouterBgp,
        *,
        include_ttl: bool,
    ) -> dict[str, str]:
        """
        Look up *peer_group_name* in *bgp.peer_groups* and collect the fields
        that would be inherited by a neighbor belonging to that peer group.

        Returns a dict keyed by field name.  Each value is either the human-readable
        "Inherited from peer group <name>" tag or a pre-formatted string (bfd_timers).

        *include_ttl* is True for default-VRF neighbors (where TTL Max Hops can be
        inherited) and False for per-VRF neighbors (where it is always "-").
        """
        if not peer_group_name:
            return {}

        pg = next((p for p in (bgp.peer_groups or []) if p.name == peer_group_name), None)
        if pg is None:
            return {}

        tag = f"Inherited from peer group {peer_group_name}"
        inherited: dict[str, str] = {}

        if pg.remote_as is not None:
            inherited["remote_as"] = tag
        if pg.vrf is not None:
            inherited["vrf"] = tag
        if pg.send_community is not None:
            inherited["send_community"] = tag
        if pg.maximum_routes is not None:
            inherited["maximum_routes"] = tag
        if pg.allowas_in.enabled is True:
            inherited["allowas_in"] = tag
        if pg.bfd is True:
            inherited["bfd"] = tag
            if pg.bfd_timers.interval is not None and pg.bfd_timers.min_rx is not None and pg.bfd_timers.multiplier is not None:
                inherited["bfd_timers"] = f"interval: {pg.bfd_timers.interval}, min_rx: {pg.bfd_timers.min_rx}, multiplier: {pg.bfd_timers.multiplier}"
        if pg.shutdown is True:
            inherited["shutdown"] = tag
        if pg.rib_in_pre_policy_retain.enabled is True:
            inherited["rib_in_pre_policy_retain"] = tag
        if pg.route_reflector_client is True:
            inherited["route_reflector_client"] = tag
        if pg.passive is True:
            inherited["passive"] = tag
        if include_ttl and pg.ttl_maximum_hops is not None:
            inherited["ttl_maximum_hops"] = tag

        return inherited

    def _neighbor_row(
        self,
        neighbor: EosCliConfigGen.RouterBgp.NeighborsItem | EosCliConfigGen.RouterBgp.VrfsItem.NeighborsItem,
        inherited: dict[str, str],
        *,
        vrf_name: str,
        include_ttl: bool,
    ) -> list[str]:
        """
        Build one row of the BGP Neighbors table for *neighbor*.

        *inherited* is the dict returned by :meth:`_peer_group_inherited`.
        *vrf_name* is the resolved VRF column value (caller handles default-vs-VRF logic).
        *include_ttl* controls whether TTL Max Hops is resolved from data (True)
        or always shown as "-" (False, for per-VRF neighbors).
        """
        remote_as = self._default(neighbor.remote_as, inherited.get("remote_as"))
        shutdown = self._default(neighbor.shutdown, inherited.get("shutdown"))
        send_community = self._default(neighbor.send_community, inherited.get("send_community"))
        rr_client = self._default(neighbor.route_reflector_client, inherited.get("route_reflector_client"))
        passive = self._default(neighbor.passive, inherited.get("passive"))

        bfd = self._format_bfd(neighbor, inherited)
        maximum_routes = self._format_maximum_routes(neighbor, inherited)
        allowas_in = self._format_allowas_in(neighbor, inherited)
        rib = self._format_rib(neighbor, inherited)
        ttl = self._default(neighbor.ttl_maximum_hops, inherited.get("ttl_maximum_hops")) if include_ttl else "-"

        return [
            neighbor.ip_address,
            remote_as,
            vrf_name,
            shutdown,
            send_community,
            maximum_routes,
            allowas_in,
            bfd,
            rib,
            rr_client,
            passive,
            ttl,
        ]

    # ------------------------------------------------------------------
    # Per-field formatting helpers
    # ------------------------------------------------------------------

    def _format_bfd(
        self,
        neighbor: EosCliConfigGen.RouterBgp.NeighborsItem | EosCliConfigGen.RouterBgp.VrfsItem.NeighborsItem,
        inherited: dict[str, str],
    ) -> str:
        """
        Resolve the BFD column value, appending timer details when available.

        Priority:
          1. neighbor.bfd → else inherited["bfd"] → else "-"
          2. If bfd != "-": append "(interval: X, min_rx: Y, multiplier: Z)" when
             neighbor.bfd_timers are all set, falling back to inherited["bfd_timers"].
        """
        bfd = self._default(neighbor.bfd, inherited.get("bfd"))

        if bfd == "-":
            return "-"

        # Neighbour-level timers take precedence over inherited timers.
        t = neighbor.bfd_timers
        if t.interval is not None and t.min_rx is not None and t.multiplier is not None:
            timers = f"interval: {t.interval}, min_rx: {t.min_rx}, multiplier: {t.multiplier}"
        else:
            timers = inherited.get("bfd_timers", "-")

        if timers != "-":
            return f"{bfd}({timers})"
        return bfd

    def _format_maximum_routes(
        self,
        neighbor: EosCliConfigGen.RouterBgp.NeighborsItem | EosCliConfigGen.RouterBgp.VrfsItem.NeighborsItem,
        inherited: dict[str, str],
    ) -> str:
        """
        Resolve the Maximum-routes column value.

        Formats the raw integer with optional warning-limit / warning-only suffixes,
        then falls back to inherited peer group value or "-".
        """
        if neighbor.maximum_routes is None:
            return inherited.get("maximum_routes", "-")

        value = "0 (no limit)" if neighbor.maximum_routes == 0 else str(neighbor.maximum_routes)

        has_limit = neighbor.maximum_routes_warning_limit is not None
        has_warning_only = neighbor.maximum_routes_warning_only is True

        if has_limit or has_warning_only:
            parts = []
            if has_limit:
                parts.append(f"warning-limit {neighbor.maximum_routes_warning_limit}")
            if has_warning_only:
                parts.append("warning-only")
            value += " (" + ", ".join(parts) + ")"

        return value

    def _format_allowas_in(
        self,
        neighbor: EosCliConfigGen.RouterBgp.NeighborsItem | EosCliConfigGen.RouterBgp.VrfsItem.NeighborsItem,
        inherited: dict[str, str],
    ) -> str:
        """
        Resolve the Allowas-in column value.

        Returns "Allowed, allowed N times" when enabled on the neighbor,
        falling back to inherited peer group value or "-".
        """
        if neighbor.allowas_in.enabled is not True:
            return inherited.get("allowas_in", "-")

        times = neighbor.allowas_in.times
        times_str = str(times) if times is not None else "3 (default)"
        return f"Allowed, allowed {times_str} times"

    def _format_rib(
        self,
        neighbor: EosCliConfigGen.RouterBgp.NeighborsItem | EosCliConfigGen.RouterBgp.VrfsItem.NeighborsItem,
        inherited: dict[str, str],
    ) -> str:
        """
        Resolve the RIB Pre-Policy Retain column value.

        Note: ``is arista.avd.defined()`` in J2 (empty args) matches any defined value,
        including False — so we check ``is not None``, not ``is True``.
        """
        if neighbor.rib_in_pre_policy_retain.enabled is None:
            return inherited.get("rib_in_pre_policy_retain", "-")

        value = str(neighbor.rib_in_pre_policy_retain.enabled)
        if neighbor.rib_in_pre_policy_retain.enabled is True and neighbor.rib_in_pre_policy_retain.all is True:
            value += " (All)"
        return value
