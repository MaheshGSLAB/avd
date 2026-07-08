# Copyright (c) 2026 Arista Networks, Inc.
# Use of this source code is governed by the Apache License 2.0
# that can be found in the LICENSE file.
"""Enable password CLI section block.

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
class EnablePasswordBlock(CliSection):
    """
    Renders 'enable password ...' or 'no enable password'.

    Separator is set by the AaaSecurityBootstrapGenerator orchestrator.
    """

    inputs: EosCliConfigGen

    def _section(self) -> None:
        enable_password = self.inputs.enable_password
        if enable_password.disabled:
            self._section_heading("no enable password")
            return
        if not enable_password.key:
            return
        if enable_password.hash_algorithm == "md5":
            algorithm_token = "5"
        elif enable_password.hash_algorithm == "sha512":
            algorithm_token = "sha512"
        else:
            return
        key = hide_passwords(enable_password.key, self.inputs.eos_cli_config_gen_configuration.hide_passwords)
        self._section_heading(f"enable password {algorithm_token} {key}")
