# Copyright (c) 2026 Arista Networks, Inc.
# Use of this source code is governed by the Apache License 2.0
# that can be found in the LICENSE file.
"""AAA authentication policy nopassword CLI section block.

Rendered as part of the AaaSecurityBootstrapGenerator group, which owns the
shared leading '!' separator across enable-password / aaa-root /
aaa-authentication-policy-nopassword / aaa-authorization-default-role.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from .base import CliSection

if TYPE_CHECKING:
    from pyavd._eos_cli_config_gen.schema import EosCliConfigGen


@dataclass
class AaaAuthenticationPolicyNopasswordBlock(CliSection):
    """
    Renders 'aaa authentication policy local allow-nopassword-remote-login'.

    Separator is set by the AaaSecurityBootstrapGenerator orchestrator.
    """

    inputs: EosCliConfigGen

    def _section(self) -> None:
        if self.inputs.aaa_authentication.policies.local.allow_nopassword:
            self._section_heading("aaa authentication policy local allow-nopassword-remote-login")
