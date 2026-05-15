# Copyright (c) 2026 Arista Networks, Inc.
# Use of this source code is governed by the Apache License 2.0
# that can be found in the LICENSE file.
"""AAA authentication policy nopassword CLI section block.

Rendered as part of the AaaSecurityBootstrapGenerator group, which owns the
shared leading '!' separator across enable-password / aaa-root /
aaa-authentication-policy-nopassword / aaa-authorization-default-role.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from .base import CliSection

if TYPE_CHECKING:
    from pyavd._eos_cli_config_gen.schema import EosCliConfigGen


class AaaAuthenticationPolicyNopasswordBlock(CliSection):
    """
    Renders 'aaa authentication policy local allow-nopassword-remote-login'.

    Separator is set by the AaaSecurityBootstrapGenerator orchestrator.
    """

    def __init__(self, data: EosCliConfigGen) -> None:
        self.data = data

    def _generate(self) -> None:
        if self.data.aaa_authentication.policies.local.allow_nopassword:
            self._header("aaa authentication policy local allow-nopassword-remote-login")
