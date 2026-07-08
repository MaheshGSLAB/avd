# Copyright (c) 2023-2026 Arista Networks, Inc.
# Use of this source code is governed by the Apache License 2.0
# that can be found in the LICENSE file.
"""DHCP servers CLI configuration generator."""

from __future__ import annotations

from dataclasses import KW_ONLY, dataclass
from typing import TYPE_CHECKING, Any

from pyavd.j2filters import natural_sort

from .base import CliGenerator, CliSection, cli_config_contributor

if TYPE_CHECKING:
    from pyavd._eos_cli_config_gen.schema import EosCliConfigGen


class DhcpServersGenerator(CliGenerator):
    """
    Generator for DHCP servers CLI configuration.

    Single contributor method `dhcp_servers` iterates over the sorted
    `dhcp_servers` list and delegates each entry to a `DhcpServerBlock`.
    """

    @cli_config_contributor
    def dhcp_servers(self) -> None:
        """Render all 'dhcp server [vrf X]' blocks sorted by vrf (case-sensitive)."""
        for dhcp_server in natural_sort(self.inputs.dhcp_servers or [], sort_key="vrf", ignore_case=False):
            self._model.extend(DhcpServerBlock(dhcp_server).render())


@dataclass
class DhcpServerBlock(CliSection):
    """Render a single 'dhcp server [vrf X]' block in EOS output order."""

    dhcp_server: EosCliConfigGen.DhcpServersItem

    def _section(self) -> None:
        ds = self.dhcp_server
        header = "dhcp server" if ds.vrf == "default" else f"dhcp server vrf {ds.vrf}"
        self._section_heading(header)

        if ds.disabled is True:
            self._cli_line("disabled")

        self._render_lease_time("ipv4", ds.lease_time_ipv4)
        self._cli_line("dns domain name ipv4 {}", ds.dns_domain_name_ipv4)
        if ds.dns_servers_ipv4:
            self._cli_line(f"dns server ipv4 {' '.join(natural_sort(ds.dns_servers_ipv4))}")

        self._render_lease_time("ipv6", ds.lease_time_ipv6)
        self._cli_line("dns domain name ipv6 {}", ds.dns_domain_name_ipv6)
        if ds.dns_servers_ipv6:
            self._cli_line(f"dns server ipv6 {' '.join(natural_sort(ds.dns_servers_ipv6))}")

        tftp = ds.tftp_server
        self._cli_line("tftp server option 66 ipv4 {}", tftp.option_66_ipv4)
        if tftp.option_150_ipv4:
            self._cli_line(f"tftp server option 150 ipv4 {' '.join(tftp.option_150_ipv4)}")
        self._cli_line("tftp server file ipv4 {}", tftp.file_ipv4)
        self._cli_line("tftp server file ipv6 {}", tftp.file_ipv6)

        for subnet in natural_sort(ds.ipv4_subnets or [], sort_key="subnet"):
            self._sub_section(Ipv4SubnetBlock(subnet))

        for subnet in natural_sort(ds.ipv6_subnets or [], sort_key="subnet"):
            self._sub_section(Ipv6SubnetBlock(subnet))

        for option in natural_sort(ds.ipv4_vendor_options or [], sort_key="vendor_id", ignore_case=False):
            self._sub_section(VendorOptionBlock(option))

        if ds.eos_cli is not None:
            for line in ds.eos_cli.splitlines():
                self._cli_line(line)

    def _render_lease_time(self, family: str, lease_time: Any) -> None:
        if lease_time.days is None or lease_time.hours is None or lease_time.minutes is None:
            return
        self._cli_line(f"lease time {family} {lease_time.days} days {lease_time.hours} hours {lease_time.minutes} minutes")


@dataclass
class Ipv4SubnetBlock(CliSection):
    """Render a single 'subnet <X>' block under an ipv4 dhcp server."""

    subnet: EosCliConfigGen.DhcpServersItem.Ipv4SubnetsItem

    def _section(self) -> None:
        subnet = self.subnet
        self._section_heading(f"subnet {subnet.subnet}")

        if subnet.reservations:
            self._sub_section(ReservationsBlock(subnet.reservations, ipv6=False))

        for range_ in natural_sort(natural_sort(subnet.ranges or [], sort_key="end"), sort_key="start"):
            self._sub_section(RangeBlock(range_))

        self._cli_line("name {}", subnet.name)
        if subnet.dns_servers:
            self._cli_line(f"dns server {' '.join(subnet.dns_servers)}")
        lt = subnet.lease_time
        if lt.days is not None and lt.hours is not None and lt.minutes is not None:
            self._cli_line(f"lease time {lt.days} days {lt.hours} hours {lt.minutes} minutes")
        self._cli_line("default-gateway {}", subnet.default_gateway)

        tftp = subnet.tftp_server
        self._cli_line("tftp server option 66 {}", tftp.option_66)
        if tftp.option_150:
            self._cli_line(f"tftp server option 150 {' '.join(tftp.option_150)}")
        self._cli_line("tftp server file {}", tftp.file)


@dataclass
class Ipv6SubnetBlock(CliSection):
    """Render a single 'subnet <X>' block under an ipv6 dhcp server."""

    subnet: EosCliConfigGen.DhcpServersItem.Ipv6SubnetsItem

    def _section(self) -> None:
        subnet = self.subnet
        self._section_heading(f"subnet {subnet.subnet}")

        if subnet.reservations:
            self._sub_section(ReservationsBlock(subnet.reservations, ipv6=True))

        for range_ in natural_sort(natural_sort(subnet.ranges or [], sort_key="end"), sort_key="start"):
            self._sub_section(RangeBlock(range_))

        self._cli_line("name {}", subnet.name)
        if subnet.dns_servers:
            self._cli_line(f"dns server {' '.join(subnet.dns_servers)}")
        lt = subnet.lease_time
        if lt.days is not None and lt.hours is not None and lt.minutes is not None:
            self._cli_line(f"lease time {lt.days} days {lt.hours} hours {lt.minutes} minutes")

        self._cli_line("tftp server file {}", subnet.tftp_server.file)


@dataclass
class RangeBlock(CliSection):
    """Render a single 'range <start> <end>' line. Own '!' separator between entries."""

    range_: EosCliConfigGen.DhcpServersItem.Ipv4SubnetsItem.RangesItem | EosCliConfigGen.DhcpServersItem.Ipv6SubnetsItem.RangesItem

    def _section(self) -> None:
        self._section_heading(f"range {self.range_.start} {self.range_.end}")


@dataclass
class ReservationsBlock(CliSection):
    """
    Render the 'reservations' header followed by one MacReservation per entry.

    `separator = False` so no leading '!' is added before the 'reservations'
    header (the subnet block does not separate reservations from its preceding body).
    MacReservation uses the default `separator = True`, producing a '!' between
    entries; `skip_separator=True` on the first sub-render suppresses
    the leading '!' before the first mac.
    """

    separator = False

    reservations: Any
    _: KW_ONLY
    ipv6: bool

    def _section(self) -> None:
        self._section_heading("reservations")
        for i, res in enumerate(natural_sort(self.reservations, sort_key="mac_address")):
            self._sub_section(MacReservation(res, ipv6=self.ipv6), skip_separator=(i == 0))


@dataclass
class MacReservation(CliSection):
    """Render a single 'mac-address X' entry with its address and hostname fields."""

    reservation: Any
    _: KW_ONLY
    ipv6: bool

    def _section(self) -> None:
        res = self.reservation
        self._section_heading(f"mac-address {res.mac_address}")
        if self.ipv6:
            self._cli_line("ipv6-address {}", res.ipv6_address)
        else:
            self._cli_line("ipv4-address {}", res.ipv4_address)
        self._cli_line("hostname {}", res.hostname)


@dataclass
class VendorOptionBlock(CliSection):
    """Render a single 'vendor-option ipv4 <vendor_id>' block."""

    option: EosCliConfigGen.DhcpServersItem.Ipv4VendorOptionsItem

    def _section(self) -> None:
        option = self.option
        self._section_heading(f"vendor-option ipv4 {option.vendor_id}")

        for sub_option in natural_sort(option.sub_options or [], sort_key="code"):
            if sub_option.string is not None:
                self._cli_line(f'sub-option {sub_option.code} type string data "{sub_option.string}"')
            elif sub_option.ipv4_address is not None:
                self._cli_line(f"sub-option {sub_option.code} type ipv4-address data {sub_option.ipv4_address}")
            elif sub_option.array_ipv4_address:
                self._cli_line(f"sub-option {sub_option.code} type array ipv4-address data {' '.join(sub_option.array_ipv4_address)}")
