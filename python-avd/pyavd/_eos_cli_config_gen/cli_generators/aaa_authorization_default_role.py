# Copyright (c) 2026 Arista Networks, Inc.
# Use of this source code is governed by the Apache License 2.0
# that can be found in the LICENSE file.
"""AAA authorization default-role CLI section block.

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
class AaaAuthorizationDefaultRoleBlock(CliSection):
    """
    Renders 'aaa authorization policy local default-role <role>'.

    Separator is set by the AaaSecurityBootstrapGenerator orchestrator.
    """

    inputs: EosCliConfigGen

    def _section(self) -> None:
        local_default_role = self.inputs.aaa_authorization.policy.local_default_role
        if not local_default_role:
            return
        self._section_heading(f"aaa authorization policy local default-role {local_default_role}")
