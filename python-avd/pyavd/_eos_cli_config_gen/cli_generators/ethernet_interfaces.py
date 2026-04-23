# Copyright (c) 2023-2026 Arista Networks, Inc.
# Use of this source code is governed by the Apache License 2.0
# that can be found in the LICENSE file.
"""Ethernet interfaces CLI configuration generator."""

from __future__ import annotations

from typing import Any, ClassVar

from pyavd.j2filters import hide_passwords, natural_sort, range_expand

from .base import CliGenerator, CliModel, CliSection, cli_config_contributor

# ---------------------------------------------------------------------------
# CliSection subclasses
# ---------------------------------------------------------------------------


class EthernetInterfacesGenerator(CliGenerator):
    """
    Generator for ethernet interfaces CLI configuration.

    Single contributor method `ethernet_interfaces` iterates over sorted interfaces
    and delegates each interface block to an `EthernetInterface` CliSection, following
    the same order as ethernet-interfaces.j2.
    """

    @property
    def _model(self) -> CliModel:
        """Ethernet interfaces config section."""
        return self.cli_config.ethernet_interfaces

    @cli_config_contributor
    def ethernet_interfaces(self) -> None:
        """Render all ethernet interface blocks sorted by name (J2 line 8)."""
        for intf in natural_sort(self.data.ethernet_interfaces or [], sort_key="name"):
            self._model.extend(EthernetInterface(intf, self.data).render(indent=0))


class EthernetInterface(CliSection):
    """
    Render a single 'interface <name>' block and all its sub-sections.

    separator=True means a '!' line is prepended when any output is produced.
    """

    _POE_CLASS_MAP: ClassVar[dict[int, str]] = {
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

    def __init__(self, intf: Any, data: Any) -> None:
        self._intf = intf
        self._data = data

    def _generate(self) -> None:
        intf = self._intf
        self._header(f"interface {intf.name}")

        # Comment lines (J2 11-15)
        if intf.comment:
            for line in intf.comment.splitlines():
                self._add(f"!! {line}")

        self._add("profile {}", intf.profile)
        self._add("description {}", intf.description)

        # shutdown / no shutdown (J2 22-26)
        if intf.shutdown is True:
            self._add("shutdown")
        elif intf.shutdown is False:
            self._add("no shutdown")

        self._add("load-interval {}", intf.load_interval)
        self._add("mtu {}", intf.mtu)

        # logging event link-status (J2 33-37)
        if intf.logging.event.link_status is True:
            self._add("logging event link-status")
        elif intf.logging.event.link_status is False:
            self._add("no logging event link-status")

        self._add("traffic-policy input {}", intf.traffic_policy.input)
        self._add("traffic-policy output {}", intf.traffic_policy.output)
        self._add("bgp session tracker {}", intf.bgp.session_tracker)
        self._add("l2-protocol forwarding profile {}", intf.l2_protocol.forwarding_profile)
        self._add("flowcontrol receive {}", intf.flowcontrol.received)
        self._add("l2 mtu {}", intf.l2_mtu)
        self._add("l2 mru {}", intf.l2_mru)

        # logging event congestion-drops (J2 59-63)
        if intf.logging.event.congestion_drops is True:
            self._add("logging event congestion-drops")
        elif intf.logging.event.congestion_drops is False:
            self._add("no logging event congestion-drops")

        self._add("speed {}", intf.speed)
        self._render_error_correction_encoding(intf)
        self._render_switchport(intf)
        self._render_encapsulation_dot1q(intf)
        self._add("vlan id {}", intf.vlan_id)
        self._sub(EthernetInterfaceEncapsulationVlan(intf))
        self._add("switchport source-interface {}", intf.switchport.source_interface)
        self._render_vlan_translations(intf)
        self._add("l2-protocol encapsulation dot1q vlan {}", intf.l2_protocol.encapsulation_dot1q_vlan)
        self._add("mac timestamp {}", intf.mac_timestamp)
        self._sub(EthernetInterfaceAddressLocking(intf))
        self._sub(EthernetInterfaceEvpnEthernetSegment(intf))
        self._add("flow tracker hardware {}", intf.flow_tracker.hardware)
        self._add("flow tracker sampled {}", intf.flow_tracker.sampled)

        # snmp trap link-change (J2 308-312)
        if intf.snmp_trap_link_change is False:
            self._add("no snmp trap link-change")
        elif intf.snmp_trap_link_change is True:
            self._add("snmp trap link-change")

        self._add("vrf {}", intf.vrf)
        self._render_ip_address(intf)

        if intf.ip_proxy_arp is True:
            self._add("ip proxy-arp")
        if intf.arp_gratuitous_accept is True:
            self._add("arp gratuitous accept")
        if intf.ip_address == "dhcp" and intf.dhcp_client_accept_default_route is True:
            self._add("dhcp client accept default-route")

        self._add("ip verify unicast source reachable-via {}", intf.ip_verify_unicast_source_reachable_via)
        self._render_ipv6_nd_cache(intf)
        self._render_bfd_interface(intf)
        self._render_ip_helpers(intf)
        self._render_ipv6_dhcp_relay(intf)

        if intf.dhcp_server_ipv4 is True:
            self._add("dhcp server ipv4")
        if intf.dhcp_server_ipv6 is True:
            self._add("dhcp server ipv6")

        self._render_ip_igmp_host_proxy(intf)
        self._render_ipv6(intf)
        self._render_tcp_mss_ceiling(intf)
        self._render_channel_group(intf)

        self._add("ip access-group {} in", intf.access_group_in)
        self._add("ip access-group {} out", intf.access_group_out)
        self._add("ipv6 access-group {} in", intf.ipv6_access_group_in)
        self._add("ipv6 access-group {} out", intf.ipv6_access_group_out)
        self._add("mac access-group {} in", intf.mac_access_group_in)
        self._add("mac access-group {} out", intf.mac_access_group_out)

        self._render_mpls_ldp(intf)

        # lldp (J2 514-522)
        if intf.lldp.transmit is False:
            self._add("no lldp transmit")
        if intf.lldp.receive is False:
            self._add("no lldp receive")
        self._add("lldp tlv transmit ztp vlan {}", intf.lldp.ztp_vlan)

        # loop protection (J2 523-527)
        if intf.loop_protection is False:
            self._add("no loop-protection")
        elif intf.loop_protection is True:
            self._add("loop-protection")

        self._add("mac security profile {}", intf.mac_security.profile)
        self._render_multicast(intf)

        # mpls ip (J2 549-553)
        if intf.mpls.ip is True:
            self._add("mpls ip")
        elif intf.mpls.ip is False:
            self._add("no mpls ip")

        self._render_ip_nat(intf)

        # ntp serve (J2 561-567)
        if intf.ntp_serve is True:
            self._add("ntp serve")
        elif intf.ntp_serve is False:
            self._add("no ntp serve")

        self._render_ospf(intf)
        self._add("service-policy type pbr input {}", intf.service_policy.pbr.input)
        self._render_pim(intf)
        self._render_poe(intf)
        self._render_port_security(intf)
        self._render_ptp(intf)
        self._add("service-policy type qos input {}", intf.service_policy.qos.input)
        self._add("service-profile {}", intf.service_profile)
        self._render_qos(intf)
        self._add("shape rate {}", intf.shape.rate)
        self._render_priority_flow_control(intf)
        self._render_tx_queues(intf)
        self._render_uc_tx_queues(intf)
        self._render_sflow(intf)
        self._render_isis(intf)
        self._render_storm_control(intf)

        # logging event storm-control discards (J2 901-905)
        if intf.logging.event.storm_control_discards is True:
            self._add("logging event storm-control discards")
        elif intf.logging.event.storm_control_discards is False:
            self._add("no logging event storm-control discards")

        self._render_spanning_tree(intf)
        self._render_backup_link(intf)
        self._sub(EthernetInterfaceSyncE(intf))
        self._render_tap_tool(intf)
        self._render_traffic_engineering(intf)
        self._render_link_tracking(intf)

        if intf.vmtracer is True:
            self._add("vmtracer vmware-esx")

        self._render_vrrp(intf)
        self._render_transceiver(intf)
        self._render_dot1x(intf)

        # monitor link-flap profiles (J2 1351-1353)
        if intf.monitor_link_flap_profiles:
            profiles = " ".join(natural_sort(intf.monitor_link_flap_profiles, ignore_case=False))
            self._add(f"monitor link-flap profiles {profiles}")

        # eos_cli (J2 1354-1356)
        if intf.eos_cli:
            for line in intf.eos_cli.splitlines():
                self._add(line)
            self._output_lines.append("")

    # ---------------------------------------------------------------------------
    # Helper methods (flat — no _block usage) in J2 template order
    # ---------------------------------------------------------------------------

    def _render_error_correction_encoding(self, intf: Any) -> None:
        """Render error-correction encoding configuration (J2 67-80)."""
        error_correction_encoding = intf.error_correction_encoding
        if error_correction_encoding.enabled is False:
            self._add("no error-correction encoding")
        else:
            if error_correction_encoding.fire_code is True:
                self._add("error-correction encoding fire-code")
            elif error_correction_encoding.fire_code is False:
                self._add("no error-correction encoding fire-code")
            if error_correction_encoding.reed_solomon is True:
                self._add("error-correction encoding reed-solomon")
            elif error_correction_encoding.reed_solomon is False:
                self._add("no error-correction encoding reed-solomon")

    def _render_switchport(self, intf: Any) -> None:
        """Render switchport configuration (J2 81-129)."""
        switchport = intf.switchport
        if switchport.trunk.private_vlan_secondary is True:
            self._add("switchport trunk private-vlan secondary")
        self._add("switchport pvlan mapping {}", switchport.pvlan_mapping)
        self._add("switchport access vlan {}", switchport.access_vlan)
        if switchport.trunk.native_vlan_tag is True:
            self._add("switchport trunk native vlan tag")
        elif switchport.trunk.native_vlan:
            self._add("switchport trunk native vlan {}", switchport.trunk.native_vlan)
        self._add("switchport phone vlan {}", switchport.phone.vlan)
        self._add("switchport phone trunk {}", switchport.phone.trunk)
        if switchport.vlan_translations.in_required is True:
            self._add("switchport vlan translation in required")
        if switchport.vlan_translations.out_required is True:
            self._add("switchport vlan translation out required")
        self._add("switchport dot1q vlan tag {}", switchport.dot1q.vlan_tag)
        self._add("switchport trunk allowed vlan {}", switchport.trunk.allowed_vlan)
        self._add("switchport mode {}", switchport.mode)
        self._add("switchport dot1q ethertype {}", switchport.dot1q.ethertype)
        if switchport.vlan_forwarding_accept_all is True:
            self._add("switchport vlan forwarding accept all")
        for trunk_group in natural_sort(switchport.trunk.groups or [], ignore_case=False):
            self._add(f"switchport trunk group {trunk_group}")
        if switchport.enabled is True:
            self._add("switchport")
        elif switchport.enabled is False:
            self._add("no switchport")

    def _render_encapsulation_dot1q(self, intf: Any) -> None:
        """Render encapsulation dot1q configuration (J2 130-136)."""
        if intf.encapsulation_dot1q.vlan is None:
            return
        cli = f"encapsulation dot1q vlan {intf.encapsulation_dot1q.vlan}"
        if intf.encapsulation_dot1q.inner_vlan:
            cli += f" inner {intf.encapsulation_dot1q.inner_vlan}"
        self._add(cli)

    def _render_vlan_translations(self, intf: Any) -> None:
        """Render VLAN translation configuration (J2 186-225)."""
        switchport = intf.switchport

        # direction_both — sorted by 'from' field (J2 186-198)
        for vt in natural_sort(switchport.vlan_translations.direction_both or [], sort_key="field_from"):
            cli = f"switchport vlan translation {vt.field_from}"
            if vt.dot1q_tunnel is True:
                cli += " dot1q-tunnel"
            elif vt.inner_vlan_from:
                cli += f" inner {vt.inner_vlan_from}"
                if vt.network is True:
                    cli += " network"
            cli += f" {vt.to}"
            self._add(cli)

        # direction_in (J2 199-210)
        for vt in switchport.vlan_translations.direction_in or []:
            cli = f"switchport vlan translation in {vt.field_from}"
            if vt.dot1q_tunnel is True:
                cli += " dot1q-tunnel"
            elif vt.inner_vlan_from:
                cli += f" inner {vt.inner_vlan_from}"
            cli += f" {vt.to}"
            self._add(cli)

        # direction_out (J2 211-225)
        for vt in switchport.vlan_translations.direction_out or []:
            cli: str | None = None
            if vt.dot1q_tunnel_to:
                cli = f"switchport vlan translation out {vt.field_from} dot1q-tunnel {vt.dot1q_tunnel_to}"
            elif vt.to:
                cli = f"switchport vlan translation out {vt.field_from} {vt.to}"
                if vt.inner_vlan_to:
                    cli += f" inner {vt.inner_vlan_to}"
            if cli:
                self._add(cli)

    def _render_ip_address(self, intf: Any) -> None:
        """Render IP address configuration (J2 316-321)."""
        if intf.ip_address is None:
            return
        self._add(f"ip address {intf.ip_address}")
        for ip_secondary in natural_sort(intf.ip_address_secondaries or []):
            self._add(f"ip address {ip_secondary} secondary")

    def _render_ipv6_nd_cache(self, intf: Any) -> None:
        """Render IPv6 ND cache configuration (J2 334-344)."""
        cache = intf.ipv6_nd.cache
        self._add("ipv6 nd cache expire {}", cache.expire)
        self._add("ipv6 nd cache dynamic capacity {}", cache.dynamic_capacity)
        if cache.refresh_always is True:
            self._add("ipv6 nd cache refresh always")

    def _render_bfd_interface(self, intf: Any) -> None:
        """Render BFD configuration (J2 345-354)."""
        bfd = intf.bfd
        if bfd.interval and bfd.min_rx and bfd.multiplier:
            self._add(f"bfd interval {bfd.interval} min-rx {bfd.min_rx} multiplier {bfd.multiplier}")
        if bfd.echo is True:
            self._add("bfd echo")
        elif bfd.echo is False:
            self._add("no bfd echo")

    def _render_ip_helpers(self, intf: Any) -> None:
        """Render IP helper-address configuration (J2 355-364)."""
        for helper in natural_sort(intf.ip_helpers or [], sort_key="ip_helper"):
            cli = f"ip helper-address {helper.ip_helper}"
            if helper.vrf:
                cli += f" vrf {helper.vrf}"
            if helper.source_interface:
                cli += f" source-interface {helper.source_interface}"
            self._add(cli)

    def _render_ipv6_dhcp_relay(self, intf: Any) -> None:
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
            self._add(cli)

    def _render_ip_igmp_host_proxy(self, intf: Any) -> None:
        """Render IP IGMP host-proxy configuration (J2 390-418)."""
        proxy = intf.ip_igmp_host_proxy
        if proxy.enabled is not True:
            return

        host_proxy_cli = "ip igmp host-proxy"
        self._add(host_proxy_cli)

        for group in proxy.groups or []:
            if group.exclude or group.include:
                for include_source in group.include or []:
                    self._add(f"{host_proxy_cli} {group.group} include {include_source.source}")
                for exclude_source in group.exclude or []:
                    self._add(f"{host_proxy_cli} {group.group} exclude {exclude_source.source}")
            elif group.group:
                self._add(f"{host_proxy_cli} {group.group}")

        for access_list in proxy.access_lists or []:
            self._add(f"{host_proxy_cli} access-list {access_list.name}")

        if proxy.report_interval:
            self._add(f"{host_proxy_cli} report-interval {proxy.report_interval}")
        if proxy.version:
            self._add(f"{host_proxy_cli} version {proxy.version}")

    def _render_ipv6(self, intf: Any) -> None:
        """Render IPv6 address and ND configuration (J2 419-462)."""
        if intf.ipv6_enable is True:
            self._add("ipv6 enable")

        # ipv6 address (J2 422-430)
        if intf.ipv6_addresses:
            for addr in natural_sort(intf.ipv6_addresses):
                self._add(f"ipv6 address {addr}")
        elif intf.ipv6_address_auto_config is True:
            self._add("ipv6 address auto-config")
        elif intf.ipv6_address:
            self._add(f"ipv6 address {intf.ipv6_address}")

        if intf.ipv6_address_link_local:
            self._add(f"ipv6 address {intf.ipv6_address_link_local} link-local")

        ipv6_nd = intf.ipv6_nd
        if ipv6_nd.ra.rx_accept.default_route is True:
            self._add("ipv6 nd ra rx accept default-route")
        if ipv6_nd.ra.rx_accept.route_preference is True:
            self._add("ipv6 nd ra rx accept route-preference")
        if ipv6_nd.ra.disabled is True or intf.ipv6_nd_ra_disabled is True:
            self._add("ipv6 nd ra disabled")
        if ipv6_nd.managed_config_flag is True or intf.ipv6_nd_managed_config_flag is True:
            self._add("ipv6 nd managed-config-flag")
        if ipv6_nd.other_config_flag is True:
            self._add("ipv6 nd other-config-flag")

        # ipv6 nd prefixes — ipv6_nd.prefixes with fallback to intf.ipv6_nd_prefixes (J2 449-462)
        prefixes = ipv6_nd.prefixes or intf.ipv6_nd_prefixes
        for prefix in natural_sort(prefixes or [], sort_key="ipv6_prefix"):
            cli = f"ipv6 nd prefix {prefix.ipv6_prefix}"
            if prefix.valid_lifetime:
                cli += f" {prefix.valid_lifetime}"
                if prefix.preferred_lifetime:
                    cli += f" {prefix.preferred_lifetime}"
            if prefix.no_autoconfig_flag is True:
                cli += " no-autoconfig"
            self._add(cli)

    def _render_tcp_mss_ceiling(self, intf: Any) -> None:
        """Render TCP MSS ceiling configuration (J2 463-475)."""
        tcp_mss_ceiling = intf.tcp_mss_ceiling
        if tcp_mss_ceiling.ipv4 is None and tcp_mss_ceiling.ipv6 is None:
            return
        cli = "tcp mss ceiling"
        if tcp_mss_ceiling.ipv4:
            cli += f" ipv4 {tcp_mss_ceiling.ipv4}"
        if tcp_mss_ceiling.ipv6:
            cli += f" ipv6 {tcp_mss_ceiling.ipv6}"
        if tcp_mss_ceiling.direction:
            cli += f" {tcp_mss_ceiling.direction}"
        self._add(cli)

    def _render_channel_group(self, intf: Any) -> None:
        """Render channel-group and LACP configuration (J2 476-487)."""
        channel_group = intf.channel_group
        if channel_group.id is None or channel_group.mode is None:
            return
        self._add(f"channel-group {channel_group.id} mode {channel_group.mode}")
        self._add("lacp timer {}", intf.lacp_timer.mode)
        self._add("lacp timer multiplier {}", intf.lacp_timer.multiplier)
        self._add("lacp port-priority {}", intf.lacp_port_priority)

    def _render_mpls_ldp(self, intf: Any) -> None:
        """Render MPLS LDP configuration (J2 506-512)."""
        if intf.mpls.ldp.igp_sync is True:
            self._add("mpls ldp igp sync")
        if intf.mpls.ldp.interface is True:
            self._add("mpls ldp interface")
        elif intf.mpls.ldp.interface is False:
            self._add("no mpls ldp interface")

    def _render_multicast(self, intf: Any) -> None:
        """Render multicast boundary and static configuration (J2 531-547)."""
        multicast = intf.multicast
        if multicast is None:
            return
        for boundary in multicast.ipv4.boundaries or []:
            cli = f"multicast ipv4 boundary {boundary.boundary}"
            if boundary.out is True:
                cli += " out"
            self._add(cli)
        for boundary in multicast.ipv6.boundaries or []:
            self._add(f"multicast ipv6 boundary {boundary.boundary} out")
        if multicast.ipv4.static is True:
            self._add("multicast ipv4 static")
        if multicast.ipv6.static is True:
            self._add("multicast ipv6 static")

    def _render_ip_nat(self, intf: Any) -> None:
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
            self._add(entry["cli"])

        self._add("ip nat service-profile {}", ip_nat.service_profile)

    def _render_ospf(self, intf: Any) -> None:
        """Render OSPF configuration (J2 568-589)."""
        self._add("ip ospf cost {}", intf.ospf_cost)
        if intf.ospf_network_point_to_point is True:
            self._add("ip ospf network point-to-point")
        if intf.ospf_authentication == "simple":
            self._add("ip ospf authentication")
        elif intf.ospf_authentication == "message-digest":
            self._add("ip ospf authentication message-digest")
        if intf.ospf_authentication_key:
            key_type = intf.ospf_authentication_key_type or "7"
            key = hide_passwords(intf.ospf_authentication_key, self._data.eos_cli_config_gen_configuration.hide_passwords)
            self._add(f"ip ospf authentication-key {key_type} {key}")
        self._add("ip ospf area {}", intf.ospf_area)
        for key in natural_sort(intf.ospf_message_digest_keys or [], sort_key="id"):
            if key.hash_algorithm and key.key:
                key_type = key.key_type or "7"
                masked_key = hide_passwords(key.key, self._data.eos_cli_config_gen_configuration.hide_passwords)
                self._add(f"ip ospf message-digest-key {key.id} {key.hash_algorithm} {key_type} {masked_key}")

    def _render_pim(self, intf: Any) -> None:
        """Render PIM IPv4 configuration (J2 593-616)."""
        pim = intf.pim.ipv4
        if pim.sparse_mode is True:
            self._add("pim ipv4 sparse-mode")
        if pim.bidirectional is True:
            self._add("pim ipv4 bidirectional")
        if pim.border_router is True:
            self._add("pim ipv4 border-router")
        self._add("pim ipv4 hello interval {}", pim.hello.interval)
        self._add("pim ipv4 hello count {}", pim.hello.count)
        self._add("pim ipv4 dr-priority {}", pim.dr_priority)
        self._add("pim ipv4 neighbor filter {}", pim.neighbor_filter)
        if pim.bfd is True:
            self._add("pim ipv4 bfd")

    def _render_poe(self, intf: Any) -> None:
        """Render Power over Ethernet configuration (J2 617-652)."""
        poe = intf.poe
        self._add("poe priority {}", poe.priority)
        self._add("poe reboot action {}", poe.reboot.action)
        if poe.link_down.action:
            cli = f"poe link down action {poe.link_down.action}"
            if poe.link_down.power_off_delay and poe.link_down.action == "power-off":
                cli += f" {poe.link_down.power_off_delay} seconds"
            self._add(cli)
        self._add("poe shutdown action {}", poe.shutdown.action)
        if poe.disabled is True:
            self._add("poe disabled")
        if poe.limit:
            poe_limit_cli: str | None = None
            if poe.limit.field_class:
                poe_limit_cli = f"poe limit {self._POE_CLASS_MAP[poe.limit.field_class]} watts"
            elif poe.limit.watts:
                poe_limit_cli = f"poe limit {float(poe.limit.watts):.2f} watts"
            if poe_limit_cli and poe.limit.fixed is True:
                poe_limit_cli += " fixed"
            if poe_limit_cli:
                self._add(poe_limit_cli)
        if poe.negotiation_lldp is False:
            self._add("poe negotiation lldp disabled")
        if poe.legacy_detect is True:
            self._add("poe legacy detect")

    def _render_port_security(self, intf: Any) -> None:
        """Render switchport port-security configuration (J2 653-687)."""
        port_security = intf.switchport.port_security
        if port_security is None:
            return

        if port_security.enabled is True or port_security.violation.mode == "shutdown":
            self._add("switchport port-security")
        elif port_security.violation.mode == "protect":
            if port_security.violation.protect_log is True:
                self._add("switchport port-security violation protect log")
            else:
                self._add("switchport port-security violation protect")

        if port_security.mac_address_maximum.disabled is True:
            self._add("switchport port-security mac-address maximum disabled")
        elif port_security.mac_address_maximum.disabled is False:
            self._add("no switchport port-security mac-address maximum disabled")
        elif port_security.mac_address_maximum.limit:
            self._add(f"switchport port-security mac-address maximum {port_security.mac_address_maximum.limit}")

        if port_security.violation.mode != "protect":
            sorted_vlans_cli: list[str] = [
                f"switchport port-security vlan {vlan_id} mac-address maximum {vlan.mac_address_maximum}"
                for vlan in port_security.vlans or []
                for vlan_id in range_expand(vlan.range)
            ]
            for vlan_cli in natural_sort(sorted_vlans_cli):
                self._add(vlan_cli)
            self._add(
                "switchport port-security vlan default mac-address maximum {}",
                port_security.vlan_default_mac_address_maximum,
            )

    def _render_ptp(self, intf: Any) -> None:
        """Render PTP configuration (J2 688-717)."""
        ptp = intf.ptp
        if ptp.enable is True:
            self._add("ptp enable")
        self._add("ptp announce interval {}", ptp.announce.interval)
        self._add("ptp announce timeout {}", ptp.announce.timeout)
        self._add("ptp delay-mechanism {}", ptp.delay_mechanism)
        self._add("ptp delay-req interval {}", ptp.delay_req)
        self._add("ptp profile g8275.1 destination mac-address {}", ptp.profile.g8275_1.destination_mac_address)
        self._add("ptp role {}", ptp.role)
        self._add("ptp sync-message interval {}", ptp.sync_message.interval)
        self._add("ptp transport {}", ptp.transport)
        self._add("ptp vlan {}", ptp.vlan)

    def _render_qos(self, intf: Any) -> None:
        """Render QoS trust and marking configuration (J2 724-735)."""
        if intf.qos.trust == "disabled":
            self._add("no qos trust")
        elif intf.qos.trust:
            self._add(f"qos trust {intf.qos.trust}")
        self._add("qos cos {}", intf.qos.cos)
        self._add("qos dscp {}", intf.qos.dscp)

    def _render_priority_flow_control(self, intf: Any) -> None:
        """Render priority flow control configuration (J2 740-751)."""
        if intf.priority_flow_control.enabled is True:
            self._add("priority-flow-control on")
        elif intf.priority_flow_control.enabled is False:
            self._add("no priority-flow-control")
        for priority_block in natural_sort(intf.priority_flow_control.priorities or [], sort_key="priority"):
            if priority_block.no_drop is True:
                self._add(f"priority-flow-control priority {priority_block.priority} no-drop")
            elif priority_block.no_drop is False:
                self._add(f"priority-flow-control priority {priority_block.priority} drop")

    def _render_tx_queues(self, intf: Any) -> None:
        """
        Render tx-queue configuration (J2 752-754, ethernet-interface-tx-queues.j2).

        Note: TxQueuesItem inside EthernetInterfacesItem only exposes id, scheduler_profile_responsive,
        and random_detect.ecn — other fields (comment, priority, bandwidth_percent, shape, drop) are
        not part of this schema context and are intentionally omitted.
        """
        for tx_queue in natural_sort(intf.tx_queues or [], sort_key="id"):
            self._sub(EthernetInterfaceTxQueue(tx_queue))

    def _render_uc_tx_queues(self, intf: Any) -> None:
        """
        Render uc-tx-queue configuration (J2 755-757, ethernet-interface-uc-tx-queues.j2).

        Note: UcTxQueuesItem inside EthernetInterfacesItem only exposes id, scheduler_profile_responsive,
        and random_detect.ecn — other fields (comment, priority, bandwidth_percent, shape, drop) are
        not part of this schema context and are intentionally omitted.
        """
        for uc_tx_queue in natural_sort(intf.uc_tx_queues or [], sort_key="id"):
            self._sub(EthernetInterfaceUcTxQueue(uc_tx_queue))

    def _render_sflow(self, intf: Any) -> None:
        """Render sflow configuration (J2 758-774)."""
        sflow = intf.sflow
        if sflow is None:
            return
        if sflow.enable is True:
            self._add("sflow enable")
        elif sflow.enable is False:
            self._add("no sflow enable")
        if sflow.egress.enable is True:
            self._add("sflow egress enable")
        elif sflow.egress.enable is False:
            self._add("no sflow egress enable")
        if sflow.egress.unmodified_enable is True:
            self._add("sflow egress unmodified enable")
        elif sflow.egress.unmodified_enable is False:
            self._add("no sflow egress unmodified enable")

    def _render_isis(self, intf: Any) -> None:
        """Render IS-IS configuration (J2 775-884)."""
        self._add("isis enable {}", intf.isis_enable)
        if intf.isis_bfd is True:
            self._add("isis bfd")
        self._add("isis circuit-type {}", intf.isis_circuit_type)
        self._add("isis metric {}", intf.isis_metric)
        if intf.isis_passive is True:
            self._add("isis passive")
        if intf.isis_hello_padding is False:
            self._add("no isis hello padding")
        elif intf.isis_hello_padding is True:
            self._add("isis hello padding")
        if intf.isis_network_point_to_point is True:
            self._add("isis network point-to-point")

        isis_auth = intf.isis_authentication
        if isis_auth is None:
            return

        self._render_isis_authentication_mode(isis_auth)
        self._render_isis_authentication_key_ids(isis_auth)
        self._render_isis_authentication_keys(isis_auth)

    def _render_isis_authentication_mode(self, isis_auth: Any) -> None:
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
            return mode == "shared-secret" and getattr(mode_obj, "shared_secret", None) is not None

        def _build_mode_cli(mode_obj: object, prefix: str, suffix: str = "") -> str | None:
            mode = getattr(mode_obj, "mode", None)
            if not _mode_is_valid(mode_obj):
                return None
            cli = f"{prefix} {mode}"
            if mode == "sha":
                cli += f" key-id {mode_obj.sha.key_id}"  # type: ignore[union-attr]
            elif mode == "shared-secret":
                shared_secret = mode_obj.shared_secret  # type: ignore[union-attr]
                cli += f" profile {shared_secret.profile} algorithm {shared_secret.algorithm}"
            if getattr(mode_obj, "rx_disabled", None) is True:
                cli += " rx-disabled"
            return cli + suffix

        if _mode_is_valid(both):
            if cli := _build_mode_cli(both, "isis authentication mode"):
                self._add(cli)
        else:
            if cli := _build_mode_cli(isis_auth.level_1, "isis authentication mode", " level-1"):
                self._add(cli)
            if cli := _build_mode_cli(isis_auth.level_2, "isis authentication mode", " level-2"):
                self._add(cli)

    def _render_isis_authentication_key_ids(self, isis_auth: Any) -> None:
        """Render IS-IS authentication key-id lines (J2 847-873)."""
        both_key_ids: list = []

        def _add_key_id(auth_key: object, suffix: str = "") -> None:
            if auth_key.rfc_5310 is True:  # type: ignore[union-attr]
                key_cli = (
                    f"isis authentication key-id {auth_key.id} algorithm {auth_key.algorithm}"  # type: ignore[union-attr]
                    f" rfc-5310 key {auth_key.key_type} "  # type: ignore[union-attr]
                    f"{hide_passwords(auth_key.key, self._data.eos_cli_config_gen_configuration.hide_passwords)}"  # type: ignore[union-attr]
                )
            else:
                key_cli = (
                    f"isis authentication key-id {auth_key.id} algorithm {auth_key.algorithm}"  # type: ignore[union-attr]
                    f" key {auth_key.key_type} "  # type: ignore[union-attr]
                    f"{hide_passwords(auth_key.key, self._data.eos_cli_config_gen_configuration.hide_passwords)}"  # type: ignore[union-attr]
                )
            self._add(key_cli + suffix)

        for auth_key in natural_sort(isis_auth.both.key_ids or [], sort_key="id"):
            both_key_ids.append(auth_key.id)
            _add_key_id(auth_key)

        for auth_key in natural_sort(isis_auth.level_1.key_ids or [], sort_key="id"):
            if auth_key.id not in both_key_ids:
                _add_key_id(auth_key, " level-1")

        for auth_key in natural_sort(isis_auth.level_2.key_ids or [], sort_key="id"):
            if auth_key.id not in both_key_ids:
                _add_key_id(auth_key, " level-2")

    def _render_isis_authentication_keys(self, isis_auth: Any) -> None:
        """Render IS-IS authentication key lines (J2 874-883)."""
        both = isis_auth.both
        hide_passwords_enabled = self._data.eos_cli_config_gen_configuration.hide_passwords
        if both.key_type and both.key:
            self._add(f"isis authentication key {both.key_type} {hide_passwords(both.key, hide_passwords_enabled)}")
        else:
            level_1 = isis_auth.level_1
            if level_1.key_type and level_1.key:
                self._add(f"isis authentication key {level_1.key_type} {hide_passwords(level_1.key, hide_passwords_enabled)} level-1")
            level_2 = isis_auth.level_2
            if level_2.key_type and level_2.key:
                self._add(f"isis authentication key {level_2.key_type} {hide_passwords(level_2.key, hide_passwords_enabled)} level-2")

    def _render_storm_control(self, intf: Any) -> None:
        """Render storm-control configuration (J2 885-900)."""
        storm_control = intf.storm_control
        for section_name in natural_sort(["broadcast", "multicast", "unknown_unicast"]):
            section = getattr(storm_control, section_name)
            if section.level:
                section_cli = section_name.replace("_", "-")
                if section.unit == "pps":
                    self._add(f"storm-control {section_cli} level pps {section.level}")
                else:
                    self._add(f"storm-control {section_cli} level {section.level}")
        if storm_control.all.level:
            if storm_control.all.unit == "pps":
                self._add(f"storm-control all level pps {storm_control.all.level}")
            else:
                self._add(f"storm-control all level {storm_control.all.level}")

    def _render_spanning_tree(self, intf: Any) -> None:
        """Render spanning-tree configuration (J2 906-942)."""
        if intf.spanning_tree_portfast == "edge":
            self._add("spanning-tree portfast")
        elif intf.spanning_tree_portfast == "network":
            self._add("spanning-tree portfast network")

        self._add("spanning-tree link-type {}", intf.spanning_tree_link_type)

        if intf.spanning_tree_bpduguard and intf.spanning_tree_bpduguard in (True, "True", "enabled"):
            self._add("spanning-tree bpduguard enable")
        elif intf.spanning_tree_bpduguard == "disabled":
            self._add("spanning-tree bpduguard disable")

        if intf.spanning_tree_bpdufilter and intf.spanning_tree_bpdufilter in (True, "True", "enabled"):
            self._add("spanning-tree bpdufilter enable")
        elif intf.spanning_tree_bpdufilter == "disabled":
            self._add("spanning-tree bpdufilter disable")

        if intf.spanning_tree_guard == "disabled":
            self._add("spanning-tree guard none")
        elif intf.spanning_tree_guard:
            self._add(f"spanning-tree guard {intf.spanning_tree_guard}")

        if intf.spanning_tree_bpduguard_rate_limit.enabled is True:
            self._add("spanning-tree bpduguard rate-limit enable")
        elif intf.spanning_tree_bpduguard_rate_limit.enabled is False:
            self._add("spanning-tree bpduguard rate-limit disable")

        if intf.spanning_tree_bpduguard_rate_limit.count:
            cli = f"spanning-tree bpduguard rate-limit count {intf.spanning_tree_bpduguard_rate_limit.count}"
            if intf.spanning_tree_bpduguard_rate_limit.interval:
                cli += f" interval {intf.spanning_tree_bpduguard_rate_limit.interval}"
            self._add(cli)

        # logging event spanning-tree (J2 943-947)
        if intf.logging.event.spanning_tree is True:
            self._add("logging event spanning-tree")
        elif intf.logging.event.spanning_tree is False:
            self._add("no logging event spanning-tree")

    def _render_backup_link(self, intf: Any) -> None:
        """Render switchport backup-link configuration (J2 948-969)."""
        switchport = intf.switchport
        if switchport.backup_link.interface is None:
            return
        cli = f"switchport backup-link {switchport.backup_link.interface}"
        if switchport.backup_link.prefer_vlan:
            cli += f" prefer vlan {switchport.backup_link.prefer_vlan}"
        self._add(cli)
        self._add("switchport backup preemption-delay {}", switchport.backup.preemption_delay)
        self._add("switchport backup mac-move-burst {}", switchport.backup.mac_move_burst)
        self._add("switchport backup mac-move-burst-interval {}", switchport.backup.mac_move_burst_interval)
        self._add("switchport backup initial-mac-move-delay {}", switchport.backup.initial_mac_move_delay)
        self._add("switchport backup dest-macaddr {}", switchport.backup.dest_macaddr)

    def _render_tap_tool(self, intf: Any) -> None:
        """Render switchport tap/tool configuration (J2 977-1086)."""
        switchport = intf.switchport
        if switchport.tap is None and switchport.tool is None:
            return

        # tap settings
        self._add("switchport tap native vlan {}", switchport.tap.native_vlan)

        if switchport.tap.identity.id:
            cli = f"switchport tap identity {switchport.tap.identity.id}"
            if switchport.tap.identity.inner_vlan:
                cli += f" inner {switchport.tap.identity.inner_vlan}"
            self._add(cli)

        if switchport.tap.mac_address.destination:
            cli = f"switchport tap mac-address dest {switchport.tap.mac_address.destination}"
            if switchport.tap.mac_address.source:
                cli += f" src {switchport.tap.mac_address.source}"
            self._add(cli)

        if switchport.tap.encapsulation.vxlan_strip is True and switchport.tap.mpls_pop_all is not True:
            self._add("switchport tap encapsulation vxlan strip")

        for protocol in natural_sort(switchport.tap.encapsulation.gre.protocols or [], sort_key="protocol"):
            if protocol.strip is True:
                cli = f"switchport tap encapsulation gre protocol {protocol.protocol}"
                if protocol.feature_header_length:
                    cli += f" feature header length {protocol.feature_header_length}"
                cli += " strip"
                if protocol.re_encapsulation_ethernet_header is True:
                    cli += " re-encapsulation ethernet"
                self._add(cli)

        if switchport.tap.encapsulation.gre.strip is True:
            self._add("switchport tap encapsulation gre strip")

        for destination in natural_sort(switchport.tap.encapsulation.gre.destinations or [], sort_key="destination"):
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
                    self._add(proto_cli)
            if destination.strip is True:
                self._add(f"{tap_enc_cli} strip")

        if switchport.tap.mpls_pop_all is True:
            self._add("switchport tap mpls pop all")

        # tool settings
        if switchport.tool.mpls_pop_all is True:
            self._add("switchport tool mpls pop all")
        if switchport.tool.encapsulation.vn_tag_strip is True:
            self._add("switchport tool encapsulation vn-tag strip")
        if switchport.tool.encapsulation.dot1br_strip is True:
            self._add("switchport tool encapsulation dot1br strip")

        self._add("switchport tap allowed vlan {}", switchport.tap.allowed_vlan)
        self._add("switchport tool allowed vlan {}", switchport.tool.allowed_vlan)

        self._add("switchport tool identity {}", switchport.tool.identity.tag)
        if switchport.tool.identity.dot1q_dzgre_source:
            self._add(f"switchport tool identity dot1q source dzgre {switchport.tool.identity.dot1q_dzgre_source}")
        elif switchport.tool.identity.qinq_dzgre_source:
            self._add(f"switchport tool identity qinq source dzgre {switchport.tool.identity.qinq_dzgre_source}")

        if switchport.tap.truncation.enabled is True:
            cli = "switchport tap truncation"
            if switchport.tap.truncation.size:
                cli += f" {switchport.tap.truncation.size}"
            self._add(cli)

        if switchport.tap.default.groups:
            groups = " group ".join(natural_sort(switchport.tap.default.groups, ignore_case=False))
            self._add(f"switchport tap default group {groups}")

        if switchport.tap.default.nexthop_groups:
            nxhop_groups = " ".join(natural_sort(switchport.tap.default.nexthop_groups, ignore_case=False))
            self._add(f"switchport tap default nexthop-group {nxhop_groups}")

        for interface in natural_sort(switchport.tap.default.interfaces or []):
            self._add(f"switchport tap default interface {interface}")

        if switchport.tool.groups:
            tool_groups = " ".join(natural_sort(switchport.tool.groups, ignore_case=False))
            self._add(f"switchport tool group set {tool_groups}")

        self._add("switchport tool dot1q remove outer {}", switchport.tool.dot1q_remove_outer_vlan_tag)

    def _render_traffic_engineering(self, intf: Any) -> None:
        """Render traffic-engineering configuration (J2 1087-1106)."""
        traffic_engineering = intf.traffic_engineering
        if traffic_engineering.enabled is True:
            self._add("traffic-engineering")
        if traffic_engineering.bandwidth:
            self._add(f"traffic-engineering bandwidth {traffic_engineering.bandwidth.number} {traffic_engineering.bandwidth.unit}")
        if traffic_engineering.administrative_groups:
            self._add(f"traffic-engineering administrative-group {','.join(traffic_engineering.administrative_groups)}")
        for srlg in natural_sort(traffic_engineering.srlgs or [], ignore_case=False):
            self._add(f"traffic-engineering srlg {srlg}")
        self._add("traffic-engineering metric {}", traffic_engineering.metric)
        if traffic_engineering.min_delay_static:
            self._add(f"traffic-engineering min-delay static {traffic_engineering.min_delay_static.number} {traffic_engineering.min_delay_static.unit}")
        elif traffic_engineering.min_delay_dynamic.twamp_light_fallback:
            fallback = traffic_engineering.min_delay_dynamic.twamp_light_fallback
            self._add(f"traffic-engineering min-delay dynamic twamp-light fallback {fallback.number} {fallback.unit}")

    def _render_link_tracking(self, intf: Any) -> None:
        """Render link tracking group configuration (J2 1107-1114)."""
        for group in intf.link_tracking_groups or []:
            self._add(f"link tracking group {group.name} {group.direction}")
        if intf.link_tracking.direction and intf.link_tracking.groups:
            for group_name in intf.link_tracking.groups:
                self._add(f"link tracking group {group_name} {intf.link_tracking.direction}")

    def _render_vrrp(self, intf: Any) -> None:
        """Render VRRP configuration (J2 1118-1178)."""
        hide_passwords_enabled = self._data.eos_cli_config_gen_configuration.hide_passwords
        for vrid in natural_sort(intf.vrrp_ids or [], sort_key="id"):
            vrrp_id = vrid.id
            self._add("vrrp {} priority-level {}", vrrp_id, vrid.priority_level)
            self._add("vrrp {} advertisement interval {}", vrrp_id, vrid.advertisement.interval)

            if vrid.preempt.enabled is True and (vrid.preempt.delay.minimum or vrid.preempt.delay.reload):
                delay_cli = f"vrrp {vrrp_id} preempt delay"
                if vrid.preempt.delay.minimum:
                    delay_cli += f" minimum {vrid.preempt.delay.minimum}"
                if vrid.preempt.delay.reload:
                    delay_cli += f" reload {vrid.preempt.delay.reload}"
                self._add(delay_cli)
            elif vrid.preempt.enabled is False:
                self._add(f"no vrrp {vrrp_id} preempt")

            self._add("vrrp {} timers delay reload {}", vrrp_id, vrid.timers.delay.reload)

            if vrid.peer_authentication:
                peer_authentication = vrid.peer_authentication
                peer_auth_cli = f"vrrp {vrrp_id} peer authentication"
                if peer_authentication.mode == "ietf-md5":
                    peer_auth_cli += " ietf-md5 key-string"
                else:
                    peer_auth_cli += " text"
                if peer_authentication.key_type:
                    peer_auth_cli += f" {peer_authentication.key_type}"
                peer_auth_cli += f" {hide_passwords(peer_authentication.key, hide_passwords_enabled)}"
                self._add(peer_auth_cli)

            self._add("vrrp {} ipv4 {}", vrrp_id, vrid.ipv4.address)
            for secondary_ip in natural_sort(vrid.ipv4.secondary_addresses or []):
                self._add(f"vrrp {vrrp_id} ipv4 {secondary_ip} secondary")
            self._add("vrrp {} ipv4 version {}", vrrp_id, vrid.ipv4.version)

            for ipv6_address in natural_sort(vrid.ipv6.addresses or []):
                self._add(f"vrrp {vrrp_id} ipv6 {ipv6_address}")

            for tracked_obj in natural_sort(vrid.tracked_object or [], sort_key="name", ignore_case=False):
                if tracked_obj.name:
                    tracked_cli = f"vrrp {vrrp_id} tracked-object {tracked_obj.name}"
                    if tracked_obj.decrement:
                        tracked_cli += f" decrement {tracked_obj.decrement}"
                    elif tracked_obj.shutdown is True:
                        tracked_cli += " shutdown"
                    self._add(tracked_cli)

    def _render_transceiver(self, intf: Any) -> None:
        """Render transceiver configuration (J2 1179-1207)."""
        transceiver = intf.transceiver
        self._add("transceiver media override {}", transceiver.media.override)
        if transceiver.power.ignore is True:
            self._add("transceiver power ignore")
        self._add("transceiver application override {}", transceiver.application_override)

        for app_override in transceiver.application_override_lanes or []:
            cli = f"transceiver application override {app_override.override} lanes start {app_override.first_lane}"
            if app_override.last_lane:
                cli += f" end {app_override.last_lane}"
            self._add(cli)

        if transceiver.frequency:
            cli = f"transceiver frequency {float(transceiver.frequency):.3f}"
            if transceiver.frequency_unit:
                cli += f" {transceiver.frequency_unit}"
            self._add(cli)

        if transceiver.transmitter.signal_power:
            self._add(f"transceiver transmitter signal-power {float(transceiver.transmitter.signal_power):.2f}")
        if transceiver.transmitter.disabled is True:
            self._add("transceiver transmitter disabled")

    def _render_dot1x(self, intf: Any) -> None:
        """Render 802.1x configuration (J2 1208-1350)."""
        dot1x = intf.dot1x
        if dot1x is None:
            return

        # pae mode (J2 1209-1213)
        if dot1x.pae.mode == "authenticator":
            self._add(f"dot1x pae {dot1x.pae.mode}")
        elif dot1x.pae.mode == "supplicant" and dot1x.pae.supplicant_profile:
            self._add(f"dot1x pae {dot1x.pae.mode} {dot1x.pae.supplicant_profile}")

        # authentication failure action (J2 1214-1221)
        if dot1x.authentication_failure:
            if dot1x.authentication_failure.action == "allow" and dot1x.authentication_failure.allow_vlan:
                self._add(f"dot1x authentication failure action traffic allow vlan {dot1x.authentication_failure.allow_vlan}")
            elif dot1x.authentication_failure.action == "drop":
                self._add("dot1x authentication failure action traffic drop")

        # aaa unresponsive (J2 1222-1274)
        if dot1x.aaa.unresponsive:
            self._render_dot1x_aaa_unresponsive(dot1x)

        if dot1x.reauthentication is True:
            self._add("dot1x reauthentication")
        self._add("dot1x port-control {}", dot1x.port_control)

        if dot1x.port_control_force_authorized_phone is True:
            self._add("dot1x port-control force-authorized phone")
        elif dot1x.port_control_force_authorized_phone is False:
            self._add("no dot1x port-control force-authorized phone")

        # host-mode (J2 1286-1296)
        if dot1x.host_mode:
            if dot1x.host_mode.mode == "single-host":
                self._add("dot1x host-mode single-host")
            elif dot1x.host_mode.mode == "multi-host":
                host_mode_cli = "dot1x host-mode multi-host"
                if dot1x.host_mode.multi_host_authenticated is True:
                    host_mode_cli += " authenticated"
                self._add(host_mode_cli)

        if dot1x.eapol.disabled is True:
            self._add("dot1x eapol disabled")
        if dot1x.mac_based_access_list is True:
            self._add("dot1x mac based access-list")

        # mac based authentication (J2 1303-1316)
        if dot1x.mac_based_authentication.enabled is True:
            if dot1x.mac_based_authentication.host_mode_common is True:
                self._add("dot1x mac based authentication host-mode common")
                if dot1x.mac_based_authentication.always is True:
                    self._add("dot1x mac based authentication always")
            else:
                auth_cli = "dot1x mac based authentication"
                if dot1x.mac_based_authentication.always is True:
                    auth_cli += " always"
                self._add(auth_cli)

        # timeout (J2 1317-1333)
        if dot1x.timeout:
            self._add("dot1x timeout quiet-period {}", dot1x.timeout.quiet_period)
            if dot1x.timeout.reauth_timeout_ignore is True:
                self._add("dot1x timeout reauth-timeout-ignore always")
            self._add("dot1x timeout tx-period {}", dot1x.timeout.tx_period)
            self._add("dot1x timeout reauth-period {}", dot1x.timeout.reauth_period)
            self._add("dot1x timeout idle-host {} seconds", dot1x.timeout.idle_host)

        self._add("dot1x reauthorization request limit {}", dot1x.reauthorization_request_limit)

        if dot1x.unauthorized.access_vlan_membership_egress is True:
            self._add("dot1x unauthorized access vlan membership egress")
        if dot1x.unauthorized.native_vlan_membership_egress is True:
            self._add("dot1x unauthorized native vlan membership egress")

        # eapol authentication failure fallback mba (J2 1343-1349)
        if dot1x.eapol.authentication_failure_fallback_mba.enabled is True:
            mba_cli = "dot1x eapol authentication failure fallback mba"
            if dot1x.eapol.authentication_failure_fallback_mba.timeout:
                mba_cli += f" timeout {dot1x.eapol.authentication_failure_fallback_mba.timeout}"
            self._add(mba_cli)

    def _render_dot1x_aaa_unresponsive(self, dot1x: Any) -> None:
        """
        Render dot1x aaa unresponsive action and phone-action lines (J2 1222-1274).

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
            elif traffic_allow_vlan and traffic_allow_access_list:
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
            self._add(aaa_action_config)

        if unresponsive.eap_response:
            self._add(f"{aaa_config} eap response {unresponsive.eap_response}")


class EthernetInterfaceEncapsulationVlan(CliSection):
    """Render encapsulation vlan sub-block (J2 140-182). No separator (exclamation=False)."""

    separator = False

    def __init__(self, intf: Any) -> None:
        self._intf = intf

    def _generate(self) -> None:
        intf = self._intf
        encapsulation_vlan = intf.encapsulation_vlan
        if encapsulation_vlan.client.encapsulation is None or intf.encapsulation_dot1q.vlan:
            return

        client_encapsulation = encapsulation_vlan.client.encapsulation
        network_flag = False
        encapsulation_cli: str | None = None

        if client_encapsulation in ("dot1q", "dot1ad"):
            if encapsulation_vlan.client.vlan:
                encapsulation_cli = f"client {client_encapsulation} {encapsulation_vlan.client.vlan}"
            elif encapsulation_vlan.client.outer_vlan and encapsulation_vlan.client.inner_vlan:
                if encapsulation_vlan.client.inner_encapsulation:
                    encapsulation_cli = (
                        f"client {client_encapsulation} outer {encapsulation_vlan.client.outer_vlan} inner {encapsulation_vlan.client.inner_encapsulation} {encapsulation_vlan.client.inner_vlan}"
                    )
                else:
                    encapsulation_cli = f"client {client_encapsulation} outer {encapsulation_vlan.client.outer_vlan} inner {encapsulation_vlan.client.inner_vlan}"
                # Check network encapsulation 'client inner'
                if (encapsulation_vlan.network.encapsulation or None) == "client inner":
                    network_flag = True
                    encapsulation_cli += f" network {encapsulation_vlan.network.encapsulation}"
        elif client_encapsulation in ("untagged", "unmatched"):
            encapsulation_cli = f"client {client_encapsulation}"

        if encapsulation_cli is None:
            return

        if client_encapsulation in ("dot1q", "dot1ad", "untagged") and encapsulation_vlan.network.encapsulation and not network_flag:
            network_encapsulation = encapsulation_vlan.network.encapsulation
            if network_encapsulation in ("dot1q", "dot1ad"):
                if encapsulation_vlan.network.vlan:
                    encapsulation_cli += f" network {network_encapsulation} {encapsulation_vlan.network.vlan}"
                elif encapsulation_vlan.network.outer_vlan and encapsulation_vlan.network.inner_vlan:
                    if encapsulation_vlan.network.inner_encapsulation:
                        encapsulation_cli += (
                            f" network {network_encapsulation} outer {encapsulation_vlan.network.outer_vlan} inner {encapsulation_vlan.network.inner_encapsulation} {encapsulation_vlan.network.inner_vlan}"
                        )
                    else:
                        encapsulation_cli += f" network {network_encapsulation} outer {encapsulation_vlan.network.outer_vlan} inner {encapsulation_vlan.network.inner_vlan}"
            elif network_encapsulation == "untagged" and client_encapsulation == "untagged":
                encapsulation_cli += " network untagged"
            elif network_encapsulation == "client" and client_encapsulation != "untagged":
                encapsulation_cli += " network client"

        self._header("encapsulation vlan")
        self._add(encapsulation_cli)


class EthernetInterfaceAddressLocking(CliSection):
    """Render address locking sub-block (J2 232-259)."""

    separator = False

    def __init__(self, intf: Any) -> None:
        self._intf = intf

    def _generate(self) -> None:
        address_locking = self._intf.address_locking
        if address_locking.address_family.ipv4 is not None or address_locking.address_family.ipv6 is not None or address_locking.ipv4_enforcement_disabled is True:
            self._header("!")
            self._header("address locking")
            if address_locking.address_family.ipv4 is True:
                self._add("address-family ipv4")
            if address_locking.address_family.ipv6 is True:
                self._add("address-family ipv6")
            if address_locking.address_family.ipv4 is False:
                self._add("address-family ipv4 disabled")
            if address_locking.address_family.ipv6 is False:
                self._add("address-family ipv6 disabled")
            if address_locking.ipv4_enforcement_disabled is True:
                self._add("locked-address ipv4 enforcement disabled")
        elif address_locking.ipv4 is True or address_locking.ipv6 is True:
            cli = "address locking"
            if address_locking.ipv4 is True:
                cli += " ipv4"
            if address_locking.ipv6 is True:
                cli += " ipv6"
            self._header(cli)


class EthernetInterfaceEvpnEthernetSegment(CliSection):
    """Render EVPN ethernet-segment sub-block (J2 260-301). separator=True."""

    def __init__(self, intf: Any) -> None:
        self._intf = intf

    def _generate(self) -> None:
        evpn_ethernet_segment = self._intf.evpn_ethernet_segment
        if not evpn_ethernet_segment:
            return

        self._header("evpn ethernet-segment")
        self._add("identifier {}", evpn_ethernet_segment.identifier)
        self._add("redundancy {}", evpn_ethernet_segment.redundancy)

        designated_forwarder_election = evpn_ethernet_segment.designated_forwarder_election
        if designated_forwarder_election:
            if designated_forwarder_election.algorithm == "modulus":
                self._add("designated-forwarder election algorithm modulus")
            elif designated_forwarder_election.algorithm == "preference" and designated_forwarder_election.preference_value:
                cli = f"designated-forwarder election algorithm preference {designated_forwarder_election.preference_value}"
                if designated_forwarder_election.dont_preempt is True:
                    cli += " dont-preempt"
                self._add(cli)
            if designated_forwarder_election.hold_time:
                cli = f"designated-forwarder election hold-time {designated_forwarder_election.hold_time}"
                if designated_forwarder_election.subsequent_hold_time:
                    cli += f" subsequent-hold-time {designated_forwarder_election.subsequent_hold_time}"
                self._add(cli)
            if designated_forwarder_election.candidate_reachability_required is True:
                self._add("designated-forwarder election candidate reachability required")
            elif designated_forwarder_election.candidate_reachability_required is False:
                self._add("no designated-forwarder election candidate reachability required")

        self._add("mpls tunnel flood filter time {}", evpn_ethernet_segment.mpls.tunnel_flood_filter_time)
        self._add("mpls shared index {}", evpn_ethernet_segment.mpls.shared_index)
        self._add("route-target import {}", evpn_ethernet_segment.route_target)


class EthernetInterfaceTxQueue(CliSection):
    """Render a single tx-queue sub-block (J2 752-754). separator=True."""

    def __init__(self, tx_queue: Any) -> None:
        self._tx_queue = tx_queue

    def _generate(self) -> None:
        tx_queue = self._tx_queue
        self._header(f"tx-queue {tx_queue.id}")
        if tx_queue.scheduler_profile_responsive is True:
            self._add("scheduler profile responsive")
        if tx_queue.random_detect:
            random_detect = tx_queue.random_detect
            if random_detect.ecn.threshold:
                thresh = random_detect.ecn.threshold
                ecn_cmd = f"random-detect ecn minimum-threshold {thresh.min} {thresh.units} maximum-threshold {thresh.max} {thresh.units}"
                if thresh.max_probability:
                    ecn_cmd += f" max-mark-probability {thresh.max_probability}"
                if thresh.weight:
                    ecn_cmd += f" weight {thresh.weight}"
                self._add(ecn_cmd)
            if random_detect.ecn.count is True:
                self._add("random-detect ecn count")


class EthernetInterfaceUcTxQueue(CliSection):
    """Render a single uc-tx-queue sub-block (J2 755-757). separator=True."""

    def __init__(self, uc_tx_queue: Any) -> None:
        self._uc_tx_queue = uc_tx_queue

    def _generate(self) -> None:
        uc_tx_queue = self._uc_tx_queue
        self._header(f"uc-tx-queue {uc_tx_queue.id}")
        if uc_tx_queue.random_detect:
            random_detect = uc_tx_queue.random_detect
            if random_detect.ecn.threshold:
                thresh = random_detect.ecn.threshold
                ecn_cmd = f"random-detect ecn minimum-threshold {thresh.min} {thresh.units} maximum-threshold {thresh.max} {thresh.units}"
                if thresh.max_probability:
                    ecn_cmd += f" max-mark-probability {thresh.max_probability}"
                if thresh.weight:
                    ecn_cmd += f" weight {thresh.weight}"
                self._add(ecn_cmd)
            if random_detect.ecn.count is True:
                self._add("random-detect ecn count")


class EthernetInterfaceSyncE(CliSection):
    """Render sync-e sub-block (J2 970-976). separator=True."""

    def __init__(self, intf: Any) -> None:
        self._intf = intf

    def _generate(self) -> None:
        intf = self._intf
        if intf.sync_e.enable is not True:
            return
        self._header("sync-e")
        self._add("priority {}", intf.sync_e.priority)
