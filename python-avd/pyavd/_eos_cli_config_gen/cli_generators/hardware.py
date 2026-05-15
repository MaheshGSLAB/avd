# Copyright (c) 2026 Arista Networks, Inc.
# Use of this source code is governed by the Apache License 2.0
# that can be found in the LICENSE file.
"""
Combined CLI generator for the three sections of `eos/hardware.j2`.

In EOS output order:

    hardware port-group ... select ...     (data: hardware.port_groups)
    hardware counter feature ...           (data: hardware_counters.features)
    hardware access-list mechanism ...     (data: hardware.access_list.mechanism)

Unlike the AAA security-bootstrap group, these three sections do NOT share a
leading `!`: each is rendered independently, and each gets its own `!` only
when it actually emits content (default CliSection.separator=True behavior).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from pyavd.j2filters import natural_sort

from .base import CliGenerator, CliModel, CliSection, cli_config_contributor

if TYPE_CHECKING:
    from pyavd._eos_cli_config_gen.schema import EosCliConfigGen


class HardwareGenerator(CliGenerator):
    """Generator for the three hardware sections, rendered in EOS output order."""

    @property
    def _model(self) -> CliModel:
        return self.cli_config.hardware

    @cli_config_contributor
    def hardware(self) -> None:
        """Render the three sections in order; each owns its own leading '!'."""
        for block_cls in (
            HardwarePortGroupBlock,
            HardwareCounterFeatureBlock,
            HardwareAccessListMechanismBlock,
        ):
            self._model.extend(block_cls(self.data).render(indent=0))


class HardwarePortGroupBlock(CliSection):
    """Renders `hardware port-group X select Y` lines (one per port group)."""

    def __init__(self, data: EosCliConfigGen) -> None:
        self.data = data

    def _generate(self) -> None:
        port_groups = self.data.hardware.port_groups
        if not port_groups:
            return
        for port_group in port_groups:
            if not port_group.select:
                continue
            self._header(f"hardware port-group {port_group.port_group} select {port_group.select}")


class HardwareCounterFeatureBlock(CliSection):
    """Renders one `hardware counter feature ...` line per configured feature."""

    def __init__(self, data: EosCliConfigGen) -> None:
        self.data = data

    def _generate(self) -> None:
        features = self.data.hardware_counters.features
        if not features:
            return
        for feature in natural_sort(features, sort_key="name"):
            parts = ["hardware counter feature", feature.name]
            if feature.direction:
                parts.append(feature.direction)
            if feature.address_type:
                parts.append(feature.address_type)
            if feature.layer3 is True:
                parts.append("layer3")
            if feature.vrf:
                parts.append(f"vrf {feature.vrf}")
            if feature.prefix:
                parts.append(feature.prefix)
            if feature.units_packets is True:
                parts.append("units packets")
            line = " ".join(parts)
            if feature.enabled is False:
                line = f"no {line}"
            self._header(line)


class HardwareAccessListMechanismBlock(CliSection):
    """Renders the single-line `hardware access-list mechanism <value>`."""

    def __init__(self, data: EosCliConfigGen) -> None:
        self.data = data

    def _generate(self) -> None:
        mechanism = self.data.hardware.access_list.mechanism
        if not mechanism:
            return
        self._header(f"hardware access-list mechanism {mechanism}")
