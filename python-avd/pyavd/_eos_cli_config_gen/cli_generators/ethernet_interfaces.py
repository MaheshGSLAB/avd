# Copyright (c) 2023-2026 Arista Networks, Inc.
# Use of this source code is governed by the Apache License 2.0
# that can be found in the LICENSE file.
"""Ethernet interfaces CLI configuration generator."""

from __future__ import annotations

from typing import TYPE_CHECKING

from pyavd.j2filters import hide_passwords, natural_sort, range_expand

from .base import CliConfigSection, CliGenerator, cli_config_contributor

if TYPE_CHECKING:
    from pyavd._eos_cli_config_gen.schema import EosCliConfigGen


class EthernetInterfacesGenerator(CliGenerator):
    """
    Generator for ethernet interfaces CLI configuration.

    Single contributor method `ethernet_interfaces` iterates over sorted interfaces
    and delegates each interface block to `_render_ethernet_interface`. Each helper
    maps to a recognisable block or group of related commands in the CLI output,
    following the same order as ethernet-interfaces.j2.
    """

    _POE_CLASS_MAP: dict[int, str] = {
        0: "15.40",
        1: "4.00",
        2: "7.00",
        3: "15.40",
        4: "30.00",
        5: "45.00",
        6: "60.00",
        7: "75.00",
        8: "90.00",
    }

    @property
    def _section(self) -> CliConfigSection:
        """Ethernet interfaces config section."""
        return self.cli_config.ethernet_interfaces

    @cli_config_contributor
    def ethernet_interfaces(self) -> None:
        """Render all ethernet interface blocks sorted by name (J2 line 8)."""
        for intf in natural_sort(self.data.ethernet_interfaces or [], sort_key="name"):
            self._render_ethernet_interface(intf)

    def _render_ethernet_interface(self, intf: EosCliConfigGen.EthernetInterfacesItem) -> None:
        """Render a single 'interface <name>' block in EOS output order."""
        with self._indent(f"interface {intf.name}"):
            # Comment lines (J2 11-15)
            if intf.comment:
                for line in intf.comment.splitlines():
                    self._write(f"!! {line}")

            self._write("profile {}", intf.profile)
            self._write("description {}", intf.description)

            # shutdown / no shutdown (J2 22-26)
            if intf.shutdown is True:
                self._write("shutdown")
            elif intf.shutdown is False:
                self._write("no shutdown")

            self._write("load-interval {}", intf.load_interval)
            self._write("mtu {}", intf.mtu)

            # logging event link-status (J2 33-37)
            if intf.logging.event.link_status is True:
                self._write("logging event link-status")
            elif intf.logging.event.link_status is False:
                self._write("no logging event link-status")

            self._write("traffic-policy input {}", intf.traffic_policy.input)
            self._write("traffic-policy output {}", intf.traffic_policy.output)
            self._write("bgp session tracker {}", intf.bgp.session_tracker)
            self._write("l2-protocol forwarding profile {}", intf.l2_protocol.forwarding_profile)
            self._write("flowcontrol receive {}", intf.flowcontrol.received)
            self._write("l2 mtu {}", intf.l2_mtu)
            self._write("l2 mru {}", intf.l2_mru)

            # logging event congestion-drops (J2 59-63)
            if intf.logging.event.congestion_drops is True:
                self._write("logging event congestion-drops")
            elif intf.logging.event.congestion_drops is False:
                self._write("no logging event congestion-drops")

            self._write("speed {}", intf.speed)
            self._render_error_correction_encoding(intf)
            self._render_switchport(intf)
            self._render_encapsulation_dot1q(intf)
            self._write("vlan id {}", intf.vlan_id)
            self._render_encapsulation_vlan(intf)
            self._write("switchport source-interface {}", intf.switchport.source_interface)
            self._render_vlan_translations(intf)
            self._write("l2-protocol encapsulation dot1q vlan {}", intf.l2_protocol.encapsulation_dot1q_vlan)
            self._write("mac timestamp {}", intf.mac_timestamp)
            self._render_address_locking(intf)
            self._render_evpn_ethernet_segment(intf)
            self._write("flow tracker hardware {}", intf.flow_tracker.hardware)
            self._write("flow tracker sampled {}", intf.flow_tracker.sampled)

            # snmp trap link-change (J2 308-312)
            if intf.snmp_trap_link_change is False:
                self._write("no snmp trap link-change")
            elif intf.snmp_trap_link_change is True:
                self._write("snmp trap link-change")

            self._write("vrf {}", intf.vrf)
            self._render_ip_address(intf)

            if intf.ip_proxy_arp is True:
                self._write("ip proxy-arp")
            if intf.arp_gratuitous_accept is True:
                self._write("arp gratuitous accept")
            if intf.ip_address == "dhcp" and intf.dhcp_client_accept_default_route is True:
                self._write("dhcp client accept default-route")

            self._write("ip verify unicast source reachable-via {}", intf.ip_verify_unicast_source_reachable_via)
            self._render_ipv6_nd_cache(intf)
            self._render_bfd_interface(intf)
            self._render_ip_helpers(intf)
            self._render_ipv6_dhcp_relay(intf)

            if intf.dhcp_server_ipv4 is True:
                self._write("dhcp server ipv4")
            if intf.dhcp_server_ipv6 is True:
                self._write("dhcp server ipv6")

            self._render_ip_igmp_host_proxy(intf)
            self._render_ipv6(intf)
            self._render_tcp_mss_ceiling(intf)
            self._render_channel_group(intf)

            self._write("ip access-group {} in", intf.access_group_in)
            self._write("ip access-group {} out", intf.access_group_out)
            self._write("ipv6 access-group {} in", intf.ipv6_access_group_in)
            self._write("ipv6 access-group {} out", intf.ipv6_access_group_out)
            self._write("mac access-group {} in", intf.mac_access_group_in)
            self._write("mac access-group {} out", intf.mac_access_group_out)

            self._render_mpls_ldp(intf)

            # lldp (J2 514-522)
            if intf.lldp.transmit is False:
                self._write("no lldp transmit")
            if intf.lldp.receive is False:
                self._write("no lldp receive")
            self._write("lldp tlv transmit ztp vlan {}", intf.lldp.ztp_vlan)

            # loop protection (J2 523-527)
            if intf.loop_protection is False:
                self._write("no loop-protection")
            elif intf.loop_protection is True:
                self._write("loop-protection")

            self._write("mac security profile {}", intf.mac_security.profile)
            self._render_multicast(intf)

            # mpls ip (J2 549-553)
            if intf.mpls.ip is True:
                self._write("mpls ip")
            elif intf.mpls.ip is False:
                self._write("no mpls ip")

            self._render_ip_nat(intf)

            # ntp serve (J2 561-567)
            if intf.ntp_serve is True:
                self._write("ntp serve")
            elif intf.ntp_serve is False:
                self._write("no ntp serve")

            self._render_ospf(intf)
            self._write("service-policy type pbr input {}", intf.service_policy.pbr.input)
            self._render_pim(intf)
            self._render_poe(intf)
            self._render_port_security(intf)
            self._render_ptp(intf)
            self._write("service-policy type qos input {}", intf.service_policy.qos.input)
            self._write("service-profile {}", intf.service_profile)
            self._render_qos(intf)
            self._write("shape rate {}", intf.shape.rate)
            self._render_priority_flow_control(intf)
            self._render_tx_queues(intf)
            self._render_uc_tx_queues(intf)
            self._render_sflow(intf)
            self._render_isis(intf)
            self._render_storm_control(intf)

            # logging event storm-control discards (J2 901-905)
            if intf.logging.event.storm_control_discards is True:
                self._write("logging event storm-control discards")
            elif intf.logging.event.storm_control_discards is False:
                self._write("no logging event storm-control discards")

            self._render_spanning_tree(intf)
            self._render_backup_link(intf)
            self._render_sync_e(intf)
            self._render_tap_tool(intf)
            self._render_traffic_engineering(intf)
            self._render_link_tracking(intf)

            if intf.vmtracer is True:
                self._write("vmtracer vmware-esx")

            self._render_vrrp(intf)
            self._render_transceiver(intf)
            self._render_dot1x(intf)

            # monitor link-flap profiles (J2 1351-1353)
            if intf.monitor_link_flap_profiles:
                profiles = " ".join(natural_sort(intf.monitor_link_flap_profiles, ignore_case=False))
                self._write(f"monitor link-flap profiles {profiles}")

            # eos_cli (J2 1354-1356)
            if intf.eos_cli:
                for line in intf.eos_cli.splitlines():
                    self._write(line)
                self._section._lines.append("")

    # ---------------------------------------------------------------------------
    # Helper methods in J2 template order
    # ---------------------------------------------------------------------------

    def _render_error_correction_encoding(self, intf: EosCliConfigGen.EthernetInterfacesItem) -> None:
        """Render error-correction encoding configuration (J2 67-80)."""
        ece = intf.error_correction_encoding
        if ece.enabled is False:
            self._write("no error-correction encoding")
        else:
            if ece.fire_code is True:
                self._write("error-correction encoding fire-code")
            elif ece.fire_code is False:
                self._write("no error-correction encoding fire-code")
            if ece.reed_solomon is True:
                self._write("error-correction encoding reed-solomon")
            elif ece.reed_solomon is False:
                self._write("no error-correction encoding reed-solomon")

    def _render_switchport(self, intf: EosCliConfigGen.EthernetInterfacesItem) -> None:
        """Render switchport configuration (J2 81-129)."""
        sp = intf.switchport
        if sp.trunk.private_vlan_secondary is True:
            self._write("switchport trunk private-vlan secondary")
        self._write("switchport pvlan mapping {}", sp.pvlan_mapping)
        self._write("switchport access vlan {}", sp.access_vlan)
        if sp.trunk.native_vlan_tag is True:
            self._write("switchport trunk native vlan tag")
        elif sp.trunk.native_vlan:
            self._write("switchport trunk native vlan {}", sp.trunk.native_vlan)
        self._write("switchport phone vlan {}", sp.phone.vlan)
        self._write("switchport phone trunk {}", sp.phone.trunk)
        if sp.vlan_translations.in_required is True:
            self._write("switchport vlan translation in required")
        if sp.vlan_translations.out_required is True:
            self._write("switchport vlan translation out required")
        self._write("switchport dot1q vlan tag {}", sp.dot1q.vlan_tag)
        self._write("switchport trunk allowed vlan {}", sp.trunk.allowed_vlan)
        self._write("switchport mode {}", sp.mode)
        self._write("switchport dot1q ethertype {}", sp.dot1q.ethertype)
        if sp.vlan_forwarding_accept_all is True:
            self._write("switchport vlan forwarding accept all")
        for trunk_group in natural_sort(sp.trunk.groups or [], ignore_case=False):
            self._write(f"switchport trunk group {trunk_group}")
        if sp.enabled is True:
            self._write("switchport")
        elif sp.enabled is False:
            self._write("no switchport")

    def _render_encapsulation_dot1q(self, intf: EosCliConfigGen.EthernetInterfacesItem) -> None:
        """Render encapsulation dot1q configuration (J2 130-136)."""
        if intf.encapsulation_dot1q.vlan is None:
            return
        cli = f"encapsulation dot1q vlan {intf.encapsulation_dot1q.vlan}"
        if intf.encapsulation_dot1q.inner_vlan:
            cli += f" inner {intf.encapsulation_dot1q.inner_vlan}"
        self._write(cli)

    def _render_encapsulation_vlan(self, intf: EosCliConfigGen.EthernetInterfacesItem) -> None:
        """Render encapsulation vlan configuration (J2 140-182)."""
        ev = intf.encapsulation_vlan
        if ev.client.encapsulation is None or intf.encapsulation_dot1q.vlan:
            return

        client_encapsulation = ev.client.encapsulation
        network_flag = False
        encapsulation_cli: str | None = None

        if client_encapsulation in ("dot1q", "dot1ad"):
            if ev.client.vlan:
                encapsulation_cli = f"client {client_encapsulation} {ev.client.vlan}"
            elif ev.client.outer_vlan and ev.client.inner_vlan:
                if ev.client.inner_encapsulation:
                    encapsulation_cli = (
                        f"client {client_encapsulation} outer {ev.client.outer_vlan}"
                        f" inner {ev.client.inner_encapsulation} {ev.client.inner_vlan}"
                    )
                else:
                    encapsulation_cli = (
                        f"client {client_encapsulation} outer {ev.client.outer_vlan}"
                        f" inner {ev.client.inner_vlan}"
                    )
                # Check network encapsulation 'client inner'
                if (ev.network.encapsulation or None) == "client inner":
                    network_flag = True
                    encapsulation_cli += f" network {ev.network.encapsulation}"
        elif client_encapsulation in ("untagged", "unmatched"):
            encapsulation_cli = f"client {client_encapsulation}"

        if encapsulation_cli is None:
            return

        if client_encapsulation in ("dot1q", "dot1ad", "untagged") and ev.network.encapsulation and not network_flag:
            network_encapsulation = ev.network.encapsulation
            if network_encapsulation in ("dot1q", "dot1ad"):
                if ev.network.vlan:
                    encapsulation_cli += f" network {network_encapsulation} {ev.network.vlan}"
                elif ev.network.outer_vlan and ev.network.inner_vlan:
                    if ev.network.inner_encapsulation:
                        encapsulation_cli += (
                            f" network {network_encapsulation} outer {ev.network.outer_vlan}"
                            f" inner {ev.network.inner_encapsulation} {ev.network.inner_vlan}"
                        )
                    else:
                        encapsulation_cli += (
                            f" network {network_encapsulation} outer {ev.network.outer_vlan}"
                            f" inner {ev.network.inner_vlan}"
                        )
            elif network_encapsulation == "untagged" and client_encapsulation == "untagged":
                encapsulation_cli += " network untagged"
            elif network_encapsulation == "client" and client_encapsulation != "untagged":
                encapsulation_cli += " network client"

        with self._indent("encapsulation vlan", sep=False):
            self._write(encapsulation_cli)

    def _render_vlan_translations(self, intf: EosCliConfigGen.EthernetInterfacesItem) -> None:
        """Render VLAN translation configuration (J2 186-225)."""
        sp = intf.switchport

        # direction_both — sorted by 'from' field (J2 186-198)
        for vt in natural_sort(sp.vlan_translations.direction_both or [], sort_key="field_from"):
            cli = f"switchport vlan translation {vt.field_from}"
            if vt.dot1q_tunnel is True:
                cli += " dot1q-tunnel"
            elif vt.inner_vlan_from:
                cli += f" inner {vt.inner_vlan_from}"
                if vt.network is True:
                    cli += " network"
            cli += f" {vt.to}"
            self._write(cli)

        # direction_in (J2 199-210)
        for vt in sp.vlan_translations.direction_in or []:
            cli = f"switchport vlan translation in {vt.field_from}"
            if vt.dot1q_tunnel is True:
                cli += " dot1q-tunnel"
            elif vt.inner_vlan_from:
                cli += f" inner {vt.inner_vlan_from}"
            cli += f" {vt.to}"
            self._write(cli)

        # direction_out (J2 211-225)
        for vt in sp.vlan_translations.direction_out or []:
            cli: str | None = None
            if vt.dot1q_tunnel_to:
                cli = f"switchport vlan translation out {vt.field_from} dot1q-tunnel {vt.dot1q_tunnel_to}"
            elif vt.to:
                cli = f"switchport vlan translation out {vt.field_from} {vt.to}"
                if vt.inner_vlan_to:
                    cli += f" inner {vt.inner_vlan_to}"
            if cli:
                self._write(cli)

    def _render_address_locking(self, intf: EosCliConfigGen.EthernetInterfacesItem) -> None:
        """Render address locking configuration (J2 232-259)."""
        al = intf.address_locking
        if al.address_family.ipv4 is not None or al.address_family.ipv6 is not None or al.ipv4_enforcement_disabled is True:
            with self._indent("address locking"):
                if al.address_family.ipv4 is True:
                    self._write("address-family ipv4")
                if al.address_family.ipv6 is True:
                    self._write("address-family ipv6")
                if al.address_family.ipv4 is False:
                    self._write("address-family ipv4 disabled")
                if al.address_family.ipv6 is False:
                    self._write("address-family ipv6 disabled")
                if al.ipv4_enforcement_disabled is True:
                    self._write("locked-address ipv4 enforcement disabled")
        elif al.ipv4 is True or al.ipv6 is True:
            cli = "address locking"
            if al.ipv4 is True:
                cli += " ipv4"
            if al.ipv6 is True:
                cli += " ipv6"
            self._write(cli)

    def _render_evpn_ethernet_segment(self, intf: EosCliConfigGen.EthernetInterfacesItem) -> None:
        """Render EVPN ethernet-segment configuration (J2 260-301)."""
        ees = intf.evpn_ethernet_segment
        if not ees:
            return

        with self._indent("evpn ethernet-segment"):
            self._write("identifier {}", ees.identifier)
            self._write("redundancy {}", ees.redundancy)

            dfe = ees.designated_forwarder_election
            if dfe:
                if dfe.algorithm == "modulus":
                    self._write("designated-forwarder election algorithm modulus")
                elif dfe.algorithm == "preference" and dfe.preference_value:
                    cli = f"designated-forwarder election algorithm preference {dfe.preference_value}"
                    if dfe.dont_preempt is True:
                        cli += " dont-preempt"
                    self._write(cli)
                if dfe.hold_time:
                    cli = f"designated-forwarder election hold-time {dfe.hold_time}"
                    if dfe.subsequent_hold_time:
                        cli += f" subsequent-hold-time {dfe.subsequent_hold_time}"
                    self._write(cli)
                if dfe.candidate_reachability_required is True:
                    self._write("designated-forwarder election candidate reachability required")
                elif dfe.candidate_reachability_required is False:
                    self._write("no designated-forwarder election candidate reachability required")

            self._write("mpls tunnel flood filter time {}", ees.mpls.tunnel_flood_filter_time)
            self._write("mpls shared index {}", ees.mpls.shared_index)
            self._write("route-target import {}", ees.route_target)

    def _render_ip_address(self, intf: EosCliConfigGen.EthernetInterfacesItem) -> None:
        """Render IP address configuration (J2 316-321)."""
        if intf.ip_address is None:
            return
        self._write(f"ip address {intf.ip_address}")
        for ip_secondary in natural_sort(intf.ip_address_secondaries or []):
            self._write(f"ip address {ip_secondary} secondary")

    def _render_ipv6_nd_cache(self, intf: EosCliConfigGen.EthernetInterfacesItem) -> None:
        """Render IPv6 ND cache configuration (J2 334-344)."""
        cache = intf.ipv6_nd.cache
        self._write("ipv6 nd cache expire {}", cache.expire)
        self._write("ipv6 nd cache dynamic capacity {}", cache.dynamic_capacity)
        if cache.refresh_always is True:
            self._write("ipv6 nd cache refresh always")

    def _render_bfd_interface(self, intf: EosCliConfigGen.EthernetInterfacesItem) -> None:
        """Render BFD configuration (J2 345-354)."""
        bfd = intf.bfd
        if bfd.interval and bfd.min_rx and bfd.multiplier:
            self._write(f"bfd interval {bfd.interval} min-rx {bfd.min_rx} multiplier {bfd.multiplier}")
        if bfd.echo is True:
            self._write("bfd echo")
        elif bfd.echo is False:
            self._write("no bfd echo")

    def _render_ip_helpers(self, intf: EosCliConfigGen.EthernetInterfacesItem) -> None:
        """Render IP helper-address configuration (J2 355-364)."""
        for helper in natural_sort(intf.ip_helpers or [], sort_key="ip_helper"):
            cli = f"ip helper-address {helper.ip_helper}"
            if helper.vrf:
                cli += f" vrf {helper.vrf}"
            if helper.source_interface:
                cli += f" source-interface {helper.source_interface}"
            self._write(cli)

    def _render_ipv6_dhcp_relay(self, intf: EosCliConfigGen.EthernetInterfacesItem) -> None:
        """Render IPv6 DHCP relay destination configuration (J2 365-383)."""
        destinations = intf.ipv6_dhcp_relay_destinations
        if not destinations:
            return

        non_default_vrf = [d for d in destinations if d.vrf and d.vrf != "default"]
        default_vrf = [d for d in destinations if d.vrf is None or d.vrf == "default"]

        sorted_destinations = natural_sort(default_vrf, sort_key="address") + natural_sort(
            natural_sort(non_default_vrf, sort_key="address"), sort_key="vrf", ignore_case=False
        )

        for dest in sorted_destinations:
            cli = f"ipv6 dhcp relay destination {dest.address}"
            if dest.vrf:
                cli += f" vrf {dest.vrf}"
            if dest.local_interface:
                cli += f" local-interface {dest.local_interface}"
            elif dest.source_address:
                cli += f" source-address {dest.source_address}"
            if dest.link_address:
                cli += f" link-address {dest.link_address}"
            self._write(cli)

    def _render_ip_igmp_host_proxy(self, intf: EosCliConfigGen.EthernetInterfacesItem) -> None:
        """Render IP IGMP host-proxy configuration (J2 390-418)."""
        proxy = intf.ip_igmp_host_proxy
        if proxy.enabled is not True:
            return

        host_proxy_cli = "ip igmp host-proxy"
        self._write(host_proxy_cli)

        for group in proxy.groups or []:
            if group.exclude or group.include:
                for include_source in group.include or []:
                    self._write(f"{host_proxy_cli} {group.group} include {include_source.source}")
                for exclude_source in group.exclude or []:
                    self._write(f"{host_proxy_cli} {group.group} exclude {exclude_source.source}")
            elif group.group:
                self._write(f"{host_proxy_cli} {group.group}")

        for access_list in proxy.access_lists or []:
            self._write(f"{host_proxy_cli} access-list {access_list.name}")

        if proxy.report_interval:
            self._write(f"{host_proxy_cli} report-interval {proxy.report_interval}")
        if proxy.version:
            self._write(f"{host_proxy_cli} version {proxy.version}")

    def _render_ipv6(self, intf: EosCliConfigGen.EthernetInterfacesItem) -> None:
        """Render IPv6 address and ND configuration (J2 419-462)."""
        if intf.ipv6_enable is True:
            self._write("ipv6 enable")

        # ipv6 address (J2 422-430)
        if intf.ipv6_addresses:
            for addr in natural_sort(intf.ipv6_addresses):
                self._write(f"ipv6 address {addr}")
        elif intf.ipv6_address_auto_config is True:
            self._write("ipv6 address auto-config")
        elif intf.ipv6_address:
            self._write(f"ipv6 address {intf.ipv6_address}")

        if intf.ipv6_address_link_local:
            self._write(f"ipv6 address {intf.ipv6_address_link_local} link-local")

        nd = intf.ipv6_nd
        if nd.ra.rx_accept.default_route is True:
            self._write("ipv6 nd ra rx accept default-route")
        if nd.ra.rx_accept.route_preference is True:
            self._write("ipv6 nd ra rx accept route-preference")
        if nd.ra.disabled is True or intf.ipv6_nd_ra_disabled is True:
            self._write("ipv6 nd ra disabled")
        if nd.managed_config_flag is True or intf.ipv6_nd_managed_config_flag is True:
            self._write("ipv6 nd managed-config-flag")
        if nd.other_config_flag is True:
            self._write("ipv6 nd other-config-flag")

        # ipv6 nd prefixes — nd.prefixes with fallback to intf.ipv6_nd_prefixes (J2 449-462)
        prefixes = nd.prefixes if nd.prefixes else intf.ipv6_nd_prefixes
        for prefix in natural_sort(prefixes or [], sort_key="ipv6_prefix"):
            cli = f"ipv6 nd prefix {prefix.ipv6_prefix}"
            if prefix.valid_lifetime:
                cli += f" {prefix.valid_lifetime}"
                if prefix.preferred_lifetime:
                    cli += f" {prefix.preferred_lifetime}"
            if prefix.no_autoconfig_flag is True:
                cli += " no-autoconfig"
            self._write(cli)

    def _render_tcp_mss_ceiling(self, intf: EosCliConfigGen.EthernetInterfacesItem) -> None:
        """Render TCP MSS ceiling configuration (J2 463-475)."""
        tmc = intf.tcp_mss_ceiling
        if tmc.ipv4 is None and tmc.ipv6 is None:
            return
        cli = "tcp mss ceiling"
        if tmc.ipv4:
            cli += f" ipv4 {tmc.ipv4}"
        if tmc.ipv6:
            cli += f" ipv6 {tmc.ipv6}"
        if tmc.direction:
            cli += f" {tmc.direction}"
        self._write(cli)

    def _render_channel_group(self, intf: EosCliConfigGen.EthernetInterfacesItem) -> None:
        """Render channel-group and LACP configuration (J2 476-487)."""
        cg = intf.channel_group
        if cg.id is None or cg.mode is None:
            return
        self._write(f"channel-group {cg.id} mode {cg.mode}")
        self._write("lacp timer {}", intf.lacp_timer.mode)
        self._write("lacp timer multiplier {}", intf.lacp_timer.multiplier)
        self._write("lacp port-priority {}", intf.lacp_port_priority)

    def _render_mpls_ldp(self, intf: EosCliConfigGen.EthernetInterfacesItem) -> None:
        """Render MPLS LDP configuration (J2 506-512)."""
        if intf.mpls.ldp.igp_sync is True:
            self._write("mpls ldp igp sync")
        if intf.mpls.ldp.interface is True:
            self._write("mpls ldp interface")
        elif intf.mpls.ldp.interface is False:
            self._write("no mpls ldp interface")

    def _render_multicast(self, intf: EosCliConfigGen.EthernetInterfacesItem) -> None:
        """Render multicast boundary and static configuration (J2 531-547)."""
        mc = intf.multicast
        if mc is None:
            return
        for boundary in mc.ipv4.boundaries or []:
            cli = f"multicast ipv4 boundary {boundary.boundary}"
            if boundary.out is True:
                cli += " out"
            self._write(cli)
        for boundary in mc.ipv6.boundaries or []:
            self._write(f"multicast ipv6 boundary {boundary.boundary} out")
        if mc.ipv4.static is True:
            self._write("multicast ipv4 static")
        if mc.ipv6.static is True:
            self._write("multicast ipv6 static")

    def _render_ip_nat(self, intf: EosCliConfigGen.EthernetInterfacesItem) -> None:
        """Render IP NAT configuration (J2 554-560, interface-ip-nat.j2)."""
        ip_nat = intf.ip_nat
        if ip_nat is None:
            return

        unsorted_nat_entries: list[dict] = []

        # Static source NAT entries
        for nat in ip_nat.source.static or []:
            # Skip entries where both access_list and group are defined, or where original_port is
            # absent but translated_port is present (invalid combinations per interface-ip-nat.j2)
            if nat.access_list and nat.group:
                continue
            if nat.original_port is None and nat.translated_port:
                continue
            nat_cli = "ip nat source"
            sort_key = f"a_{nat.original_ip}"
            if nat.direction:
                nat_cli += f" {nat.direction}"
            nat_cli += f" static {nat.original_ip}"
            if nat.original_port:
                nat_cli += f" {nat.original_port}"
                sort_key += f"_{nat.original_port}"
            if nat.access_list:
                nat_cli += f" access-list {nat.access_list}"
            nat_cli += f" {nat.translated_ip}"
            if nat.translated_port:
                nat_cli += f" {nat.translated_port}"
            if nat.protocol:
                nat_cli += f" protocol {nat.protocol}"
            if nat.group:
                nat_cli += f" group {nat.group}"
                sort_key = f"c_{nat.group}"
            if nat.comment:
                nat_cli += f" comment {nat.comment}"
            unsorted_nat_entries.append({"sort_key": sort_key, "cli": nat_cli})

        # Static destination NAT entries
        for nat in ip_nat.destination.static or []:
            if nat.access_list and nat.group:
                continue
            if nat.original_port is None and nat.translated_port:
                continue
            nat_cli = "ip nat destination"
            sort_key = f"a_{nat.original_ip}"
            if nat.direction:
                nat_cli += f" {nat.direction}"
            nat_cli += f" static {nat.original_ip}"
            if nat.original_port:
                nat_cli += f" {nat.original_port}"
                sort_key += f"_{nat.original_port}"
            if nat.access_list:
                nat_cli += f" access-list {nat.access_list}"
            nat_cli += f" {nat.translated_ip}"
            if nat.translated_port:
                nat_cli += f" {nat.translated_port}"
            if nat.protocol:
                nat_cli += f" protocol {nat.protocol}"
            if nat.group:
                nat_cli += f" group {nat.group}"
                sort_key = f"c_{nat.group}"
            if nat.comment:
                nat_cli += f" comment {nat.comment}"
            unsorted_nat_entries.append({"sort_key": sort_key, "cli": nat_cli})

        # Dynamic source NAT entries
        # The sort_key explodes the access-list name character-by-character to avoid natural sort on it.
        for nat in ip_nat.source.dynamic or []:
            nat_cli = f"ip nat source dynamic access-list {nat.access_list}"
            sort_key = "d_" + ".".join(nat.access_list)
            valid = False
            if nat.nat_type == "overload":
                nat_cli += " overload"
                valid = True
            elif nat.pool_name:
                nat_cli += f" pool {nat.pool_name}"
                valid = True
                if nat.nat_type == "pool-address-only":
                    nat_cli += " address-only"
                elif nat.nat_type == "pool-full-cone":
                    nat_cli += " full-cone"
            if valid:
                if (nat.priority or 0) > 0:
                    nat_cli += f" priority {nat.priority}"
                if nat.comment:
                    nat_cli += f" comment {nat.comment}"
                unsorted_nat_entries.append({"sort_key": sort_key, "cli": nat_cli})

        # Dynamic destination NAT entries
        for nat in ip_nat.destination.dynamic or []:
            nat_cli = f"ip nat destination dynamic access-list {nat.access_list} pool {nat.pool_name}"
            sort_key = "d_" + ".".join(nat.access_list)
            if (nat.priority or 0) > 0:
                nat_cli += f" priority {nat.priority}"
            if nat.comment:
                nat_cli += f" comment {nat.comment}"
            unsorted_nat_entries.append({"sort_key": sort_key, "cli": nat_cli})

        for entry in natural_sort(unsorted_nat_entries, sort_key="sort_key"):
            self._write(entry["cli"])

        self._write("ip nat service-profile {}", ip_nat.service_profile)

    def _render_ospf(self, intf: EosCliConfigGen.EthernetInterfacesItem) -> None:
        """Render OSPF configuration (J2 568-589)."""
        self._write("ip ospf cost {}", intf.ospf_cost)
        if intf.ospf_network_point_to_point is True:
            self._write("ip ospf network point-to-point")
        if intf.ospf_authentication == "simple":
            self._write("ip ospf authentication")
        elif intf.ospf_authentication == "message-digest":
            self._write("ip ospf authentication message-digest")
        if intf.ospf_authentication_key:
            key_type = intf.ospf_authentication_key_type if intf.ospf_authentication_key_type else "7"
            key = hide_passwords(intf.ospf_authentication_key, self.data.eos_cli_config_gen_configuration.hide_passwords)
            self._write(f"ip ospf authentication-key {key_type} {key}")
        self._write("ip ospf area {}", intf.ospf_area)
        for key in natural_sort(intf.ospf_message_digest_keys or [], sort_key="id"):
            if key.hash_algorithm and key.key:
                key_type = key.key_type if key.key_type else "7"
                masked_key = hide_passwords(key.key, self.data.eos_cli_config_gen_configuration.hide_passwords)
                self._write(f"ip ospf message-digest-key {key.id} {key.hash_algorithm} {key_type} {masked_key}")

    def _render_pim(self, intf: EosCliConfigGen.EthernetInterfacesItem) -> None:
        """Render PIM IPv4 configuration (J2 593-616)."""
        pim = intf.pim.ipv4
        if pim.sparse_mode is True:
            self._write("pim ipv4 sparse-mode")
        if pim.bidirectional is True:
            self._write("pim ipv4 bidirectional")
        if pim.border_router is True:
            self._write("pim ipv4 border-router")
        self._write("pim ipv4 hello interval {}", pim.hello.interval)
        self._write("pim ipv4 hello count {}", pim.hello.count)
        self._write("pim ipv4 dr-priority {}", pim.dr_priority)
        self._write("pim ipv4 neighbor filter {}", pim.neighbor_filter)
        if pim.bfd is True:
            self._write("pim ipv4 bfd")

    def _render_poe(self, intf: EosCliConfigGen.EthernetInterfacesItem) -> None:
        """Render Power over Ethernet configuration (J2 617-652)."""
        poe = intf.poe
        self._write("poe priority {}", poe.priority)
        self._write("poe reboot action {}", poe.reboot.action)
        if poe.link_down.action:
            cli = f"poe link down action {poe.link_down.action}"
            if poe.link_down.power_off_delay and poe.link_down.action == "power-off":
                cli += f" {poe.link_down.power_off_delay} seconds"
            self._write(cli)
        self._write("poe shutdown action {}", poe.shutdown.action)
        if poe.disabled is True:
            self._write("poe disabled")
        if poe.limit:
            poe_limit_cli: str | None = None
            if poe.limit.field_class:
                poe_limit_cli = f"poe limit {self._POE_CLASS_MAP[poe.limit.field_class]} watts"
            elif poe.limit.watts:
                poe_limit_cli = f"poe limit {float(poe.limit.watts):.2f} watts"
            if poe_limit_cli and poe.limit.fixed is True:
                poe_limit_cli += " fixed"
            if poe_limit_cli:
                self._write(poe_limit_cli)
        if poe.negotiation_lldp is False:
            self._write("poe negotiation lldp disabled")
        if poe.legacy_detect is True:
            self._write("poe legacy detect")

    def _render_port_security(self, intf: EosCliConfigGen.EthernetInterfacesItem) -> None:
        """Render switchport port-security configuration (J2 653-687)."""
        ps = intf.switchport.port_security
        if ps is None:
            return

        if ps.enabled is True or ps.violation.mode == "shutdown":
            self._write("switchport port-security")
        elif ps.violation.mode == "protect":
            if ps.violation.protect_log is True:
                self._write("switchport port-security violation protect log")
            else:
                self._write("switchport port-security violation protect")

        if ps.mac_address_maximum.disabled is True:
            self._write("switchport port-security mac-address maximum disabled")
        elif ps.mac_address_maximum.disabled is False:
            self._write("no switchport port-security mac-address maximum disabled")
        elif ps.mac_address_maximum.limit:
            self._write(f"switchport port-security mac-address maximum {ps.mac_address_maximum.limit}")

        if ps.violation.mode != "protect":
            sorted_vlans_cli: list[str] = []
            for vlan in ps.vlans or []:
                for vlan_id in range_expand(vlan.range):
                    sorted_vlans_cli.append(
                        f"switchport port-security vlan {vlan_id} mac-address maximum {vlan.mac_address_maximum}"
                    )
            for vlan_cli in natural_sort(sorted_vlans_cli):
                self._write(vlan_cli)
            self._write(
                "switchport port-security vlan default mac-address maximum {}",
                ps.vlan_default_mac_address_maximum,
            )

    def _render_ptp(self, intf: EosCliConfigGen.EthernetInterfacesItem) -> None:
        """Render PTP configuration (J2 688-717)."""
        ptp = intf.ptp
        if ptp.enable is True:
            self._write("ptp enable")
        self._write("ptp announce interval {}", ptp.announce.interval)
        self._write("ptp announce timeout {}", ptp.announce.timeout)
        self._write("ptp delay-mechanism {}", ptp.delay_mechanism)
        self._write("ptp delay-req interval {}", ptp.delay_req)
        self._write("ptp profile g8275.1 destination mac-address {}", ptp.profile.g8275_1.destination_mac_address)
        self._write("ptp role {}", ptp.role)
        self._write("ptp sync-message interval {}", ptp.sync_message.interval)
        self._write("ptp transport {}", ptp.transport)
        self._write("ptp vlan {}", ptp.vlan)

    def _render_qos(self, intf: EosCliConfigGen.EthernetInterfacesItem) -> None:
        """Render QoS trust and marking configuration (J2 724-735)."""
        if intf.qos.trust == "disabled":
            self._write("no qos trust")
        elif intf.qos.trust:
            self._write(f"qos trust {intf.qos.trust}")
        self._write("qos cos {}", intf.qos.cos)
        self._write("qos dscp {}", intf.qos.dscp)

    def _render_priority_flow_control(self, intf: EosCliConfigGen.EthernetInterfacesItem) -> None:
        """Render priority flow control configuration (J2 740-751)."""
        if intf.priority_flow_control.enabled is True:
            self._write("priority-flow-control on")
        elif intf.priority_flow_control.enabled is False:
            self._write("no priority-flow-control")
        for priority_block in natural_sort(intf.priority_flow_control.priorities or [], sort_key="priority"):
            if priority_block.no_drop is True:
                self._write(f"priority-flow-control priority {priority_block.priority} no-drop")
            elif priority_block.no_drop is False:
                self._write(f"priority-flow-control priority {priority_block.priority} drop")

    def _render_tx_queues(self, intf: EosCliConfigGen.EthernetInterfacesItem) -> None:
        """
        Render tx-queue configuration (J2 752-754, ethernet-interface-tx-queues.j2).

        Note: TxQueuesItem inside EthernetInterfacesItem only exposes id, scheduler_profile_responsive,
        and random_detect.ecn — other fields (comment, priority, bandwidth_percent, shape, drop) are
        not part of this schema context and are intentionally omitted.
        """
        for tx_queue in natural_sort(intf.tx_queues or [], sort_key="id"):
            with self._indent(f"tx-queue {tx_queue.id}"):
                if tx_queue.scheduler_profile_responsive is True:
                    self._write("scheduler profile responsive")
                if tx_queue.random_detect:
                    rd = tx_queue.random_detect
                    if rd.ecn.threshold:
                        thresh = rd.ecn.threshold
                        ecn_cmd = (
                            f"random-detect ecn"
                            f" minimum-threshold {thresh.min} {thresh.units}"
                            f" maximum-threshold {thresh.max} {thresh.units}"
                        )
                        if thresh.max_probability:
                            ecn_cmd += f" max-mark-probability {thresh.max_probability}"
                        if thresh.weight:
                            ecn_cmd += f" weight {thresh.weight}"
                        self._write(ecn_cmd)
                    if rd.ecn.count is True:
                        self._write("random-detect ecn count")

    def _render_uc_tx_queues(self, intf: EosCliConfigGen.EthernetInterfacesItem) -> None:
        """
        Render uc-tx-queue configuration (J2 755-757, ethernet-interface-uc-tx-queues.j2).

        Note: UcTxQueuesItem inside EthernetInterfacesItem only exposes id, scheduler_profile_responsive,
        and random_detect.ecn — other fields (comment, priority, bandwidth_percent, shape, drop) are
        not part of this schema context and are intentionally omitted.
        """
        for uc_tx_queue in natural_sort(intf.uc_tx_queues or [], sort_key="id"):
            with self._indent(f"uc-tx-queue {uc_tx_queue.id}"):
                if uc_tx_queue.random_detect:
                    rd = uc_tx_queue.random_detect
                    if rd.ecn.threshold:
                        thresh = rd.ecn.threshold
                        ecn_cmd = (
                            f"random-detect ecn"
                            f" minimum-threshold {thresh.min} {thresh.units}"
                            f" maximum-threshold {thresh.max} {thresh.units}"
                        )
                        if thresh.max_probability:
                            ecn_cmd += f" max-mark-probability {thresh.max_probability}"
                        if thresh.weight:
                            ecn_cmd += f" weight {thresh.weight}"
                        self._write(ecn_cmd)
                    if rd.ecn.count is True:
                        self._write("random-detect ecn count")

    def _render_sflow(self, intf: EosCliConfigGen.EthernetInterfacesItem) -> None:
        """Render sflow configuration (J2 758-774)."""
        sflow = intf.sflow
        if sflow is None:
            return
        if sflow.enable is True:
            self._write("sflow enable")
        elif sflow.enable is False:
            self._write("no sflow enable")
        if sflow.egress.enable is True:
            self._write("sflow egress enable")
        elif sflow.egress.enable is False:
            self._write("no sflow egress enable")
        if sflow.egress.unmodified_enable is True:
            self._write("sflow egress unmodified enable")
        elif sflow.egress.unmodified_enable is False:
            self._write("no sflow egress unmodified enable")

    def _render_isis(self, intf: EosCliConfigGen.EthernetInterfacesItem) -> None:
        """Render IS-IS configuration (J2 775-884)."""
        self._write("isis enable {}", intf.isis_enable)
        if intf.isis_bfd is True:
            self._write("isis bfd")
        self._write("isis circuit-type {}", intf.isis_circuit_type)
        self._write("isis metric {}", intf.isis_metric)
        if intf.isis_passive is True:
            self._write("isis passive")
        if intf.isis_hello_padding is False:
            self._write("no isis hello padding")
        elif intf.isis_hello_padding is True:
            self._write("isis hello padding")
        if intf.isis_network_point_to_point is True:
            self._write("isis network point-to-point")

        isis_auth = intf.isis_authentication
        if isis_auth is None:
            return

        self._render_isis_authentication_mode(isis_auth)
        self._render_isis_authentication_key_ids(isis_auth)
        self._render_isis_authentication_keys(isis_auth)

    def _render_isis_authentication_mode(
        self, isis_auth: EosCliConfigGen.EthernetInterfacesItem.IsisAuthentication
    ) -> None:
        """Render IS-IS authentication mode lines (J2 799-846)."""
        both = isis_auth.both
        valid_modes = ("md5", "text")

        def _mode_is_valid(mode_obj: object) -> bool:
            """Return True if the mode object has a valid authentication mode."""
            mode = getattr(mode_obj, "mode", None)
            if mode in valid_modes:
                return True
            if mode == "sha" and getattr(getattr(mode_obj, "sha", None), "key_id", None) is not None:
                return True
            if mode == "shared-secret" and getattr(mode_obj, "shared_secret", None) is not None:
                return True
            return False

        def _build_mode_cli(mode_obj: object, prefix: str, suffix: str = "") -> str | None:
            mode = getattr(mode_obj, "mode", None)
            if not _mode_is_valid(mode_obj):
                return None
            cli = f"{prefix} {mode}"
            if mode == "sha":
                cli += f" key-id {mode_obj.sha.key_id}"  # type: ignore[union-attr]
            elif mode == "shared-secret":
                ss = mode_obj.shared_secret  # type: ignore[union-attr]
                cli += f" profile {ss.profile} algorithm {ss.algorithm}"
            if getattr(mode_obj, "rx_disabled", None) is True:
                cli += " rx-disabled"
            return cli + suffix

        if _mode_is_valid(both):
            if (cli := _build_mode_cli(both, "isis authentication mode")):
                self._write(cli)
        else:
            if (cli := _build_mode_cli(isis_auth.level_1, "isis authentication mode", " level-1")):
                self._write(cli)
            if (cli := _build_mode_cli(isis_auth.level_2, "isis authentication mode", " level-2")):
                self._write(cli)

    def _render_isis_authentication_key_ids(
        self, isis_auth: EosCliConfigGen.EthernetInterfacesItem.IsisAuthentication
    ) -> None:
        """Render IS-IS authentication key-id lines (J2 847-873)."""
        both_key_ids: list = []

        def _write_key_id(auth_key: object, suffix: str = "") -> None:
            if auth_key.rfc_5310 is True:  # type: ignore[union-attr]
                key_cli = (
                    f"isis authentication key-id {auth_key.id} algorithm {auth_key.algorithm}"  # type: ignore[union-attr]
                    f" rfc-5310 key {auth_key.key_type} "  # type: ignore[union-attr]
                    f"{hide_passwords(auth_key.key, self.data.eos_cli_config_gen_configuration.hide_passwords)}"  # type: ignore[union-attr]
                )
            else:
                key_cli = (
                    f"isis authentication key-id {auth_key.id} algorithm {auth_key.algorithm}"  # type: ignore[union-attr]
                    f" key {auth_key.key_type} "  # type: ignore[union-attr]
                    f"{hide_passwords(auth_key.key, self.data.eos_cli_config_gen_configuration.hide_passwords)}"  # type: ignore[union-attr]
                )
            self._write(key_cli + suffix)

        for auth_key in natural_sort(isis_auth.both.key_ids or [], sort_key="id"):
            both_key_ids.append(auth_key.id)
            _write_key_id(auth_key)

        for auth_key in natural_sort(isis_auth.level_1.key_ids or [], sort_key="id"):
            if auth_key.id not in both_key_ids:
                _write_key_id(auth_key, " level-1")

        for auth_key in natural_sort(isis_auth.level_2.key_ids or [], sort_key="id"):
            if auth_key.id not in both_key_ids:
                _write_key_id(auth_key, " level-2")

    def _render_isis_authentication_keys(
        self, isis_auth: EosCliConfigGen.EthernetInterfacesItem.IsisAuthentication
    ) -> None:
        """Render IS-IS authentication key lines (J2 874-883)."""
        both = isis_auth.both
        hide_pw = self.data.eos_cli_config_gen_configuration.hide_passwords
        if both.key_type and both.key:
            self._write(f"isis authentication key {both.key_type} {hide_passwords(both.key, hide_pw)}")
        else:
            lvl1 = isis_auth.level_1
            if lvl1.key_type and lvl1.key:
                self._write(f"isis authentication key {lvl1.key_type} {hide_passwords(lvl1.key, hide_pw)} level-1")
            lvl2 = isis_auth.level_2
            if lvl2.key_type and lvl2.key:
                self._write(f"isis authentication key {lvl2.key_type} {hide_passwords(lvl2.key, hide_pw)} level-2")

    def _render_storm_control(self, intf: EosCliConfigGen.EthernetInterfacesItem) -> None:
        """Render storm-control configuration (J2 885-900)."""
        sc = intf.storm_control
        for section_name in natural_sort(["broadcast", "multicast", "unknown_unicast"]):
            section = getattr(sc, section_name)
            if section.level:
                section_cli = section_name.replace("_", "-")
                if section.unit == "pps":
                    self._write(f"storm-control {section_cli} level pps {section.level}")
                else:
                    self._write(f"storm-control {section_cli} level {section.level}")
        if sc.all.level:
            if sc.all.unit == "pps":
                self._write(f"storm-control all level pps {sc.all.level}")
            else:
                self._write(f"storm-control all level {sc.all.level}")

    def _render_spanning_tree(self, intf: EosCliConfigGen.EthernetInterfacesItem) -> None:
        """Render spanning-tree configuration (J2 906-942)."""
        if intf.spanning_tree_portfast == "edge":
            self._write("spanning-tree portfast")
        elif intf.spanning_tree_portfast == "network":
            self._write("spanning-tree portfast network")

        self._write("spanning-tree link-type {}", intf.spanning_tree_link_type)

        if intf.spanning_tree_bpduguard and intf.spanning_tree_bpduguard in (True, "True", "enabled"):
            self._write("spanning-tree bpduguard enable")
        elif intf.spanning_tree_bpduguard == "disabled":
            self._write("spanning-tree bpduguard disable")

        if intf.spanning_tree_bpdufilter and intf.spanning_tree_bpdufilter in (True, "True", "enabled"):
            self._write("spanning-tree bpdufilter enable")
        elif intf.spanning_tree_bpdufilter == "disabled":
            self._write("spanning-tree bpdufilter disable")

        if intf.spanning_tree_guard == "disabled":
            self._write("spanning-tree guard none")
        elif intf.spanning_tree_guard:
            self._write(f"spanning-tree guard {intf.spanning_tree_guard}")

        if intf.spanning_tree_bpduguard_rate_limit.enabled is True:
            self._write("spanning-tree bpduguard rate-limit enable")
        elif intf.spanning_tree_bpduguard_rate_limit.enabled is False:
            self._write("spanning-tree bpduguard rate-limit disable")

        if intf.spanning_tree_bpduguard_rate_limit.count:
            cli = f"spanning-tree bpduguard rate-limit count {intf.spanning_tree_bpduguard_rate_limit.count}"
            if intf.spanning_tree_bpduguard_rate_limit.interval:
                cli += f" interval {intf.spanning_tree_bpduguard_rate_limit.interval}"
            self._write(cli)

        # logging event spanning-tree (J2 943-947)
        if intf.logging.event.spanning_tree is True:
            self._write("logging event spanning-tree")
        elif intf.logging.event.spanning_tree is False:
            self._write("no logging event spanning-tree")

    def _render_backup_link(self, intf: EosCliConfigGen.EthernetInterfacesItem) -> None:
        """Render switchport backup-link configuration (J2 948-969)."""
        sp = intf.switchport
        if sp.backup_link.interface is None:
            return
        cli = f"switchport backup-link {sp.backup_link.interface}"
        if sp.backup_link.prefer_vlan:
            cli += f" prefer vlan {sp.backup_link.prefer_vlan}"
        self._write(cli)
        self._write("switchport backup preemption-delay {}", sp.backup.preemption_delay)
        self._write("switchport backup mac-move-burst {}", sp.backup.mac_move_burst)
        self._write("switchport backup mac-move-burst-interval {}", sp.backup.mac_move_burst_interval)
        self._write("switchport backup initial-mac-move-delay {}", sp.backup.initial_mac_move_delay)
        self._write("switchport backup dest-macaddr {}", sp.backup.dest_macaddr)

    def _render_sync_e(self, intf: EosCliConfigGen.EthernetInterfacesItem) -> None:
        """Render Synchronous Ethernet configuration (J2 970-976)."""
        if intf.sync_e.enable is not True:
            return
        with self._indent("sync-e"):
            self._write("priority {}", intf.sync_e.priority)

    def _render_tap_tool(self, intf: EosCliConfigGen.EthernetInterfacesItem) -> None:
        """Render switchport tap/tool configuration (J2 977-1086)."""
        sp = intf.switchport
        if sp.tap is None and sp.tool is None:
            return

        # tap settings
        self._write("switchport tap native vlan {}", sp.tap.native_vlan)

        if sp.tap.identity.id:
            cli = f"switchport tap identity {sp.tap.identity.id}"
            if sp.tap.identity.inner_vlan:
                cli += f" inner {sp.tap.identity.inner_vlan}"
            self._write(cli)

        if sp.tap.mac_address.destination:
            cli = f"switchport tap mac-address dest {sp.tap.mac_address.destination}"
            if sp.tap.mac_address.source:
                cli += f" src {sp.tap.mac_address.source}"
            self._write(cli)

        if sp.tap.encapsulation.vxlan_strip is True and sp.tap.mpls_pop_all is not True:
            self._write("switchport tap encapsulation vxlan strip")

        for protocol in natural_sort(sp.tap.encapsulation.gre.protocols or [], sort_key="protocol"):
            if protocol.strip is True:
                cli = f"switchport tap encapsulation gre protocol {protocol.protocol}"
                if protocol.feature_header_length:
                    cli += f" feature header length {protocol.feature_header_length}"
                cli += " strip"
                if protocol.re_encapsulation_ethernet_header is True:
                    cli += " re-encapsulation ethernet"
                self._write(cli)

        if sp.tap.encapsulation.gre.strip is True:
            self._write("switchport tap encapsulation gre strip")

        for destination in natural_sort(sp.tap.encapsulation.gre.destinations or [], sort_key="destination"):
            tap_enc_cli = f"switchport tap encapsulation gre destination {destination.destination}"
            if destination.source:
                tap_enc_cli += f" source {destination.source}"
            for dest_protocol in natural_sort(destination.protocols or [], sort_key="protocol"):
                if dest_protocol.strip is True:
                    proto_cli = f"{tap_enc_cli} protocol {dest_protocol.protocol}"
                    if dest_protocol.feature_header_length:
                        proto_cli += f" feature header length {dest_protocol.feature_header_length}"
                    proto_cli += " strip"
                    if dest_protocol.re_encapsulation_ethernet_header is True:
                        proto_cli += " re-encapsulation ethernet"
                    self._write(proto_cli)
            if destination.strip is True:
                self._write(f"{tap_enc_cli} strip")

        if sp.tap.mpls_pop_all is True:
            self._write("switchport tap mpls pop all")

        # tool settings
        if sp.tool.mpls_pop_all is True:
            self._write("switchport tool mpls pop all")
        if sp.tool.encapsulation.vn_tag_strip is True:
            self._write("switchport tool encapsulation vn-tag strip")
        if sp.tool.encapsulation.dot1br_strip is True:
            self._write("switchport tool encapsulation dot1br strip")

        self._write("switchport tap allowed vlan {}", sp.tap.allowed_vlan)
        self._write("switchport tool allowed vlan {}", sp.tool.allowed_vlan)

        self._write("switchport tool identity {}", sp.tool.identity.tag)
        if sp.tool.identity.dot1q_dzgre_source:
            self._write(f"switchport tool identity dot1q source dzgre {sp.tool.identity.dot1q_dzgre_source}")
        elif sp.tool.identity.qinq_dzgre_source:
            self._write(f"switchport tool identity qinq source dzgre {sp.tool.identity.qinq_dzgre_source}")

        if sp.tap.truncation.enabled is True:
            cli = "switchport tap truncation"
            if sp.tap.truncation.size:
                cli += f" {sp.tap.truncation.size}"
            self._write(cli)

        if sp.tap.default.groups:
            groups = " group ".join(natural_sort(sp.tap.default.groups, ignore_case=False))
            self._write(f"switchport tap default group {groups}")

        if sp.tap.default.nexthop_groups:
            nxhop_groups = " ".join(natural_sort(sp.tap.default.nexthop_groups, ignore_case=False))
            self._write(f"switchport tap default nexthop-group {nxhop_groups}")

        for interface in natural_sort(sp.tap.default.interfaces or []):
            self._write(f"switchport tap default interface {interface}")

        if sp.tool.groups:
            tool_groups = " ".join(natural_sort(sp.tool.groups, ignore_case=False))
            self._write(f"switchport tool group set {tool_groups}")

        self._write("switchport tool dot1q remove outer {}", sp.tool.dot1q_remove_outer_vlan_tag)

    def _render_traffic_engineering(self, intf: EosCliConfigGen.EthernetInterfacesItem) -> None:
        """Render traffic-engineering configuration (J2 1087-1106)."""
        te = intf.traffic_engineering
        if te.enabled is True:
            self._write("traffic-engineering")
        if te.bandwidth:
            self._write(f"traffic-engineering bandwidth {te.bandwidth.number} {te.bandwidth.unit}")
        if te.administrative_groups:
            self._write(f"traffic-engineering administrative-group {','.join(te.administrative_groups)}")
        for srlg in natural_sort(te.srlgs or [], ignore_case=False):
            self._write(f"traffic-engineering srlg {srlg}")
        self._write("traffic-engineering metric {}", te.metric)
        if te.min_delay_static:
            self._write(
                f"traffic-engineering min-delay static {te.min_delay_static.number} {te.min_delay_static.unit}"
            )
        elif te.min_delay_dynamic.twamp_light_fallback:
            fallback = te.min_delay_dynamic.twamp_light_fallback
            self._write(
                f"traffic-engineering min-delay dynamic twamp-light fallback {fallback.number} {fallback.unit}"
            )

    def _render_link_tracking(self, intf: EosCliConfigGen.EthernetInterfacesItem) -> None:
        """Render link tracking group configuration (J2 1107-1114)."""
        for group in intf.link_tracking_groups or []:
            self._write(f"link tracking group {group.name} {group.direction}")
        if intf.link_tracking.direction and intf.link_tracking.groups:
            for group_name in intf.link_tracking.groups:
                self._write(f"link tracking group {group_name} {intf.link_tracking.direction}")

    def _render_vrrp(self, intf: EosCliConfigGen.EthernetInterfacesItem) -> None:
        """Render VRRP configuration (J2 1118-1178)."""
        hide_pw = self.data.eos_cli_config_gen_configuration.hide_passwords
        for vrid in natural_sort(intf.vrrp_ids or [], sort_key="id"):
            vid = vrid.id
            self._write("vrrp {} priority-level {}", vid, vrid.priority_level)
            self._write("vrrp {} advertisement interval {}", vid, vrid.advertisement.interval)

            if vrid.preempt.enabled is True and (
                vrid.preempt.delay.minimum or vrid.preempt.delay.reload
            ):
                delay_cli = f"vrrp {vid} preempt delay"
                if vrid.preempt.delay.minimum:
                    delay_cli += f" minimum {vrid.preempt.delay.minimum}"
                if vrid.preempt.delay.reload:
                    delay_cli += f" reload {vrid.preempt.delay.reload}"
                self._write(delay_cli)
            elif vrid.preempt.enabled is False:
                self._write(f"no vrrp {vid} preempt")

            self._write("vrrp {} timers delay reload {}", vid, vrid.timers.delay.reload)

            if vrid.peer_authentication:
                pa = vrid.peer_authentication
                peer_auth_cli = f"vrrp {vid} peer authentication"
                if pa.mode == "ietf-md5":
                    peer_auth_cli += " ietf-md5 key-string"
                else:
                    peer_auth_cli += " text"
                if pa.key_type:
                    peer_auth_cli += f" {pa.key_type}"
                peer_auth_cli += f" {hide_passwords(pa.key, hide_pw)}"
                self._write(peer_auth_cli)

            self._write("vrrp {} ipv4 {}", vid, vrid.ipv4.address)
            for secondary_ip in natural_sort(vrid.ipv4.secondary_addresses or []):
                self._write(f"vrrp {vid} ipv4 {secondary_ip} secondary")
            self._write("vrrp {} ipv4 version {}", vid, vrid.ipv4.version)

            for ipv6_address in natural_sort(vrid.ipv6.addresses or []):
                self._write(f"vrrp {vid} ipv6 {ipv6_address}")

            for tracked_obj in natural_sort(vrid.tracked_object or [], sort_key="name", ignore_case=False):
                if tracked_obj.name:
                    tracked_cli = f"vrrp {vid} tracked-object {tracked_obj.name}"
                    if tracked_obj.decrement:
                        tracked_cli += f" decrement {tracked_obj.decrement}"
                    elif tracked_obj.shutdown is True:
                        tracked_cli += " shutdown"
                    self._write(tracked_cli)

    def _render_transceiver(self, intf: EosCliConfigGen.EthernetInterfacesItem) -> None:
        """Render transceiver configuration (J2 1179-1207)."""
        tr = intf.transceiver
        self._write("transceiver media override {}", tr.media.override)
        if tr.power.ignore is True:
            self._write("transceiver power ignore")
        self._write("transceiver application override {}", tr.application_override)

        for app_override in tr.application_override_lanes or []:
            cli = f"transceiver application override {app_override.override} lanes start {app_override.first_lane}"
            if app_override.last_lane:
                cli += f" end {app_override.last_lane}"
            self._write(cli)

        if tr.frequency:
            cli = f"transceiver frequency {float(tr.frequency):.3f}"
            if tr.frequency_unit:
                cli += f" {tr.frequency_unit}"
            self._write(cli)

        if tr.transmitter.signal_power:
            self._write(f"transceiver transmitter signal-power {float(tr.transmitter.signal_power):.2f}")
        if tr.transmitter.disabled is True:
            self._write("transceiver transmitter disabled")

    def _render_dot1x(self, intf: EosCliConfigGen.EthernetInterfacesItem) -> None:
        """Render 802.1x configuration (J2 1208-1350)."""
        dot1x = intf.dot1x
        if dot1x is None:
            return

        # pae mode (J2 1209-1213)
        if dot1x.pae.mode == "authenticator":
            self._write(f"dot1x pae {dot1x.pae.mode}")
        elif dot1x.pae.mode == "supplicant" and dot1x.pae.supplicant_profile:
            self._write(f"dot1x pae {dot1x.pae.mode} {dot1x.pae.supplicant_profile}")

        # authentication failure action (J2 1214-1221)
        if dot1x.authentication_failure:
            if dot1x.authentication_failure.action == "allow" and dot1x.authentication_failure.allow_vlan:
                self._write(f"dot1x authentication failure action traffic allow vlan {dot1x.authentication_failure.allow_vlan}")
            elif dot1x.authentication_failure.action == "drop":
                self._write("dot1x authentication failure action traffic drop")

        # aaa unresponsive (J2 1222-1274)
        if dot1x.aaa.unresponsive:
            self._render_dot1x_aaa_unresponsive(dot1x)

        if dot1x.reauthentication is True:
            self._write("dot1x reauthentication")
        self._write("dot1x port-control {}", dot1x.port_control)

        if dot1x.port_control_force_authorized_phone is True:
            self._write("dot1x port-control force-authorized phone")
        elif dot1x.port_control_force_authorized_phone is False:
            self._write("no dot1x port-control force-authorized phone")

        # host-mode (J2 1286-1296)
        if dot1x.host_mode:
            if dot1x.host_mode.mode == "single-host":
                self._write("dot1x host-mode single-host")
            elif dot1x.host_mode.mode == "multi-host":
                host_mode_cli = "dot1x host-mode multi-host"
                if dot1x.host_mode.multi_host_authenticated is True:
                    host_mode_cli += " authenticated"
                self._write(host_mode_cli)

        if dot1x.eapol.disabled is True:
            self._write("dot1x eapol disabled")
        if dot1x.mac_based_access_list is True:
            self._write("dot1x mac based access-list")

        # mac based authentication (J2 1303-1316)
        if dot1x.mac_based_authentication.enabled is True:
            if dot1x.mac_based_authentication.host_mode_common is True:
                self._write("dot1x mac based authentication host-mode common")
                if dot1x.mac_based_authentication.always is True:
                    self._write("dot1x mac based authentication always")
            else:
                auth_cli = "dot1x mac based authentication"
                if dot1x.mac_based_authentication.always is True:
                    auth_cli += " always"
                self._write(auth_cli)

        # timeout (J2 1317-1333)
        if dot1x.timeout:
            self._write("dot1x timeout quiet-period {}", dot1x.timeout.quiet_period)
            if dot1x.timeout.reauth_timeout_ignore is True:
                self._write("dot1x timeout reauth-timeout-ignore always")
            self._write("dot1x timeout tx-period {}", dot1x.timeout.tx_period)
            self._write("dot1x timeout reauth-period {}", dot1x.timeout.reauth_period)
            self._write("dot1x timeout idle-host {} seconds", dot1x.timeout.idle_host)

        self._write("dot1x reauthorization request limit {}", dot1x.reauthorization_request_limit)

        if dot1x.unauthorized.access_vlan_membership_egress is True:
            self._write("dot1x unauthorized access vlan membership egress")
        if dot1x.unauthorized.native_vlan_membership_egress is True:
            self._write("dot1x unauthorized native vlan membership egress")

        # eapol authentication failure fallback mba (J2 1343-1349)
        if dot1x.eapol.authentication_failure_fallback_mba.enabled is True:
            mba_cli = "dot1x eapol authentication failure fallback mba"
            if dot1x.eapol.authentication_failure_fallback_mba.timeout:
                mba_cli += f" timeout {dot1x.eapol.authentication_failure_fallback_mba.timeout}"
            self._write(mba_cli)

    def _render_dot1x_aaa_unresponsive(self, dot1x: EosCliConfigGen.EthernetInterfacesItem.Dot1x) -> None:
        """Render dot1x aaa unresponsive action and phone-action lines (J2 1222-1274).

        The J2 template iterates over the unresponsive object keys in reverse sort order
        (phone_action before action) and renders each configured action block.

        PhoneAction schema has: apply_cached_results, cached_results_timeout, apply_alternate, traffic_allow.
        Action schema has the same plus: traffic_allow_vlan.
        Fields absent from a class are accessed via getattr(…, None) to mirror Jinja2's Undefined behaviour.
        """
        aaa_config = "dot1x aaa unresponsive"
        unresponsive = dot1x.aaa.unresponsive

        # Process phone_action then action (reverse-sorted order matching J2 behaviour)
        for action_name, cli_part in (("phone_action", "phone action"), ("action", "action")):
            action = getattr(unresponsive, action_name, None)
            if not action:
                continue
            aaa_action_config = f"{aaa_config} {cli_part}"
            if action.apply_cached_results is True:
                action_apply_config = "apply cached-results"
                crt = action.cached_results_timeout
                if crt.time_duration and crt.time_duration_unit:
                    aaa_action_config += f" {action_apply_config} timeout {crt.time_duration} {crt.time_duration_unit}"
            # traffic_allow_vlan and traffic_allow_access_list exist on Action but not PhoneAction — use getattr
            traffic_allow_vlan = getattr(action, "traffic_allow_vlan", None)
            traffic_allow_access_list = getattr(action, "traffic_allow_access_list", None)
            if action.traffic_allow is True:
                if action.apply_alternate is True:
                    aaa_action_config += " else traffic allow"
                else:
                    aaa_action_config += " traffic allow"
            else:
                if traffic_allow_vlan and traffic_allow_access_list:
                    if action.apply_alternate is True:
                        aaa_action_config += f" else traffic allow vlan {traffic_allow_vlan} access-list {traffic_allow_access_list}"
                    else:
                        aaa_action_config += f" traffic allow vlan {traffic_allow_vlan} access-list {traffic_allow_access_list}"
                else:
                    if traffic_allow_vlan:
                        if action.apply_alternate is True:
                            aaa_action_config += f" else traffic allow vlan {traffic_allow_vlan}"
                        else:
                            aaa_action_config += f" traffic allow vlan {traffic_allow_vlan}"
                    if traffic_allow_access_list:
                        if action.apply_alternate is True:
                            aaa_action_config += f" else traffic allow access list {traffic_allow_access_list}"
                        else:
                            aaa_action_config += f" traffic allow access list {traffic_allow_access_list}"
            self._write(aaa_action_config)

        if unresponsive.eap_response:
            self._write(f"{aaa_config} eap response {unresponsive.eap_response}")
