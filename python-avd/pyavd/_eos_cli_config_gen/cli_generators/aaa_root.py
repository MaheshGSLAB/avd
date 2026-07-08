# Copyright (c) 2026 Arista Networks, Inc.
# Use of this source code is governed by the Apache License 2.0
# that can be found in the LICENSE file.
"""AAA root CLI section block.

Rendered as part of the AaaSecurityBootstrapGenerator group, which owns the
shared leading '!' separator across enable-password / aaa-root /
aaa-authentication-policy-nopassword / aaa-authorization-default-role.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from pyavd.j2filters import hide_passwords

from .base import CliSection

if TYPE_CHECKING:
    from pyavd._eos_cli_config_gen.schema import EosCliConfigGen


@dataclass
class AaaRootBlock(CliSection):
    """
    Renders 'aaa root secret sha512 ...' or 'no aaa root'.

    Separator is set by the AaaSecurityBootstrapGenerator orchestrator.
    """

    inputs: EosCliConfigGen

    def _section(self) -> None:
        aaa_root = self.inputs.aaa_root
        if aaa_root.disabled:
            self._section_heading("no aaa root")
            return
        sha512_password = aaa_root.secret.sha512_password
        if not sha512_password:
            return
        password = hide_passwords(sha512_password, self.inputs.eos_cli_config_gen_configuration.hide_passwords)
        self._section_heading(f"aaa root secret sha512 {password}")
