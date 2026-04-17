# Copyright (c) 2023-2026 Arista Networks, Inc.
# Use of this source code is governed by the Apache License 2.0
# that can be found in the LICENSE file.
"""Router BGP CLI configuration generator."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from pyavd._utils import Undefined
from pyavd._utils.get import get_v2
from pyavd.j2filters import hide_passwords, natural_sort

from .base import CliGenerator, CliModel, cli_config_contributor

if TYPE_CHECKING:
    from pyavd._eos_cli_config_gen.schema import EosCliConfigGen


class RouterBgpGenerator(CliGenerator):
    """
    Generator for router BGP CLI configuration.

    Single contributor method `router_bgp` orchestrates section helpers in EOS
    output order. Each helper maps to one recognisable block in the CLI output.
    """

    @property
    def _model(self) -> CliModel:
        """Router BGP config section."""
        return self.cli_config.router_bgp

    @cli_config_contributor
    def router_bgp(self) -> None:
        """Render the full 'router bgp' block in EOS output order."""
        bgp = self.data.router_bgp
        # `as` is a Python reserved word.
        if (bgp_as := get_v2(bgp, "as")) is None:
            return

        with self._block(f"router bgp {bgp_as}"):
            self._render_global_settings(bgp)
            self._render_peer_groups(bgp)
            self._render_neighbors(bgp)
            self._render_redistribute_internal(bgp)
            self._render_aggregate_addresses(bgp)
            self._render_redistribute(bgp)
            self._render_neighbor_interfaces(bgp)
            self._render_vlans(bgp)
            self._render_vpws(bgp)
            self._render_vlan_aware_bundles(bgp)
            self._render_route_distinguisher(bgp)
            self._render_address_family_evpn(bgp)
            self._render_address_family_flow_spec_ipv4(bgp)
            self._render_address_family_flow_spec_ipv6(bgp)
            self._render_address_family_ipv4(bgp)
            self._render_address_family_ipv4_labeled_unicast(bgp)
            self._render_address_family_ipv4_multicast(bgp)
            self._render_address_family_ipv4_sr_te(bgp)
            self._render_address_family_ipv6(bgp)
            self._render_address_family_ipv6_multicast(bgp)
            self._render_address_family_ipv6_sr_te(bgp)
            self._render_address_family_link_state(bgp)
            self._render_address_family_path_selection(bgp)
            self._render_address_family_rtc(bgp)
            self._render_address_family_vpn_ipv4(bgp)
            self._render_address_family_vpn_ipv6(bgp)
            self._render_vrfs(bgp)
            self._render_session_trackers(bgp)
            self._render_bgp_eos_cli(bgp)

    def _render_global_settings(self, bgp: EosCliConfigGen.RouterBgp) -> None:
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
        ip = neighbor.ip_address

        self._add("neighbor {} peer group {}", ip, neighbor.peer_group)
        self._add("neighbor {} remote-as {}", ip, neighbor.remote_as)
        if neighbor.shutdown is True:
            self._add(f"neighbor {ip} shutdown")

        self._render_next_hop(ip, neighbor.next_hop_self, neighbor.next_hop_peer)
        self._render_remove_private_as(ip, neighbor.remove_private_as)
        self._render_as_path(ip, neighbor.as_path)

        self._add("neighbor {} local-as {} no-prepend replace-as", ip, neighbor.local_as)
        self._add("neighbor {} weight {}", ip, neighbor.weight)
        if neighbor.passive is True:
            self._add(f"neighbor {ip} passive")
        self._add("neighbor {} update-source {}", ip, neighbor.update_source)

        # Neighbors can disable bfd inherited from a peer-group; peer-groups cannot.
        self._render_bfd(ip, neighbor.bfd, neighbor.bfd_timers, allow_negation=neighbor.peer_group is not None)

        self._add("neighbor {} description {}", ip, neighbor.description)

        self._render_allowas_in(ip, neighbor.allowas_in)
        self._render_rib_in_pre_policy_retain(ip, neighbor.rib_in_pre_policy_retain)

        self._add("neighbor {} ebgp-multihop {}", ip, neighbor.ebgp_multihop)
        self._add("neighbor {} ttl maximum-hops {}", ip, neighbor.ttl_maximum_hops)

        # Neighbors support negation for route-reflector-client; peer-groups do not.
        if neighbor.route_reflector_client is True:
            self._add(f"neighbor {ip} route-reflector-client")
        elif neighbor.route_reflector_client is False:
            self._add(f"no neighbor {ip} route-reflector-client")

        self._add("neighbor {} session tracker {}", ip, neighbor.session_tracker)
        self._add("neighbor {} timers {}", ip, neighbor.timers)

        self._render_route_maps(ip, neighbor.route_map_in, neighbor.route_map_out)

        # shared-secret before password key for neighbors (J2 ordering)
        self._render_shared_secret(ip, neighbor.shared_secret)
        self._render_password_key(ip, neighbor.password, neighbor.password_type)

        self._render_default_originate(ip, neighbor.default_originate)
        self._render_send_community(ip, neighbor.send_community)
        self._render_maximum_routes(ip, neighbor.maximum_routes, neighbor.maximum_routes_warning_limit, neighbor.maximum_routes_warning_only)

        if neighbor.missing_policy is not None:
            self._render_missing_policy(ip, neighbor.missing_policy)

        self._render_peer_tags(ip, neighbor.peer_tag_in, neighbor.peer_tag_out_discard)
        self._render_link_bandwidth(ip, neighbor.link_bandwidth)
        self._render_remove_private_as_ingress(ip, neighbor.remove_private_as_ingress)

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

    def _render_vlans(self, bgp: EosCliConfigGen.RouterBgp) -> None:
        """Render VLAN-based L2VPN entries sorted by id (J2 lines 681-721)."""
        for vlan in natural_sort(bgp.vlans or [], sort_key="id"):
            with self._block(f"vlan {vlan.id}"):
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
                    self._add(self._EXCLAMATION)
                    for line in vlan.eos_cli.splitlines():
                        self._add(line)
                    if vlan.eos_cli.endswith("\n"):
                        self._model._lines.append("")

    def _render_vpws(self, bgp: EosCliConfigGen.RouterBgp) -> None:
        """Render VPWS BGP service entries sorted by name (J2 lines 722-752)."""
        for svc in natural_sort(bgp.vpws or [], sort_key="name"):
            if svc.name is None:
                continue
            with self._block(f"vpws {svc.name}"):
                self._add("rd {}", svc.rd)
                self._add("route-target import export evpn {}", svc.route_targets.import_export)
                self._add("mpls control-word", svc.mpls_control_word)
                self._add("label flow", svc.label_flow)
                self._add("mtu {}", svc.mtu)
                for pw in natural_sort(svc.pseudowires or [], sort_key="name"):
                    if pw.name is not None and pw.id_local is not None and pw.id_remote is not None:
                        with self._block(f"pseudowire {pw.name}"):
                            self._add(f"evpn vpws id local {pw.id_local} remote {pw.id_remote}")

    def _render_vlan_aware_bundles(self, bgp: EosCliConfigGen.RouterBgp) -> None:
        """Render vlan-aware-bundle entries sorted by name (J2 lines 753-792)."""
        for bundle in natural_sort(bgp.vlan_aware_bundles or [], sort_key="name"):
            with self._block(f"vlan-aware-bundle {bundle.name}"):
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
                    self._add(self._EXCLAMATION)
                    for line in bundle.eos_cli.splitlines():
                        self._add(line)
                    if bundle.eos_cli.endswith("\n"):
                        self._model._lines.append("")

    def _render_route_distinguisher(self, bgp: EosCliConfigGen.RouterBgp) -> None:
        """Render 'route-distinguisher' block (J2 lines 809-819)."""
        assignment_auto = bgp.route_distinguisher.assignment_auto
        if not assignment_auto:
            return
        with self._block("route-distinguisher"):
            self._add("assignment auto range {} {}", assignment_auto.range.start, assignment_auto.range.end)
            for af in natural_sort(assignment_auto.address_families or []):
                self._add(f"assignment auto address-family {af}")

    def _render_address_family_evpn(self, bgp: EosCliConfigGen.RouterBgp) -> None:
        """Render 'address-family evpn' block (J2 lines 793-1018)."""
        af = bgp.address_family_evpn
        if not af:
            return
        with self._block("address-family evpn"):
            self._add("route export ethernet-segment ip mass-withdraw", af.route.export_ethernet_segment_ip_mass_withdraw)
            self._add("route import ethernet-segment ip mass-withdraw", af.route.import_ethernet_segment_ip_mass_withdraw)
            self._add("bgp additional-paths receive", af.bgp.additional_paths.receive)
            self._render_af_bgp_additional_paths_send(af.bgp.additional_paths)
            self._add("bgp next-hop-unchanged", af.next_hop_unchanged)
            if af.neighbor_default.encapsulation is not None:
                enc_cli = f"neighbor default encapsulation {af.neighbor_default.encapsulation}"
                if af.neighbor_default.encapsulation == "mpls" and af.neighbor_default.next_hop_self_source_interface is not None:
                    enc_cli += f" next-hop-self source-interface {af.neighbor_default.next_hop_self_source_interface}"
                self._add(enc_cli)

            rib_tokens: list[str] = []
            for rib in af.next_hop_mpls_resolution_ribs or []:
                if rib.rib_type == "tunnel-rib-colored":
                    rib_tokens.append("tunnel-rib colored system-colored-tunnel-rib")
                elif rib.rib_type == "tunnel-rib" and rib.rib_name is not None:
                    rib_tokens.append(f"tunnel-rib {rib.rib_name}")
                elif rib.rib_type is not None:
                    rib_tokens.append(rib.rib_type)
            if rib_tokens:
                self._add(f"next-hop mpls resolution ribs {' '.join(rib_tokens)}")

            for pg in natural_sort(af.peer_groups or [], sort_key="name"):
                self._render_af_evpn_peer_group(pg)
            for neighbor in natural_sort(af.neighbors or [], sort_key="ip_address"):
                self._render_af_evpn_neighbor(neighbor)

            self._add("domain identifier {}", af.domain_identifier)
            self._add("domain identifier {} remote", af.domain_identifier_remote)
            self._add("next-hop resolution disabled", af.next_hop.resolution_disabled)
            if af.route.import_match_failure_action == "discard":
                self._add("route import match-failure action discard")
            if af.neighbor_default.next_hop_self_received_evpn_routes.enable is True:
                nhs_cli = "neighbor default next-hop-self received-evpn-routes route-type ip-prefix"
                if af.neighbor_default.next_hop_self_received_evpn_routes.inter_domain is True:
                    nhs_cli += " inter-domain"
                self._add(nhs_cli)

            if af.evpn_hostflap_detection.enabled is False:
                self._add("no host-flap detection")
            elif af.evpn_hostflap_detection.enabled is True:
                hfd_suffix = ""
                if af.evpn_hostflap_detection.window is not None:
                    hfd_suffix += f" window {af.evpn_hostflap_detection.window}"
                if af.evpn_hostflap_detection.threshold is not None:
                    hfd_suffix += f" threshold {af.evpn_hostflap_detection.threshold}"
                if af.evpn_hostflap_detection.expiry_timeout is not None:
                    hfd_suffix += f" expiry timeout {af.evpn_hostflap_detection.expiry_timeout} seconds"
                if hfd_suffix:
                    self._add(f"host-flap detection{hfd_suffix}")

            if af.layer_2_fec_in_place_update.enabled is True:
                l2_cli = "layer-2 fec in-place update"
                if af.layer_2_fec_in_place_update.timeout is not None:
                    l2_cli += f" timeout {af.layer_2_fec_in_place_update.timeout} seconds"
                self._add(l2_cli)

            self._add("route import overlay-index gateway", af.route.import_overlay_index_gateway)

            for segment in natural_sort(af.evpn_ethernet_segment or [], sort_key="domain"):
                with self._block(f"evpn ethernet-segment domain {segment.domain}"):
                    self._add("identifier {}", segment.identifier)
                    self._add("route-target import {}", segment.route_target_import)

    def _render_address_family_flow_spec_ipv4(self, bgp: EosCliConfigGen.RouterBgp) -> None:
        """Render 'address-family flow-spec ipv4' block (J2 lines 1019-1041)."""
        self._render_address_family_flow_spec(bgp.address_family_flow_spec_ipv4, "ipv4")

    def _render_address_family_flow_spec_ipv6(self, bgp: EosCliConfigGen.RouterBgp) -> None:
        """Render 'address-family flow-spec ipv6' block (J2 lines 1042-1064)."""
        self._render_address_family_flow_spec(bgp.address_family_flow_spec_ipv6, "ipv6")

    def _render_address_family_flow_spec(self, af: Any, ip_version: str) -> None:
        """Shared renderer for 'address-family flow-spec {ipv4|ipv6}' blocks."""
        if not af:
            return
        with self._block(f"address-family flow-spec {ip_version}"):
            self._add("bgp missing-policy direction in action {}", af.bgp.missing_policy.direction_in_action)
            self._add("bgp missing-policy direction out action {}", af.bgp.missing_policy.direction_out_action)
            for pg in natural_sort(af.peer_groups or [], sort_key="name"):
                if pg.activate is True:
                    self._add(f"neighbor {pg.name} activate")
                elif pg.activate is False:
                    self._add(f"no neighbor {pg.name} activate")
            for neighbor in natural_sort(af.neighbors or [], sort_key="ip_address"):
                if neighbor.activate is True:
                    self._add(f"neighbor {neighbor.ip_address} activate")

    def _render_address_family_ipv4(self, bgp: EosCliConfigGen.RouterBgp) -> None:
        """Render 'address-family ipv4' block (J2 lines 1065-1413)."""
        af = bgp.address_family_ipv4
        if not af:
            return
        with self._block("address-family ipv4"):
            if af.bgp.additional_paths.install is True:
                self._add("bgp additional-paths install")
            elif af.bgp.additional_paths.install_ecmp_primary is True:
                self._add("bgp additional-paths install ecmp-primary")
            self._add("bgp additional-paths receive", af.bgp.additional_paths.receive)
            self._render_af_bgp_additional_paths_send(af.bgp.additional_paths)

            for pg in natural_sort(af.peer_groups or [], sort_key="name"):
                self._render_af_ipv4_peer_group(pg)
            for neighbor in natural_sort(af.neighbors or [], sort_key="ip_address"):
                self._render_af_ipv4_neighbor(neighbor)

            for network in natural_sort(af.networks or [], sort_key="prefix"):
                if network.route_map is not None:
                    self._add(f"network {network.prefix} route-map {network.route_map}")
                elif network.rcf is not None:
                    self._add(f"network {network.prefix} rcf {network.rcf}")
                else:
                    self._add(f"network {network.prefix}")

            if af.bgp.redistribute_internal is True:
                self._add("bgp redistribute-internal")
            elif af.bgp.redistribute_internal is False:
                self._add("no bgp redistribute-internal")

            self._render_af_ipv4_redistribute(af.redistribute)

    def _render_labeled_unicast_rib(self, bgp: EosCliConfigGen.RouterBgp) -> None:
        """Render 'bgp labeled-unicast rib [ip [route-map X]] [tunnel [route-map Y]]' (J2 lines 13-28)."""
        rib = bgp.bgp.labeled_unicast.rib
        if rib.ip.enabled is not True and rib.tunnel.enabled is not True:
            return
        cmd = "bgp labeled-unicast rib"
        if rib.ip.enabled is True:
            cmd += " ip"
            if rib.ip.route_map is not None:
                cmd += f" route-map {rib.ip.route_map}"
        if rib.tunnel.enabled is True:
            cmd += " tunnel"
            if rib.tunnel.route_map is not None:
                cmd += f" route-map {rib.tunnel.route_map}"
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
        t = bgp.timers
        if t.keepalive_time is None and t.hold_time is None and t.min_hold_time is None and t.send_failure_hold_time is None:
            return
        cmd = "timers bgp"
        if t.keepalive_time is not None and t.hold_time is not None:
            cmd += f" {t.keepalive_time} {t.hold_time}"
        if t.min_hold_time is not None:
            cmd += f" min-hold-time {t.min_hold_time}"
        if t.send_failure_hold_time is not None:
            cmd += f" send-failure hold-time {t.send_failure_hold_time}"
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
        pw = hide_passwords(password, self.data.eos_cli_config_gen_configuration.hide_passwords)
        self._add(f"neighbor {entity_id} password {pw_type} {pw}")

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

    def _render_af_bgp_additional_paths_send(self, additional_paths: Any) -> None:
        """Render 'bgp additional-paths send ...' at L2 for an address-family block."""
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
        """Render 'neighbor X additional-paths send ...' at L2 for an address-family block."""
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

    def _render_af_evpn_peer_group(self, pg: Any) -> None:
        """Render address-family evpn commands for a peer group at L2 (J2 lines 845-903)."""
        name = pg.name
        if pg.activate is True:
            self._add(f"neighbor {name} activate")
        elif pg.activate is False:
            self._add(f"no neighbor {name} activate")
        if pg.additional_paths.receive is True:
            self._add(f"neighbor {name} additional-paths receive")
        self._add("neighbor {} route-map {} in", name, pg.route_map_in)
        self._add("neighbor {} route-map {} out", name, pg.route_map_out)
        self._add("neighbor {} rcf in {}", name, pg.rcf_in)
        self._add("neighbor {} rcf out {}", name, pg.rcf_out)
        if pg.default_route.enabled is True:
            dr_cli = f"neighbor {name} default-route"
            if pg.default_route.rcf is not None:
                dr_cli += f" rcf {pg.default_route.rcf}"
            elif pg.default_route.route_map is not None:
                dr_cli += f" route-map {pg.default_route.route_map}"
            self._add(dr_cli)
        self._render_af_neighbor_additional_paths_send(name, pg.additional_paths)
        self._add("neighbor {} peer-tag in {}", name, pg.peer_tag_in)
        self._add("neighbor {} peer-tag out discard {}", name, pg.peer_tag_out_discard)
        if pg.encapsulation is not None:
            enc_cli = f"neighbor {name} encapsulation {pg.encapsulation}"
            if pg.encapsulation == "mpls" and pg.next_hop_self_source_interface is not None:
                enc_cli += f" next-hop-self source-interface {pg.next_hop_self_source_interface}"
            self._add(enc_cli)
        if pg.domain_remote is True:
            self._add(f"neighbor {name} domain remote")

    def _render_af_evpn_neighbor(self, neighbor: Any) -> None:
        """Render address-family evpn commands for a neighbor at L2 (J2 lines 905-961)."""
        ip = neighbor.ip_address
        if neighbor.activate is True:
            self._add(f"neighbor {ip} activate")
        elif neighbor.activate is False:
            self._add(f"no neighbor {ip} activate")
        if neighbor.additional_paths.receive is True:
            self._add(f"neighbor {ip} additional-paths receive")
        self._add("neighbor {} route-map {} in", ip, neighbor.route_map_in)
        self._add("neighbor {} route-map {} out", ip, neighbor.route_map_out)
        self._add("neighbor {} rcf in {}", ip, neighbor.rcf_in)
        self._add("neighbor {} rcf out {}", ip, neighbor.rcf_out)
        if neighbor.default_route.enabled is True:
            dr_cli = f"neighbor {ip} default-route"
            if neighbor.default_route.rcf is not None:
                dr_cli += f" rcf {neighbor.default_route.rcf}"
            elif neighbor.default_route.route_map is not None:
                dr_cli += f" route-map {neighbor.default_route.route_map}"
            self._add(dr_cli)
        self._render_af_neighbor_additional_paths_send(ip, neighbor.additional_paths)
        self._add("neighbor {} peer-tag in {}", ip, neighbor.peer_tag_in)
        self._add("neighbor {} peer-tag out discard {}", ip, neighbor.peer_tag_out_discard)
        if neighbor.encapsulation is not None:
            enc_cli = f"neighbor {ip} encapsulation {neighbor.encapsulation}"
            if neighbor.encapsulation == "mpls" and neighbor.next_hop_self_source_interface is not None:
                enc_cli += f" next-hop-self source-interface {neighbor.next_hop_self_source_interface}"
            self._add(enc_cli)

    def _render_af_ipv4_additional_paths_send(self, entity_id: str, additional_paths: Any) -> None:
        """Render 'neighbor X additional-paths send ...' with optional prefix-list at L2 (J2 IPv4 AF variant)."""
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

    def _render_af_ipv4_peer_group(self, pg: Any) -> None:
        """Render address-family ipv4 commands for a peer group at L2 (J2 lines 1090-1161)."""
        name = pg.name
        if pg.activate is True:
            self._add(f"neighbor {name} activate")
        elif pg.activate is False:
            self._add(f"no neighbor {name} activate")
        if pg.additional_paths.receive is True:
            self._add(f"neighbor {name} additional-paths receive")
        self._add("neighbor {} route-map {} in", name, pg.route_map_in)
        self._add("neighbor {} route-map {} out", name, pg.route_map_out)
        self._add("neighbor {} rcf in {}", name, pg.rcf_in)
        self._add("neighbor {} rcf out {}", name, pg.rcf_out)
        self._add("neighbor {} prefix-list {} in", name, pg.prefix_list_in)
        self._add("neighbor {} prefix-list {} out", name, pg.prefix_list_out)
        if pg.default_originate:
            do_cli = f"neighbor {name} default-originate"
            if pg.default_originate.route_map is not None:
                do_cli += f" route-map {pg.default_originate.route_map}"
            if pg.default_originate.always is True:
                do_cli += " always"
            self._add(do_cli)
        self._render_af_ipv4_additional_paths_send(name, pg.additional_paths)
        if pg.next_hop.address_family_ipv6.enabled is True:
            nhv6_cli = f"neighbor {name} next-hop address-family ipv6"
            if pg.next_hop.address_family_ipv6.originate is True:
                nhv6_cli += " originate"
            self._add(nhv6_cli)
        self._add("neighbor {} peer-tag in {}", name, pg.peer_tag_in)
        self._add("neighbor {} peer-tag out discard {}", name, pg.peer_tag_out_discard)

    def _render_af_ipv4_neighbor(self, neighbor: Any) -> None:
        """Render address-family ipv4 commands for a neighbor at L2 (J2 lines 1162-1237)."""
        ip = neighbor.ip_address
        if neighbor.activate is True:
            self._add(f"neighbor {ip} activate")
        elif neighbor.activate is False:
            self._add(f"no neighbor {ip} activate")
        if neighbor.additional_paths.receive is True:
            self._add(f"neighbor {ip} additional-paths receive")
        self._add("neighbor {} route-map {} in", ip, neighbor.route_map_in)
        self._add("neighbor {} route-map {} out", ip, neighbor.route_map_out)
        self._add("neighbor {} rcf in {}", ip, neighbor.rcf_in)
        self._add("neighbor {} rcf out {}", ip, neighbor.rcf_out)
        self._add("neighbor {} prefix-list {} in", ip, neighbor.prefix_list_in)
        self._add("neighbor {} prefix-list {} out", ip, neighbor.prefix_list_out)
        if neighbor.default_originate:
            do_cli = f"neighbor {ip} default-originate"
            if neighbor.default_originate.route_map is not None:
                do_cli += f" route-map {neighbor.default_originate.route_map}"
            if neighbor.default_originate.always is True:
                do_cli += " always"
            self._add(do_cli)
        self._render_af_ipv4_additional_paths_send(ip, neighbor.additional_paths)
        if neighbor.next_hop.address_family_ipv6.enabled is True:
            nhv6_cli = f"neighbor {ip} next-hop address-family ipv6"
            if neighbor.next_hop.address_family_ipv6.originate is True:
                nhv6_cli += " originate"
            self._add(nhv6_cli)
        elif neighbor.next_hop.address_family_ipv6.enabled is False:
            self._add(f"no neighbor {ip} next-hop address-family ipv6")
        self._add("neighbor {} peer-tag in {}", ip, neighbor.peer_tag_in)
        self._add("neighbor {} peer-tag out discard {}", ip, neighbor.peer_tag_out_discard)

    def _render_af_ipv4_redistribute(self, r: Any) -> None:
        """Render redistribute entries for address-family ipv4 at L2 (J2 lines 1250-1412)."""
        if r.attached_host.enabled is True:
            cli = "redistribute attached-host"
            if r.attached_host.route_map is not None:
                cli += f" route-map {r.attached_host.route_map}"
            self._add(cli)

        if r.bgp.enabled is True:
            cli = "redistribute bgp leaked"
            if r.bgp.route_map is not None:
                cli += f" route-map {r.bgp.route_map}"
            self._add(cli)

        if r.connected.enabled is True:
            cli = "redistribute connected"
            if r.connected.include_leaked is True:
                cli += " include leaked"
            if r.connected.route_map is not None:
                cli += f" route-map {r.connected.route_map}"
            elif r.connected.rcf is not None:
                cli += f" rcf {r.connected.rcf}"
            self._add(cli)

        if r.dynamic.enabled is True:
            cli = "redistribute dynamic"
            if r.dynamic.route_map is not None:
                cli += f" route-map {r.dynamic.route_map}"
            elif r.dynamic.rcf is not None:
                cli += f" rcf {r.dynamic.rcf}"
            self._add(cli)

        if r.user.enabled is True:
            cli = "redistribute user"
            if r.user.rcf is not None:
                cli += f" rcf {r.user.rcf}"
            self._add(cli)

        if r.isis.enabled is True:
            cli = "redistribute isis"
            if r.isis.isis_level is not None:
                cli += f" {r.isis.isis_level}"
            if r.isis.include_leaked is True:
                cli += " include leaked"
            if r.isis.route_map is not None:
                cli += f" route-map {r.isis.route_map}"
            elif r.isis.rcf is not None:
                cli += f" rcf {r.isis.rcf}"
            self._add(cli)

        if r.ospf.enabled is True:
            cli = "redistribute ospf"
            if r.ospf.include_leaked is True:
                cli += " include leaked"
            if r.ospf.route_map is not None:
                cli += f" route-map {r.ospf.route_map}"
            self._add(cli)
        elif r.ospf.match_internal.enabled is True:
            cli = "redistribute ospf match internal"
            if r.ospf.match_internal.include_leaked is True:
                cli += " include leaked"
            if r.ospf.match_internal.route_map is not None:
                cli += f" route-map {r.ospf.match_internal.route_map}"
            self._add(cli)

        if r.ospfv3.enabled is True:
            cli = "redistribute ospfv3"
            if r.ospfv3.include_leaked is True:
                cli += " include leaked"
            if r.ospfv3.route_map is not None:
                cli += f" route-map {r.ospfv3.route_map}"
            self._add(cli)
        elif r.ospfv3.match_internal.enabled is True:
            cli = "redistribute ospfv3 match internal"
            if r.ospfv3.match_internal.include_leaked is True:
                cli += " include leaked"
            if r.ospfv3.match_internal.route_map is not None:
                cli += f" route-map {r.ospfv3.match_internal.route_map}"
            self._add(cli)

        if r.ospfv3.match_external.enabled is True:
            cli = "redistribute ospfv3 match external"
            if r.ospfv3.match_external.include_leaked is True:
                cli += " include leaked"
            if r.ospfv3.match_external.route_map is not None:
                cli += f" route-map {r.ospfv3.match_external.route_map}"
            self._add(cli)

        if r.ospfv3.match_nssa_external.enabled is True:
            cli = "redistribute ospfv3 match nssa-external"
            if r.ospfv3.match_nssa_external.nssa_type is not None:
                cli += f" {r.ospfv3.match_nssa_external.nssa_type}"
            if r.ospfv3.match_nssa_external.include_leaked is True:
                cli += " include leaked"
            if r.ospfv3.match_nssa_external.route_map is not None:
                cli += f" route-map {r.ospfv3.match_nssa_external.route_map}"
            self._add(cli)

        if r.ospf.match_external.enabled is True:
            cli = "redistribute ospf match external"
            if r.ospf.match_external.include_leaked is True:
                cli += " include leaked"
            if r.ospf.match_external.route_map is not None:
                cli += f" route-map {r.ospf.match_external.route_map}"
            self._add(cli)

        if r.ospf.match_nssa_external.enabled is True:
            cli = "redistribute ospf match nssa-external"
            if r.ospf.match_nssa_external.nssa_type is not None:
                cli += f" {r.ospf.match_nssa_external.nssa_type}"
            if r.ospf.match_nssa_external.include_leaked is True:
                cli += " include leaked"
            if r.ospf.match_nssa_external.route_map is not None:
                cli += f" route-map {r.ospf.match_nssa_external.route_map}"
            self._add(cli)

        if r.rip.enabled is True:
            cli = "redistribute rip"
            if r.rip.route_map is not None:
                cli += f" route-map {r.rip.route_map}"
            self._add(cli)

        if r.static.enabled is True:
            cli = "redistribute static"
            if r.static.include_leaked is True:
                cli += " include leaked"
            if r.static.route_map is not None:
                cli += f" route-map {r.static.route_map}"
            elif r.static.rcf is not None:
                cli += f" rcf {r.static.rcf}"
            self._add(cli)

    # TODO: fix the double space
    def _build_missing_policy_cli(self, prefix: str, missing_policy: Any, double_space_before_include: bool = False) -> list[str]:
        """
        Build 'missing-policy' CLI lines for directions in and out.

        Returns a list of zero, one, or two CLI strings (one per direction that
        has an action defined).  The caller is responsible for appending each
        line at the correct indentation level.

        Args:
            prefix:                    Command prefix, e.g. ``"bgp missing-policy"`` or
                                       ``"neighbor X missing-policy"``.
            missing_policy:            AvdModel with ``direction_in`` / ``direction_out`` fields.
            double_space_before_include: When True, inserts two spaces before ``include``
                                       instead of one (required for ipv4 labeled-unicast neighbors).
        """
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

    def _render_address_family_ipv4_labeled_unicast(self, bgp: EosCliConfigGen.RouterBgp) -> None:
        """Render 'address-family ipv4 labeled-unicast' block (J2 lines 1414-1714)."""
        af = bgp.address_family_ipv4_labeled_unicast
        if not af:
            return
        with self._block("address-family ipv4 labeled-unicast"):
            self._add("update wait-for-convergence", af.update_wait_for_convergence)

            if af.bgp.missing_policy:
                for line in self._build_missing_policy_cli("bgp missing-policy", af.bgp.missing_policy):
                    self._add(line)

            self._add("bgp additional-paths receive", af.bgp.additional_paths.receive)

            self._render_af_bgp_additional_paths_send(af.bgp.additional_paths)

            self._add("bgp next-hop-unchanged", af.bgp.next_hop_unchanged)

            self._add("neighbor default next-hop-self", af.neighbor_default.next_hop_self)

            next_hop_ribs = af.next_hop_resolution_ribs
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

            for pg in natural_sort(af.peer_groups or [], sort_key="name"):
                self._render_af_lu_entity(pg.name, pg)

            for neighbor in natural_sort(af.neighbors or [], sort_key="ip_address"):
                self._render_af_lu_entity(neighbor.ip_address, neighbor)

            for network in af.networks or []:
                cli = f"network {network.prefix}"
                if network.route_map is not None:
                    cli += f" route-map {network.route_map}"
                elif network.rcf is not None:
                    cli += f" rcf {network.rcf}"
                self._add(cli)

            for next_hop in af.next_hops or []:
                cli = f"next-hop {next_hop.ip_address} originate"
                if next_hop.lfib_backup_ip_forwarding is True:
                    cli += " lfib-backup ip-forwarding"
                self._add(cli)

            self._add("lfib entry installation skipped", af.lfib_entry_installation_skipped)

            self._add("label local-termination {}", af.label_local_termination)

            self._add("graceful-restart", af.graceful_restart)

            for tunnel_protocol in af.tunnel_source_protocols or []:
                cli = f"tunnel source-protocol {tunnel_protocol.protocol}"
                if tunnel_protocol.rcf is not None:
                    cli += f" rcf {tunnel_protocol.rcf}"
                self._add(cli)

            aigp_session = af.aigp_session
            if aigp_session:
                for session_type in ["ibgp", "confederation", "ebgp"]:
                    if getattr(aigp_session, session_type, None) is True:
                        self._add(f"aigp-session {session_type}")

    def _render_af_lu_entity(self, entity_id: str, entity: Any) -> None:
        """Render AF IPv4 labeled-unicast commands for a peer-group or neighbor at L2."""
        # J2 uses if/else (not elif): always renders activate or no activate.
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

    def _render_address_family_ipv4_multicast(self, bgp: EosCliConfigGen.RouterBgp) -> None:
        """Render 'address-family ipv4 multicast' block (J2 lines 1715-1865)."""
        af = bgp.address_family_ipv4_multicast
        if not af:
            return
        with self._block("address-family ipv4 multicast"):
            self._add("bgp additional-paths receive", af.bgp.additional_paths.receive)

            for pg in natural_sort(af.peer_groups or [], sort_key="name"):
                self._render_af_ipv4mc_entity(pg.name, pg)

            for neighbor in natural_sort(af.neighbors or [], sort_key="ip_address"):
                self._render_af_ipv4mc_entity(neighbor.ip_address, neighbor)

            if af.redistribute:
                self._render_af_ipv4mc_redistribute(af.redistribute)

    def _render_af_ipv4mc_entity(self, entity_id: str, entity: Any) -> None:
        """Render AF IPv4 multicast commands for a peer-group or neighbor at L2."""
        # J2 uses if/elif: only renders when explicitly True or explicitly False.
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

    def _render_af_ipv4mc_redistribute(self, r: Any) -> None:
        """Render IPv4 multicast address-family redistribute commands at L2."""
        if r.attached_host.enabled is True:
            cli = "redistribute attached-host"
            if r.attached_host.route_map is not None:
                cli += f" route-map {r.attached_host.route_map}"
            self._add(cli)

        if r.connected.enabled is True:
            cli = "redistribute connected"
            if r.connected.route_map is not None:
                cli += f" route-map {r.connected.route_map}"
            self._add(cli)

        if r.isis.enabled is True:
            cli = "redistribute isis"
            if r.isis.isis_level is not None:
                cli += f" {r.isis.isis_level}"
            if r.isis.include_leaked is True:
                cli += " include leaked"
            if r.isis.route_map is not None:
                cli += f" route-map {r.isis.route_map}"
            elif r.isis.rcf is not None:
                cli += f" rcf {r.isis.rcf}"
            self._add(cli)

        if r.ospf.enabled is True:
            cli = "redistribute ospf"
            if r.ospf.route_map is not None:
                cli += f" route-map {r.ospf.route_map}"
            self._add(cli)
        elif r.ospf.match_internal.enabled is True:
            cli = "redistribute ospf match internal"
            if r.ospf.match_internal.route_map is not None:
                cli += f" route-map {r.ospf.match_internal.route_map}"
            self._add(cli)

        if r.ospfv3.enabled is True:
            cli = "redistribute ospfv3"
            if r.ospfv3.route_map is not None:
                cli += f" route-map {r.ospfv3.route_map}"
            self._add(cli)
        elif r.ospfv3.match_internal.enabled is True:
            cli = "redistribute ospfv3 match internal"
            if r.ospfv3.match_internal.route_map is not None:
                cli += f" route-map {r.ospfv3.match_internal.route_map}"
            self._add(cli)

        if r.ospfv3.match_external.enabled is True:
            cli = "redistribute ospfv3 match external"
            if r.ospfv3.match_external.route_map is not None:
                cli += f" route-map {r.ospfv3.match_external.route_map}"
            self._add(cli)

        if r.ospfv3.match_nssa_external.enabled is True:
            cli = "redistribute ospfv3 match nssa-external"
            if r.ospfv3.match_nssa_external.nssa_type is not None:
                cli += f" {r.ospfv3.match_nssa_external.nssa_type}"
            if r.ospfv3.match_nssa_external.route_map is not None:
                cli += f" route-map {r.ospfv3.match_nssa_external.route_map}"
            self._add(cli)

        if r.ospf.match_external.enabled is True:
            cli = "redistribute ospf match external"
            if r.ospf.match_external.route_map is not None:
                cli += f" route-map {r.ospf.match_external.route_map}"
            self._add(cli)

        if r.ospf.match_nssa_external.enabled is True:
            cli = "redistribute ospf match nssa-external"
            if r.ospf.match_nssa_external.nssa_type is not None:
                cli += f" {r.ospf.match_nssa_external.nssa_type}"
            if r.ospf.match_nssa_external.route_map is not None:
                cli += f" route-map {r.ospf.match_nssa_external.route_map}"
            self._add(cli)

        if r.static.enabled is True:
            cli = "redistribute static"
            if r.static.route_map is not None:
                cli += f" route-map {r.static.route_map}"
            self._add(cli)

    def _render_address_family_ipv4_sr_te(self, bgp: EosCliConfigGen.RouterBgp) -> None:
        """Render 'address-family ipv4 sr-te' block (J2 lines 1866-1908)."""
        af = bgp.address_family_ipv4_sr_te
        if not af:
            return
        with self._block("address-family ipv4 sr-te"):
            for pg in natural_sort(af.peer_groups or [], sort_key="name"):
                self._render_af_sr_te_entity(pg.name, pg)

            for neighbor in natural_sort(af.neighbors or [], sort_key="ip_address"):
                self._render_af_sr_te_entity(neighbor.ip_address, neighbor)

    def _render_af_sr_te_entity(self, entity_id: str, entity: Any) -> None:
        """Render AF SR-TE commands for a peer-group or neighbor at L2 (shared by ipv4 and ipv6 sr-te)."""
        if entity.activate is True:
            self._add(f"neighbor {entity_id} activate")
        elif entity.activate is False:
            self._add(f"no neighbor {entity_id} activate")

        self._add("neighbor {} route-map {} in", entity_id, entity.route_map_in)

        self._add("neighbor {} route-map {} out", entity_id, entity.route_map_out)

        self._add("neighbor {} peer-tag in {}", entity_id, entity.peer_tag_in)

        self._add("neighbor {} peer-tag out discard {}", entity_id, entity.peer_tag_out_discard)

    def _render_address_family_ipv6(self, bgp: EosCliConfigGen.RouterBgp) -> None:
        """Render 'address-family ipv6' block (J2 lines 1909-2177)."""
        af = bgp.address_family_ipv6
        if not af:
            return
        with self._block("address-family ipv6"):
            if af.bgp.additional_paths.install is True:
                self._add("bgp additional-paths install")
            elif af.bgp.additional_paths.install_ecmp_primary is True:
                self._add("bgp additional-paths install ecmp-primary")

            self._add("bgp additional-paths receive", af.bgp.additional_paths.receive)

            self._render_af_bgp_additional_paths_send(af.bgp.additional_paths)

            # Section-level prefix_list is appended to per-neighbor send commands.
            # Use getattr since prefix_list is not always present in the schema model.
            bg_prefix_list = getattr(af.bgp.additional_paths, "prefix_list", None)

            for pg in natural_sort(af.peer_groups or [], sort_key="name"):
                self._render_af_ipv6_entity(pg.name, pg, bg_prefix_list)

            for neighbor in natural_sort(af.neighbors or [], sort_key="ip_address"):
                self._render_af_ipv6_entity(neighbor.ip_address, neighbor, bg_prefix_list)

            for network in natural_sort(af.networks or [], sort_key="prefix"):
                cli = f"network {network.prefix}"
                if network.route_map is not None:
                    cli += f" route-map {network.route_map}"
                elif network.rcf is not None:
                    cli += f" rcf {network.rcf}"
                self._add(cli)

            if af.bgp.redistribute_internal is True:
                self._add("bgp redistribute-internal")
            elif af.bgp.redistribute_internal is False:
                self._add("no bgp redistribute-internal")

            if af.redistribute:
                self._render_af_ipv6_redistribute(af.redistribute)

    def _render_af_ipv6_entity(self, entity_id: str, entity: Any, bg_prefix_list: str | None) -> None:
        """Render AF IPv6 commands for a peer-group or neighbor at L2."""
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

        # additional_paths send: section-level prefix_list is appended when set.
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

    def _render_af_ipv6_redistribute(self, r: Any) -> None:
        """Render IPv6 address-family redistribute commands at L2."""
        if r.attached_host.enabled is True:
            cli = "redistribute attached-host"
            if r.attached_host.route_map is not None:
                cli += f" route-map {r.attached_host.route_map}"
            self._add(cli)

        if r.bgp.enabled is True:
            cli = "redistribute bgp leaked"
            if r.bgp.route_map is not None:
                cli += f" route-map {r.bgp.route_map}"
            self._add(cli)

        if r.dhcp.enabled is True:
            cli = "redistribute dhcp"
            if r.dhcp.route_map is not None:
                cli += f" route-map {r.dhcp.route_map}"
            self._add(cli)

        if r.connected.enabled is True:
            cli = "redistribute connected"
            if r.connected.include_leaked is True:
                cli += " include leaked"
            if r.connected.route_map is not None:
                cli += f" route-map {r.connected.route_map}"
            elif r.connected.rcf is not None:
                cli += f" rcf {r.connected.rcf}"
            self._add(cli)

        if r.dynamic.enabled is True:
            cli = "redistribute dynamic"
            if r.dynamic.route_map is not None:
                cli += f" route-map {r.dynamic.route_map}"
            elif r.dynamic.rcf is not None:
                cli += f" rcf {r.dynamic.rcf}"
            self._add(cli)

        if r.user.enabled is True:
            cli = "redistribute user"
            if r.user.rcf is not None:
                cli += f" rcf {r.user.rcf}"
            self._add(cli)

        if r.isis.enabled is True:
            cli = "redistribute isis"
            if r.isis.isis_level is not None:
                cli += f" {r.isis.isis_level}"
            if r.isis.include_leaked is True:
                cli += " include leaked"
            if r.isis.route_map is not None:
                cli += f" route-map {r.isis.route_map}"
            elif r.isis.rcf is not None:
                cli += f" rcf {r.isis.rcf}"
            self._add(cli)

        if r.ospfv3.enabled is True:
            cli = "redistribute ospfv3"
            if r.ospfv3.include_leaked is True:
                cli += " include leaked"
            if r.ospfv3.route_map is not None:
                cli += f" route-map {r.ospfv3.route_map}"
            self._add(cli)
        elif r.ospfv3.match_internal.enabled is True:
            cli = "redistribute ospfv3 match internal"
            if r.ospfv3.match_internal.include_leaked is True:
                cli += " include leaked"
            if r.ospfv3.match_internal.route_map is not None:
                cli += f" route-map {r.ospfv3.match_internal.route_map}"
            self._add(cli)

        if r.ospfv3.match_external.enabled is True:
            cli = "redistribute ospfv3 match external"
            if r.ospfv3.match_external.include_leaked is True:
                cli += " include leaked"
            if r.ospfv3.match_external.route_map is not None:
                cli += f" route-map {r.ospfv3.match_external.route_map}"
            self._add(cli)

        if r.ospfv3.match_nssa_external.enabled is True:
            cli = "redistribute ospfv3 match nssa-external"
            if r.ospfv3.match_nssa_external.nssa_type is not None:
                cli += f" {r.ospfv3.match_nssa_external.nssa_type}"
            if r.ospfv3.match_nssa_external.include_leaked is True:
                cli += " include leaked"
            if r.ospfv3.match_nssa_external.route_map is not None:
                cli += f" route-map {r.ospfv3.match_nssa_external.route_map}"
            self._add(cli)

        if r.static.enabled is True:
            cli = "redistribute static"
            if r.static.include_leaked is True:
                cli += " include leaked"
            if r.static.route_map is not None:
                cli += f" route-map {r.static.route_map}"
            elif r.static.rcf is not None:
                cli += f" rcf {r.static.rcf}"
            self._add(cli)

    def _render_address_family_ipv6_multicast(self, bgp: EosCliConfigGen.RouterBgp) -> None:
        """Render 'address-family ipv6 multicast' block (J2 lines 2178-2320)."""
        af = bgp.address_family_ipv6_multicast
        if not af:
            return
        with self._block("address-family ipv6 multicast"):
            # bgp missing-policy uses flat direction_{in,out}_action fields (not nested).
            self._add("bgp missing-policy direction in action {}", af.bgp.missing_policy.direction_in_action)
            self._add("bgp missing-policy direction out action {}", af.bgp.missing_policy.direction_out_action)

            self._add("bgp additional-paths receive", af.bgp.additional_paths.receive)

            for pg in natural_sort(af.peer_groups or [], sort_key="name"):
                if pg.activate is True:
                    self._add(f"neighbor {pg.name} activate")
                elif pg.activate is False:
                    self._add(f"no neighbor {pg.name} activate")
                if pg.additional_paths.receive is True:
                    self._add(f"neighbor {pg.name} additional-paths receive")

            for neighbor in natural_sort(af.neighbors or [], sort_key="ip_address"):
                # J2 checks only 'if True' (no elif False) for neighbor activate.
                if neighbor.activate is True:
                    self._add(f"neighbor {neighbor.ip_address} activate")
                if neighbor.additional_paths.receive is True:
                    self._add(f"neighbor {neighbor.ip_address} additional-paths receive")
                self._add("neighbor {} route-map {} in", neighbor.ip_address, neighbor.route_map_in)
                self._add("neighbor {} route-map {} out", neighbor.ip_address, neighbor.route_map_out)
                self._add("neighbor {} peer-tag in {}", neighbor.ip_address, neighbor.peer_tag_in)
                self._add("neighbor {} peer-tag out discard {}", neighbor.ip_address, neighbor.peer_tag_out_discard)

            for network in natural_sort(af.networks or [], sort_key="prefix"):
                cli = f"network {network.prefix}"
                if network.route_map is not None:
                    cli += f" route-map {network.route_map}"
                self._add(cli)

            if af.redistribute:
                self._render_af_ipv6mc_redistribute(af.redistribute)

    def _render_af_ipv6mc_redistribute(self, r: Any) -> None:
        """Render IPv6 multicast address-family redistribute commands at L2."""
        if r.connected.enabled is True:
            cli = "redistribute connected"
            if r.connected.route_map is not None:
                cli += f" route-map {r.connected.route_map}"
            self._add(cli)

        if r.isis.enabled is True:
            cli = "redistribute isis"
            if r.isis.isis_level is not None:
                cli += f" {r.isis.isis_level}"
            if r.isis.include_leaked is True:
                cli += " include leaked"
            if r.isis.route_map is not None:
                cli += f" route-map {r.isis.route_map}"
            elif r.isis.rcf is not None:
                cli += f" rcf {r.isis.rcf}"
            self._add(cli)

        if r.ospf.enabled is True:
            cli = "redistribute ospf"
            if r.ospf.route_map is not None:
                cli += f" route-map {r.ospf.route_map}"
            self._add(cli)
        elif r.ospf.match_internal.enabled is True:
            cli = "redistribute ospf match internal"
            if r.ospf.match_internal.route_map is not None:
                cli += f" route-map {r.ospf.match_internal.route_map}"
            self._add(cli)

        if r.ospfv3.enabled is True:
            cli = "redistribute ospfv3"
            if r.ospfv3.route_map is not None:
                cli += f" route-map {r.ospfv3.route_map}"
            self._add(cli)
        elif r.ospfv3.match_internal.enabled is True:
            cli = "redistribute ospfv3 match internal"
            if r.ospfv3.match_internal.route_map is not None:
                cli += f" route-map {r.ospfv3.match_internal.route_map}"
            self._add(cli)

        if r.ospfv3.match_external.enabled is True:
            cli = "redistribute ospfv3 match external"
            if r.ospfv3.match_external.route_map is not None:
                cli += f" route-map {r.ospfv3.match_external.route_map}"
            self._add(cli)

        if r.ospfv3.match_nssa_external.enabled is True:
            cli = "redistribute ospfv3 match nssa-external"
            if r.ospfv3.match_nssa_external.nssa_type is not None:
                cli += f" {r.ospfv3.match_nssa_external.nssa_type}"
            if r.ospfv3.match_nssa_external.route_map is not None:
                cli += f" route-map {r.ospfv3.match_nssa_external.route_map}"
            self._add(cli)

        if r.ospf.match_external.enabled is True:
            cli = "redistribute ospf match external"
            if r.ospf.match_external.route_map is not None:
                cli += f" route-map {r.ospf.match_external.route_map}"
            self._add(cli)

        if r.ospf.match_nssa_external.enabled is True:
            cli = "redistribute ospf match nssa-external"
            if r.ospf.match_nssa_external.nssa_type is not None:
                cli += f" {r.ospf.match_nssa_external.nssa_type}"
            if r.ospf.match_nssa_external.route_map is not None:
                cli += f" route-map {r.ospf.match_nssa_external.route_map}"
            self._add(cli)

        if r.static.enabled is True:
            cli = "redistribute static"
            if r.static.route_map is not None:
                cli += f" route-map {r.static.route_map}"
            self._add(cli)

    def _render_address_family_ipv6_sr_te(self, bgp: EosCliConfigGen.RouterBgp) -> None:
        """Render 'address-family ipv6 sr-te' block (J2 lines 2321-2363)."""
        af = bgp.address_family_ipv6_sr_te
        if not af:
            return
        with self._block("address-family ipv6 sr-te"):
            for pg in natural_sort(af.peer_groups or [], sort_key="name"):
                self._render_af_sr_te_entity(pg.name, pg)

            for neighbor in natural_sort(af.neighbors or [], sort_key="ip_address"):
                self._render_af_sr_te_entity(neighbor.ip_address, neighbor)

    def _render_address_family_link_state(self, bgp: EosCliConfigGen.RouterBgp) -> None:
        """Render 'address-family link-state' block (J2 lines 2364-2413)."""
        af = bgp.address_family_link_state
        if not af:
            return
        with self._block("address-family link-state"):
            # bgp missing-policy uses flat direction_{in,out}_action fields.
            self._add("bgp missing-policy direction in action {}", af.bgp.missing_policy.direction_in_action)
            self._add("bgp missing-policy direction out action {}", af.bgp.missing_policy.direction_out_action)

            for pg in natural_sort(af.peer_groups or [], sort_key="name"):
                if pg.activate is True:
                    self._add(f"neighbor {pg.name} activate")
                elif pg.activate is False:
                    self._add(f"no neighbor {pg.name} activate")
                self._add("neighbor {} missing-policy direction in action {}", pg.name, pg.missing_policy.direction_in_action)
                self._add("neighbor {} missing-policy direction out action {}", pg.name, pg.missing_policy.direction_out_action)

            for neighbor in natural_sort(af.neighbors or [], sort_key="ip_address"):
                # J2 checks only 'if True' (no elif False) for neighbor activate.
                if neighbor.activate is True:
                    self._add(f"neighbor {neighbor.ip_address} activate")
                self._add("neighbor {} missing-policy direction in action {}", neighbor.ip_address, neighbor.missing_policy.direction_in_action)
                self._add("neighbor {} missing-policy direction out action {}", neighbor.ip_address, neighbor.missing_policy.direction_out_action)

            path_selection = af.path_selection
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

    def _render_address_family_path_selection(self, bgp: EosCliConfigGen.RouterBgp) -> None:
        """Render 'address-family path-selection' block (J2 lines 2414-2480)."""
        af = bgp.address_family_path_selection
        if not af:
            return
        with self._block("address-family path-selection"):
            self._add("bgp additional-paths receive", af.bgp.additional_paths.receive)

            self._render_af_bgp_additional_paths_send(af.bgp.additional_paths)

            for pg in natural_sort(af.peer_groups or [], sort_key="name"):
                if pg.activate is True:
                    self._add(f"neighbor {pg.name} activate")
                elif pg.activate is False:
                    self._add(f"no neighbor {pg.name} activate")
                if pg.additional_paths.receive is True:
                    self._add(f"neighbor {pg.name} additional-paths receive")
                # Path-selection peer-group send: send_limit checked before send type.
                send = pg.additional_paths.send
                send_limit = pg.additional_paths.send_limit
                if send is not None:
                    if send == "disabled":
                        self._add(f"no neighbor {pg.name} additional-paths send")
                    elif send_limit is not None:
                        if send == "ecmp":
                            self._add(f"neighbor {pg.name} additional-paths send ecmp limit {send_limit}")
                        elif send == "limit":
                            self._add(f"neighbor {pg.name} additional-paths send limit {send_limit}")
                    else:
                        self._add(f"neighbor {pg.name} additional-paths send {send}")

            for neighbor in natural_sort(af.neighbors or [], sort_key="ip_address"):
                if neighbor.activate is True:
                    self._add(f"neighbor {neighbor.ip_address} activate")
                elif neighbor.activate is False:
                    self._add(f"no neighbor {neighbor.ip_address} activate")
                if neighbor.additional_paths.receive is True:
                    self._add(f"neighbor {neighbor.ip_address} additional-paths receive")
                self._render_af_neighbor_additional_paths_send(neighbor.ip_address, neighbor.additional_paths)

    def _render_address_family_rtc(self, bgp: EosCliConfigGen.RouterBgp) -> None:
        """Render 'address-family rt-membership' block (J2 lines 2481-2502)."""
        af = bgp.address_family_rtc
        if not af:
            return
        with self._block("address-family rt-membership"):
            for pg in natural_sort(af.peer_groups or [], sort_key="name"):
                if pg.activate is True:
                    self._add(f"neighbor {pg.name} activate")
                elif pg.activate is False:
                    self._add(f"no neighbor {pg.name} activate")
                # default_route_target: key-presence check (null value is valid, means plain "default-route-target").
                if pg._get_defined_attr("default_route_target") is not Undefined:
                    default_rt = pg.default_route_target
                    if default_rt is not None and default_rt.only is True:
                        self._add(f"neighbor {pg.name} default-route-target only")
                    else:
                        self._add(f"neighbor {pg.name} default-route-target")
                    # encoding_origin_as_omit is type str; YAML null means key is present → render command.
                    if default_rt is not None and default_rt._get_defined_attr("encoding_origin_as_omit") is not Undefined:
                        self._add(f"neighbor {pg.name} default-route-target encoding origin-as omit")

    def _render_address_family_vpn_ipv4(self, bgp: EosCliConfigGen.RouterBgp) -> None:
        """Render 'address-family vpn-ipv4' block (J2 lines 2503-2584)."""
        af = bgp.address_family_vpn_ipv4
        if not af:
            return
        with self._block("address-family vpn-ipv4"):
            for pg in natural_sort(af.peer_groups or [], sort_key="name"):
                self._render_af_vpn_entity(pg.name, pg)

            for neighbor in natural_sort(af.neighbors or [], sort_key="ip_address"):
                self._render_af_vpn_entity(neighbor.ip_address, neighbor)

            if af.neighbor_default_encapsulation_mpls_next_hop_self.source_interface is not None:
                src_iface = af.neighbor_default_encapsulation_mpls_next_hop_self.source_interface
                self._add(f"neighbor default encapsulation mpls next-hop-self source-interface {src_iface}")
            self._add("domain identifier {}", af.domain_identifier)
            if af.route.import_match_failure_action == "discard":
                self._add("route import match-failure action discard")

    def _render_address_family_vpn_ipv6(self, bgp: EosCliConfigGen.RouterBgp) -> None:
        """Render 'address-family vpn-ipv6' block (J2 lines 2585-2666)."""
        af = bgp.address_family_vpn_ipv6
        if not af:
            return
        with self._block("address-family vpn-ipv6"):
            for pg in natural_sort(af.peer_groups or [], sort_key="name"):
                self._render_af_vpn_entity(pg.name, pg)

            for neighbor in natural_sort(af.neighbors or [], sort_key="ip_address"):
                self._render_af_vpn_entity(neighbor.ip_address, neighbor)

            if af.neighbor_default_encapsulation_mpls_next_hop_self.source_interface is not None:
                src_iface = af.neighbor_default_encapsulation_mpls_next_hop_self.source_interface
                self._add(f"neighbor default encapsulation mpls next-hop-self source-interface {src_iface}")
            self._add("domain identifier {}", af.domain_identifier)
            if af.route.import_match_failure_action == "discard":
                self._add("route import match-failure action discard")

    def _render_af_vpn_entity(self, entity_id: str, entity: Any) -> None:
        """Render AF VPN-IPv4/IPv6 commands for a peer-group or neighbor at L2."""
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

    def _render_vrfs(self, bgp: EosCliConfigGen.RouterBgp) -> None:
        """Render all 'vrf' blocks (J2 lines 2667+)."""
        for vrf in natural_sort(bgp.vrfs or [], sort_key="name"):
            self._render_vrf(vrf)

    def _render_vrf(self, vrf: Any) -> None:
        """Render a single VRF block."""
        with self._block(f"vrf {vrf.name}"):
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

            for af in vrf.route_targets.field_import or []:
                for rt in af.route_targets or []:
                    self._add(f"route-target import {af.address_family} {rt}")
                if af.address_family in ["evpn", "vpn-ipv4", "vpn-ipv6"]:
                    if af.rcf is not None:
                        if af.vpn_route_filter_rcf is not None and af.address_family in ["vpn-ipv4", "vpn-ipv6"]:
                            self._add(f"route-target import {af.address_family} rcf {af.rcf} vpn-route filter-rcf {af.vpn_route_filter_rcf}")
                        else:
                            self._add(f"route-target import {af.address_family} rcf {af.rcf}")
                    self._add("route-target import {} route-map {}", af.address_family, af.route_map)

            for rt in natural_sort([r for r in vrf.route_targets.import_evpn_domains or [] if r.domain == "all"], sort_key="route_target"):
                self._add(f"route-target import evpn domain {rt.domain} {rt.route_target}")
            for rt in natural_sort([r for r in vrf.route_targets.import_evpn_domains or [] if r.domain == "remote"], sort_key="route_target"):
                self._add(f"route-target import evpn domain {rt.domain} {rt.route_target}")

            for af in vrf.route_targets.export or []:
                for rt in af.route_targets or []:
                    self._add(f"route-target export {af.address_family} {rt}")
                if af.address_family in ["evpn", "vpn-ipv4", "vpn-ipv6"]:
                    if af.rcf is not None:
                        if af.vrf_route_filter_rcf is not None and af.address_family in ["vpn-ipv4", "vpn-ipv6"]:
                            self._add(f"route-target export {af.address_family} rcf {af.rcf} vrf-route filter-rcf {af.vrf_route_filter_rcf}")
                        else:
                            self._add(f"route-target export {af.address_family} rcf {af.rcf}")
                    self._add("route-target export {} route-map {}", af.address_family, af.route_map)

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
            self._render_af_bgp_additional_paths_send(vrf.bgp.additional_paths)

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
                self._render_vrf_neighbor(neighbor)

            self._render_vrf_body(vrf)

    def _render_vrf_neighbor(self, neighbor: Any) -> None:
        """Render a single VRF neighbor block at L2 (J2 lines 2791-2912+)."""
        ip = neighbor.ip_address

        self._add("neighbor {} peer group {}", ip, neighbor.peer_group)
        self._add("neighbor {} remote-as {}", ip, neighbor.remote_as)
        if neighbor.next_hop_self is True:
            self._add(f"neighbor {ip} next-hop-self")
        if neighbor.next_hop_peer is True:
            self._add(f"neighbor {ip} next-hop-peer")
        if neighbor.shutdown is True:
            self._add(f"neighbor {ip} shutdown")

        if neighbor.remove_private_as.enabled is True:
            cli = f"neighbor {ip} remove-private-as"
            if neighbor.remove_private_as.all is True:
                cli += " all"
                if neighbor.remove_private_as.replace_as is True:
                    cli += " replace-as"
            self._add(cli)
        elif neighbor.remove_private_as.enabled is False:
            self._add(f"no neighbor {ip} remove-private-as")

        if neighbor.as_path.prepend_own_disabled is True:
            self._add(f"neighbor {ip} as-path prepend-own disabled")
        if neighbor.as_path.remote_as_replace_out is True:
            self._add(f"neighbor {ip} as-path remote-as replace out")
        self._add("neighbor {} local-as {} no-prepend replace-as", ip, neighbor.local_as)
        self._add("neighbor {} weight {}", ip, neighbor.weight)
        if neighbor.passive is True:
            self._add(f"neighbor {ip} passive")
        self._add("neighbor {} update-source {}", ip, neighbor.update_source)

        if neighbor.bfd is True:
            self._add(f"neighbor {ip} bfd")
            bfd_timers = neighbor.bfd_timers
            self._add("neighbor {} bfd interval {} min-rx {} multiplier {}", ip, bfd_timers.interval, bfd_timers.min_rx, bfd_timers.multiplier)
        elif neighbor.bfd is False and neighbor.peer_group is not None:
            self._add(f"no neighbor {ip} bfd")

        self._add("neighbor {} description {}", ip, neighbor.description)

        if neighbor.allowas_in.enabled is True:
            cli = f"neighbor {ip} allowas-in"
            if neighbor.allowas_in.times is not None:
                cli += f" {neighbor.allowas_in.times}"
            self._add(cli)

        if neighbor.rib_in_pre_policy_retain.enabled is True:
            cli = f"neighbor {ip} rib-in pre-policy retain"
            if neighbor.rib_in_pre_policy_retain.all is True:
                cli += " all"
            self._add(cli)
        elif neighbor.rib_in_pre_policy_retain.enabled is False:
            self._add(f"no neighbor {ip} rib-in pre-policy retain")

        self._add("neighbor {} ebgp-multihop {}", ip, neighbor.ebgp_multihop)

        if neighbor.route_reflector_client is True:
            self._add(f"neighbor {ip} route-reflector-client")
        elif neighbor.route_reflector_client is False:
            self._add(f"no neighbor {ip} route-reflector-client")

        self._add("neighbor {} timers {}", ip, neighbor.timers)
        self._add("neighbor {} route-map {} in", ip, neighbor.route_map_in)

        if neighbor.additional_paths.receive is True:
            self._add(f"neighbor {ip} additional-paths receive")
        self._render_af_neighbor_additional_paths_send(ip, neighbor.additional_paths)

        self._add("neighbor {} route-map {} out", ip, neighbor.route_map_out)

        if neighbor.password is not None:
            pw = hide_passwords(neighbor.password, self.data.eos_cli_config_gen_configuration.hide_passwords)
            pw_type = neighbor.password_type if neighbor.password_type is not None else "7"
            self._add(f"neighbor {ip} password {pw_type} {pw}")

        # default_originate: object-presence check (no enabled flag required).
        default_originate = neighbor.default_originate
        if default_originate:
            cli = f"neighbor {ip} default-originate"
            if default_originate.route_map is not None:
                cli += f" route-map {default_originate.route_map}"
            if default_originate.always is True:
                cli += " always"
            self._add(cli)

        if neighbor.send_community == "all":
            self._add(f"neighbor {ip} send-community")
        elif neighbor.send_community is not None:
            self._add(f"neighbor {ip} send-community {neighbor.send_community}")

        if neighbor.maximum_routes is not None:
            cli = f"neighbor {ip} maximum-routes {neighbor.maximum_routes}"
            if neighbor.maximum_routes_warning_limit is not None:
                cli += f" warning-limit {neighbor.maximum_routes_warning_limit}"
            if neighbor.maximum_routes_warning_only is True:
                cli += " warning-only"
            self._add(cli)

        self._add("neighbor {} peer-tag in {}", ip, neighbor.peer_tag_in)
        self._add("neighbor {} peer-tag out discard {}", ip, neighbor.peer_tag_out_discard)

        if neighbor.remove_private_as_ingress.enabled is True:
            cli = f"neighbor {ip} remove-private-as ingress"
            if neighbor.remove_private_as_ingress.replace_as is True:
                cli += " replace-as"
            self._add(cli)
        elif neighbor.remove_private_as_ingress.enabled is False:
            self._add(f"no neighbor {ip} remove-private-as ingress")

    def _render_vrf_body(self, vrf: Any) -> None:
        """
        Render the VRF sections that follow the neighbors loop.

        Called from _render_vrf after the neighbors loop (J2 lines 2948-3151).
        Networks, bgp redistribute-internal, aggregate-addresses, redistribute,
        neighbor-interfaces, and nested address-families are handled here.
        """
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
            self._render_vrf_redistribute(vrf.redistribute)

        for ni in natural_sort(vrf.neighbor_interfaces or [], sort_key="name"):
            if ni.peer_group is not None and ni.remote_as is not None:
                self._add(f"neighbor interface {ni.name} peer-group {ni.peer_group} remote-as {ni.remote_as}")
            elif ni.peer_group is not None and ni.peer_filter is not None:
                self._add(f"neighbor interface {ni.name} peer-group {ni.peer_group} peer-filter {ni.peer_filter}")

        self._render_vrf_af_flow_spec(vrf.address_family_flow_spec_ipv4, "ipv4")
        self._render_vrf_af_flow_spec(vrf.address_family_flow_spec_ipv6, "ipv6")
        self._render_vrf_af_ipv4(vrf)
        self._render_vrf_af_ipv4mc(vrf)
        self._render_vrf_af_ipv6(vrf)
        self._render_vrf_af_ipv6mc(vrf)
        self._render_vrf_evpn_multicast(vrf)
        if vrf.eos_cli is not None:
            self._add(self._EXCLAMATION)
            for line in vrf.eos_cli.splitlines():
                self._add(line)
            if vrf.eos_cli.endswith("\n"):
                self._model._lines.append("")

    def _render_vrf_redistribute(self, r: Any) -> None:
        """Render VRF-level redistribute commands at L2 (J2 lines 2982-3144)."""
        if r.connected.enabled is True:
            cli = "redistribute connected"
            if r.connected.include_leaked is True:
                cli += " include leaked"
            if r.connected.route_map is not None:
                cli += f" route-map {r.connected.route_map}"
            elif r.connected.rcf is not None:
                cli += f" rcf {r.connected.rcf}"
            self._add(cli)

        if r.isis.enabled is True:
            cli = "redistribute isis"
            if r.isis.isis_level is not None:
                cli += f" {r.isis.isis_level}"
            if r.isis.include_leaked is True:
                cli += " include leaked"
            if r.isis.route_map is not None:
                cli += f" route-map {r.isis.route_map}"
            elif r.isis.rcf is not None:
                cli += f" rcf {r.isis.rcf}"
            self._add(cli)

        if r.ospf.enabled is True:
            cli = "redistribute ospf"
            if r.ospf.include_leaked is True:
                cli += " include leaked"
            if r.ospf.route_map is not None:
                cli += f" route-map {r.ospf.route_map}"
            self._add(cli)
        elif r.ospf.match_internal.enabled is True:
            cli = "redistribute ospf match internal"
            if r.ospf.match_internal.include_leaked is True:
                cli += " include leaked"
            if r.ospf.match_internal.route_map is not None:
                cli += f" route-map {r.ospf.match_internal.route_map}"
            self._add(cli)

        if r.ospf.match_external.enabled is True:
            cli = "redistribute ospf match external"
            if r.ospf.match_external.include_leaked is True:
                cli += " include leaked"
            if r.ospf.match_external.route_map is not None:
                cli += f" route-map {r.ospf.match_external.route_map}"
            self._add(cli)

        if r.ospf.match_nssa_external.enabled is True:
            cli = "redistribute ospf match nssa-external"
            if r.ospf.match_nssa_external.nssa_type is not None:
                cli += f" {r.ospf.match_nssa_external.nssa_type}"
            if r.ospf.match_nssa_external.include_leaked is True:
                cli += " include leaked"
            if r.ospf.match_nssa_external.route_map is not None:
                cli += f" route-map {r.ospf.match_nssa_external.route_map}"
            self._add(cli)

        if r.ospfv3.enabled is True:
            cli = "redistribute ospfv3"
            if r.ospfv3.include_leaked is True:
                cli += " include leaked"
            if r.ospfv3.route_map is not None:
                cli += f" route-map {r.ospfv3.route_map}"
            self._add(cli)
        elif r.ospfv3.match_internal.enabled is True:
            cli = "redistribute ospfv3 match internal"
            if r.ospfv3.match_internal.include_leaked is True:
                cli += " include leaked"
            if r.ospfv3.match_internal.route_map is not None:
                cli += f" route-map {r.ospfv3.match_internal.route_map}"
            self._add(cli)

        if r.ospfv3.match_external.enabled is True:
            cli = "redistribute ospfv3 match external"
            if r.ospfv3.match_external.include_leaked is True:
                cli += " include leaked"
            if r.ospfv3.match_external.route_map is not None:
                cli += f" route-map {r.ospfv3.match_external.route_map}"
            self._add(cli)

        if r.ospfv3.match_nssa_external.enabled is True:
            cli = "redistribute ospfv3 match nssa-external"
            if r.ospfv3.match_nssa_external.nssa_type is not None:
                cli += f" {r.ospfv3.match_nssa_external.nssa_type}"
            if r.ospfv3.match_nssa_external.include_leaked is True:
                cli += " include leaked"
            if r.ospfv3.match_nssa_external.route_map is not None:
                cli += f" route-map {r.ospfv3.match_nssa_external.route_map}"
            self._add(cli)

        if r.static.enabled is True:
            cli = "redistribute static"
            if r.static.include_leaked is True:
                cli += " include leaked"
            if r.static.route_map is not None:
                cli += f" route-map {r.static.route_map}"
            elif r.static.rcf is not None:
                cli += f" rcf {r.static.rcf}"
            self._add(cli)

        if r.rip.enabled is True:
            cli = "redistribute rip"
            if r.rip.route_map is not None:
                cli += f" route-map {r.rip.route_map}"
            self._add(cli)

        if r.attached_host.enabled is True:
            cli = "redistribute attached-host"
            if r.attached_host.route_map is not None:
                cli += f" route-map {r.attached_host.route_map}"
            self._add(cli)

        if r.dynamic.enabled is True:
            cli = "redistribute dynamic"
            if r.dynamic.route_map is not None:
                cli += f" route-map {r.dynamic.route_map}"
            elif r.dynamic.rcf is not None:
                cli += f" rcf {r.dynamic.rcf}"
            self._add(cli)

        if r.bgp.enabled is True:
            cli = "redistribute bgp leaked"
            if r.bgp.route_map is not None:
                cli += f" route-map {r.bgp.route_map}"
            self._add(cli)

        if r.user.enabled is True:
            cli = "redistribute user"
            if r.user.rcf is not None:
                cli += f" rcf {r.user.rcf}"
            self._add(cli)

    def _render_vrf_af_flow_spec(self, af: Any, protocol: str) -> None:
        """Render VRF 'address-family flow-spec {ipv4|ipv6}' block at L2/L3."""
        if not af:
            return
        with self._block(f"address-family flow-spec {protocol}"):
            self._add("bgp missing-policy direction in action {}", af.bgp.missing_policy.direction_in_action)
            self._add("bgp missing-policy direction out action {}", af.bgp.missing_policy.direction_out_action)
            for neighbor in natural_sort(af.neighbors or [], sort_key="ip_address"):
                if neighbor.activate is True:
                    self._add(f"neighbor {neighbor.ip_address} activate")

    def _render_vrf_af_ipv4(self, vrf: Any) -> None:
        """Render VRF 'address-family ipv4' block at L2/L3 (J2 lines 3182-3411+)."""
        af = vrf.address_family_ipv4
        if not af:
            return
        with self._block("address-family ipv4"):
            if af.bgp.additional_paths.install is True:
                self._add("bgp additional-paths install")
            elif af.bgp.additional_paths.install_ecmp_primary is True:
                self._add("bgp additional-paths install ecmp-primary")

            self._add("bgp missing-policy direction in action {}", af.bgp.missing_policy.direction_in_action)
            self._add("bgp missing-policy direction out action {}", af.bgp.missing_policy.direction_out_action)

            self._add("bgp additional-paths receive", af.bgp.additional_paths.receive)

            # bgp additional-paths send (standard EVPN pattern) at L3.
            send = af.bgp.additional_paths.send
            send_limit = af.bgp.additional_paths.send_limit
            if send is not None:
                if send == "disabled":
                    self._add("no bgp additional-paths send")
                elif send == "ecmp" and send_limit is not None:
                    self._add(f"bgp additional-paths send ecmp limit {send_limit}")
                elif send == "limit" and send_limit is not None:
                    self._add(f"bgp additional-paths send limit {send_limit}")
                else:
                    self._add(f"bgp additional-paths send {send}")

            for neighbor in natural_sort(af.neighbors or [], sort_key="ip_address"):
                ip = neighbor.ip_address
                if neighbor.activate is True:
                    self._add(f"neighbor {ip} activate")
                if neighbor.additional_paths.receive is True:
                    self._add(f"neighbor {ip} additional-paths receive")
                self._add("neighbor {} route-map {} in", ip, neighbor.route_map_in)
                self._add("neighbor {} route-map {} out", ip, neighbor.route_map_out)
                self._add("neighbor {} rcf in {}", ip, neighbor.rcf_in)
                self._add("neighbor {} rcf out {}", ip, neighbor.rcf_out)
                self._add("neighbor {} prefix-list {} in", ip, neighbor.prefix_list_in)
                self._add("neighbor {} prefix-list {} out", ip, neighbor.prefix_list_out)
                # additional-paths send at L3 (standard EVPN pattern, no prefix_list).
                neighbor_send = neighbor.additional_paths.send
                neighbor_send_limit = neighbor.additional_paths.send_limit
                if neighbor_send is not None:
                    if neighbor_send == "disabled":
                        self._add(f"no neighbor {ip} additional-paths send")
                    elif neighbor_send == "ecmp" and neighbor_send_limit is not None:
                        self._add(f"neighbor {ip} additional-paths send ecmp limit {neighbor_send_limit}")
                    elif neighbor_send == "limit" and neighbor_send_limit is not None:
                        self._add(f"neighbor {ip} additional-paths send limit {neighbor_send_limit}")
                    else:
                        self._add(f"neighbor {ip} additional-paths send {neighbor_send}")
                # next-hop address-family ipv6.
                next_hop_ipv6 = neighbor.next_hop.address_family_ipv6
                if next_hop_ipv6.enabled is not None:
                    if next_hop_ipv6.enabled:
                        cli = f"neighbor {ip} next-hop address-family ipv6"
                        if next_hop_ipv6.originate is True:
                            cli += " originate"
                        self._add(cli)
                    else:
                        self._add(f"no neighbor {ip} next-hop address-family ipv6")
                self._add("neighbor {} peer-tag in {}", ip, neighbor.peer_tag_in)
                self._add("neighbor {} peer-tag out discard {}", ip, neighbor.peer_tag_out_discard)

            for network in natural_sort(af.networks or [], sort_key="prefix"):
                cli = f"network {network.prefix}"
                if network.route_map is not None:
                    cli += f" route-map {network.route_map}"
                elif network.rcf is not None:
                    cli += f" rcf {network.rcf}"
                self._add(cli)

            if af.bgp.redistribute_internal is True:
                self._add("bgp redistribute-internal")
            elif af.bgp.redistribute_internal is False:
                self._add("no bgp redistribute-internal")

            if af.redistribute:
                self._render_vrf_af_ipv4_redistribute(af.redistribute)

    def _render_vrf_af_ipv4_redistribute(self, r: Any) -> None:
        """Render VRF address-family ipv4 redistribute commands at L3 (J2 lines 3280-3411+)."""
        if r.attached_host.enabled is True:
            cli = "redistribute attached-host"
            if r.attached_host.route_map is not None:
                cli += f" route-map {r.attached_host.route_map}"
            self._add(cli)

        if r.bgp.enabled is True:
            cli = "redistribute bgp leaked"
            if r.bgp.route_map is not None:
                cli += f" route-map {r.bgp.route_map}"
            self._add(cli)

        if r.connected.enabled is True:
            cli = "redistribute connected"
            if r.connected.include_leaked is True:
                cli += " include leaked"
            if r.connected.route_map is not None:
                cli += f" route-map {r.connected.route_map}"
            elif r.connected.rcf is not None:
                cli += f" rcf {r.connected.rcf}"
            self._add(cli)

        if r.dynamic.enabled is True:
            cli = "redistribute dynamic"
            if r.dynamic.route_map is not None:
                cli += f" route-map {r.dynamic.route_map}"
            elif r.dynamic.rcf is not None:
                cli += f" rcf {r.dynamic.rcf}"
            self._add(cli)

        if r.user.enabled is True:
            cli = "redistribute user"
            if r.user.rcf is not None:
                cli += f" rcf {r.user.rcf}"
            self._add(cli)

        if r.isis.enabled is True:
            cli = "redistribute isis"
            if r.isis.isis_level is not None:
                cli += f" {r.isis.isis_level}"
            if r.isis.include_leaked is True:
                cli += " include leaked"
            if r.isis.route_map is not None:
                cli += f" route-map {r.isis.route_map}"
            elif r.isis.rcf is not None:
                cli += f" rcf {r.isis.rcf}"
            self._add(cli)

        if r.ospf.enabled is True:
            cli = "redistribute ospf"
            if r.ospf.include_leaked is True:
                cli += " include leaked"
            if r.ospf.route_map is not None:
                cli += f" route-map {r.ospf.route_map}"
            self._add(cli)
        elif r.ospf.match_internal.enabled is True:
            cli = "redistribute ospf match internal"
            if r.ospf.match_internal.include_leaked is True:
                cli += " include leaked"
            if r.ospf.match_internal.route_map is not None:
                cli += f" route-map {r.ospf.match_internal.route_map}"
            self._add(cli)

        if r.ospfv3.enabled is True:
            cli = "redistribute ospfv3"
            if r.ospfv3.include_leaked is True:
                cli += " include leaked"
            if r.ospfv3.route_map is not None:
                cli += f" route-map {r.ospfv3.route_map}"
            self._add(cli)
        elif r.ospfv3.match_internal.enabled is True:
            cli = "redistribute ospfv3 match internal"
            if r.ospfv3.match_internal.include_leaked is True:
                cli += " include leaked"
            if r.ospfv3.match_internal.route_map is not None:
                cli += f" route-map {r.ospfv3.match_internal.route_map}"
            self._add(cli)

        if r.ospfv3.match_external.enabled is True:
            cli = "redistribute ospfv3 match external"
            if r.ospfv3.match_external.include_leaked is True:
                cli += " include leaked"
            if r.ospfv3.match_external.route_map is not None:
                cli += f" route-map {r.ospfv3.match_external.route_map}"
            self._add(cli)

        if r.ospfv3.match_nssa_external.enabled is True:
            cli = "redistribute ospfv3 match nssa-external"
            if r.ospfv3.match_nssa_external.nssa_type is not None:
                cli += f" {r.ospfv3.match_nssa_external.nssa_type}"
            if r.ospfv3.match_nssa_external.include_leaked is True:
                cli += " include leaked"
            if r.ospfv3.match_nssa_external.route_map is not None:
                cli += f" route-map {r.ospfv3.match_nssa_external.route_map}"
            self._add(cli)

        if r.ospf.match_external.enabled is True:
            cli = "redistribute ospf match external"
            if r.ospf.match_external.include_leaked is True:
                cli += " include leaked"
            if r.ospf.match_external.route_map is not None:
                cli += f" route-map {r.ospf.match_external.route_map}"
            self._add(cli)

        if r.ospf.match_nssa_external.enabled is True:
            cli = "redistribute ospf match nssa-external"
            if r.ospf.match_nssa_external.nssa_type is not None:
                cli += f" {r.ospf.match_nssa_external.nssa_type}"
            if r.ospf.match_nssa_external.include_leaked is True:
                cli += " include leaked"
            if r.ospf.match_nssa_external.route_map is not None:
                cli += f" route-map {r.ospf.match_nssa_external.route_map}"
            self._add(cli)

        if r.rip.enabled is True:
            cli = "redistribute rip"
            if r.rip.route_map is not None:
                cli += f" route-map {r.rip.route_map}"
            self._add(cli)

        if r.static.enabled is True:
            cli = "redistribute static"
            if r.static.include_leaked is True:
                cli += " include leaked"
            if r.static.route_map is not None:
                cli += f" route-map {r.static.route_map}"
            elif r.static.rcf is not None:
                cli += f" rcf {r.static.rcf}"
            self._add(cli)

    def _render_vrf_af_ipv4mc(self, vrf: Any) -> None:
        """Render VRF 'address-family ipv4 multicast' block at L2/L3 (J2 lines 3444-3582)."""
        af = vrf.address_family_ipv4_multicast
        if not af:
            return
        with self._block("address-family ipv4 multicast"):
            self._add("bgp missing-policy direction in action {}", af.bgp.missing_policy.direction_in_action)
            self._add("bgp missing-policy direction out action {}", af.bgp.missing_policy.direction_out_action)
            self._add("bgp additional-paths receive", af.bgp.additional_paths.receive)

            for neighbor in natural_sort(af.neighbors or [], sort_key="ip_address"):
                ip = neighbor.ip_address
                if neighbor.activate is True:
                    self._add(f"neighbor {ip} activate")
                if neighbor.additional_paths.receive is True:
                    self._add(f"neighbor {ip} additional-paths receive")
                self._add("neighbor {} route-map {} in", ip, neighbor.route_map_in)
                self._add("neighbor {} route-map {} out", ip, neighbor.route_map_out)
                self._add("neighbor {} peer-tag in {}", ip, neighbor.peer_tag_in)
                self._add("neighbor {} peer-tag out discard {}", ip, neighbor.peer_tag_out_discard)

            for network in natural_sort(af.networks or [], sort_key="prefix"):
                cli = f"network {network.prefix}"
                if network.route_map is not None:
                    cli += f" route-map {network.route_map}"
                self._add(cli)

            if af.redistribute:
                self._render_vrf_af_ipv4mc_redistribute(af.redistribute)

    def _render_vrf_af_ipv4mc_redistribute(self, r: Any) -> None:
        """Render VRF address-family ipv4 multicast redistribute commands at L3 (J2 lines 3485-3580)."""
        if r.attached_host.enabled is True:
            cli = "redistribute attached-host"
            if r.attached_host.route_map is not None:
                cli += f" route-map {r.attached_host.route_map}"
            self._add(cli)

        if r.connected.enabled is True:
            cli = "redistribute connected"
            if r.connected.route_map is not None:
                cli += f" route-map {r.connected.route_map}"
            self._add(cli)

        if r.isis.enabled is True:
            cli = "redistribute isis"
            if r.isis.isis_level is not None:
                cli += f" {r.isis.isis_level}"
            if r.isis.include_leaked is True:
                cli += " include leaked"
            if r.isis.route_map is not None:
                cli += f" route-map {r.isis.route_map}"
            elif r.isis.rcf is not None:
                cli += f" rcf {r.isis.rcf}"
            self._add(cli)

        if r.ospf.enabled is True:
            cli = "redistribute ospf"
            if r.ospf.route_map is not None:
                cli += f" route-map {r.ospf.route_map}"
            self._add(cli)
        elif r.ospf.match_internal.enabled is True:
            cli = "redistribute ospf match internal"
            if r.ospf.match_internal.route_map is not None:
                cli += f" route-map {r.ospf.match_internal.route_map}"
            self._add(cli)

        if r.ospfv3.enabled is True:
            cli = "redistribute ospfv3"
            if r.ospfv3.route_map is not None:
                cli += f" route-map {r.ospfv3.route_map}"
            self._add(cli)
        elif r.ospfv3.match_internal.enabled is True:
            cli = "redistribute ospfv3 match internal"
            if r.ospfv3.match_internal.route_map is not None:
                cli += f" route-map {r.ospfv3.match_internal.route_map}"
            self._add(cli)

        if r.ospfv3.match_external.enabled is True:
            cli = "redistribute ospfv3 match external"
            if r.ospfv3.match_external.route_map is not None:
                cli += f" route-map {r.ospfv3.match_external.route_map}"
            self._add(cli)

        if r.ospfv3.match_nssa_external.enabled is True:
            cli = "redistribute ospfv3 match nssa-external"
            if r.ospfv3.match_nssa_external.nssa_type is not None:
                cli += f" {r.ospfv3.match_nssa_external.nssa_type}"
            if r.ospfv3.match_nssa_external.route_map is not None:
                cli += f" route-map {r.ospfv3.match_nssa_external.route_map}"
            self._add(cli)

        if r.ospf.match_external.enabled is True:
            cli = "redistribute ospf match external"
            if r.ospf.match_external.route_map is not None:
                cli += f" route-map {r.ospf.match_external.route_map}"
            self._add(cli)

        if r.ospf.match_nssa_external.enabled is True:
            cli = "redistribute ospf match nssa-external"
            if r.ospf.match_nssa_external.nssa_type is not None:
                cli += f" {r.ospf.match_nssa_external.nssa_type}"
            if r.ospf.match_nssa_external.route_map is not None:
                cli += f" route-map {r.ospf.match_nssa_external.route_map}"
            self._add(cli)

        if r.static.enabled is True:
            cli = "redistribute static"
            if r.static.route_map is not None:
                cli += f" route-map {r.static.route_map}"
            self._add(cli)

    def _render_vrf_af_ipv6(self, vrf: Any) -> None:
        """Render VRF 'address-family ipv6' block at L2/L3 (J2 lines 3583-3791)."""
        af = vrf.address_family_ipv6
        if not af:
            return
        with self._block("address-family ipv6"):
            if af.bgp.additional_paths.install is True:
                self._add("bgp additional-paths install")
            elif af.bgp.additional_paths.install_ecmp_primary is True:
                self._add("bgp additional-paths install ecmp-primary")

            self._add("bgp missing-policy direction in action {}", af.bgp.missing_policy.direction_in_action)
            self._add("bgp missing-policy direction out action {}", af.bgp.missing_policy.direction_out_action)
            self._add("bgp additional-paths receive", af.bgp.additional_paths.receive)

            # bgp additional-paths send (standard EVPN pattern) at L3.
            send = af.bgp.additional_paths.send
            send_limit = af.bgp.additional_paths.send_limit
            if send is not None:
                if send == "disabled":
                    self._add("no bgp additional-paths send")
                elif send == "ecmp" and send_limit is not None:
                    self._add(f"bgp additional-paths send ecmp limit {send_limit}")
                elif send == "limit" and send_limit is not None:
                    self._add(f"bgp additional-paths send limit {send_limit}")
                else:
                    self._add(f"bgp additional-paths send {send}")

            for neighbor in natural_sort(af.neighbors or [], sort_key="ip_address"):
                ip = neighbor.ip_address
                if neighbor.activate is True:
                    self._add(f"neighbor {ip} activate")
                if neighbor.additional_paths.receive is True:
                    self._add(f"neighbor {ip} additional-paths receive")
                self._add("neighbor {} route-map {} in", ip, neighbor.route_map_in)
                self._add("neighbor {} route-map {} out", ip, neighbor.route_map_out)
                self._add("neighbor {} rcf in {}", ip, neighbor.rcf_in)
                self._add("neighbor {} rcf out {}", ip, neighbor.rcf_out)
                self._add("neighbor {} prefix-list {} in", ip, neighbor.prefix_list_in)
                self._add("neighbor {} prefix-list {} out", ip, neighbor.prefix_list_out)
                # additional-paths send per-neighbor (standard EVPN pattern).
                neighbor_send = neighbor.additional_paths.send
                neighbor_send_limit = neighbor.additional_paths.send_limit
                if neighbor_send is not None:
                    if neighbor_send == "disabled":
                        self._add(f"no neighbor {ip} additional-paths send")
                    elif neighbor_send == "ecmp" and neighbor_send_limit is not None:
                        self._add(f"neighbor {ip} additional-paths send ecmp limit {neighbor_send_limit}")
                    elif neighbor_send == "limit" and neighbor_send_limit is not None:
                        self._add(f"neighbor {ip} additional-paths send limit {neighbor_send_limit}")
                    else:
                        self._add(f"neighbor {ip} additional-paths send {neighbor_send}")
                self._add("neighbor {} peer-tag in {}", ip, neighbor.peer_tag_in)
                self._add("neighbor {} peer-tag out discard {}", ip, neighbor.peer_tag_out_discard)

            for network in natural_sort(af.networks or [], sort_key="prefix"):
                cli = f"network {network.prefix}"
                if network.route_map is not None:
                    cli += f" route-map {network.route_map}"
                elif network.rcf is not None:
                    cli += f" rcf {network.rcf}"
                self._add(cli)

            if af.bgp.redistribute_internal is True:
                self._add("bgp redistribute-internal")
            elif af.bgp.redistribute_internal is False:
                self._add("no bgp redistribute-internal")

            if af.redistribute:
                self._render_vrf_af_ipv6_redistribute(af.redistribute)

    def _render_vrf_af_ipv6_redistribute(self, r: Any) -> None:
        """Render VRF address-family ipv6 redistribute commands at L3 (J2 lines 3672-3789)."""
        if r.attached_host.enabled is True:
            cli = "redistribute attached-host"
            if r.attached_host.route_map is not None:
                cli += f" route-map {r.attached_host.route_map}"
            self._add(cli)

        if r.bgp.enabled is True:
            cli = "redistribute bgp leaked"
            if r.bgp.route_map is not None:
                cli += f" route-map {r.bgp.route_map}"
            self._add(cli)

        if r.dhcp.enabled is True:
            cli = "redistribute dhcp"
            if r.dhcp.route_map is not None:
                cli += f" route-map {r.dhcp.route_map}"
            self._add(cli)

        if r.connected.enabled is True:
            cli = "redistribute connected"
            if r.connected.include_leaked is True:
                cli += " include leaked"
            if r.connected.route_map is not None:
                cli += f" route-map {r.connected.route_map}"
            elif r.connected.rcf is not None:
                cli += f" rcf {r.connected.rcf}"
            self._add(cli)

        if r.dynamic.enabled is True:
            cli = "redistribute dynamic"
            if r.dynamic.route_map is not None:
                cli += f" route-map {r.dynamic.route_map}"
            elif r.dynamic.rcf is not None:
                cli += f" rcf {r.dynamic.rcf}"
            self._add(cli)

        if r.user.enabled is True:
            cli = "redistribute user"
            if r.user.rcf is not None:
                cli += f" rcf {r.user.rcf}"
            self._add(cli)

        if r.isis.enabled is True:
            cli = "redistribute isis"
            if r.isis.isis_level is not None:
                cli += f" {r.isis.isis_level}"
            if r.isis.include_leaked is True:
                cli += " include leaked"
            if r.isis.route_map is not None:
                cli += f" route-map {r.isis.route_map}"
            elif r.isis.rcf is not None:
                cli += f" rcf {r.isis.rcf}"
            self._add(cli)

        if r.ospfv3.enabled is True:
            cli = "redistribute ospfv3"
            if r.ospfv3.include_leaked is True:
                cli += " include leaked"
            if r.ospfv3.route_map is not None:
                cli += f" route-map {r.ospfv3.route_map}"
            self._add(cli)
        elif r.ospfv3.match_internal.enabled is True:
            cli = "redistribute ospfv3 match internal"
            if r.ospfv3.match_internal.include_leaked is True:
                cli += " include leaked"
            if r.ospfv3.match_internal.route_map is not None:
                cli += f" route-map {r.ospfv3.match_internal.route_map}"
            self._add(cli)

        if r.ospfv3.match_external.enabled is True:
            cli = "redistribute ospfv3 match external"
            if r.ospfv3.match_external.include_leaked is True:
                cli += " include leaked"
            if r.ospfv3.match_external.route_map is not None:
                cli += f" route-map {r.ospfv3.match_external.route_map}"
            self._add(cli)

        if r.ospfv3.match_nssa_external.enabled is True:
            cli = "redistribute ospfv3 match nssa-external"
            if r.ospfv3.match_nssa_external.nssa_type is not None:
                cli += f" {r.ospfv3.match_nssa_external.nssa_type}"
            if r.ospfv3.match_nssa_external.include_leaked is True:
                cli += " include leaked"
            if r.ospfv3.match_nssa_external.route_map is not None:
                cli += f" route-map {r.ospfv3.match_nssa_external.route_map}"
            self._add(cli)

        if r.static.enabled is True:
            cli = "redistribute static"
            if r.static.include_leaked is True:
                cli += " include leaked"
            if r.static.route_map is not None:
                cli += f" route-map {r.static.route_map}"
            elif r.static.rcf is not None:
                cli += f" rcf {r.static.rcf}"
            self._add(cli)

    def _render_vrf_af_ipv6mc(self, vrf: Any) -> None:
        """Render VRF 'address-family ipv6 multicast' block at L2/L3 (J2 lines 3792-3910+)."""
        af = vrf.address_family_ipv6_multicast
        if not af:
            return
        with self._block("address-family ipv6 multicast"):
            self._add("bgp missing-policy direction in action {}", af.bgp.missing_policy.direction_in_action)
            self._add("bgp missing-policy direction out action {}", af.bgp.missing_policy.direction_out_action)
            self._add("bgp additional-paths receive", af.bgp.additional_paths.receive)

            for neighbor in natural_sort(af.neighbors or [], sort_key="ip_address"):
                ip = neighbor.ip_address
                if neighbor.activate is True:
                    self._add(f"neighbor {ip} activate")
                if neighbor.additional_paths.receive is True:
                    self._add(f"neighbor {ip} additional-paths receive")
                self._add("neighbor {} route-map {} in", ip, neighbor.route_map_in)
                self._add("neighbor {} route-map {} out", ip, neighbor.route_map_out)
                self._add("neighbor {} peer-tag in {}", ip, neighbor.peer_tag_in)
                self._add("neighbor {} peer-tag out discard {}", ip, neighbor.peer_tag_out_discard)

            for network in natural_sort(af.networks or [], sort_key="prefix"):
                cli = f"network {network.prefix}"
                if network.route_map is not None:
                    cli += f" route-map {network.route_map}"
                self._add(cli)

            if af.redistribute:
                self._render_vrf_af_ipv6mc_redistribute(af.redistribute)

    def _render_vrf_af_ipv6mc_redistribute(self, r: Any) -> None:
        """Render VRF address-family ipv6 multicast redistribute commands at L3 (J2 lines 3831-3921)."""
        if r.connected.enabled is True:
            cli = "redistribute connected"
            if r.connected.route_map is not None:
                cli += f" route-map {r.connected.route_map}"
            self._add(cli)

        if r.isis.enabled is True:
            cli = "redistribute isis"
            if r.isis.isis_level is not None:
                cli += f" {r.isis.isis_level}"
            if r.isis.include_leaked is True:
                cli += " include leaked"
            if r.isis.route_map is not None:
                cli += f" route-map {r.isis.route_map}"
            elif r.isis.rcf is not None:
                cli += f" rcf {r.isis.rcf}"
            self._add(cli)

        if r.ospf.enabled is True:
            cli = "redistribute ospf"
            if r.ospf.route_map is not None:
                cli += f" route-map {r.ospf.route_map}"
            self._add(cli)
        elif r.ospf.match_internal.enabled is True:
            cli = "redistribute ospf match internal"
            if r.ospf.match_internal.route_map is not None:
                cli += f" route-map {r.ospf.match_internal.route_map}"
            self._add(cli)

        if r.ospfv3.enabled is True:
            cli = "redistribute ospfv3"
            if r.ospfv3.route_map is not None:
                cli += f" route-map {r.ospfv3.route_map}"
            self._add(cli)
        elif r.ospfv3.match_internal.enabled is True:
            cli = "redistribute ospfv3 match internal"
            if r.ospfv3.match_internal.route_map is not None:
                cli += f" route-map {r.ospfv3.match_internal.route_map}"
            self._add(cli)

        if r.ospfv3.match_external.enabled is True:
            cli = "redistribute ospfv3 match external"
            if r.ospfv3.match_external.route_map is not None:
                cli += f" route-map {r.ospfv3.match_external.route_map}"
            self._add(cli)

        if r.ospfv3.match_nssa_external.enabled is True:
            cli = "redistribute ospfv3 match nssa-external"
            if r.ospfv3.match_nssa_external.nssa_type is not None:
                cli += f" {r.ospfv3.match_nssa_external.nssa_type}"
            if r.ospfv3.match_nssa_external.route_map is not None:
                cli += f" route-map {r.ospfv3.match_nssa_external.route_map}"
            self._add(cli)

        if r.ospf.match_external.enabled is True:
            cli = "redistribute ospf match external"
            if r.ospf.match_external.route_map is not None:
                cli += f" route-map {r.ospf.match_external.route_map}"
            self._add(cli)

        if r.ospf.match_nssa_external.enabled is True:
            cli = "redistribute ospf match nssa-external"
            if r.ospf.match_nssa_external.nssa_type is not None:
                cli += f" {r.ospf.match_nssa_external.nssa_type}"
            if r.ospf.match_nssa_external.route_map is not None:
                cli += f" route-map {r.ospf.match_nssa_external.route_map}"
            self._add(cli)

        if r.static.enabled is True:
            cli = "redistribute static"
            if r.static.route_map is not None:
                cli += f" route-map {r.static.route_map}"
            self._add(cli)

    def _render_vrf_evpn_multicast(self, vrf: Any) -> None:
        """Render VRF 'evpn multicast' block at L2/L3/L4 (J2 lines 3924-3942)."""
        if vrf.evpn_multicast is not True:
            return
        with self._block("evpn multicast", exclamation=False):
            algo = vrf.evpn_multicast_gateway_dr_election.algorithm
            if algo is not None:
                if algo == "preference":
                    pref = vrf.evpn_multicast_gateway_dr_election.preference_value
                    self._add("gateway dr election algorithm preference {}", pref)
                else:
                    self._add(f"gateway dr election algorithm {algo}")

            af_ipv4 = vrf.evpn_multicast_address_family.ipv4
            if af_ipv4 and af_ipv4.transit is True:
                with self._block("address-family ipv4", exclamation=False):
                    self._add("transit")

    def _render_session_trackers(self, bgp: Any) -> None:
        """Render 'session tracker' blocks at L1/L2 (J2 lines 3948-3954)."""
        for tracker in natural_sort(bgp.session_trackers or [], sort_key="name"):
            with self._block(f"session tracker {tracker.name}", exclamation=False):
                self._add("recovery delay {} seconds", tracker.recovery_delay)

    def _render_bgp_eos_cli(self, bgp: Any) -> None:
        """Render top-level 'router bgp' eos_cli block at L1 (J2 lines 3955-3958)."""
        if bgp.eos_cli is None:
            return
        self._add(self._EXCLAMATION)
        for line in bgp.eos_cli.splitlines():
            self._add(line)
