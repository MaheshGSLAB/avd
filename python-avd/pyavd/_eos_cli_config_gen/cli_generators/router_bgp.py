# Copyright (c) 2023-2026 Arista Networks, Inc.
# Use of this source code is governed by the Apache License 2.0
# that can be found in the LICENSE file.
"""Router BGP CLI configuration generator."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from pyavd._utils import Undefined
from pyavd._utils.get import get_v2
from pyavd.j2filters import hide_passwords, natural_sort

from .base import CliGenerator, CliModel, CliSection, cli_config_contributor

if TYPE_CHECKING:
    from pyavd._eos_cli_config_gen.schema import EosCliConfigGen


class RouterBgpGenerator(CliGenerator):
    """
    Generator for router BGP CLI configuration.

    Single contributor method `router_bgp` delegates entirely to RouterBgpBlock.
    """

    @property
    def _model(self) -> CliModel:
        """Router BGP config section."""
        return self.cli_config.router_bgp

    @cli_config_contributor
    def router_bgp(self) -> None:
        """Render the full 'router bgp' block in EOS output order."""
        self._model.extend(RouterBgpBlock(self.data.router_bgp, self.data).render(indent=0))


class RouterBgpBlock(CliSection):
    """Renders the full 'router bgp X' block."""

    def __init__(self, bgp: Any, data: Any) -> None:
        self.bgp = bgp
        self.data = data

    def _generate(self) -> None:
        bgp = self.bgp
        bgp_as = get_v2(bgp, "as")
        if bgp_as is None:
            return
        self._header(f"router bgp {bgp_as}")
        self._render_global_settings(bgp)
        self._render_peer_groups(bgp)
        self._render_neighbors(bgp)
        self._render_redistribute_internal(bgp)
        self._render_aggregate_addresses(bgp)
        self._render_redistribute(bgp)
        self._render_neighbor_interfaces(bgp)

        for vlan in natural_sort(bgp.vlans or [], sort_key="id"):
            self._sub(RouterBgpVlan(vlan))

        for svc in natural_sort(bgp.vpws or [], sort_key="name"):
            self._sub(RouterBgpVpwsService(svc))

        for bundle in natural_sort(bgp.vlan_aware_bundles or [], sort_key="name"):
            self._sub(RouterBgpVlanAwareBundle(bundle))

        self._sub(RouterBgpRouteDistinguisher(bgp))
        self._sub(RouterBgpAddressFamilyEvpn(bgp))
        self._sub(RouterBgpAddressFamilyFlowSpec(bgp.address_family_flow_spec_ipv4, "ipv4"))
        self._sub(RouterBgpAddressFamilyFlowSpec(bgp.address_family_flow_spec_ipv6, "ipv6"))
        self._sub(RouterBgpAddressFamilyIpv4(bgp))
        self._sub(RouterBgpAddressFamilyIpv4LabeledUnicast(bgp))
        self._sub(RouterBgpAddressFamilyIpv4Multicast(bgp))
        self._sub(RouterBgpAddressFamilyIpv4SrTe(bgp))
        self._sub(RouterBgpAddressFamilyIpv6(bgp))
        self._sub(RouterBgpAddressFamilyIpv6Multicast(bgp))
        self._sub(RouterBgpAddressFamilyIpv6SrTe(bgp))
        self._sub(RouterBgpAddressFamilyLinkState(bgp))
        self._sub(RouterBgpAddressFamilyPathSelection(bgp))
        self._sub(RouterBgpAddressFamilyRtc(bgp))
        self._sub(RouterBgpAddressFamilyVpnIpv4(bgp))
        self._sub(RouterBgpAddressFamilyVpnIpv6(bgp))

        for vrf in natural_sort(bgp.vrfs or [], sort_key="name"):
            self._sub(RouterBgpVrf(vrf, self.data))

        for tracker in natural_sort(bgp.session_trackers or [], sort_key="name"):
            self._sub(RouterBgpSessionTracker(tracker))

        self._render_bgp_eos_cli(bgp)

    def _render_bgp_eos_cli(self, bgp: Any) -> None:
        if bgp.eos_cli is None:
            return
        self._add("!")
        for line in bgp.eos_cli.splitlines():
            self._add(line)

    def _render_global_settings(self, bgp: Any) -> None:
        """
        Render global BGP settings in EOS output order (J2 lines 10-134).

        Simple flags are inlined; multi-line concepts delegate to sub-helpers.
        """
        self._add("bgp asn notation {}", bgp.as_notation)
        self._render_labeled_unicast_rib(bgp)
        self._add("router-id {}", bgp.router_id)
        self._add("update wait-for-convergence", bgp.updates.wait_for_convergence)
        self._add("update wait-install", bgp.updates.wait_install)

        self._render_bgp_default_flags(bgp)
        self._render_timers(bgp)
        self._render_distance(bgp)
        self._render_graceful_restart(bgp)

        self._add("bgp cluster-id {}", bgp.bgp_cluster_id)

        self._render_graceful_restart_helper(bgp)
        self._render_route_reflector_preserve(bgp)
        self._render_maximum_paths_global(bgp)

        for bgp_default in bgp.bgp_defaults or []:
            self._add(bgp_default)

        self._render_additional_paths(bgp)
        self._render_listen_ranges(bgp)

        self._add("bgp bestpath d-path", bgp.bgp.bestpath.d_path)

        if bgp.neighbor_default.send_community == "all":
            self._add("neighbor default send-community")
        elif bgp.neighbor_default.send_community is not None:
            self._add(f"neighbor default send-community {bgp.neighbor_default.send_community}")

    def _render_peer_groups(self, bgp: EosCliConfigGen.RouterBgp) -> None:
        """Render all peer-group entries sorted by name (J2 lines 135-307)."""
        for peer_group in natural_sort(bgp.peer_groups or [], sort_key="name"):
            self._render_peer_group(peer_group)

    def _render_peer_group(self, peer_group: EosCliConfigGen.RouterBgp.PeerGroupsItem) -> None:
        """Render a single peer-group block in EOS output order."""
        name = peer_group.name

        self._add(f"neighbor {name} peer group")

        self._add("neighbor {} remote-as {}", name, peer_group.remote_as)
        if peer_group.shutdown is True:
            self._add(f"neighbor {name} shutdown")

        self._render_next_hop(name, peer_group.next_hop_self, peer_group.next_hop_peer, peer_group.next_hop_unchanged)
        self._render_remove_private_as(name, peer_group.remove_private_as)
        self._render_as_path(name, peer_group.as_path)

        self._add("neighbor {} local-as {} no-prepend replace-as", name, peer_group.local_as)
        self._add("neighbor {} weight {}", name, peer_group.weight)
        if peer_group.passive is True:
            self._add(f"neighbor {name} passive")
        self._add("neighbor {} update-source {}", name, peer_group.update_source)

        self._render_bfd(name, peer_group.bfd, peer_group.bfd_timers)

        self._add("neighbor {} description {}", name, peer_group.description)

        self._render_allowas_in(name, peer_group.allowas_in)
        self._render_rib_in_pre_policy_retain(name, peer_group.rib_in_pre_policy_retain)

        self._add("neighbor {} ebgp-multihop {}", name, peer_group.ebgp_multihop)
        self._add("neighbor {} ttl maximum-hops {}", name, peer_group.ttl_maximum_hops)
        if peer_group.route_reflector_client is True:
            self._add(f"neighbor {name} route-reflector-client")
        self._add("neighbor {} session tracker {}", name, peer_group.session_tracker)
        self._add("neighbor {} timers {}", name, peer_group.timers)

        self._render_route_maps(name, peer_group.route_map_in, peer_group.route_map_out)

        # password key before shared-secret for peer-groups (J2 ordering)
        self._render_password_key(name, peer_group.password, peer_group.password_type)
        self._render_shared_secret(name, peer_group.shared_secret)

        self._render_default_originate(name, peer_group.default_originate)
        self._render_send_community(name, peer_group.send_community)
        self._render_maximum_routes(name, peer_group.maximum_routes, peer_group.maximum_routes_warning_limit, peer_group.maximum_routes_warning_only)

        if peer_group.missing_policy is not None:
            self._render_missing_policy(name, peer_group.missing_policy)

        self._render_peer_tags(name, peer_group.peer_tag_in, peer_group.peer_tag_out_discard)
        self._render_link_bandwidth(name, peer_group.link_bandwidth)
        self._render_remove_private_as_ingress(name, peer_group.remove_private_as_ingress)

    def _render_neighbors(self, bgp: EosCliConfigGen.RouterBgp) -> None:
        """Render all neighbor entries sorted by IP address (J2 lines 308-483)."""
        for neighbor in natural_sort(bgp.neighbors or [], sort_key="ip_address"):
            self._render_neighbor(neighbor)

    def _render_neighbor(self, neighbor: EosCliConfigGen.RouterBgp.NeighborsItem) -> None:
        """
        Render a single neighbor block in EOS output order.

        Differences from peer-group:
        - 'no neighbor X bfd' is valid (inherited bfd can be disabled per neighbor)
        - 'no neighbor X route-reflector-client' is valid
        - shared-secret is rendered before password key (J2 ordering)
        """
        neighbor_ip_address = neighbor.ip_address

        self._add("neighbor {} peer group {}", neighbor_ip_address, neighbor.peer_group)
        self._add("neighbor {} remote-as {}", neighbor_ip_address, neighbor.remote_as)
        if neighbor.shutdown is True:
            self._add(f"neighbor {neighbor_ip_address} shutdown")

        self._render_next_hop(neighbor_ip_address, neighbor.next_hop_self, neighbor.next_hop_peer)
        self._render_remove_private_as(neighbor_ip_address, neighbor.remove_private_as)
        self._render_as_path(neighbor_ip_address, neighbor.as_path)

        self._add("neighbor {} local-as {} no-prepend replace-as", neighbor_ip_address, neighbor.local_as)
        self._add("neighbor {} weight {}", neighbor_ip_address, neighbor.weight)
        if neighbor.passive is True:
            self._add(f"neighbor {neighbor_ip_address} passive")
        self._add("neighbor {} update-source {}", neighbor_ip_address, neighbor.update_source)

        # Neighbors can disable bfd inherited from a peer-group; peer-groups cannot.
        self._render_bfd(neighbor_ip_address, neighbor.bfd, neighbor.bfd_timers, allow_negation=neighbor.peer_group is not None)

        self._add("neighbor {} description {}", neighbor_ip_address, neighbor.description)

        self._render_allowas_in(neighbor_ip_address, neighbor.allowas_in)
        self._render_rib_in_pre_policy_retain(neighbor_ip_address, neighbor.rib_in_pre_policy_retain)

        self._add("neighbor {} ebgp-multihop {}", neighbor_ip_address, neighbor.ebgp_multihop)
        self._add("neighbor {} ttl maximum-hops {}", neighbor_ip_address, neighbor.ttl_maximum_hops)

        # Neighbors support negation for route-reflector-client; peer-groups do not.
        if neighbor.route_reflector_client is True:
            self._add(f"neighbor {neighbor_ip_address} route-reflector-client")
        elif neighbor.route_reflector_client is False:
            self._add(f"no neighbor {neighbor_ip_address} route-reflector-client")

        self._add("neighbor {} session tracker {}", neighbor_ip_address, neighbor.session_tracker)
        self._add("neighbor {} timers {}", neighbor_ip_address, neighbor.timers)

        self._render_route_maps(neighbor_ip_address, neighbor.route_map_in, neighbor.route_map_out)

        # shared-secret before password key for neighbors (J2 ordering)
        self._render_shared_secret(neighbor_ip_address, neighbor.shared_secret)
        self._render_password_key(neighbor_ip_address, neighbor.password, neighbor.password_type)

        self._render_default_originate(neighbor_ip_address, neighbor.default_originate)
        self._render_send_community(neighbor_ip_address, neighbor.send_community)
        self._render_maximum_routes(neighbor_ip_address, neighbor.maximum_routes, neighbor.maximum_routes_warning_limit, neighbor.maximum_routes_warning_only)

        if neighbor.missing_policy is not None:
            self._render_missing_policy(neighbor_ip_address, neighbor.missing_policy)

        self._render_peer_tags(neighbor_ip_address, neighbor.peer_tag_in, neighbor.peer_tag_out_discard)
        self._render_link_bandwidth(neighbor_ip_address, neighbor.link_bandwidth)
        self._render_remove_private_as_ingress(neighbor_ip_address, neighbor.remove_private_as_ingress)

    def _render_redistribute_internal(self, bgp: EosCliConfigGen.RouterBgp) -> None:
        """Render 'bgp redistribute-internal' or its negation (J2 lines 484-488)."""
        if bgp.bgp.redistribute_internal is True:
            self._add("bgp redistribute-internal")
        elif bgp.bgp.redistribute_internal is False:
            self._add("no bgp redistribute-internal")

    def _render_aggregate_addresses(self, bgp: EosCliConfigGen.RouterBgp) -> None:
        """Render aggregate-address entries sorted by prefix (J2 lines 489-510)."""
        for agg in natural_sort(bgp.aggregate_addresses or [], sort_key="prefix"):
            agg_cli = f"aggregate-address {agg.prefix}"
            if agg.as_set is True:
                agg_cli += " as-set"
            if agg.summary_only is True:
                agg_cli += " summary-only"
            if agg.attribute_map is not None:
                agg_cli += f" attribute-map {agg.attribute_map}"
            if agg.attribute.rcf is not None:
                agg_cli += f" attribute rcf {agg.attribute.rcf}"
            if agg.match_map is not None:
                agg_cli += f" match-map {agg.match_map}"
            if agg.advertise_only is True:
                agg_cli += " advertise-only"
            self._add(agg_cli)

    def _render_redistribute(self, bgp: EosCliConfigGen.RouterBgp) -> None:
        """Render global 'redistribute' entries (J2 lines 511-673)."""
        redist = bgp.redistribute

        if redist.connected.enabled is True:
            cli = "redistribute connected"
            if redist.connected.include_leaked is True:
                cli += " include leaked"
            if redist.connected.route_map is not None:
                cli += f" route-map {redist.connected.route_map}"
            elif redist.connected.rcf is not None:
                cli += f" rcf {redist.connected.rcf}"
            self._add(cli)

        if redist.isis.enabled is True:
            cli = "redistribute isis"
            if redist.isis.isis_level is not None:
                cli += f" {redist.isis.isis_level}"
            if redist.isis.include_leaked is True:
                cli += " include leaked"
            if redist.isis.route_map is not None:
                cli += f" route-map {redist.isis.route_map}"
            elif redist.isis.rcf is not None:
                cli += f" rcf {redist.isis.rcf}"
            self._add(cli)

        if redist.ospf.enabled is True:
            cli = "redistribute ospf"
            if redist.ospf.include_leaked is True:
                cli += " include leaked"
            if redist.ospf.route_map is not None:
                cli += f" route-map {redist.ospf.route_map}"
            self._add(cli)
        elif redist.ospf.match_internal.enabled is True:
            cli = "redistribute ospf match internal"
            if redist.ospf.match_internal.include_leaked is True:
                cli += " include leaked"
            if redist.ospf.match_internal.route_map is not None:
                cli += f" route-map {redist.ospf.match_internal.route_map}"
            self._add(cli)

        if redist.ospf.match_external.enabled is True:
            cli = "redistribute ospf match external"
            if redist.ospf.match_external.include_leaked is True:
                cli += " include leaked"
            if redist.ospf.match_external.route_map is not None:
                cli += f" route-map {redist.ospf.match_external.route_map}"
            self._add(cli)

        if redist.ospf.match_nssa_external.enabled is True:
            cli = "redistribute ospf match nssa-external"
            if redist.ospf.match_nssa_external.nssa_type is not None:
                cli += f" {redist.ospf.match_nssa_external.nssa_type}"
            if redist.ospf.match_nssa_external.include_leaked is True:
                cli += " include leaked"
            if redist.ospf.match_nssa_external.route_map is not None:
                cli += f" route-map {redist.ospf.match_nssa_external.route_map}"
            self._add(cli)

        if redist.ospfv3.enabled is True:
            cli = "redistribute ospfv3"
            if redist.ospfv3.include_leaked is True:
                cli += " include leaked"
            if redist.ospfv3.route_map is not None:
                cli += f" route-map {redist.ospfv3.route_map}"
            self._add(cli)
        elif redist.ospfv3.match_internal.enabled is True:
            cli = "redistribute ospfv3 match internal"
            if redist.ospfv3.match_internal.include_leaked is True:
                cli += " include leaked"
            if redist.ospfv3.match_internal.route_map is not None:
                cli += f" route-map {redist.ospfv3.match_internal.route_map}"
            self._add(cli)

        if redist.ospfv3.match_external.enabled is True:
            cli = "redistribute ospfv3 match external"
            if redist.ospfv3.match_external.include_leaked is True:
                cli += " include leaked"
            if redist.ospfv3.match_external.route_map is not None:
                cli += f" route-map {redist.ospfv3.match_external.route_map}"
            self._add(cli)

        if redist.ospfv3.match_nssa_external.enabled is True:
            cli = "redistribute ospfv3 match nssa-external"
            if redist.ospfv3.match_nssa_external.nssa_type is not None:
                cli += f" {redist.ospfv3.match_nssa_external.nssa_type}"
            if redist.ospfv3.match_nssa_external.include_leaked is True:
                cli += " include leaked"
            if redist.ospfv3.match_nssa_external.route_map is not None:
                cli += f" route-map {redist.ospfv3.match_nssa_external.route_map}"
            self._add(cli)

        if redist.static.enabled is True:
            cli = "redistribute static"
            if redist.static.include_leaked is True:
                cli += " include leaked"
            if redist.static.route_map is not None:
                cli += f" route-map {redist.static.route_map}"
            elif redist.static.rcf is not None:
                cli += f" rcf {redist.static.rcf}"
            self._add(cli)

        if redist.rip.enabled is True:
            cli = "redistribute rip"
            if redist.rip.route_map is not None:
                cli += f" route-map {redist.rip.route_map}"
            self._add(cli)

        if redist.attached_host.enabled is True:
            cli = "redistribute attached-host"
            if redist.attached_host.route_map is not None:
                cli += f" route-map {redist.attached_host.route_map}"
            self._add(cli)

        if redist.dynamic.enabled is True:
            cli = "redistribute dynamic"
            if redist.dynamic.route_map is not None:
                cli += f" route-map {redist.dynamic.route_map}"
            elif redist.dynamic.rcf is not None:
                cli += f" rcf {redist.dynamic.rcf}"
            self._add(cli)

        if redist.bgp.enabled is True:
            cli = "redistribute bgp leaked"
            if redist.bgp.route_map is not None:
                cli += f" route-map {redist.bgp.route_map}"
            self._add(cli)

        if redist.user.enabled is True:
            cli = "redistribute user"
            if redist.user.rcf is not None:
                cli += f" rcf {redist.user.rcf}"
            self._add(cli)

    def _render_neighbor_interfaces(self, bgp: EosCliConfigGen.RouterBgp) -> None:
        """Render 'neighbor interface' entries sorted by name (J2 lines 674-680)."""
        for ni in natural_sort(bgp.neighbor_interfaces or [], sort_key="name"):
            if ni.peer_group is not None and ni.remote_as is not None:
                self._add(f"neighbor interface {ni.name} peer-group {ni.peer_group} remote-as {ni.remote_as}")
            elif ni.peer_group is not None and ni.peer_filter is not None:
                self._add(f"neighbor interface {ni.name} peer-group {ni.peer_group} peer-filter {ni.peer_filter}")

    def _render_labeled_unicast_rib(self, bgp: EosCliConfigGen.RouterBgp) -> None:
        """Render 'bgp labeled-unicast rib [ip [route-map X]] [tunnel [route-map Y]]' (J2 lines 13-28)."""
        labeled_unicast_rib = bgp.bgp.labeled_unicast.rib
        if labeled_unicast_rib.ip.enabled is not True and labeled_unicast_rib.tunnel.enabled is not True:
            return
        cmd = "bgp labeled-unicast rib"
        if labeled_unicast_rib.ip.enabled is True:
            cmd += " ip"
            if labeled_unicast_rib.ip.route_map is not None:
                cmd += f" route-map {labeled_unicast_rib.ip.route_map}"
        if labeled_unicast_rib.tunnel.enabled is True:
            cmd += " tunnel"
            if labeled_unicast_rib.tunnel.route_map is not None:
                cmd += f" route-map {labeled_unicast_rib.tunnel.route_map}"
        self._add(cmd)

    def _render_bgp_default_flags(self, bgp: EosCliConfigGen.RouterBgp) -> None:
        """Render 'bgp default ipv4-unicast' and 'bgp default ipv4-unicast transport ipv6' flags."""
        if bgp.bgp.default.ipv4_unicast is True:
            self._add("bgp default ipv4-unicast")
        elif bgp.bgp.default.ipv4_unicast is False:
            self._add("no bgp default ipv4-unicast")

        if bgp.bgp.default.ipv4_unicast_transport_ipv6 is True:
            self._add("bgp default ipv4-unicast transport ipv6")
        elif bgp.bgp.default.ipv4_unicast_transport_ipv6 is False:
            self._add("no bgp default ipv4-unicast transport ipv6")

    def _render_timers(self, bgp: EosCliConfigGen.RouterBgp) -> None:
        """Render 'timers bgp keepalive hold [min-hold-time X] [send-failure hold-time Y]'."""
        timers = bgp.timers
        if timers.keepalive_time is None and timers.hold_time is None and timers.min_hold_time is None and timers.send_failure_hold_time is None:
            return
        cmd = "timers bgp"
        if timers.keepalive_time is not None and timers.hold_time is not None:
            cmd += f" {timers.keepalive_time} {timers.hold_time}"
        if timers.min_hold_time is not None:
            cmd += f" min-hold-time {timers.min_hold_time}"
        if timers.send_failure_hold_time is not None:
            cmd += f" send-failure hold-time {timers.send_failure_hold_time}"
        self._add(cmd)

    def _render_distance(self, bgp: EosCliConfigGen.RouterBgp) -> None:
        """Render 'distance bgp external [internal local]'."""
        if bgp.distance.external_routes is None:
            return
        distance_cli = f"distance bgp {bgp.distance.external_routes}"
        if bgp.distance.internal_routes is not None and bgp.distance.local_routes is not None:
            distance_cli += f" {bgp.distance.internal_routes} {bgp.distance.local_routes}"
        self._add(distance_cli)

    def _render_graceful_restart(self, bgp: EosCliConfigGen.RouterBgp) -> None:
        """
        Render graceful-restart timers then the enable command.

        Timers must be configured before the 'graceful-restart' enable command.
        """
        if bgp.graceful_restart.enabled is not True:
            return
        self._add("graceful-restart restart-time {}", bgp.graceful_restart.restart_time)
        self._add("graceful-restart stalepath-time {}", bgp.graceful_restart.stalepath_time)
        self._add("graceful-restart")

    def _render_graceful_restart_helper(self, bgp: EosCliConfigGen.RouterBgp) -> None:
        """Render 'graceful-restart-helper' settings or its negation."""
        if bgp.graceful_restart_helper.enabled is False:
            self._add("no graceful-restart-helper")
        elif bgp.graceful_restart_helper.enabled is True:
            if bgp.graceful_restart_helper.restart_time is not None:
                self._add(f"graceful-restart-helper restart-time {bgp.graceful_restart_helper.restart_time}")
            elif bgp.graceful_restart_helper.long_lived is True:
                self._add("graceful-restart-helper long-lived")

    def _render_route_reflector_preserve(self, bgp: EosCliConfigGen.RouterBgp) -> None:
        """Render 'bgp route-reflector preserve-attributes [always]'."""
        if bgp.bgp.route_reflector_preserve_attributes.enabled is not True:
            return
        cmd = "bgp route-reflector preserve-attributes"
        if bgp.bgp.route_reflector_preserve_attributes.always is True:
            cmd += " always"
        self._add(cmd)

    def _render_maximum_paths_global(self, bgp: EosCliConfigGen.RouterBgp) -> None:
        """Render 'maximum-paths X [ecmp Y]'."""
        if bgp.maximum_paths.paths is None:
            return
        cmd = f"maximum-paths {bgp.maximum_paths.paths}"
        if bgp.maximum_paths.ecmp is not None:
            cmd += f" ecmp {bgp.maximum_paths.ecmp}"
        self._add(cmd)

    def _render_additional_paths(self, bgp: EosCliConfigGen.RouterBgp) -> None:
        """Render 'bgp additional-paths receive' and 'bgp additional-paths send ...'."""
        if bgp.bgp.additional_paths.receive is True:
            self._add("bgp additional-paths receive")
        elif bgp.bgp.additional_paths.receive is False:
            self._add("no bgp additional-paths receive")

        send = bgp.bgp.additional_paths.send
        send_limit = bgp.bgp.additional_paths.send_limit
        if send is None:
            return
        if send == "disabled":
            self._add("no bgp additional-paths send")
        elif send == "ecmp" and send_limit is not None:
            self._add(f"bgp additional-paths send ecmp limit {send_limit}")
        elif send == "limit" and send_limit is not None:
            self._add(f"bgp additional-paths send limit {send_limit}")
        else:
            self._add(f"bgp additional-paths send {send}")

    def _render_listen_ranges(self, bgp: EosCliConfigGen.RouterBgp) -> None:
        """Render 'bgp listen range' entries sorted by peer-group."""
        for listen_range in natural_sort(bgp.listen_ranges or [], sort_key="peer_group"):
            if listen_range.peer_group is None or listen_range.prefix is None:
                continue
            if listen_range.peer_filter is None and listen_range.remote_as is None:
                continue
            cmd = f"bgp listen range {listen_range.prefix}"
            if listen_range.peer_id_include_router_id is True:
                cmd += " peer-id include router-id"
            cmd += f" peer-group {listen_range.peer_group}"
            if listen_range.peer_filter is not None:
                cmd += f" peer-filter {listen_range.peer_filter}"
            elif listen_range.remote_as is not None:
                cmd += f" remote-as {listen_range.remote_as}"
            self._add(cmd)

    def _render_next_hop(
        self,
        entity_id: str,
        next_hop_self: bool | None,
        next_hop_peer: bool | None,
        next_hop_unchanged: bool | None = None,
    ) -> None:
        """Render next-hop-self, next-hop-peer, and (peer-groups only) next-hop-unchanged."""
        if next_hop_self is True:
            self._add(f"neighbor {entity_id} next-hop-self")
        if next_hop_peer is True:
            self._add(f"neighbor {entity_id} next-hop-peer")
        if next_hop_unchanged is True:
            self._add(f"neighbor {entity_id} next-hop-unchanged")

    def _render_as_path(self, entity_id: str, as_path: Any) -> None:
        """Render 'as-path prepend-own disabled' and 'as-path remote-as replace out'."""
        if as_path.prepend_own_disabled is True:
            self._add(f"neighbor {entity_id} as-path prepend-own disabled")
        if as_path.remote_as_replace_out is True:
            self._add(f"neighbor {entity_id} as-path remote-as replace out")

    def _render_bfd(self, entity_id: str, bfd: bool | None, bfd_timers: Any, *, allow_negation: bool = False) -> None:
        """
        Render BFD configuration for a neighbor or peer-group.

        When allow_negation=True (neighbors only), 'no neighbor X bfd' is rendered
        when bfd is explicitly False, to override a peer-group's bfd=True.
        """
        if bfd is True:
            self._add(f"neighbor {entity_id} bfd")
            self._add("neighbor {} bfd interval {} min-rx {} multiplier {}", entity_id, bfd_timers.interval, bfd_timers.min_rx, bfd_timers.multiplier)
        elif bfd is False and allow_negation:
            self._add(f"no neighbor {entity_id} bfd")

    def _render_route_maps(self, entity_id: str, route_map_in: str | None, route_map_out: str | None) -> None:
        """Render inbound and outbound route-map assignments."""
        self._add("neighbor {} route-map {} in", entity_id, route_map_in)
        self._add("neighbor {} route-map {} out", entity_id, route_map_out)

    def _render_password_key(self, entity_id: str, password: str | None, password_type: str | None) -> None:
        """Render 'neighbor X password [type] key' (type defaults to 7)."""
        if password is None:
            return
        pw_type = password_type if password_type is not None else "7"
        hashed_password = hide_passwords(password, self.data.eos_cli_config_gen_configuration.hide_passwords)
        self._add(f"neighbor {entity_id} password {pw_type} {hashed_password}")

    def _render_shared_secret(self, entity_id: str, shared_secret: Any) -> None:
        """Render 'neighbor X password shared-secret profile P algorithm A'."""
        if shared_secret.profile is None or shared_secret.hash_algorithm is None:
            return
        self._add(f"neighbor {entity_id} password shared-secret profile {shared_secret.profile} algorithm {shared_secret.hash_algorithm}")

    def _render_peer_tags(self, entity_id: str, peer_tag_in: str | None, peer_tag_out_discard: str | None) -> None:
        """Render 'peer-tag in' and 'peer-tag out discard'."""
        self._add("neighbor {} peer-tag in {}", entity_id, peer_tag_in)
        self._add("neighbor {} peer-tag out discard {}", entity_id, peer_tag_out_discard)

    def _render_remove_private_as(self, entity_id: str, remove_private_as: Any) -> None:
        """Render 'remove-private-as [all [replace-as]]' or its negation."""
        if remove_private_as.enabled is True:
            cmd = f"neighbor {entity_id} remove-private-as"
            if remove_private_as.all is True:
                cmd += " all"
                if remove_private_as.replace_as is True:
                    cmd += " replace-as"
            self._add(cmd)
        elif remove_private_as.enabled is False:
            self._add(f"no neighbor {entity_id} remove-private-as")

    def _render_remove_private_as_ingress(self, entity_id: str, remove_private_as_ingress: Any) -> None:
        """Render 'remove-private-as ingress [replace-as]' or its negation."""
        if remove_private_as_ingress.enabled is True:
            cmd = f"neighbor {entity_id} remove-private-as ingress"
            if remove_private_as_ingress.replace_as is True:
                cmd += " replace-as"
            self._add(cmd)
        elif remove_private_as_ingress.enabled is False:
            self._add(f"no neighbor {entity_id} remove-private-as ingress")

    def _render_allowas_in(self, entity_id: str, allowas_in: Any) -> None:
        """Render 'allowas-in [N]'."""
        if allowas_in.enabled is not True:
            return
        cmd = f"neighbor {entity_id} allowas-in"
        if allowas_in.times is not None:
            cmd += f" {allowas_in.times}"
        self._add(cmd)

    def _render_rib_in_pre_policy_retain(self, entity_id: str, rib_in: Any) -> None:
        """Render 'rib-in pre-policy retain [all]' or its negation."""
        if rib_in.enabled is True:
            cmd = f"neighbor {entity_id} rib-in pre-policy retain"
            if rib_in.all is True:
                cmd += " all"
            self._add(cmd)
        elif rib_in.enabled is False:
            self._add(f"no neighbor {entity_id} rib-in pre-policy retain")

    def _render_default_originate(self, entity_id: str, default_originate: Any) -> None:
        """Render 'default-originate [route-map X] [always]'."""
        if default_originate.enabled is not True:
            return
        cmd = f"neighbor {entity_id} default-originate"
        if default_originate.route_map is not None:
            cmd += f" route-map {default_originate.route_map}"
        if default_originate.always is True:
            cmd += " always"
        self._add(cmd)

    def _render_send_community(self, entity_id: str, send_community: str | None) -> None:
        """Render 'send-community [extended|large|...]' ('all' omits the keyword)."""
        if send_community == "all":
            self._add(f"neighbor {entity_id} send-community")
        elif send_community is not None:
            self._add(f"neighbor {entity_id} send-community {send_community}")

    def _render_maximum_routes(
        self,
        entity_id: str,
        maximum_routes: int | None,
        warning_limit: int | str | None,
        warning_only: bool | None,
    ) -> None:
        """Render 'maximum-routes N [warning-limit M] [warning-only]'."""
        if maximum_routes is None:
            return
        cmd = f"neighbor {entity_id} maximum-routes {maximum_routes}"
        if warning_limit is not None:
            cmd += f" warning-limit {warning_limit}"
        if warning_only is True:
            cmd += " warning-only"
        self._add(cmd)

    def _render_missing_policy(self, entity_id: str, missing_policy: Any) -> None:
        """Render 'missing-policy address-family all [include ...] direction {in|out} action X'."""
        for direction in ("in", "out"):
            policy = getattr(missing_policy, f"direction_{direction}", None)
            if policy is None or policy.action is None:
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
            self._add(cmd)

    def _render_link_bandwidth(self, entity_id: str, link_bandwidth: Any) -> None:
        """Render 'link-bandwidth [default X]'."""
        if link_bandwidth.enabled is not True:
            return
        cmd = f"neighbor {entity_id} link-bandwidth"
        if link_bandwidth.default is not None:
            cmd += f" default {link_bandwidth.default}"
        self._add(cmd)


class RouterBgpVrf(CliSection):
    """Renders a single 'vrf X' block inside 'router bgp'."""

    def __init__(self, vrf: Any, data: EosCliConfigGen) -> None:
        self.vrf = vrf
        self.data = data

    def _generate(self) -> None:
        vrf = self.vrf
        self._header(f"vrf {vrf.name}")

        self._add("rd {}", vrf.rd)
        self._add("rd evpn domain {} {}", vrf.rd_evpn_domain.domain, vrf.rd_evpn_domain.rd)

        for export in natural_sort(vrf.default_route_exports or [], sort_key="address_family"):
            cli = f"default-route export {export.address_family}"
            if export.always is True:
                cli += " always"
            if export.rcf is not None:
                cli += f" rcf {export.rcf}"
            elif export.route_map is not None:
                cli += f" route-map {export.route_map}"
            self._add(cli)

        for address_family_entry in vrf.route_targets.field_import or []:
            for rt in address_family_entry.route_targets or []:
                self._add(f"route-target import {address_family_entry.address_family} {rt}")
            if address_family_entry.address_family in ["evpn", "vpn-ipv4", "vpn-ipv6"]:
                if address_family_entry.rcf is not None:
                    if address_family_entry.vpn_route_filter_rcf is not None and address_family_entry.address_family in ["vpn-ipv4", "vpn-ipv6"]:
                        self._add(f"route-target import {address_family_entry.address_family} rcf {address_family_entry.rcf} vpn-route filter-rcf {address_family_entry.vpn_route_filter_rcf}")
                    else:
                        self._add(f"route-target import {address_family_entry.address_family} rcf {address_family_entry.rcf}")
                self._add("route-target import {} route-map {}", address_family_entry.address_family, address_family_entry.route_map)

        for rt in natural_sort([r for r in vrf.route_targets.import_evpn_domains or [] if r.domain == "all"], sort_key="route_target"):
            self._add(f"route-target import evpn domain {rt.domain} {rt.route_target}")
        for rt in natural_sort([r for r in vrf.route_targets.import_evpn_domains or [] if r.domain == "remote"], sort_key="route_target"):
            self._add(f"route-target import evpn domain {rt.domain} {rt.route_target}")

        for address_family_entry in vrf.route_targets.export or []:
            for rt in address_family_entry.route_targets or []:
                self._add(f"route-target export {address_family_entry.address_family} {rt}")
            if address_family_entry.address_family in ["evpn", "vpn-ipv4", "vpn-ipv6"]:
                if address_family_entry.rcf is not None:
                    if address_family_entry.vrf_route_filter_rcf is not None and address_family_entry.address_family in ["vpn-ipv4", "vpn-ipv6"]:
                        self._add(f"route-target export {address_family_entry.address_family} rcf {address_family_entry.rcf} vrf-route filter-rcf {address_family_entry.vrf_route_filter_rcf}")
                    else:
                        self._add(f"route-target export {address_family_entry.address_family} rcf {address_family_entry.rcf}")
                self._add("route-target export {} route-map {}", address_family_entry.address_family, address_family_entry.route_map)

        for rt in natural_sort([r for r in vrf.route_targets.export_evpn_domains or [] if r.domain == "all"], sort_key="route_target"):
            self._add(f"route-target export evpn domain {rt.domain} {rt.route_target}")
        for rt in natural_sort([r for r in vrf.route_targets.export_evpn_domains or [] if r.domain == "remote"], sort_key="route_target"):
            self._add(f"route-target export evpn domain {rt.domain} {rt.route_target}")

        self._add("router-id {}", vrf.router_id)
        self._add("update wait-for-convergence", vrf.updates.wait_for_convergence)
        self._add("update wait-install", vrf.updates.wait_install)
        self._add("timers bgp {}", vrf.timers)

        if vrf.graceful_restart.enabled is True:
            self._add("graceful-restart restart-time {}", vrf.graceful_restart.restart_time)
            self._add("graceful-restart stalepath-time {}", vrf.graceful_restart.stalepath_time)
            self._add("graceful-restart")

        if vrf.maximum_paths.paths is not None:
            cli = f"maximum-paths {vrf.maximum_paths.paths}"
            if vrf.maximum_paths.ecmp is not None:
                cli += f" ecmp {vrf.maximum_paths.ecmp}"
            self._add(cli)

        if vrf.bgp.additional_paths.install is True:
            self._add("bgp additional-paths install")
        elif vrf.bgp.additional_paths.install_ecmp_primary is True:
            self._add("bgp additional-paths install ecmp-primary")
        self._add("bgp additional-paths receive", vrf.bgp.additional_paths.receive)
        self._render_bgp_additional_paths_send(vrf.bgp.additional_paths)

        for listen_range in natural_sort(vrf.listen_ranges or [], sort_key="peer_group"):
            if listen_range.peer_group is None or listen_range.prefix is None:
                continue
            if listen_range.peer_filter is None and listen_range.remote_as is None:
                continue
            cli = f"bgp listen range {listen_range.prefix}"
            if listen_range.peer_id_include_router_id is True:
                cli += " peer-id include router-id"
            cli += f" peer-group {listen_range.peer_group}"
            if listen_range.peer_filter is not None:
                cli += f" peer-filter {listen_range.peer_filter}"
            elif listen_range.remote_as is not None:
                cli += f" remote-as {listen_range.remote_as}"
            self._add(cli)

        for neighbor in natural_sort(vrf.neighbors or [], sort_key="ip_address"):
            self._render_neighbor(neighbor)

        for network in natural_sort(vrf.networks or [], sort_key="prefix"):
            cli = f"network {network.prefix}"
            if network.route_map is not None:
                cli += f" route-map {network.route_map}"
            self._add(cli)

        if vrf.bgp.redistribute_internal is True:
            self._add("bgp redistribute-internal")
        elif vrf.bgp.redistribute_internal is False:
            self._add("no bgp redistribute-internal")

        for agg in natural_sort(vrf.aggregate_addresses or [], sort_key="prefix"):
            cli = f"aggregate-address {agg.prefix}"
            if agg.as_set is True:
                cli += " as-set"
            if agg.summary_only is True:
                cli += " summary-only"
            if agg.attribute_map is not None:
                cli += f" attribute-map {agg.attribute_map}"
            if agg.attribute.rcf is not None:
                cli += f" attribute rcf {agg.attribute.rcf}"
            if agg.match_map is not None:
                cli += f" match-map {agg.match_map}"
            if agg.advertise_only is True:
                cli += " advertise-only"
            self._add(cli)

        if vrf.redistribute:
            self._render_redistribute(vrf.redistribute)

        for ni in natural_sort(vrf.neighbor_interfaces or [], sort_key="name"):
            if ni.peer_group is not None and ni.remote_as is not None:
                self._add(f"neighbor interface {ni.name} peer-group {ni.peer_group} remote-as {ni.remote_as}")
            elif ni.peer_group is not None and ni.peer_filter is not None:
                self._add(f"neighbor interface {ni.name} peer-group {ni.peer_group} peer-filter {ni.peer_filter}")

        self._sub(RouterBgpVrfAddressFamilyFlowSpec(vrf.address_family_flow_spec_ipv4, "ipv4"))
        self._sub(RouterBgpVrfAddressFamilyFlowSpec(vrf.address_family_flow_spec_ipv6, "ipv6"))
        self._sub(RouterBgpVrfAddressFamilyIpv4(vrf))
        self._sub(RouterBgpVrfAddressFamilyIpv4Multicast(vrf))
        self._sub(RouterBgpVrfAddressFamilyIpv6(vrf))
        self._sub(RouterBgpVrfAddressFamilyIpv6Multicast(vrf))
        self._sub(RouterBgpVrfEvpnMulticast(vrf))

        if vrf.eos_cli is not None:
            self._add("!")
            for line in vrf.eos_cli.splitlines():
                self._add(line)
            if vrf.eos_cli.endswith("\n"):
                self._output_lines.append("")

    def _render_neighbor(self, neighbor: Any) -> None:
        neighbor_ip_address = neighbor.ip_address

        self._add("neighbor {} peer group {}", neighbor_ip_address, neighbor.peer_group)
        self._add("neighbor {} remote-as {}", neighbor_ip_address, neighbor.remote_as)
        if neighbor.next_hop_self is True:
            self._add(f"neighbor {neighbor_ip_address} next-hop-self")
        if neighbor.next_hop_peer is True:
            self._add(f"neighbor {neighbor_ip_address} next-hop-peer")
        if neighbor.shutdown is True:
            self._add(f"neighbor {neighbor_ip_address} shutdown")

        if neighbor.remove_private_as.enabled is True:
            cli = f"neighbor {neighbor_ip_address} remove-private-as"
            if neighbor.remove_private_as.all is True:
                cli += " all"
                if neighbor.remove_private_as.replace_as is True:
                    cli += " replace-as"
            self._add(cli)
        elif neighbor.remove_private_as.enabled is False:
            self._add(f"no neighbor {neighbor_ip_address} remove-private-as")

        if neighbor.as_path.prepend_own_disabled is True:
            self._add(f"neighbor {neighbor_ip_address} as-path prepend-own disabled")
        if neighbor.as_path.remote_as_replace_out is True:
            self._add(f"neighbor {neighbor_ip_address} as-path remote-as replace out")
        self._add("neighbor {} local-as {} no-prepend replace-as", neighbor_ip_address, neighbor.local_as)
        self._add("neighbor {} weight {}", neighbor_ip_address, neighbor.weight)
        if neighbor.passive is True:
            self._add(f"neighbor {neighbor_ip_address} passive")
        self._add("neighbor {} update-source {}", neighbor_ip_address, neighbor.update_source)

        if neighbor.bfd is True:
            self._add(f"neighbor {neighbor_ip_address} bfd")
            bfd_timers = neighbor.bfd_timers
            self._add("neighbor {} bfd interval {} min-rx {} multiplier {}", neighbor_ip_address, bfd_timers.interval, bfd_timers.min_rx, bfd_timers.multiplier)
        elif neighbor.bfd is False and neighbor.peer_group is not None:
            self._add(f"no neighbor {neighbor_ip_address} bfd")

        self._add("neighbor {} description {}", neighbor_ip_address, neighbor.description)

        if neighbor.allowas_in.enabled is True:
            cli = f"neighbor {neighbor_ip_address} allowas-in"
            if neighbor.allowas_in.times is not None:
                cli += f" {neighbor.allowas_in.times}"
            self._add(cli)

        if neighbor.rib_in_pre_policy_retain.enabled is True:
            cli = f"neighbor {neighbor_ip_address} rib-in pre-policy retain"
            if neighbor.rib_in_pre_policy_retain.all is True:
                cli += " all"
            self._add(cli)
        elif neighbor.rib_in_pre_policy_retain.enabled is False:
            self._add(f"no neighbor {neighbor_ip_address} rib-in pre-policy retain")

        self._add("neighbor {} ebgp-multihop {}", neighbor_ip_address, neighbor.ebgp_multihop)

        if neighbor.route_reflector_client is True:
            self._add(f"neighbor {neighbor_ip_address} route-reflector-client")
        elif neighbor.route_reflector_client is False:
            self._add(f"no neighbor {neighbor_ip_address} route-reflector-client")

        self._add("neighbor {} timers {}", neighbor_ip_address, neighbor.timers)
        self._add("neighbor {} route-map {} in", neighbor_ip_address, neighbor.route_map_in)

        if neighbor.additional_paths.receive is True:
            self._add(f"neighbor {neighbor_ip_address} additional-paths receive")
        self._render_neighbor_additional_paths_send(neighbor_ip_address, neighbor.additional_paths)

        self._add("neighbor {} route-map {} out", neighbor_ip_address, neighbor.route_map_out)

        if neighbor.password is not None:
            hashed_password = hide_passwords(neighbor.password, self.data.eos_cli_config_gen_configuration.hide_passwords)
            pw_type = neighbor.password_type if neighbor.password_type is not None else "7"
            self._add(f"neighbor {neighbor_ip_address} password {pw_type} {hashed_password}")

        default_originate = neighbor.default_originate
        if default_originate:
            cli = f"neighbor {neighbor_ip_address} default-originate"
            if default_originate.route_map is not None:
                cli += f" route-map {default_originate.route_map}"
            if default_originate.always is True:
                cli += " always"
            self._add(cli)

        if neighbor.send_community == "all":
            self._add(f"neighbor {neighbor_ip_address} send-community")
        elif neighbor.send_community is not None:
            self._add(f"neighbor {neighbor_ip_address} send-community {neighbor.send_community}")

        if neighbor.maximum_routes is not None:
            cli = f"neighbor {neighbor_ip_address} maximum-routes {neighbor.maximum_routes}"
            if neighbor.maximum_routes_warning_limit is not None:
                cli += f" warning-limit {neighbor.maximum_routes_warning_limit}"
            if neighbor.maximum_routes_warning_only is True:
                cli += " warning-only"
            self._add(cli)

        self._add("neighbor {} peer-tag in {}", neighbor_ip_address, neighbor.peer_tag_in)
        self._add("neighbor {} peer-tag out discard {}", neighbor_ip_address, neighbor.peer_tag_out_discard)

        if neighbor.remove_private_as_ingress.enabled is True:
            cli = f"neighbor {neighbor_ip_address} remove-private-as ingress"
            if neighbor.remove_private_as_ingress.replace_as is True:
                cli += " replace-as"
            self._add(cli)
        elif neighbor.remove_private_as_ingress.enabled is False:
            self._add(f"no neighbor {neighbor_ip_address} remove-private-as ingress")

    def _render_neighbor_additional_paths_send(self, ip: str, additional_paths: Any) -> None:
        send = additional_paths.send
        send_limit = additional_paths.send_limit
        if send is None:
            return
        if send == "disabled":
            self._add(f"no neighbor {ip} additional-paths send")
        elif send == "ecmp" and send_limit is not None:
            self._add(f"neighbor {ip} additional-paths send ecmp limit {send_limit}")
        elif send == "limit":
            self._add("neighbor {} additional-paths send limit {}", ip, send_limit)
        else:
            self._add(f"neighbor {ip} additional-paths send {send}")

    def _render_bgp_additional_paths_send(self, additional_paths: Any) -> None:
        send = additional_paths.send
        send_limit = additional_paths.send_limit
        if send is None:
            return
        if send == "disabled":
            self._add("no bgp additional-paths send")
        elif send == "ecmp" and send_limit is not None:
            self._add(f"bgp additional-paths send ecmp limit {send_limit}")
        elif send == "limit" and send_limit is not None:
            self._add(f"bgp additional-paths send limit {send_limit}")
        else:
            self._add(f"bgp additional-paths send {send}")

    def _render_redistribute(self, redistribute: Any) -> None:
        if redistribute.connected.enabled is True:
            cli = "redistribute connected"
            if redistribute.connected.include_leaked is True:
                cli += " include leaked"
            if redistribute.connected.route_map is not None:
                cli += f" route-map {redistribute.connected.route_map}"
            elif redistribute.connected.rcf is not None:
                cli += f" rcf {redistribute.connected.rcf}"
            self._add(cli)

        if redistribute.isis.enabled is True:
            cli = "redistribute isis"
            if redistribute.isis.isis_level is not None:
                cli += f" {redistribute.isis.isis_level}"
            if redistribute.isis.include_leaked is True:
                cli += " include leaked"
            if redistribute.isis.route_map is not None:
                cli += f" route-map {redistribute.isis.route_map}"
            elif redistribute.isis.rcf is not None:
                cli += f" rcf {redistribute.isis.rcf}"
            self._add(cli)

        if redistribute.ospf.enabled is True:
            cli = "redistribute ospf"
            if redistribute.ospf.include_leaked is True:
                cli += " include leaked"
            if redistribute.ospf.route_map is not None:
                cli += f" route-map {redistribute.ospf.route_map}"
            self._add(cli)
        elif redistribute.ospf.match_internal.enabled is True:
            cli = "redistribute ospf match internal"
            if redistribute.ospf.match_internal.include_leaked is True:
                cli += " include leaked"
            if redistribute.ospf.match_internal.route_map is not None:
                cli += f" route-map {redistribute.ospf.match_internal.route_map}"
            self._add(cli)

        if redistribute.ospf.match_external.enabled is True:
            cli = "redistribute ospf match external"
            if redistribute.ospf.match_external.include_leaked is True:
                cli += " include leaked"
            if redistribute.ospf.match_external.route_map is not None:
                cli += f" route-map {redistribute.ospf.match_external.route_map}"
            self._add(cli)

        if redistribute.ospf.match_nssa_external.enabled is True:
            cli = "redistribute ospf match nssa-external"
            if redistribute.ospf.match_nssa_external.nssa_type is not None:
                cli += f" {redistribute.ospf.match_nssa_external.nssa_type}"
            if redistribute.ospf.match_nssa_external.include_leaked is True:
                cli += " include leaked"
            if redistribute.ospf.match_nssa_external.route_map is not None:
                cli += f" route-map {redistribute.ospf.match_nssa_external.route_map}"
            self._add(cli)

        if redistribute.ospfv3.enabled is True:
            cli = "redistribute ospfv3"
            if redistribute.ospfv3.include_leaked is True:
                cli += " include leaked"
            if redistribute.ospfv3.route_map is not None:
                cli += f" route-map {redistribute.ospfv3.route_map}"
            self._add(cli)
        elif redistribute.ospfv3.match_internal.enabled is True:
            cli = "redistribute ospfv3 match internal"
            if redistribute.ospfv3.match_internal.include_leaked is True:
                cli += " include leaked"
            if redistribute.ospfv3.match_internal.route_map is not None:
                cli += f" route-map {redistribute.ospfv3.match_internal.route_map}"
            self._add(cli)

        if redistribute.ospfv3.match_external.enabled is True:
            cli = "redistribute ospfv3 match external"
            if redistribute.ospfv3.match_external.include_leaked is True:
                cli += " include leaked"
            if redistribute.ospfv3.match_external.route_map is not None:
                cli += f" route-map {redistribute.ospfv3.match_external.route_map}"
            self._add(cli)

        if redistribute.ospfv3.match_nssa_external.enabled is True:
            cli = "redistribute ospfv3 match nssa-external"
            if redistribute.ospfv3.match_nssa_external.nssa_type is not None:
                cli += f" {redistribute.ospfv3.match_nssa_external.nssa_type}"
            if redistribute.ospfv3.match_nssa_external.include_leaked is True:
                cli += " include leaked"
            if redistribute.ospfv3.match_nssa_external.route_map is not None:
                cli += f" route-map {redistribute.ospfv3.match_nssa_external.route_map}"
            self._add(cli)

        if redistribute.static.enabled is True:
            cli = "redistribute static"
            if redistribute.static.include_leaked is True:
                cli += " include leaked"
            if redistribute.static.route_map is not None:
                cli += f" route-map {redistribute.static.route_map}"
            elif redistribute.static.rcf is not None:
                cli += f" rcf {redistribute.static.rcf}"
            self._add(cli)

        if redistribute.rip.enabled is True:
            cli = "redistribute rip"
            if redistribute.rip.route_map is not None:
                cli += f" route-map {redistribute.rip.route_map}"
            self._add(cli)

        if redistribute.attached_host.enabled is True:
            cli = "redistribute attached-host"
            if redistribute.attached_host.route_map is not None:
                cli += f" route-map {redistribute.attached_host.route_map}"
            self._add(cli)

        if redistribute.dynamic.enabled is True:
            cli = "redistribute dynamic"
            if redistribute.dynamic.route_map is not None:
                cli += f" route-map {redistribute.dynamic.route_map}"
            elif redistribute.dynamic.rcf is not None:
                cli += f" rcf {redistribute.dynamic.rcf}"
            self._add(cli)

        if redistribute.bgp.enabled is True:
            cli = "redistribute bgp leaked"
            if redistribute.bgp.route_map is not None:
                cli += f" route-map {redistribute.bgp.route_map}"
            self._add(cli)

        if redistribute.user.enabled is True:
            cli = "redistribute user"
            if redistribute.user.rcf is not None:
                cli += f" rcf {redistribute.user.rcf}"
            self._add(cli)


class RouterBgpVrfAddressFamilyFlowSpec(CliSection):
    """Renders 'address-family flow-spec {ipv4|ipv6}' inside a VRF block."""

    def __init__(self, address_family: Any, protocol: str) -> None:
        self.address_family = address_family
        self.protocol = protocol

    def _generate(self) -> None:
        if not self.address_family:
            return
        self._header(f"address-family flow-spec {self.protocol}")
        address_family = self.address_family
        self._add("bgp missing-policy direction in action {}", address_family.bgp.missing_policy.direction_in_action)
        self._add("bgp missing-policy direction out action {}", address_family.bgp.missing_policy.direction_out_action)
        for neighbor in natural_sort(address_family.neighbors or [], sort_key="ip_address"):
            if neighbor.activate is True:
                self._add(f"neighbor {neighbor.ip_address} activate")


class RouterBgpVrfAddressFamilyIpv4(CliSection):
    """Renders 'address-family ipv4' inside a VRF block."""

    def __init__(self, vrf: Any) -> None:
        self.vrf = vrf

    def _generate(self) -> None:
        address_family = self.vrf.address_family_ipv4
        if not address_family:
            return
        self._header("address-family ipv4")

        if address_family.bgp.additional_paths.install is True:
            self._add("bgp additional-paths install")
        elif address_family.bgp.additional_paths.install_ecmp_primary is True:
            self._add("bgp additional-paths install ecmp-primary")

        self._add("bgp missing-policy direction in action {}", address_family.bgp.missing_policy.direction_in_action)
        self._add("bgp missing-policy direction out action {}", address_family.bgp.missing_policy.direction_out_action)
        self._add("bgp additional-paths receive", address_family.bgp.additional_paths.receive)
        self._render_bgp_additional_paths_send(address_family.bgp.additional_paths)

        for neighbor in natural_sort(address_family.neighbors or [], sort_key="ip_address"):
            self._render_neighbor(neighbor)

        for network in natural_sort(address_family.networks or [], sort_key="prefix"):
            cli = f"network {network.prefix}"
            if network.route_map is not None:
                cli += f" route-map {network.route_map}"
            elif network.rcf is not None:
                cli += f" rcf {network.rcf}"
            self._add(cli)

        if address_family.bgp.redistribute_internal is True:
            self._add("bgp redistribute-internal")
        elif address_family.bgp.redistribute_internal is False:
            self._add("no bgp redistribute-internal")

        if address_family.redistribute:
            self._render_redistribute(address_family.redistribute)

    def _render_neighbor(self, neighbor: Any) -> None:
        neighbor_ip_address = neighbor.ip_address
        if neighbor.activate is True:
            self._add(f"neighbor {neighbor_ip_address} activate")
        if neighbor.additional_paths.receive is True:
            self._add(f"neighbor {neighbor_ip_address} additional-paths receive")
        self._add("neighbor {} route-map {} in", neighbor_ip_address, neighbor.route_map_in)
        self._add("neighbor {} route-map {} out", neighbor_ip_address, neighbor.route_map_out)
        self._add("neighbor {} rcf in {}", neighbor_ip_address, neighbor.rcf_in)
        self._add("neighbor {} rcf out {}", neighbor_ip_address, neighbor.rcf_out)
        self._add("neighbor {} prefix-list {} in", neighbor_ip_address, neighbor.prefix_list_in)
        self._add("neighbor {} prefix-list {} out", neighbor_ip_address, neighbor.prefix_list_out)
        self._render_neighbor_additional_paths_send(neighbor_ip_address, neighbor.additional_paths)
        next_hop_ipv6 = neighbor.next_hop.address_family_ipv6
        if next_hop_ipv6.enabled is not None:
            if next_hop_ipv6.enabled:
                cli = f"neighbor {neighbor_ip_address} next-hop address-family ipv6"
                if next_hop_ipv6.originate is True:
                    cli += " originate"
                self._add(cli)
            else:
                self._add(f"no neighbor {neighbor_ip_address} next-hop address-family ipv6")
        self._add("neighbor {} peer-tag in {}", neighbor_ip_address, neighbor.peer_tag_in)
        self._add("neighbor {} peer-tag out discard {}", neighbor_ip_address, neighbor.peer_tag_out_discard)

    def _render_bgp_additional_paths_send(self, additional_paths: Any) -> None:
        send = additional_paths.send
        send_limit = additional_paths.send_limit
        if send is None:
            return
        if send == "disabled":
            self._add("no bgp additional-paths send")
        elif send == "ecmp" and send_limit is not None:
            self._add(f"bgp additional-paths send ecmp limit {send_limit}")
        elif send == "limit" and send_limit is not None:
            self._add(f"bgp additional-paths send limit {send_limit}")
        else:
            self._add(f"bgp additional-paths send {send}")

    def _render_neighbor_additional_paths_send(self, ip: str, additional_paths: Any) -> None:
        send = additional_paths.send
        send_limit = additional_paths.send_limit
        if send is None:
            return
        if send == "disabled":
            self._add(f"no neighbor {ip} additional-paths send")
        elif send == "ecmp" and send_limit is not None:
            self._add(f"neighbor {ip} additional-paths send ecmp limit {send_limit}")
        elif send == "limit" and send_limit is not None:
            self._add(f"neighbor {ip} additional-paths send limit {send_limit}")
        else:
            self._add(f"neighbor {ip} additional-paths send {send}")

    def _render_redistribute(self, redistribute: Any) -> None:
        if redistribute.attached_host.enabled is True:
            cli = "redistribute attached-host"
            if redistribute.attached_host.route_map is not None:
                cli += f" route-map {redistribute.attached_host.route_map}"
            self._add(cli)

        if redistribute.bgp.enabled is True:
            cli = "redistribute bgp leaked"
            if redistribute.bgp.route_map is not None:
                cli += f" route-map {redistribute.bgp.route_map}"
            self._add(cli)

        if redistribute.connected.enabled is True:
            cli = "redistribute connected"
            if redistribute.connected.include_leaked is True:
                cli += " include leaked"
            if redistribute.connected.route_map is not None:
                cli += f" route-map {redistribute.connected.route_map}"
            elif redistribute.connected.rcf is not None:
                cli += f" rcf {redistribute.connected.rcf}"
            self._add(cli)

        if redistribute.dynamic.enabled is True:
            cli = "redistribute dynamic"
            if redistribute.dynamic.route_map is not None:
                cli += f" route-map {redistribute.dynamic.route_map}"
            elif redistribute.dynamic.rcf is not None:
                cli += f" rcf {redistribute.dynamic.rcf}"
            self._add(cli)

        if redistribute.user.enabled is True:
            cli = "redistribute user"
            if redistribute.user.rcf is not None:
                cli += f" rcf {redistribute.user.rcf}"
            self._add(cli)

        if redistribute.isis.enabled is True:
            cli = "redistribute isis"
            if redistribute.isis.isis_level is not None:
                cli += f" {redistribute.isis.isis_level}"
            if redistribute.isis.include_leaked is True:
                cli += " include leaked"
            if redistribute.isis.route_map is not None:
                cli += f" route-map {redistribute.isis.route_map}"
            elif redistribute.isis.rcf is not None:
                cli += f" rcf {redistribute.isis.rcf}"
            self._add(cli)

        if redistribute.ospf.enabled is True:
            cli = "redistribute ospf"
            if redistribute.ospf.include_leaked is True:
                cli += " include leaked"
            if redistribute.ospf.route_map is not None:
                cli += f" route-map {redistribute.ospf.route_map}"
            self._add(cli)
        elif redistribute.ospf.match_internal.enabled is True:
            cli = "redistribute ospf match internal"
            if redistribute.ospf.match_internal.include_leaked is True:
                cli += " include leaked"
            if redistribute.ospf.match_internal.route_map is not None:
                cli += f" route-map {redistribute.ospf.match_internal.route_map}"
            self._add(cli)

        if redistribute.ospfv3.enabled is True:
            cli = "redistribute ospfv3"
            if redistribute.ospfv3.include_leaked is True:
                cli += " include leaked"
            if redistribute.ospfv3.route_map is not None:
                cli += f" route-map {redistribute.ospfv3.route_map}"
            self._add(cli)
        elif redistribute.ospfv3.match_internal.enabled is True:
            cli = "redistribute ospfv3 match internal"
            if redistribute.ospfv3.match_internal.include_leaked is True:
                cli += " include leaked"
            if redistribute.ospfv3.match_internal.route_map is not None:
                cli += f" route-map {redistribute.ospfv3.match_internal.route_map}"
            self._add(cli)

        if redistribute.ospfv3.match_external.enabled is True:
            cli = "redistribute ospfv3 match external"
            if redistribute.ospfv3.match_external.include_leaked is True:
                cli += " include leaked"
            if redistribute.ospfv3.match_external.route_map is not None:
                cli += f" route-map {redistribute.ospfv3.match_external.route_map}"
            self._add(cli)

        if redistribute.ospfv3.match_nssa_external.enabled is True:
            cli = "redistribute ospfv3 match nssa-external"
            if redistribute.ospfv3.match_nssa_external.nssa_type is not None:
                cli += f" {redistribute.ospfv3.match_nssa_external.nssa_type}"
            if redistribute.ospfv3.match_nssa_external.include_leaked is True:
                cli += " include leaked"
            if redistribute.ospfv3.match_nssa_external.route_map is not None:
                cli += f" route-map {redistribute.ospfv3.match_nssa_external.route_map}"
            self._add(cli)

        if redistribute.ospf.match_external.enabled is True:
            cli = "redistribute ospf match external"
            if redistribute.ospf.match_external.include_leaked is True:
                cli += " include leaked"
            if redistribute.ospf.match_external.route_map is not None:
                cli += f" route-map {redistribute.ospf.match_external.route_map}"
            self._add(cli)

        if redistribute.ospf.match_nssa_external.enabled is True:
            cli = "redistribute ospf match nssa-external"
            if redistribute.ospf.match_nssa_external.nssa_type is not None:
                cli += f" {redistribute.ospf.match_nssa_external.nssa_type}"
            if redistribute.ospf.match_nssa_external.include_leaked is True:
                cli += " include leaked"
            if redistribute.ospf.match_nssa_external.route_map is not None:
                cli += f" route-map {redistribute.ospf.match_nssa_external.route_map}"
            self._add(cli)

        if redistribute.rip.enabled is True:
            cli = "redistribute rip"
            if redistribute.rip.route_map is not None:
                cli += f" route-map {redistribute.rip.route_map}"
            self._add(cli)

        if redistribute.static.enabled is True:
            cli = "redistribute static"
            if redistribute.static.include_leaked is True:
                cli += " include leaked"
            if redistribute.static.route_map is not None:
                cli += f" route-map {redistribute.static.route_map}"
            elif redistribute.static.rcf is not None:
                cli += f" rcf {redistribute.static.rcf}"
            self._add(cli)


class RouterBgpVrfAddressFamilyIpv4Multicast(CliSection):
    """Renders 'address-family ipv4 multicast' inside a VRF block."""

    def __init__(self, vrf: Any) -> None:
        self.vrf = vrf

    def _generate(self) -> None:
        address_family = self.vrf.address_family_ipv4_multicast
        if not address_family:
            return
        self._header("address-family ipv4 multicast")

        self._add("bgp missing-policy direction in action {}", address_family.bgp.missing_policy.direction_in_action)
        self._add("bgp missing-policy direction out action {}", address_family.bgp.missing_policy.direction_out_action)
        self._add("bgp additional-paths receive", address_family.bgp.additional_paths.receive)

        for neighbor in natural_sort(address_family.neighbors or [], sort_key="ip_address"):
            neighbor_ip_address = neighbor.ip_address
            if neighbor.activate is True:
                self._add(f"neighbor {neighbor_ip_address} activate")
            if neighbor.additional_paths.receive is True:
                self._add(f"neighbor {neighbor_ip_address} additional-paths receive")
            self._add("neighbor {} route-map {} in", neighbor_ip_address, neighbor.route_map_in)
            self._add("neighbor {} route-map {} out", neighbor_ip_address, neighbor.route_map_out)
            self._add("neighbor {} peer-tag in {}", neighbor_ip_address, neighbor.peer_tag_in)
            self._add("neighbor {} peer-tag out discard {}", neighbor_ip_address, neighbor.peer_tag_out_discard)

        for network in natural_sort(address_family.networks or [], sort_key="prefix"):
            cli = f"network {network.prefix}"
            if network.route_map is not None:
                cli += f" route-map {network.route_map}"
            self._add(cli)

        if address_family.redistribute:
            self._render_redistribute(address_family.redistribute)

    def _render_redistribute(self, redistribute: Any) -> None:
        if redistribute.attached_host.enabled is True:
            cli = "redistribute attached-host"
            if redistribute.attached_host.route_map is not None:
                cli += f" route-map {redistribute.attached_host.route_map}"
            self._add(cli)

        if redistribute.connected.enabled is True:
            cli = "redistribute connected"
            if redistribute.connected.route_map is not None:
                cli += f" route-map {redistribute.connected.route_map}"
            self._add(cli)

        if redistribute.isis.enabled is True:
            cli = "redistribute isis"
            if redistribute.isis.isis_level is not None:
                cli += f" {redistribute.isis.isis_level}"
            if redistribute.isis.include_leaked is True:
                cli += " include leaked"
            if redistribute.isis.route_map is not None:
                cli += f" route-map {redistribute.isis.route_map}"
            elif redistribute.isis.rcf is not None:
                cli += f" rcf {redistribute.isis.rcf}"
            self._add(cli)

        if redistribute.ospf.enabled is True:
            cli = "redistribute ospf"
            if redistribute.ospf.route_map is not None:
                cli += f" route-map {redistribute.ospf.route_map}"
            self._add(cli)
        elif redistribute.ospf.match_internal.enabled is True:
            cli = "redistribute ospf match internal"
            if redistribute.ospf.match_internal.route_map is not None:
                cli += f" route-map {redistribute.ospf.match_internal.route_map}"
            self._add(cli)

        if redistribute.ospfv3.enabled is True:
            cli = "redistribute ospfv3"
            if redistribute.ospfv3.route_map is not None:
                cli += f" route-map {redistribute.ospfv3.route_map}"
            self._add(cli)
        elif redistribute.ospfv3.match_internal.enabled is True:
            cli = "redistribute ospfv3 match internal"
            if redistribute.ospfv3.match_internal.route_map is not None:
                cli += f" route-map {redistribute.ospfv3.match_internal.route_map}"
            self._add(cli)

        if redistribute.ospfv3.match_external.enabled is True:
            cli = "redistribute ospfv3 match external"
            if redistribute.ospfv3.match_external.route_map is not None:
                cli += f" route-map {redistribute.ospfv3.match_external.route_map}"
            self._add(cli)

        if redistribute.ospfv3.match_nssa_external.enabled is True:
            cli = "redistribute ospfv3 match nssa-external"
            if redistribute.ospfv3.match_nssa_external.nssa_type is not None:
                cli += f" {redistribute.ospfv3.match_nssa_external.nssa_type}"
            if redistribute.ospfv3.match_nssa_external.route_map is not None:
                cli += f" route-map {redistribute.ospfv3.match_nssa_external.route_map}"
            self._add(cli)

        if redistribute.ospf.match_external.enabled is True:
            cli = "redistribute ospf match external"
            if redistribute.ospf.match_external.route_map is not None:
                cli += f" route-map {redistribute.ospf.match_external.route_map}"
            self._add(cli)

        if redistribute.ospf.match_nssa_external.enabled is True:
            cli = "redistribute ospf match nssa-external"
            if redistribute.ospf.match_nssa_external.nssa_type is not None:
                cli += f" {redistribute.ospf.match_nssa_external.nssa_type}"
            if redistribute.ospf.match_nssa_external.route_map is not None:
                cli += f" route-map {redistribute.ospf.match_nssa_external.route_map}"
            self._add(cli)

        if redistribute.static.enabled is True:
            cli = "redistribute static"
            if redistribute.static.route_map is not None:
                cli += f" route-map {redistribute.static.route_map}"
            self._add(cli)


class RouterBgpVrfAddressFamilyIpv6(CliSection):
    """Renders 'address-family ipv6' inside a VRF block."""

    def __init__(self, vrf: Any) -> None:
        self.vrf = vrf

    def _generate(self) -> None:
        address_family = self.vrf.address_family_ipv6
        if not address_family:
            return
        self._header("address-family ipv6")

        if address_family.bgp.additional_paths.install is True:
            self._add("bgp additional-paths install")
        elif address_family.bgp.additional_paths.install_ecmp_primary is True:
            self._add("bgp additional-paths install ecmp-primary")

        self._add("bgp missing-policy direction in action {}", address_family.bgp.missing_policy.direction_in_action)
        self._add("bgp missing-policy direction out action {}", address_family.bgp.missing_policy.direction_out_action)
        self._add("bgp additional-paths receive", address_family.bgp.additional_paths.receive)
        self._render_bgp_additional_paths_send(address_family.bgp.additional_paths)

        for neighbor in natural_sort(address_family.neighbors or [], sort_key="ip_address"):
            self._render_neighbor(neighbor)

        for network in natural_sort(address_family.networks or [], sort_key="prefix"):
            cli = f"network {network.prefix}"
            if network.route_map is not None:
                cli += f" route-map {network.route_map}"
            elif network.rcf is not None:
                cli += f" rcf {network.rcf}"
            self._add(cli)

        if address_family.bgp.redistribute_internal is True:
            self._add("bgp redistribute-internal")
        elif address_family.bgp.redistribute_internal is False:
            self._add("no bgp redistribute-internal")

        if address_family.redistribute:
            self._render_redistribute(address_family.redistribute)

    def _render_neighbor(self, neighbor: Any) -> None:
        neighbor_ip_address = neighbor.ip_address
        if neighbor.activate is True:
            self._add(f"neighbor {neighbor_ip_address} activate")
        if neighbor.additional_paths.receive is True:
            self._add(f"neighbor {neighbor_ip_address} additional-paths receive")
        self._add("neighbor {} route-map {} in", neighbor_ip_address, neighbor.route_map_in)
        self._add("neighbor {} route-map {} out", neighbor_ip_address, neighbor.route_map_out)
        self._add("neighbor {} rcf in {}", neighbor_ip_address, neighbor.rcf_in)
        self._add("neighbor {} rcf out {}", neighbor_ip_address, neighbor.rcf_out)
        self._add("neighbor {} prefix-list {} in", neighbor_ip_address, neighbor.prefix_list_in)
        self._add("neighbor {} prefix-list {} out", neighbor_ip_address, neighbor.prefix_list_out)
        self._render_neighbor_additional_paths_send(neighbor_ip_address, neighbor.additional_paths)
        self._add("neighbor {} peer-tag in {}", neighbor_ip_address, neighbor.peer_tag_in)
        self._add("neighbor {} peer-tag out discard {}", neighbor_ip_address, neighbor.peer_tag_out_discard)

    def _render_bgp_additional_paths_send(self, additional_paths: Any) -> None:
        send = additional_paths.send
        send_limit = additional_paths.send_limit
        if send is None:
            return
        if send == "disabled":
            self._add("no bgp additional-paths send")
        elif send == "ecmp" and send_limit is not None:
            self._add(f"bgp additional-paths send ecmp limit {send_limit}")
        elif send == "limit" and send_limit is not None:
            self._add(f"bgp additional-paths send limit {send_limit}")
        else:
            self._add(f"bgp additional-paths send {send}")

    def _render_neighbor_additional_paths_send(self, ip: str, additional_paths: Any) -> None:
        send = additional_paths.send
        send_limit = additional_paths.send_limit
        if send is None:
            return
        if send == "disabled":
            self._add(f"no neighbor {ip} additional-paths send")
        elif send == "ecmp" and send_limit is not None:
            self._add(f"neighbor {ip} additional-paths send ecmp limit {send_limit}")
        elif send == "limit" and send_limit is not None:
            self._add(f"neighbor {ip} additional-paths send limit {send_limit}")
        else:
            self._add(f"neighbor {ip} additional-paths send {send}")

    def _render_redistribute(self, redistribute: Any) -> None:
        if redistribute.attached_host.enabled is True:
            cli = "redistribute attached-host"
            if redistribute.attached_host.route_map is not None:
                cli += f" route-map {redistribute.attached_host.route_map}"
            self._add(cli)

        if redistribute.bgp.enabled is True:
            cli = "redistribute bgp leaked"
            if redistribute.bgp.route_map is not None:
                cli += f" route-map {redistribute.bgp.route_map}"
            self._add(cli)

        if redistribute.dhcp.enabled is True:
            cli = "redistribute dhcp"
            if redistribute.dhcp.route_map is not None:
                cli += f" route-map {redistribute.dhcp.route_map}"
            self._add(cli)

        if redistribute.connected.enabled is True:
            cli = "redistribute connected"
            if redistribute.connected.include_leaked is True:
                cli += " include leaked"
            if redistribute.connected.route_map is not None:
                cli += f" route-map {redistribute.connected.route_map}"
            elif redistribute.connected.rcf is not None:
                cli += f" rcf {redistribute.connected.rcf}"
            self._add(cli)

        if redistribute.dynamic.enabled is True:
            cli = "redistribute dynamic"
            if redistribute.dynamic.route_map is not None:
                cli += f" route-map {redistribute.dynamic.route_map}"
            elif redistribute.dynamic.rcf is not None:
                cli += f" rcf {redistribute.dynamic.rcf}"
            self._add(cli)

        if redistribute.user.enabled is True:
            cli = "redistribute user"
            if redistribute.user.rcf is not None:
                cli += f" rcf {redistribute.user.rcf}"
            self._add(cli)

        if redistribute.isis.enabled is True:
            cli = "redistribute isis"
            if redistribute.isis.isis_level is not None:
                cli += f" {redistribute.isis.isis_level}"
            if redistribute.isis.include_leaked is True:
                cli += " include leaked"
            if redistribute.isis.route_map is not None:
                cli += f" route-map {redistribute.isis.route_map}"
            elif redistribute.isis.rcf is not None:
                cli += f" rcf {redistribute.isis.rcf}"
            self._add(cli)

        if redistribute.ospfv3.enabled is True:
            cli = "redistribute ospfv3"
            if redistribute.ospfv3.include_leaked is True:
                cli += " include leaked"
            if redistribute.ospfv3.route_map is not None:
                cli += f" route-map {redistribute.ospfv3.route_map}"
            self._add(cli)
        elif redistribute.ospfv3.match_internal.enabled is True:
            cli = "redistribute ospfv3 match internal"
            if redistribute.ospfv3.match_internal.include_leaked is True:
                cli += " include leaked"
            if redistribute.ospfv3.match_internal.route_map is not None:
                cli += f" route-map {redistribute.ospfv3.match_internal.route_map}"
            self._add(cli)

        if redistribute.ospfv3.match_external.enabled is True:
            cli = "redistribute ospfv3 match external"
            if redistribute.ospfv3.match_external.include_leaked is True:
                cli += " include leaked"
            if redistribute.ospfv3.match_external.route_map is not None:
                cli += f" route-map {redistribute.ospfv3.match_external.route_map}"
            self._add(cli)

        if redistribute.ospfv3.match_nssa_external.enabled is True:
            cli = "redistribute ospfv3 match nssa-external"
            if redistribute.ospfv3.match_nssa_external.nssa_type is not None:
                cli += f" {redistribute.ospfv3.match_nssa_external.nssa_type}"
            if redistribute.ospfv3.match_nssa_external.include_leaked is True:
                cli += " include leaked"
            if redistribute.ospfv3.match_nssa_external.route_map is not None:
                cli += f" route-map {redistribute.ospfv3.match_nssa_external.route_map}"
            self._add(cli)

        if redistribute.static.enabled is True:
            cli = "redistribute static"
            if redistribute.static.include_leaked is True:
                cli += " include leaked"
            if redistribute.static.route_map is not None:
                cli += f" route-map {redistribute.static.route_map}"
            elif redistribute.static.rcf is not None:
                cli += f" rcf {redistribute.static.rcf}"
            self._add(cli)


class RouterBgpVrfAddressFamilyIpv6Multicast(CliSection):
    """Renders 'address-family ipv6 multicast' inside a VRF block."""

    def __init__(self, vrf: Any) -> None:
        self.vrf = vrf

    def _generate(self) -> None:
        address_family = self.vrf.address_family_ipv6_multicast
        if not address_family:
            return
        self._header("address-family ipv6 multicast")

        self._add("bgp missing-policy direction in action {}", address_family.bgp.missing_policy.direction_in_action)
        self._add("bgp missing-policy direction out action {}", address_family.bgp.missing_policy.direction_out_action)
        self._add("bgp additional-paths receive", address_family.bgp.additional_paths.receive)

        for neighbor in natural_sort(address_family.neighbors or [], sort_key="ip_address"):
            neighbor_ip_address = neighbor.ip_address
            if neighbor.activate is True:
                self._add(f"neighbor {neighbor_ip_address} activate")
            if neighbor.additional_paths.receive is True:
                self._add(f"neighbor {neighbor_ip_address} additional-paths receive")
            self._add("neighbor {} route-map {} in", neighbor_ip_address, neighbor.route_map_in)
            self._add("neighbor {} route-map {} out", neighbor_ip_address, neighbor.route_map_out)
            self._add("neighbor {} peer-tag in {}", neighbor_ip_address, neighbor.peer_tag_in)
            self._add("neighbor {} peer-tag out discard {}", neighbor_ip_address, neighbor.peer_tag_out_discard)

        for network in natural_sort(address_family.networks or [], sort_key="prefix"):
            cli = f"network {network.prefix}"
            if network.route_map is not None:
                cli += f" route-map {network.route_map}"
            self._add(cli)

        if address_family.redistribute:
            self._render_redistribute(address_family.redistribute)

    def _render_redistribute(self, redistribute: Any) -> None:
        if redistribute.connected.enabled is True:
            cli = "redistribute connected"
            if redistribute.connected.route_map is not None:
                cli += f" route-map {redistribute.connected.route_map}"
            self._add(cli)

        if redistribute.isis.enabled is True:
            cli = "redistribute isis"
            if redistribute.isis.isis_level is not None:
                cli += f" {redistribute.isis.isis_level}"
            if redistribute.isis.include_leaked is True:
                cli += " include leaked"
            if redistribute.isis.route_map is not None:
                cli += f" route-map {redistribute.isis.route_map}"
            elif redistribute.isis.rcf is not None:
                cli += f" rcf {redistribute.isis.rcf}"
            self._add(cli)

        if redistribute.ospf.enabled is True:
            cli = "redistribute ospf"
            if redistribute.ospf.route_map is not None:
                cli += f" route-map {redistribute.ospf.route_map}"
            self._add(cli)
        elif redistribute.ospf.match_internal.enabled is True:
            cli = "redistribute ospf match internal"
            if redistribute.ospf.match_internal.route_map is not None:
                cli += f" route-map {redistribute.ospf.match_internal.route_map}"
            self._add(cli)

        if redistribute.ospfv3.enabled is True:
            cli = "redistribute ospfv3"
            if redistribute.ospfv3.route_map is not None:
                cli += f" route-map {redistribute.ospfv3.route_map}"
            self._add(cli)
        elif redistribute.ospfv3.match_internal.enabled is True:
            cli = "redistribute ospfv3 match internal"
            if redistribute.ospfv3.match_internal.route_map is not None:
                cli += f" route-map {redistribute.ospfv3.match_internal.route_map}"
            self._add(cli)

        if redistribute.ospfv3.match_external.enabled is True:
            cli = "redistribute ospfv3 match external"
            if redistribute.ospfv3.match_external.route_map is not None:
                cli += f" route-map {redistribute.ospfv3.match_external.route_map}"
            self._add(cli)

        if redistribute.ospfv3.match_nssa_external.enabled is True:
            cli = "redistribute ospfv3 match nssa-external"
            if redistribute.ospfv3.match_nssa_external.nssa_type is not None:
                cli += f" {redistribute.ospfv3.match_nssa_external.nssa_type}"
            if redistribute.ospfv3.match_nssa_external.route_map is not None:
                cli += f" route-map {redistribute.ospfv3.match_nssa_external.route_map}"
            self._add(cli)

        if redistribute.ospf.match_external.enabled is True:
            cli = "redistribute ospf match external"
            if redistribute.ospf.match_external.route_map is not None:
                cli += f" route-map {redistribute.ospf.match_external.route_map}"
            self._add(cli)

        if redistribute.ospf.match_nssa_external.enabled is True:
            cli = "redistribute ospf match nssa-external"
            if redistribute.ospf.match_nssa_external.nssa_type is not None:
                cli += f" {redistribute.ospf.match_nssa_external.nssa_type}"
            if redistribute.ospf.match_nssa_external.route_map is not None:
                cli += f" route-map {redistribute.ospf.match_nssa_external.route_map}"
            self._add(cli)

        if redistribute.static.enabled is True:
            cli = "redistribute static"
            if redistribute.static.route_map is not None:
                cli += f" route-map {redistribute.static.route_map}"
            self._add(cli)


class RouterBgpVrfEvpnMulticast(CliSection):
    """Renders 'evpn multicast' inside a VRF block (no separator)."""

    separator = False

    def __init__(self, vrf: Any) -> None:
        self.vrf = vrf

    def _generate(self) -> None:
        if self.vrf.evpn_multicast is not True:
            return
        self._header("evpn multicast")
        dr_election_algorithm = self.vrf.evpn_multicast_gateway_dr_election.algorithm
        if dr_election_algorithm is not None:
            if dr_election_algorithm == "preference":
                preference_value = self.vrf.evpn_multicast_gateway_dr_election.preference_value
                self._add("gateway dr election algorithm preference {}", preference_value)
            else:
                self._add(f"gateway dr election algorithm {dr_election_algorithm}")
        self._sub(_RouterBgpVrfEvpnMulticastAddressFamilyIpv4(self.vrf))


class _RouterBgpVrfEvpnMulticastAddressFamilyIpv4(CliSection):
    """Renders 'address-family ipv4' inside 'evpn multicast' (no separator)."""

    separator = False

    def __init__(self, vrf: Any) -> None:
        self.vrf = vrf

    def _generate(self) -> None:
        af_ipv4 = self.vrf.evpn_multicast_address_family.ipv4
        if not af_ipv4 or af_ipv4.transit is not True:
            return
        self._header("address-family ipv4")
        self._add("transit")


class RouterBgpVlan(CliSection):
    """Renders a single 'vlan X' block inside 'router bgp'."""

    def __init__(self, vlan: Any) -> None:
        self.vlan = vlan

    def _generate(self) -> None:
        vlan = self.vlan
        self._header(f"vlan {vlan.id}")
        self._add("rd {}", vlan.rd)
        self._add("rd evpn domain {} {}", vlan.rd_evpn_domain.domain, vlan.rd_evpn_domain.rd)
        for rt in natural_sort(vlan.route_targets.both or []):
            self._add(f"route-target both {rt}")
        for rt in natural_sort(vlan.route_targets.field_import or []):
            self._add(f"route-target import {rt}")
        for rt in natural_sort(vlan.route_targets.export or []):
            self._add(f"route-target export {rt}")
        for rt in natural_sort(vlan.route_targets.import_evpn_domains or [], sort_key="domain"):
            self._add(f"route-target import evpn domain {rt.domain} {rt.route_target}")
        for rt in natural_sort(vlan.route_targets.export_evpn_domains or [], sort_key="domain"):
            self._add(f"route-target export evpn domain {rt.domain} {rt.route_target}")
        for rt in natural_sort(vlan.route_targets.import_export_evpn_domains or [], sort_key="domain"):
            self._add(f"route-target import export evpn domain {rt.domain} {rt.route_target}")
        for r in natural_sort(vlan.redistribute_routes or []):
            self._add(f"redistribute {r}")
        for r in natural_sort(vlan.no_redistribute_routes or []):
            self._add(f"no redistribute {r}")
        if vlan.eos_cli is not None:
            self._add("!")
            for line in vlan.eos_cli.splitlines():
                self._add(line)
            if vlan.eos_cli.endswith("\n"):
                self._output_lines.append("")


class RouterBgpVpwsService(CliSection):
    """Renders a single 'vpws X' block inside 'router bgp'."""

    def __init__(self, svc: Any) -> None:
        self.vpws_service = svc

    def _generate(self) -> None:
        svc = self.vpws_service
        if svc.name is None:
            return
        self._header(f"vpws {svc.name}")
        self._add("rd {}", svc.rd)
        self._add("route-target import export evpn {}", svc.route_targets.import_export)
        self._add("mpls control-word", svc.mpls_control_word)
        self._add("label flow", svc.label_flow)
        self._add("mtu {}", svc.mtu)
        for hashed_password in natural_sort(svc.pseudowires or [], sort_key="name"):
            self._sub(RouterBgpVpwsPseudowire(hashed_password))


class RouterBgpVpwsPseudowire(CliSection):
    """Renders a single 'pseudowire X' block inside a 'vpws' service block."""

    def __init__(self, hashed_password: Any) -> None:
        self.pseudowire = hashed_password

    def _generate(self) -> None:
        hashed_password = self.pseudowire
        if hashed_password.name is None or hashed_password.id_local is None or hashed_password.id_remote is None:
            return
        self._header(f"pseudowire {hashed_password.name}")
        self._add(f"evpn vpws id local {hashed_password.id_local} remote {hashed_password.id_remote}")


class RouterBgpVlanAwareBundle(CliSection):
    """Renders a single 'vlan-aware-bundle X' block inside 'router bgp'."""

    def __init__(self, bundle: Any) -> None:
        self.bundle = bundle

    def _generate(self) -> None:
        bundle = self.bundle
        self._header(f"vlan-aware-bundle {bundle.name}")
        self._add("rd {}", bundle.rd)
        self._add("rd evpn domain {} {}", bundle.rd_evpn_domain.domain, bundle.rd_evpn_domain.rd)
        for rt in natural_sort(bundle.route_targets.both or []):
            self._add(f"route-target both {rt}")
        for rt in natural_sort(bundle.route_targets.field_import or []):
            self._add(f"route-target import {rt}")
        for rt in natural_sort(bundle.route_targets.export or []):
            self._add(f"route-target export {rt}")
        for rt in natural_sort(bundle.route_targets.import_evpn_domains or [], sort_key="domain"):
            self._add(f"route-target import evpn domain {rt.domain} {rt.route_target}")
        for rt in natural_sort(bundle.route_targets.export_evpn_domains or [], sort_key="domain"):
            self._add(f"route-target export evpn domain {rt.domain} {rt.route_target}")
        for rt in natural_sort(bundle.route_targets.import_export_evpn_domains or [], sort_key="domain"):
            self._add(f"route-target import export evpn domain {rt.domain} {rt.route_target}")
        for r in natural_sort(bundle.redistribute_routes or []):
            self._add(f"redistribute {r}")
        for r in natural_sort(bundle.no_redistribute_routes or []):
            self._add(f"no redistribute {r}")
        self._add("vlan {}", bundle.vlan)
        if bundle.eos_cli is not None:
            self._add("!")
            for line in bundle.eos_cli.splitlines():
                self._add(line)
            if bundle.eos_cli.endswith("\n"):
                self._output_lines.append("")


class RouterBgpRouteDistinguisher(CliSection):
    """Renders the 'route-distinguisher' block inside 'router bgp'."""

    def __init__(self, bgp: Any) -> None:
        self.bgp = bgp

    def _generate(self) -> None:
        assignment_auto = self.bgp.route_distinguisher.assignment_auto
        if not assignment_auto:
            return
        self._header("route-distinguisher")
        self._add("assignment auto range {} {}", assignment_auto.range.start, assignment_auto.range.end)
        for address_family in natural_sort(assignment_auto.address_families or []):
            self._add(f"assignment auto address-family {address_family}")


class RouterBgpAddressFamilyEvpn(CliSection):
    """Renders the 'address-family evpn' block inside 'router bgp'."""

    def __init__(self, bgp: Any) -> None:
        self.bgp = bgp

    def _generate(self) -> None:
        address_family = self.bgp.address_family_evpn
        if not address_family:
            return
        self._header("address-family evpn")
        self._add("route export ethernet-segment ip mass-withdraw", address_family.route.export_ethernet_segment_ip_mass_withdraw)
        self._add("route import ethernet-segment ip mass-withdraw", address_family.route.import_ethernet_segment_ip_mass_withdraw)
        self._add("bgp additional-paths receive", address_family.bgp.additional_paths.receive)
        self._render_af_bgp_additional_paths_send(address_family.bgp.additional_paths)
        self._add("bgp next-hop-unchanged", address_family.next_hop_unchanged)
        if address_family.neighbor_default.encapsulation is not None:
            enc_cli = f"neighbor default encapsulation {address_family.neighbor_default.encapsulation}"
            if address_family.neighbor_default.encapsulation == "mpls" and address_family.neighbor_default.next_hop_self_source_interface is not None:
                enc_cli += f" next-hop-self source-interface {address_family.neighbor_default.next_hop_self_source_interface}"
            self._add(enc_cli)

        rib_tokens: list[str] = []
        for rib in address_family.next_hop_mpls_resolution_ribs or []:
            if rib.rib_type == "tunnel-rib-colored":
                rib_tokens.append("tunnel-rib colored system-colored-tunnel-rib")
            elif rib.rib_type == "tunnel-rib" and rib.rib_name is not None:
                rib_tokens.append(f"tunnel-rib {rib.rib_name}")
            elif rib.rib_type is not None:
                rib_tokens.append(rib.rib_type)
        if rib_tokens:
            self._add(f"next-hop mpls resolution ribs {' '.join(rib_tokens)}")

        for peer_group in natural_sort(address_family.peer_groups or [], sort_key="name"):
            self._render_af_evpn_peer_group(peer_group)
        for neighbor in natural_sort(address_family.neighbors or [], sort_key="ip_address"):
            self._render_af_evpn_neighbor(neighbor)

        self._add("domain identifier {}", address_family.domain_identifier)
        self._add("domain identifier {} remote", address_family.domain_identifier_remote)
        self._add("next-hop resolution disabled", address_family.next_hop.resolution_disabled)
        if address_family.route.import_match_failure_action == "discard":
            self._add("route import match-failure action discard")
        if address_family.neighbor_default.next_hop_self_received_evpn_routes.enable is True:
            nhs_cli = "neighbor default next-hop-self received-evpn-routes route-type ip-prefix"
            if address_family.neighbor_default.next_hop_self_received_evpn_routes.inter_domain is True:
                nhs_cli += " inter-domain"
            self._add(nhs_cli)

        if address_family.evpn_hostflap_detection.enabled is False:
            self._add("no host-flap detection")
        elif address_family.evpn_hostflap_detection.enabled is True:
            hfd_suffix = ""
            if address_family.evpn_hostflap_detection.window is not None:
                hfd_suffix += f" window {address_family.evpn_hostflap_detection.window}"
            if address_family.evpn_hostflap_detection.threshold is not None:
                hfd_suffix += f" threshold {address_family.evpn_hostflap_detection.threshold}"
            if address_family.evpn_hostflap_detection.expiry_timeout is not None:
                hfd_suffix += f" expiry timeout {address_family.evpn_hostflap_detection.expiry_timeout} seconds"
            if hfd_suffix:
                self._add(f"host-flap detection{hfd_suffix}")

        if address_family.layer_2_fec_in_place_update.enabled is True:
            l2_cli = "layer-2 fec in-place update"
            if address_family.layer_2_fec_in_place_update.timeout is not None:
                l2_cli += f" timeout {address_family.layer_2_fec_in_place_update.timeout} seconds"
            self._add(l2_cli)

        self._add("route import overlay-index gateway", address_family.route.import_overlay_index_gateway)

        for segment in natural_sort(address_family.evpn_ethernet_segment or [], sort_key="domain"):
            self._sub(RouterBgpAddressFamilyEvpnEthernetSegment(segment))

    def _render_af_bgp_additional_paths_send(self, additional_paths: Any) -> None:
        send = additional_paths.send
        send_limit = additional_paths.send_limit
        if send is None:
            return
        if send == "disabled":
            self._add("no bgp additional-paths send")
        elif send == "ecmp" and send_limit is not None:
            self._add(f"bgp additional-paths send ecmp limit {send_limit}")
        elif send == "limit" and send_limit is not None:
            self._add(f"bgp additional-paths send limit {send_limit}")
        else:
            self._add(f"bgp additional-paths send {send}")

    def _render_af_evpn_peer_group(self, peer_group: Any) -> None:
        name = peer_group.name
        if peer_group.activate is True:
            self._add(f"neighbor {name} activate")
        elif peer_group.activate is False:
            self._add(f"no neighbor {name} activate")
        if peer_group.additional_paths.receive is True:
            self._add(f"neighbor {name} additional-paths receive")
        self._add("neighbor {} route-map {} in", name, peer_group.route_map_in)
        self._add("neighbor {} route-map {} out", name, peer_group.route_map_out)
        self._add("neighbor {} rcf in {}", name, peer_group.rcf_in)
        self._add("neighbor {} rcf out {}", name, peer_group.rcf_out)
        if peer_group.default_route.enabled is True:
            dr_cli = f"neighbor {name} default-route"
            if peer_group.default_route.rcf is not None:
                dr_cli += f" rcf {peer_group.default_route.rcf}"
            elif peer_group.default_route.route_map is not None:
                dr_cli += f" route-map {peer_group.default_route.route_map}"
            self._add(dr_cli)
        self._render_af_neighbor_additional_paths_send(name, peer_group.additional_paths)
        self._add("neighbor {} peer-tag in {}", name, peer_group.peer_tag_in)
        self._add("neighbor {} peer-tag out discard {}", name, peer_group.peer_tag_out_discard)
        if peer_group.encapsulation is not None:
            enc_cli = f"neighbor {name} encapsulation {peer_group.encapsulation}"
            if peer_group.encapsulation == "mpls" and peer_group.next_hop_self_source_interface is not None:
                enc_cli += f" next-hop-self source-interface {peer_group.next_hop_self_source_interface}"
            self._add(enc_cli)
        if peer_group.domain_remote is True:
            self._add(f"neighbor {name} domain remote")

    def _render_af_evpn_neighbor(self, neighbor: Any) -> None:
        neighbor_ip_address = neighbor.ip_address
        if neighbor.activate is True:
            self._add(f"neighbor {neighbor_ip_address} activate")
        elif neighbor.activate is False:
            self._add(f"no neighbor {neighbor_ip_address} activate")
        if neighbor.additional_paths.receive is True:
            self._add(f"neighbor {neighbor_ip_address} additional-paths receive")
        self._add("neighbor {} route-map {} in", neighbor_ip_address, neighbor.route_map_in)
        self._add("neighbor {} route-map {} out", neighbor_ip_address, neighbor.route_map_out)
        self._add("neighbor {} rcf in {}", neighbor_ip_address, neighbor.rcf_in)
        self._add("neighbor {} rcf out {}", neighbor_ip_address, neighbor.rcf_out)
        if neighbor.default_route.enabled is True:
            dr_cli = f"neighbor {neighbor_ip_address} default-route"
            if neighbor.default_route.rcf is not None:
                dr_cli += f" rcf {neighbor.default_route.rcf}"
            elif neighbor.default_route.route_map is not None:
                dr_cli += f" route-map {neighbor.default_route.route_map}"
            self._add(dr_cli)
        self._render_af_neighbor_additional_paths_send(neighbor_ip_address, neighbor.additional_paths)
        self._add("neighbor {} peer-tag in {}", neighbor_ip_address, neighbor.peer_tag_in)
        self._add("neighbor {} peer-tag out discard {}", neighbor_ip_address, neighbor.peer_tag_out_discard)
        if neighbor.encapsulation is not None:
            enc_cli = f"neighbor {neighbor_ip_address} encapsulation {neighbor.encapsulation}"
            if neighbor.encapsulation == "mpls" and neighbor.next_hop_self_source_interface is not None:
                enc_cli += f" next-hop-self source-interface {neighbor.next_hop_self_source_interface}"
            self._add(enc_cli)

    def _render_af_neighbor_additional_paths_send(self, entity_id: str, additional_paths: Any) -> None:
        send = additional_paths.send
        send_limit = additional_paths.send_limit
        if send is None:
            return
        if send == "disabled":
            self._add(f"no neighbor {entity_id} additional-paths send")
        elif send == "ecmp" and send_limit is not None:
            self._add(f"neighbor {entity_id} additional-paths send ecmp limit {send_limit}")
        elif send == "limit":
            self._add("neighbor {} additional-paths send limit {}", entity_id, send_limit)
        else:
            self._add(f"neighbor {entity_id} additional-paths send {send}")


class RouterBgpAddressFamilyEvpnEthernetSegment(CliSection):
    """Renders a single 'evpn ethernet-segment domain X' block inside address-family evpn."""

    def __init__(self, segment: Any) -> None:
        self.segment = segment

    def _generate(self) -> None:
        segment = self.segment
        self._header(f"evpn ethernet-segment domain {segment.domain}")
        self._add("identifier {}", segment.identifier)
        self._add("route-target import {}", segment.route_target_import)


class RouterBgpAddressFamilyFlowSpec(CliSection):
    """Renders 'address-family flow-spec {ipv4|ipv6}' inside 'router bgp'."""

    def __init__(self, address_family: Any, protocol: str) -> None:
        self.address_family = address_family
        self.protocol = protocol

    def _generate(self) -> None:
        address_family = self.address_family
        if not address_family:
            return
        self._header(f"address-family flow-spec {self.protocol}")
        self._add("bgp missing-policy direction in action {}", address_family.bgp.missing_policy.direction_in_action)
        self._add("bgp missing-policy direction out action {}", address_family.bgp.missing_policy.direction_out_action)
        for peer_group in natural_sort(address_family.peer_groups or [], sort_key="name"):
            if peer_group.activate is True:
                self._add(f"neighbor {peer_group.name} activate")
            elif peer_group.activate is False:
                self._add(f"no neighbor {peer_group.name} activate")
        for neighbor in natural_sort(address_family.neighbors or [], sort_key="ip_address"):
            if neighbor.activate is True:
                self._add(f"neighbor {neighbor.ip_address} activate")


class RouterBgpAddressFamilyIpv4(CliSection):
    """Renders the 'address-family ipv4' block inside 'router bgp'."""

    def __init__(self, bgp: Any) -> None:
        self.bgp = bgp

    def _generate(self) -> None:
        address_family = self.bgp.address_family_ipv4
        if not address_family:
            return
        self._header("address-family ipv4")
        if address_family.bgp.additional_paths.install is True:
            self._add("bgp additional-paths install")
        elif address_family.bgp.additional_paths.install_ecmp_primary is True:
            self._add("bgp additional-paths install ecmp-primary")
        self._add("bgp additional-paths receive", address_family.bgp.additional_paths.receive)
        self._render_af_bgp_additional_paths_send(address_family.bgp.additional_paths)

        for peer_group in natural_sort(address_family.peer_groups or [], sort_key="name"):
            self._render_af_ipv4_peer_group(peer_group)
        for neighbor in natural_sort(address_family.neighbors or [], sort_key="ip_address"):
            self._render_af_ipv4_neighbor(neighbor)

        for network in natural_sort(address_family.networks or [], sort_key="prefix"):
            if network.route_map is not None:
                self._add(f"network {network.prefix} route-map {network.route_map}")
            elif network.rcf is not None:
                self._add(f"network {network.prefix} rcf {network.rcf}")
            else:
                self._add(f"network {network.prefix}")

        if address_family.bgp.redistribute_internal is True:
            self._add("bgp redistribute-internal")
        elif address_family.bgp.redistribute_internal is False:
            self._add("no bgp redistribute-internal")

        self._render_af_ipv4_redistribute(address_family.redistribute)

    def _render_af_bgp_additional_paths_send(self, additional_paths: Any) -> None:
        send = additional_paths.send
        send_limit = additional_paths.send_limit
        if send is None:
            return
        if send == "disabled":
            self._add("no bgp additional-paths send")
        elif send == "ecmp" and send_limit is not None:
            self._add(f"bgp additional-paths send ecmp limit {send_limit}")
        elif send == "limit" and send_limit is not None:
            self._add(f"bgp additional-paths send limit {send_limit}")
        else:
            self._add(f"bgp additional-paths send {send}")

    def _render_af_ipv4_peer_group(self, peer_group: Any) -> None:
        name = peer_group.name
        if peer_group.activate is True:
            self._add(f"neighbor {name} activate")
        elif peer_group.activate is False:
            self._add(f"no neighbor {name} activate")
        if peer_group.additional_paths.receive is True:
            self._add(f"neighbor {name} additional-paths receive")
        self._add("neighbor {} route-map {} in", name, peer_group.route_map_in)
        self._add("neighbor {} route-map {} out", name, peer_group.route_map_out)
        self._add("neighbor {} rcf in {}", name, peer_group.rcf_in)
        self._add("neighbor {} rcf out {}", name, peer_group.rcf_out)
        self._add("neighbor {} prefix-list {} in", name, peer_group.prefix_list_in)
        self._add("neighbor {} prefix-list {} out", name, peer_group.prefix_list_out)
        if peer_group.default_originate:
            do_cli = f"neighbor {name} default-originate"
            if peer_group.default_originate.route_map is not None:
                do_cli += f" route-map {peer_group.default_originate.route_map}"
            if peer_group.default_originate.always is True:
                do_cli += " always"
            self._add(do_cli)
        self._render_af_ipv4_additional_paths_send(name, peer_group.additional_paths)
        if peer_group.next_hop.address_family_ipv6.enabled is True:
            nhv6_cli = f"neighbor {name} next-hop address-family ipv6"
            if peer_group.next_hop.address_family_ipv6.originate is True:
                nhv6_cli += " originate"
            self._add(nhv6_cli)
        self._add("neighbor {} peer-tag in {}", name, peer_group.peer_tag_in)
        self._add("neighbor {} peer-tag out discard {}", name, peer_group.peer_tag_out_discard)

    def _render_af_ipv4_neighbor(self, neighbor: Any) -> None:
        neighbor_ip_address = neighbor.ip_address
        if neighbor.activate is True:
            self._add(f"neighbor {neighbor_ip_address} activate")
        elif neighbor.activate is False:
            self._add(f"no neighbor {neighbor_ip_address} activate")
        if neighbor.additional_paths.receive is True:
            self._add(f"neighbor {neighbor_ip_address} additional-paths receive")
        self._add("neighbor {} route-map {} in", neighbor_ip_address, neighbor.route_map_in)
        self._add("neighbor {} route-map {} out", neighbor_ip_address, neighbor.route_map_out)
        self._add("neighbor {} rcf in {}", neighbor_ip_address, neighbor.rcf_in)
        self._add("neighbor {} rcf out {}", neighbor_ip_address, neighbor.rcf_out)
        self._add("neighbor {} prefix-list {} in", neighbor_ip_address, neighbor.prefix_list_in)
        self._add("neighbor {} prefix-list {} out", neighbor_ip_address, neighbor.prefix_list_out)
        if neighbor.default_originate:
            do_cli = f"neighbor {neighbor_ip_address} default-originate"
            if neighbor.default_originate.route_map is not None:
                do_cli += f" route-map {neighbor.default_originate.route_map}"
            if neighbor.default_originate.always is True:
                do_cli += " always"
            self._add(do_cli)
        self._render_af_ipv4_additional_paths_send(neighbor_ip_address, neighbor.additional_paths)
        if neighbor.next_hop.address_family_ipv6.enabled is True:
            nhv6_cli = f"neighbor {neighbor_ip_address} next-hop address-family ipv6"
            if neighbor.next_hop.address_family_ipv6.originate is True:
                nhv6_cli += " originate"
            self._add(nhv6_cli)
        elif neighbor.next_hop.address_family_ipv6.enabled is False:
            self._add(f"no neighbor {neighbor_ip_address} next-hop address-family ipv6")
        self._add("neighbor {} peer-tag in {}", neighbor_ip_address, neighbor.peer_tag_in)
        self._add("neighbor {} peer-tag out discard {}", neighbor_ip_address, neighbor.peer_tag_out_discard)

    def _render_af_ipv4_additional_paths_send(self, entity_id: str, additional_paths: Any) -> None:
        send = additional_paths.send
        send_limit = additional_paths.send_limit
        prefix_list = additional_paths.prefix_list
        if send is None:
            return
        if send == "disabled":
            self._add(f"no neighbor {entity_id} additional-paths send")
            return
        cmd = None
        if send == "ecmp" and send_limit is not None:
            cmd = f"neighbor {entity_id} additional-paths send ecmp limit {send_limit}"
        elif send == "limit":
            if send_limit is not None:
                cmd = f"neighbor {entity_id} additional-paths send limit {send_limit}"
        else:
            cmd = f"neighbor {entity_id} additional-paths send {send}"
        if cmd is not None:
            if prefix_list is not None:
                cmd += f" prefix-list {prefix_list}"
            self._add(cmd)

    def _render_af_ipv4_redistribute(self, redistribute: Any) -> None:
        if redistribute.attached_host.enabled is True:
            cli = "redistribute attached-host"
            if redistribute.attached_host.route_map is not None:
                cli += f" route-map {redistribute.attached_host.route_map}"
            self._add(cli)

        if redistribute.bgp.enabled is True:
            cli = "redistribute bgp leaked"
            if redistribute.bgp.route_map is not None:
                cli += f" route-map {redistribute.bgp.route_map}"
            self._add(cli)

        if redistribute.connected.enabled is True:
            cli = "redistribute connected"
            if redistribute.connected.include_leaked is True:
                cli += " include leaked"
            if redistribute.connected.route_map is not None:
                cli += f" route-map {redistribute.connected.route_map}"
            elif redistribute.connected.rcf is not None:
                cli += f" rcf {redistribute.connected.rcf}"
            self._add(cli)

        if redistribute.dynamic.enabled is True:
            cli = "redistribute dynamic"
            if redistribute.dynamic.route_map is not None:
                cli += f" route-map {redistribute.dynamic.route_map}"
            elif redistribute.dynamic.rcf is not None:
                cli += f" rcf {redistribute.dynamic.rcf}"
            self._add(cli)

        if redistribute.user.enabled is True:
            cli = "redistribute user"
            if redistribute.user.rcf is not None:
                cli += f" rcf {redistribute.user.rcf}"
            self._add(cli)

        if redistribute.isis.enabled is True:
            cli = "redistribute isis"
            if redistribute.isis.isis_level is not None:
                cli += f" {redistribute.isis.isis_level}"
            if redistribute.isis.include_leaked is True:
                cli += " include leaked"
            if redistribute.isis.route_map is not None:
                cli += f" route-map {redistribute.isis.route_map}"
            elif redistribute.isis.rcf is not None:
                cli += f" rcf {redistribute.isis.rcf}"
            self._add(cli)

        if redistribute.ospf.enabled is True:
            cli = "redistribute ospf"
            if redistribute.ospf.include_leaked is True:
                cli += " include leaked"
            if redistribute.ospf.route_map is not None:
                cli += f" route-map {redistribute.ospf.route_map}"
            self._add(cli)
        elif redistribute.ospf.match_internal.enabled is True:
            cli = "redistribute ospf match internal"
            if redistribute.ospf.match_internal.include_leaked is True:
                cli += " include leaked"
            if redistribute.ospf.match_internal.route_map is not None:
                cli += f" route-map {redistribute.ospf.match_internal.route_map}"
            self._add(cli)

        if redistribute.ospfv3.enabled is True:
            cli = "redistribute ospfv3"
            if redistribute.ospfv3.include_leaked is True:
                cli += " include leaked"
            if redistribute.ospfv3.route_map is not None:
                cli += f" route-map {redistribute.ospfv3.route_map}"
            self._add(cli)
        elif redistribute.ospfv3.match_internal.enabled is True:
            cli = "redistribute ospfv3 match internal"
            if redistribute.ospfv3.match_internal.include_leaked is True:
                cli += " include leaked"
            if redistribute.ospfv3.match_internal.route_map is not None:
                cli += f" route-map {redistribute.ospfv3.match_internal.route_map}"
            self._add(cli)

        if redistribute.ospfv3.match_external.enabled is True:
            cli = "redistribute ospfv3 match external"
            if redistribute.ospfv3.match_external.include_leaked is True:
                cli += " include leaked"
            if redistribute.ospfv3.match_external.route_map is not None:
                cli += f" route-map {redistribute.ospfv3.match_external.route_map}"
            self._add(cli)

        if redistribute.ospfv3.match_nssa_external.enabled is True:
            cli = "redistribute ospfv3 match nssa-external"
            if redistribute.ospfv3.match_nssa_external.nssa_type is not None:
                cli += f" {redistribute.ospfv3.match_nssa_external.nssa_type}"
            if redistribute.ospfv3.match_nssa_external.include_leaked is True:
                cli += " include leaked"
            if redistribute.ospfv3.match_nssa_external.route_map is not None:
                cli += f" route-map {redistribute.ospfv3.match_nssa_external.route_map}"
            self._add(cli)

        if redistribute.ospf.match_external.enabled is True:
            cli = "redistribute ospf match external"
            if redistribute.ospf.match_external.include_leaked is True:
                cli += " include leaked"
            if redistribute.ospf.match_external.route_map is not None:
                cli += f" route-map {redistribute.ospf.match_external.route_map}"
            self._add(cli)

        if redistribute.ospf.match_nssa_external.enabled is True:
            cli = "redistribute ospf match nssa-external"
            if redistribute.ospf.match_nssa_external.nssa_type is not None:
                cli += f" {redistribute.ospf.match_nssa_external.nssa_type}"
            if redistribute.ospf.match_nssa_external.include_leaked is True:
                cli += " include leaked"
            if redistribute.ospf.match_nssa_external.route_map is not None:
                cli += f" route-map {redistribute.ospf.match_nssa_external.route_map}"
            self._add(cli)

        if redistribute.rip.enabled is True:
            cli = "redistribute rip"
            if redistribute.rip.route_map is not None:
                cli += f" route-map {redistribute.rip.route_map}"
            self._add(cli)

        if redistribute.static.enabled is True:
            cli = "redistribute static"
            if redistribute.static.include_leaked is True:
                cli += " include leaked"
            if redistribute.static.route_map is not None:
                cli += f" route-map {redistribute.static.route_map}"
            elif redistribute.static.rcf is not None:
                cli += f" rcf {redistribute.static.rcf}"
            self._add(cli)


class RouterBgpAddressFamilyIpv4LabeledUnicast(CliSection):
    """Renders the 'address-family ipv4 labeled-unicast' block inside 'router bgp'."""

    def __init__(self, bgp: Any) -> None:
        self.bgp = bgp

    def _generate(self) -> None:
        address_family = self.bgp.address_family_ipv4_labeled_unicast
        if not address_family:
            return
        self._header("address-family ipv4 labeled-unicast")
        self._add("update wait-for-convergence", address_family.update_wait_for_convergence)

        if address_family.bgp.missing_policy:
            for line in self._build_missing_policy_cli("bgp missing-policy", address_family.bgp.missing_policy):
                self._add(line)

        self._add("bgp additional-paths receive", address_family.bgp.additional_paths.receive)
        self._render_af_bgp_additional_paths_send(address_family.bgp.additional_paths)
        self._add("bgp next-hop-unchanged", address_family.bgp.next_hop_unchanged)
        self._add("neighbor default next-hop-self", address_family.neighbor_default.next_hop_self)

        next_hop_ribs = address_family.next_hop_resolution_ribs
        if next_hop_ribs:
            rib_tokens: list[str] = []
            for rib in next_hop_ribs:
                if rib.rib_type == "tunnel-rib-colored":
                    rib_tokens.append("tunnel-rib colored system-colored-tunnel-rib")
                elif rib.rib_type == "tunnel-rib":
                    if rib.rib_name is not None:
                        rib_tokens.append(f"tunnel-rib {rib.rib_name}")
                elif rib.rib_type is not None:
                    rib_tokens.append(rib.rib_type)
            if rib_tokens:
                self._add(f"next-hop resolution ribs {' '.join(rib_tokens)}")

        for peer_group in natural_sort(address_family.peer_groups or [], sort_key="name"):
            self._render_af_lu_entity(peer_group.name, peer_group)

        for neighbor in natural_sort(address_family.neighbors or [], sort_key="ip_address"):
            self._render_af_lu_entity(neighbor.ip_address, neighbor)

        for network in address_family.networks or []:
            cli = f"network {network.prefix}"
            if network.route_map is not None:
                cli += f" route-map {network.route_map}"
            elif network.rcf is not None:
                cli += f" rcf {network.rcf}"
            self._add(cli)

        for next_hop in address_family.next_hops or []:
            cli = f"next-hop {next_hop.ip_address} originate"
            if next_hop.lfib_backup_ip_forwarding is True:
                cli += " lfib-backup ip-forwarding"
            self._add(cli)

        self._add("lfib entry installation skipped", address_family.lfib_entry_installation_skipped)
        self._add("label local-termination {}", address_family.label_local_termination)
        self._add("graceful-restart", address_family.graceful_restart)

        for tunnel_protocol in address_family.tunnel_source_protocols or []:
            cli = f"tunnel source-protocol {tunnel_protocol.protocol}"
            if tunnel_protocol.rcf is not None:
                cli += f" rcf {tunnel_protocol.rcf}"
            self._add(cli)

        aigp_session = address_family.aigp_session
        if aigp_session:
            for session_type in ["ibgp", "confederation", "ebgp"]:
                if getattr(aigp_session, session_type, None) is True:
                    self._add(f"aigp-session {session_type}")

    def _render_af_bgp_additional_paths_send(self, additional_paths: Any) -> None:
        send = additional_paths.send
        send_limit = additional_paths.send_limit
        if send is None:
            return
        if send == "disabled":
            self._add("no bgp additional-paths send")
        elif send == "ecmp" and send_limit is not None:
            self._add(f"bgp additional-paths send ecmp limit {send_limit}")
        elif send == "limit" and send_limit is not None:
            self._add(f"bgp additional-paths send limit {send_limit}")
        else:
            self._add(f"bgp additional-paths send {send}")

    def _render_af_neighbor_additional_paths_send(self, entity_id: str, additional_paths: Any) -> None:
        send = additional_paths.send
        send_limit = additional_paths.send_limit
        if send is None:
            return
        if send == "disabled":
            self._add(f"no neighbor {entity_id} additional-paths send")
        elif send == "ecmp" and send_limit is not None:
            self._add(f"neighbor {entity_id} additional-paths send ecmp limit {send_limit}")
        elif send == "limit":
            self._add("neighbor {} additional-paths send limit {}", entity_id, send_limit)
        else:
            self._add(f"neighbor {entity_id} additional-paths send {send}")

    def _build_missing_policy_cli(self, prefix: str, missing_policy: Any, double_space_before_include: bool = False) -> list[str]:
        lines: list[str] = []
        for direction in ["in", "out"]:
            policy = getattr(missing_policy, f"direction_{direction}", None)
            if policy is None or policy.action is None:
                continue
            cli = prefix
            if policy.include_community_list is True or policy.include_prefix_list is True or policy.include_sub_route_map is True:
                cli += "  include" if double_space_before_include else " include"
                if policy.include_community_list is True:
                    cli += " community-list"
                if policy.include_prefix_list is True:
                    cli += " prefix-list"
                if policy.include_sub_route_map is True:
                    cli += " sub-route-map"
            cli += f" direction {direction} action {policy.action}"
            lines.append(cli)
        return lines

    def _render_af_lu_entity(self, entity_id: str, entity: Any) -> None:
        if entity.activate is True:
            self._add(f"neighbor {entity_id} activate")
        else:
            self._add(f"no neighbor {entity_id} activate")

        if entity.additional_paths.receive is True:
            self._add(f"neighbor {entity_id} additional-paths receive")

        if entity.graceful_restart is True:
            self._add(f"neighbor {entity_id} graceful-restart")

        self._add("neighbor {} graceful-restart-helper stale-route route-map {}", entity_id, entity.graceful_restart_helper.stale_route_map)
        self._add("neighbor {} route-map {} in", entity_id, entity.route_map_in)
        self._add("neighbor {} route-map {} out", entity_id, entity.route_map_out)
        self._add("neighbor {} rcf in {}", entity_id, entity.rcf_in)
        self._add("neighbor {} rcf out {}", entity_id, entity.rcf_out)
        self._render_af_neighbor_additional_paths_send(entity_id, entity.additional_paths)

        if entity.next_hop_unchanged is True:
            self._add(f"neighbor {entity_id} next-hop-unchanged")

        if entity.next_hop_self is True:
            self._add(f"neighbor {entity_id} next-hop-self")

        if entity.next_hop_self_v4_mapped_v6_source_interface is not None:
            self._add(f"neighbor {entity_id} next-hop-self v4-mapped-v6 source-interface {entity.next_hop_self_v4_mapped_v6_source_interface}")
        elif entity.next_hop_self_source_interface is not None:
            self._add(f"neighbor {entity_id} next-hop-self source-interface {entity.next_hop_self_source_interface}")

        if entity.maximum_advertised_routes is not None:
            cli = f"neighbor {entity_id} maximum-advertised-routes {entity.maximum_advertised_routes}"
            if entity.maximum_advertised_routes_warning_limit is not None:
                cli += f" warning-limit {entity.maximum_advertised_routes_warning_limit}"
            self._add(cli)

        if entity.missing_policy:
            for line in self._build_missing_policy_cli(f"neighbor {entity_id} missing-policy", entity.missing_policy, double_space_before_include=True):
                self._add(line)

        self._add("neighbor {} peer-tag in {}", entity_id, entity.peer_tag_in)
        self._add("neighbor {} peer-tag out discard {}", entity_id, entity.peer_tag_out_discard)

        if entity.aigp_session is True:
            self._add(f"neighbor {entity_id} aigp-session")

        if entity.multi_path is True:
            self._add(f"neighbor {entity_id} multi-path")


class RouterBgpAddressFamilyIpv4Multicast(CliSection):
    """Renders the 'address-family ipv4 multicast' block inside 'router bgp'."""

    def __init__(self, bgp: Any) -> None:
        self.bgp = bgp

    def _generate(self) -> None:
        address_family = self.bgp.address_family_ipv4_multicast
        if not address_family:
            return
        self._header("address-family ipv4 multicast")
        self._add("bgp additional-paths receive", address_family.bgp.additional_paths.receive)

        for peer_group in natural_sort(address_family.peer_groups or [], sort_key="name"):
            self._render_af_ipv4mc_entity(peer_group.name, peer_group)

        for neighbor in natural_sort(address_family.neighbors or [], sort_key="ip_address"):
            self._render_af_ipv4mc_entity(neighbor.ip_address, neighbor)

        if address_family.redistribute:
            self._render_af_ipv4mc_redistribute(address_family.redistribute)

    def _render_af_ipv4mc_entity(self, entity_id: str, entity: Any) -> None:
        if entity.activate is True:
            self._add(f"neighbor {entity_id} activate")
        elif entity.activate is False:
            self._add(f"no neighbor {entity_id} activate")

        if entity.additional_paths.receive is True:
            self._add(f"neighbor {entity_id} additional-paths receive")

        self._add("neighbor {} route-map {} in", entity_id, entity.route_map_in)
        self._add("neighbor {} route-map {} out", entity_id, entity.route_map_out)
        self._add("neighbor {} peer-tag in {}", entity_id, entity.peer_tag_in)
        self._add("neighbor {} peer-tag out discard {}", entity_id, entity.peer_tag_out_discard)

    def _render_af_ipv4mc_redistribute(self, redistribute: Any) -> None:
        if redistribute.attached_host.enabled is True:
            cli = "redistribute attached-host"
            if redistribute.attached_host.route_map is not None:
                cli += f" route-map {redistribute.attached_host.route_map}"
            self._add(cli)

        if redistribute.connected.enabled is True:
            cli = "redistribute connected"
            if redistribute.connected.route_map is not None:
                cli += f" route-map {redistribute.connected.route_map}"
            self._add(cli)

        if redistribute.isis.enabled is True:
            cli = "redistribute isis"
            if redistribute.isis.isis_level is not None:
                cli += f" {redistribute.isis.isis_level}"
            if redistribute.isis.include_leaked is True:
                cli += " include leaked"
            if redistribute.isis.route_map is not None:
                cli += f" route-map {redistribute.isis.route_map}"
            elif redistribute.isis.rcf is not None:
                cli += f" rcf {redistribute.isis.rcf}"
            self._add(cli)

        if redistribute.ospf.enabled is True:
            cli = "redistribute ospf"
            if redistribute.ospf.route_map is not None:
                cli += f" route-map {redistribute.ospf.route_map}"
            self._add(cli)
        elif redistribute.ospf.match_internal.enabled is True:
            cli = "redistribute ospf match internal"
            if redistribute.ospf.match_internal.route_map is not None:
                cli += f" route-map {redistribute.ospf.match_internal.route_map}"
            self._add(cli)

        if redistribute.ospfv3.enabled is True:
            cli = "redistribute ospfv3"
            if redistribute.ospfv3.route_map is not None:
                cli += f" route-map {redistribute.ospfv3.route_map}"
            self._add(cli)
        elif redistribute.ospfv3.match_internal.enabled is True:
            cli = "redistribute ospfv3 match internal"
            if redistribute.ospfv3.match_internal.route_map is not None:
                cli += f" route-map {redistribute.ospfv3.match_internal.route_map}"
            self._add(cli)

        if redistribute.ospfv3.match_external.enabled is True:
            cli = "redistribute ospfv3 match external"
            if redistribute.ospfv3.match_external.route_map is not None:
                cli += f" route-map {redistribute.ospfv3.match_external.route_map}"
            self._add(cli)

        if redistribute.ospfv3.match_nssa_external.enabled is True:
            cli = "redistribute ospfv3 match nssa-external"
            if redistribute.ospfv3.match_nssa_external.nssa_type is not None:
                cli += f" {redistribute.ospfv3.match_nssa_external.nssa_type}"
            if redistribute.ospfv3.match_nssa_external.route_map is not None:
                cli += f" route-map {redistribute.ospfv3.match_nssa_external.route_map}"
            self._add(cli)

        if redistribute.ospf.match_external.enabled is True:
            cli = "redistribute ospf match external"
            if redistribute.ospf.match_external.route_map is not None:
                cli += f" route-map {redistribute.ospf.match_external.route_map}"
            self._add(cli)

        if redistribute.ospf.match_nssa_external.enabled is True:
            cli = "redistribute ospf match nssa-external"
            if redistribute.ospf.match_nssa_external.nssa_type is not None:
                cli += f" {redistribute.ospf.match_nssa_external.nssa_type}"
            if redistribute.ospf.match_nssa_external.route_map is not None:
                cli += f" route-map {redistribute.ospf.match_nssa_external.route_map}"
            self._add(cli)

        if redistribute.static.enabled is True:
            cli = "redistribute static"
            if redistribute.static.route_map is not None:
                cli += f" route-map {redistribute.static.route_map}"
            self._add(cli)


class RouterBgpAddressFamilyIpv4SrTe(CliSection):
    """Renders the 'address-family ipv4 sr-te' block inside 'router bgp'."""

    def __init__(self, bgp: Any) -> None:
        self.bgp = bgp

    def _generate(self) -> None:
        address_family = self.bgp.address_family_ipv4_sr_te
        if not address_family:
            return
        self._header("address-family ipv4 sr-te")
        for peer_group in natural_sort(address_family.peer_groups or [], sort_key="name"):
            self._render_af_sr_te_entity(peer_group.name, peer_group)
        for neighbor in natural_sort(address_family.neighbors or [], sort_key="ip_address"):
            self._render_af_sr_te_entity(neighbor.ip_address, neighbor)

    def _render_af_sr_te_entity(self, entity_id: str, entity: Any) -> None:
        if entity.activate is True:
            self._add(f"neighbor {entity_id} activate")
        elif entity.activate is False:
            self._add(f"no neighbor {entity_id} activate")
        self._add("neighbor {} route-map {} in", entity_id, entity.route_map_in)
        self._add("neighbor {} route-map {} out", entity_id, entity.route_map_out)
        self._add("neighbor {} peer-tag in {}", entity_id, entity.peer_tag_in)
        self._add("neighbor {} peer-tag out discard {}", entity_id, entity.peer_tag_out_discard)


class RouterBgpAddressFamilyIpv6(CliSection):
    """Renders the 'address-family ipv6' block inside 'router bgp'."""

    def __init__(self, bgp: Any) -> None:
        self.bgp = bgp

    def _generate(self) -> None:
        address_family = self.bgp.address_family_ipv6
        if not address_family:
            return
        self._header("address-family ipv6")
        if address_family.bgp.additional_paths.install is True:
            self._add("bgp additional-paths install")
        elif address_family.bgp.additional_paths.install_ecmp_primary is True:
            self._add("bgp additional-paths install ecmp-primary")

        self._add("bgp additional-paths receive", address_family.bgp.additional_paths.receive)
        self._render_af_bgp_additional_paths_send(address_family.bgp.additional_paths)

        bg_prefix_list = getattr(address_family.bgp.additional_paths, "prefix_list", None)

        for peer_group in natural_sort(address_family.peer_groups or [], sort_key="name"):
            self._render_af_ipv6_entity(peer_group.name, peer_group, bg_prefix_list)

        for neighbor in natural_sort(address_family.neighbors or [], sort_key="ip_address"):
            self._render_af_ipv6_entity(neighbor.ip_address, neighbor, bg_prefix_list)

        for network in natural_sort(address_family.networks or [], sort_key="prefix"):
            cli = f"network {network.prefix}"
            if network.route_map is not None:
                cli += f" route-map {network.route_map}"
            elif network.rcf is not None:
                cli += f" rcf {network.rcf}"
            self._add(cli)

        if address_family.bgp.redistribute_internal is True:
            self._add("bgp redistribute-internal")
        elif address_family.bgp.redistribute_internal is False:
            self._add("no bgp redistribute-internal")

        if address_family.redistribute:
            self._render_af_ipv6_redistribute(address_family.redistribute)

    def _render_af_bgp_additional_paths_send(self, additional_paths: Any) -> None:
        send = additional_paths.send
        send_limit = additional_paths.send_limit
        if send is None:
            return
        if send == "disabled":
            self._add("no bgp additional-paths send")
        elif send == "ecmp" and send_limit is not None:
            self._add(f"bgp additional-paths send ecmp limit {send_limit}")
        elif send == "limit" and send_limit is not None:
            self._add(f"bgp additional-paths send limit {send_limit}")
        else:
            self._add(f"bgp additional-paths send {send}")

    def _render_af_ipv6_entity(self, entity_id: str, entity: Any, bg_prefix_list: str | None) -> None:
        if entity.activate is True:
            self._add(f"neighbor {entity_id} activate")
        elif entity.activate is False:
            self._add(f"no neighbor {entity_id} activate")

        if entity.additional_paths.receive is True:
            self._add(f"neighbor {entity_id} additional-paths receive")

        self._add("neighbor {} route-map {} in", entity_id, entity.route_map_in)
        self._add("neighbor {} route-map {} out", entity_id, entity.route_map_out)
        self._add("neighbor {} rcf in {}", entity_id, entity.rcf_in)
        self._add("neighbor {} rcf out {}", entity_id, entity.rcf_out)
        self._add("neighbor {} prefix-list {} in", entity_id, entity.prefix_list_in)
        self._add("neighbor {} prefix-list {} out", entity_id, entity.prefix_list_out)

        default_originate = getattr(entity, "default_originate", None)
        if default_originate:
            do_cli = f"neighbor {entity_id} default-originate"
            if default_originate.route_map is not None:
                do_cli += f" route-map {default_originate.route_map}"
            if default_originate.always is True:
                do_cli += " always"
            self._add(do_cli)

        send = entity.additional_paths.send
        send_limit = entity.additional_paths.send_limit
        if send is not None:
            if send == "disabled":
                self._add(f"no neighbor {entity_id} additional-paths send")
            else:
                cmd: str | None = None
                if send == "ecmp" and send_limit is not None:
                    cmd = f"neighbor {entity_id} additional-paths send ecmp limit {send_limit}"
                elif send == "limit":
                    if send_limit is not None:
                        cmd = f"neighbor {entity_id} additional-paths send limit {send_limit}"
                else:
                    cmd = f"neighbor {entity_id} additional-paths send {send}"
                if cmd is not None:
                    if bg_prefix_list is not None:
                        cmd += f" prefix-list {bg_prefix_list}"
                    self._add(cmd)

        self._add("neighbor {} peer-tag in {}", entity_id, entity.peer_tag_in)
        self._add("neighbor {} peer-tag out discard {}", entity_id, entity.peer_tag_out_discard)

    def _render_af_ipv6_redistribute(self, redistribute: Any) -> None:
        if redistribute.attached_host.enabled is True:
            cli = "redistribute attached-host"
            if redistribute.attached_host.route_map is not None:
                cli += f" route-map {redistribute.attached_host.route_map}"
            self._add(cli)

        if redistribute.bgp.enabled is True:
            cli = "redistribute bgp leaked"
            if redistribute.bgp.route_map is not None:
                cli += f" route-map {redistribute.bgp.route_map}"
            self._add(cli)

        if redistribute.dhcp.enabled is True:
            cli = "redistribute dhcp"
            if redistribute.dhcp.route_map is not None:
                cli += f" route-map {redistribute.dhcp.route_map}"
            self._add(cli)

        if redistribute.connected.enabled is True:
            cli = "redistribute connected"
            if redistribute.connected.include_leaked is True:
                cli += " include leaked"
            if redistribute.connected.route_map is not None:
                cli += f" route-map {redistribute.connected.route_map}"
            elif redistribute.connected.rcf is not None:
                cli += f" rcf {redistribute.connected.rcf}"
            self._add(cli)

        if redistribute.dynamic.enabled is True:
            cli = "redistribute dynamic"
            if redistribute.dynamic.route_map is not None:
                cli += f" route-map {redistribute.dynamic.route_map}"
            elif redistribute.dynamic.rcf is not None:
                cli += f" rcf {redistribute.dynamic.rcf}"
            self._add(cli)

        if redistribute.user.enabled is True:
            cli = "redistribute user"
            if redistribute.user.rcf is not None:
                cli += f" rcf {redistribute.user.rcf}"
            self._add(cli)

        if redistribute.isis.enabled is True:
            cli = "redistribute isis"
            if redistribute.isis.isis_level is not None:
                cli += f" {redistribute.isis.isis_level}"
            if redistribute.isis.include_leaked is True:
                cli += " include leaked"
            if redistribute.isis.route_map is not None:
                cli += f" route-map {redistribute.isis.route_map}"
            elif redistribute.isis.rcf is not None:
                cli += f" rcf {redistribute.isis.rcf}"
            self._add(cli)

        if redistribute.ospfv3.enabled is True:
            cli = "redistribute ospfv3"
            if redistribute.ospfv3.include_leaked is True:
                cli += " include leaked"
            if redistribute.ospfv3.route_map is not None:
                cli += f" route-map {redistribute.ospfv3.route_map}"
            self._add(cli)
        elif redistribute.ospfv3.match_internal.enabled is True:
            cli = "redistribute ospfv3 match internal"
            if redistribute.ospfv3.match_internal.include_leaked is True:
                cli += " include leaked"
            if redistribute.ospfv3.match_internal.route_map is not None:
                cli += f" route-map {redistribute.ospfv3.match_internal.route_map}"
            self._add(cli)

        if redistribute.ospfv3.match_external.enabled is True:
            cli = "redistribute ospfv3 match external"
            if redistribute.ospfv3.match_external.include_leaked is True:
                cli += " include leaked"
            if redistribute.ospfv3.match_external.route_map is not None:
                cli += f" route-map {redistribute.ospfv3.match_external.route_map}"
            self._add(cli)

        if redistribute.ospfv3.match_nssa_external.enabled is True:
            cli = "redistribute ospfv3 match nssa-external"
            if redistribute.ospfv3.match_nssa_external.nssa_type is not None:
                cli += f" {redistribute.ospfv3.match_nssa_external.nssa_type}"
            if redistribute.ospfv3.match_nssa_external.include_leaked is True:
                cli += " include leaked"
            if redistribute.ospfv3.match_nssa_external.route_map is not None:
                cli += f" route-map {redistribute.ospfv3.match_nssa_external.route_map}"
            self._add(cli)

        if redistribute.static.enabled is True:
            cli = "redistribute static"
            if redistribute.static.include_leaked is True:
                cli += " include leaked"
            if redistribute.static.route_map is not None:
                cli += f" route-map {redistribute.static.route_map}"
            elif redistribute.static.rcf is not None:
                cli += f" rcf {redistribute.static.rcf}"
            self._add(cli)


class RouterBgpAddressFamilyIpv6Multicast(CliSection):
    """Renders the 'address-family ipv6 multicast' block inside 'router bgp'."""

    def __init__(self, bgp: Any) -> None:
        self.bgp = bgp

    def _generate(self) -> None:
        address_family = self.bgp.address_family_ipv6_multicast
        if not address_family:
            return
        self._header("address-family ipv6 multicast")
        self._add("bgp missing-policy direction in action {}", address_family.bgp.missing_policy.direction_in_action)
        self._add("bgp missing-policy direction out action {}", address_family.bgp.missing_policy.direction_out_action)
        self._add("bgp additional-paths receive", address_family.bgp.additional_paths.receive)

        for peer_group in natural_sort(address_family.peer_groups or [], sort_key="name"):
            if peer_group.activate is True:
                self._add(f"neighbor {peer_group.name} activate")
            elif peer_group.activate is False:
                self._add(f"no neighbor {peer_group.name} activate")
            if peer_group.additional_paths.receive is True:
                self._add(f"neighbor {peer_group.name} additional-paths receive")

        for neighbor in natural_sort(address_family.neighbors or [], sort_key="ip_address"):
            if neighbor.activate is True:
                self._add(f"neighbor {neighbor.ip_address} activate")
            if neighbor.additional_paths.receive is True:
                self._add(f"neighbor {neighbor.ip_address} additional-paths receive")
            self._add("neighbor {} route-map {} in", neighbor.ip_address, neighbor.route_map_in)
            self._add("neighbor {} route-map {} out", neighbor.ip_address, neighbor.route_map_out)
            self._add("neighbor {} peer-tag in {}", neighbor.ip_address, neighbor.peer_tag_in)
            self._add("neighbor {} peer-tag out discard {}", neighbor.ip_address, neighbor.peer_tag_out_discard)

        for network in natural_sort(address_family.networks or [], sort_key="prefix"):
            cli = f"network {network.prefix}"
            if network.route_map is not None:
                cli += f" route-map {network.route_map}"
            self._add(cli)

        if address_family.redistribute:
            self._render_af_ipv6mc_redistribute(address_family.redistribute)

    def _render_af_ipv6mc_redistribute(self, redistribute: Any) -> None:
        if redistribute.connected.enabled is True:
            cli = "redistribute connected"
            if redistribute.connected.route_map is not None:
                cli += f" route-map {redistribute.connected.route_map}"
            self._add(cli)

        if redistribute.isis.enabled is True:
            cli = "redistribute isis"
            if redistribute.isis.isis_level is not None:
                cli += f" {redistribute.isis.isis_level}"
            if redistribute.isis.include_leaked is True:
                cli += " include leaked"
            if redistribute.isis.route_map is not None:
                cli += f" route-map {redistribute.isis.route_map}"
            elif redistribute.isis.rcf is not None:
                cli += f" rcf {redistribute.isis.rcf}"
            self._add(cli)

        if redistribute.ospf.enabled is True:
            cli = "redistribute ospf"
            if redistribute.ospf.route_map is not None:
                cli += f" route-map {redistribute.ospf.route_map}"
            self._add(cli)
        elif redistribute.ospf.match_internal.enabled is True:
            cli = "redistribute ospf match internal"
            if redistribute.ospf.match_internal.route_map is not None:
                cli += f" route-map {redistribute.ospf.match_internal.route_map}"
            self._add(cli)

        if redistribute.ospfv3.enabled is True:
            cli = "redistribute ospfv3"
            if redistribute.ospfv3.route_map is not None:
                cli += f" route-map {redistribute.ospfv3.route_map}"
            self._add(cli)
        elif redistribute.ospfv3.match_internal.enabled is True:
            cli = "redistribute ospfv3 match internal"
            if redistribute.ospfv3.match_internal.route_map is not None:
                cli += f" route-map {redistribute.ospfv3.match_internal.route_map}"
            self._add(cli)

        if redistribute.ospfv3.match_external.enabled is True:
            cli = "redistribute ospfv3 match external"
            if redistribute.ospfv3.match_external.route_map is not None:
                cli += f" route-map {redistribute.ospfv3.match_external.route_map}"
            self._add(cli)

        if redistribute.ospfv3.match_nssa_external.enabled is True:
            cli = "redistribute ospfv3 match nssa-external"
            if redistribute.ospfv3.match_nssa_external.nssa_type is not None:
                cli += f" {redistribute.ospfv3.match_nssa_external.nssa_type}"
            if redistribute.ospfv3.match_nssa_external.route_map is not None:
                cli += f" route-map {redistribute.ospfv3.match_nssa_external.route_map}"
            self._add(cli)

        if redistribute.ospf.match_external.enabled is True:
            cli = "redistribute ospf match external"
            if redistribute.ospf.match_external.route_map is not None:
                cli += f" route-map {redistribute.ospf.match_external.route_map}"
            self._add(cli)

        if redistribute.ospf.match_nssa_external.enabled is True:
            cli = "redistribute ospf match nssa-external"
            if redistribute.ospf.match_nssa_external.nssa_type is not None:
                cli += f" {redistribute.ospf.match_nssa_external.nssa_type}"
            if redistribute.ospf.match_nssa_external.route_map is not None:
                cli += f" route-map {redistribute.ospf.match_nssa_external.route_map}"
            self._add(cli)

        if redistribute.static.enabled is True:
            cli = "redistribute static"
            if redistribute.static.route_map is not None:
                cli += f" route-map {redistribute.static.route_map}"
            self._add(cli)


class RouterBgpAddressFamilyIpv6SrTe(CliSection):
    """Renders the 'address-family ipv6 sr-te' block inside 'router bgp'."""

    def __init__(self, bgp: Any) -> None:
        self.bgp = bgp

    def _generate(self) -> None:
        address_family = self.bgp.address_family_ipv6_sr_te
        if not address_family:
            return
        self._header("address-family ipv6 sr-te")
        for peer_group in natural_sort(address_family.peer_groups or [], sort_key="name"):
            self._render_af_sr_te_entity(peer_group.name, peer_group)
        for neighbor in natural_sort(address_family.neighbors or [], sort_key="ip_address"):
            self._render_af_sr_te_entity(neighbor.ip_address, neighbor)

    def _render_af_sr_te_entity(self, entity_id: str, entity: Any) -> None:
        if entity.activate is True:
            self._add(f"neighbor {entity_id} activate")
        elif entity.activate is False:
            self._add(f"no neighbor {entity_id} activate")
        self._add("neighbor {} route-map {} in", entity_id, entity.route_map_in)
        self._add("neighbor {} route-map {} out", entity_id, entity.route_map_out)
        self._add("neighbor {} peer-tag in {}", entity_id, entity.peer_tag_in)
        self._add("neighbor {} peer-tag out discard {}", entity_id, entity.peer_tag_out_discard)


class RouterBgpAddressFamilyLinkState(CliSection):
    """Renders the 'address-family link-state' block inside 'router bgp'."""

    def __init__(self, bgp: Any) -> None:
        self.bgp = bgp

    def _generate(self) -> None:
        address_family = self.bgp.address_family_link_state
        if not address_family:
            return
        self._header("address-family link-state")
        self._add("bgp missing-policy direction in action {}", address_family.bgp.missing_policy.direction_in_action)
        self._add("bgp missing-policy direction out action {}", address_family.bgp.missing_policy.direction_out_action)

        for peer_group in natural_sort(address_family.peer_groups or [], sort_key="name"):
            if peer_group.activate is True:
                self._add(f"neighbor {peer_group.name} activate")
            elif peer_group.activate is False:
                self._add(f"no neighbor {peer_group.name} activate")
            self._add("neighbor {} missing-policy direction in action {}", peer_group.name, peer_group.missing_policy.direction_in_action)
            self._add("neighbor {} missing-policy direction out action {}", peer_group.name, peer_group.missing_policy.direction_out_action)

        for neighbor in natural_sort(address_family.neighbors or [], sort_key="ip_address"):
            if neighbor.activate is True:
                self._add(f"neighbor {neighbor.ip_address} activate")
            self._add("neighbor {} missing-policy direction in action {}", neighbor.ip_address, neighbor.missing_policy.direction_in_action)
            self._add("neighbor {} missing-policy direction out action {}", neighbor.ip_address, neighbor.missing_policy.direction_out_action)

        path_selection = address_family.path_selection
        if path_selection:
            roles = path_selection.roles
            self._add("path-selection", roles.producer)
            if roles.consumer is True or roles.propagator is True:
                cli = "path-selection role"
                if roles.consumer is True:
                    cli += " consumer"
                if roles.propagator is True:
                    cli += " propagator"
                self._add(cli)


class RouterBgpAddressFamilyPathSelection(CliSection):
    """Renders the 'address-family path-selection' block inside 'router bgp'."""

    def __init__(self, bgp: Any) -> None:
        self.bgp = bgp

    def _generate(self) -> None:
        address_family = self.bgp.address_family_path_selection
        if not address_family:
            return
        self._header("address-family path-selection")
        self._add("bgp additional-paths receive", address_family.bgp.additional_paths.receive)
        self._render_af_bgp_additional_paths_send(address_family.bgp.additional_paths)

        for peer_group in natural_sort(address_family.peer_groups or [], sort_key="name"):
            if peer_group.activate is True:
                self._add(f"neighbor {peer_group.name} activate")
            elif peer_group.activate is False:
                self._add(f"no neighbor {peer_group.name} activate")
            if peer_group.additional_paths.receive is True:
                self._add(f"neighbor {peer_group.name} additional-paths receive")
            send = peer_group.additional_paths.send
            send_limit = peer_group.additional_paths.send_limit
            if send is not None:
                if send == "disabled":
                    self._add(f"no neighbor {peer_group.name} additional-paths send")
                elif send_limit is not None:
                    if send == "ecmp":
                        self._add(f"neighbor {peer_group.name} additional-paths send ecmp limit {send_limit}")
                    elif send == "limit":
                        self._add(f"neighbor {peer_group.name} additional-paths send limit {send_limit}")
                else:
                    self._add(f"neighbor {peer_group.name} additional-paths send {send}")

        for neighbor in natural_sort(address_family.neighbors or [], sort_key="ip_address"):
            if neighbor.activate is True:
                self._add(f"neighbor {neighbor.ip_address} activate")
            elif neighbor.activate is False:
                self._add(f"no neighbor {neighbor.ip_address} activate")
            if neighbor.additional_paths.receive is True:
                self._add(f"neighbor {neighbor.ip_address} additional-paths receive")
            self._render_af_neighbor_additional_paths_send(neighbor.ip_address, neighbor.additional_paths)

    def _render_af_bgp_additional_paths_send(self, additional_paths: Any) -> None:
        send = additional_paths.send
        send_limit = additional_paths.send_limit
        if send is None:
            return
        if send == "disabled":
            self._add("no bgp additional-paths send")
        elif send == "ecmp" and send_limit is not None:
            self._add(f"bgp additional-paths send ecmp limit {send_limit}")
        elif send == "limit" and send_limit is not None:
            self._add(f"bgp additional-paths send limit {send_limit}")
        else:
            self._add(f"bgp additional-paths send {send}")

    def _render_af_neighbor_additional_paths_send(self, entity_id: str, additional_paths: Any) -> None:
        send = additional_paths.send
        send_limit = additional_paths.send_limit
        if send is None:
            return
        if send == "disabled":
            self._add(f"no neighbor {entity_id} additional-paths send")
        elif send == "ecmp" and send_limit is not None:
            self._add(f"neighbor {entity_id} additional-paths send ecmp limit {send_limit}")
        elif send == "limit":
            self._add("neighbor {} additional-paths send limit {}", entity_id, send_limit)
        else:
            self._add(f"neighbor {entity_id} additional-paths send {send}")


class RouterBgpAddressFamilyRtc(CliSection):
    """Renders the 'address-family rt-membership' block inside 'router bgp'."""

    def __init__(self, bgp: Any) -> None:
        self.bgp = bgp

    def _generate(self) -> None:
        address_family = self.bgp.address_family_rtc
        if not address_family:
            return
        self._header("address-family rt-membership")
        for peer_group in natural_sort(address_family.peer_groups or [], sort_key="name"):
            if peer_group.activate is True:
                self._add(f"neighbor {peer_group.name} activate")
            elif peer_group.activate is False:
                self._add(f"no neighbor {peer_group.name} activate")
            if peer_group._get_defined_attr("default_route_target") is not Undefined:
                default_rt = peer_group.default_route_target
                if default_rt is not None and default_rt.only is True:
                    self._add(f"neighbor {peer_group.name} default-route-target only")
                else:
                    self._add(f"neighbor {peer_group.name} default-route-target")
                if default_rt is not None and default_rt._get_defined_attr("encoding_origin_as_omit") is not Undefined:
                    self._add(f"neighbor {peer_group.name} default-route-target encoding origin-as omit")


class RouterBgpAddressFamilyVpnIpv4(CliSection):
    """Renders the 'address-family vpn-ipv4' block inside 'router bgp'."""

    def __init__(self, bgp: Any) -> None:
        self.bgp = bgp

    def _generate(self) -> None:
        address_family = self.bgp.address_family_vpn_ipv4
        if not address_family:
            return
        self._header("address-family vpn-ipv4")
        for peer_group in natural_sort(address_family.peer_groups or [], sort_key="name"):
            self._render_af_vpn_entity(peer_group.name, peer_group)
        for neighbor in natural_sort(address_family.neighbors or [], sort_key="ip_address"):
            self._render_af_vpn_entity(neighbor.ip_address, neighbor)
        if address_family.neighbor_default_encapsulation_mpls_next_hop_self.source_interface is not None:
            src_iface = address_family.neighbor_default_encapsulation_mpls_next_hop_self.source_interface
            self._add(f"neighbor default encapsulation mpls next-hop-self source-interface {src_iface}")
        self._add("domain identifier {}", address_family.domain_identifier)
        if address_family.route.import_match_failure_action == "discard":
            self._add("route import match-failure action discard")

    def _render_af_vpn_entity(self, entity_id: str, entity: Any) -> None:
        if entity.activate is True:
            self._add(f"neighbor {entity_id} activate")
        elif entity.activate is False:
            self._add(f"no neighbor {entity_id} activate")
        self._add("neighbor {} route-map {} in", entity_id, entity.route_map_in)
        self._add("neighbor {} route-map {} out", entity_id, entity.route_map_out)
        self._add("neighbor {} rcf in {}", entity_id, entity.rcf_in)
        self._add("neighbor {} rcf out {}", entity_id, entity.rcf_out)
        if entity.default_route.enabled is True:
            cli = f"neighbor {entity_id} default-route"
            if entity.default_route.rcf is not None:
                cli += f" rcf {entity.default_route.rcf}"
            elif entity.default_route.route_map is not None:
                cli += f" route-map {entity.default_route.route_map}"
            self._add(cli)
        self._add("neighbor {} peer-tag in {}", entity_id, entity.peer_tag_in)
        self._add("neighbor {} peer-tag out discard {}", entity_id, entity.peer_tag_out_discard)


class RouterBgpAddressFamilyVpnIpv6(CliSection):
    """Renders the 'address-family vpn-ipv6' block inside 'router bgp'."""

    def __init__(self, bgp: Any) -> None:
        self.bgp = bgp

    def _generate(self) -> None:
        address_family = self.bgp.address_family_vpn_ipv6
        if not address_family:
            return
        self._header("address-family vpn-ipv6")
        for peer_group in natural_sort(address_family.peer_groups or [], sort_key="name"):
            self._render_af_vpn_entity(peer_group.name, peer_group)
        for neighbor in natural_sort(address_family.neighbors or [], sort_key="ip_address"):
            self._render_af_vpn_entity(neighbor.ip_address, neighbor)
        if address_family.neighbor_default_encapsulation_mpls_next_hop_self.source_interface is not None:
            src_iface = address_family.neighbor_default_encapsulation_mpls_next_hop_self.source_interface
            self._add(f"neighbor default encapsulation mpls next-hop-self source-interface {src_iface}")
        self._add("domain identifier {}", address_family.domain_identifier)
        if address_family.route.import_match_failure_action == "discard":
            self._add("route import match-failure action discard")

    def _render_af_vpn_entity(self, entity_id: str, entity: Any) -> None:
        if entity.activate is True:
            self._add(f"neighbor {entity_id} activate")
        elif entity.activate is False:
            self._add(f"no neighbor {entity_id} activate")
        self._add("neighbor {} route-map {} in", entity_id, entity.route_map_in)
        self._add("neighbor {} route-map {} out", entity_id, entity.route_map_out)
        self._add("neighbor {} rcf in {}", entity_id, entity.rcf_in)
        self._add("neighbor {} rcf out {}", entity_id, entity.rcf_out)
        if entity.default_route.enabled is True:
            cli = f"neighbor {entity_id} default-route"
            if entity.default_route.rcf is not None:
                cli += f" rcf {entity.default_route.rcf}"
            elif entity.default_route.route_map is not None:
                cli += f" route-map {entity.default_route.route_map}"
            self._add(cli)
        self._add("neighbor {} peer-tag in {}", entity_id, entity.peer_tag_in)
        self._add("neighbor {} peer-tag out discard {}", entity_id, entity.peer_tag_out_discard)


class RouterBgpSessionTracker(CliSection):
    """Renders a single 'session tracker X' block inside 'router bgp'."""

    separator = False

    def __init__(self, tracker: Any) -> None:
        self.tracker = tracker

    def _generate(self) -> None:
        tracker = self.tracker
        self._header(f"session tracker {tracker.name}")
        self._add("recovery delay {} seconds", tracker.recovery_delay)
