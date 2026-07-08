# Copyright (c) 2026 Arista Networks, Inc.
# Use of this source code is governed by the Apache License 2.0
# that can be found in the LICENSE file.
"""Local users (username) CLI configuration generator."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from pyavd.j2filters import hide_passwords, natural_sort

from .base import CliGenerator, CliSection, cli_config_contributor

if TYPE_CHECKING:
    from pyavd._eos_cli_config_gen.schema import EosCliConfigGen


class LocalUsersGenerator(CliGenerator):
    """Generator for local users CLI configuration."""

    @cli_config_contributor
    def local_users(self) -> None:
        """Render all 'username ...' lines."""
        self._model.extend(LocalUsersBlock(self.inputs).render())


@dataclass
class LocalUsersBlock(CliSection):
    """Renders the 'username ...' lines with a leading '!' separator."""

    inputs: EosCliConfigGen

    def _section(self) -> None:
        if not self.inputs.local_users:
            return
        hide = self.inputs.eos_cli_config_gen_configuration.hide_passwords
        for user in natural_sort(self.inputs.local_users, sort_key="name", ignore_case=False):
            name = user.name
            if user.disabled:
                self._section_heading(f"no username {name}")
                continue
            parts = [f"username {name}"]
            if user.privilege is not None:
                parts.append(f"privilege {user.privilege}")
            if user.role:
                parts.append(f"role {user.role}")
            if user.shell:
                parts.append(f"shell {user.shell}")
            if user.sha512_password:
                parts.append(f"secret sha512 {hide_passwords(user.sha512_password, hide)}")
            elif user.no_password:
                parts.append("nopassword")
            self._section_heading(" ".join(parts))
            if user.ssh_key:
                self._section_heading(f"username {name} ssh-key {user.ssh_key}")
                if user.secondary_ssh_key:
                    self._section_heading(f"username {name} ssh-key secondary {user.secondary_ssh_key}")
