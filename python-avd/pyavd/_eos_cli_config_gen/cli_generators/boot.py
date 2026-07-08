# Copyright (c) 2026 Arista Networks, Inc.
# Use of this source code is governed by the Apache License 2.0
# that can be found in the LICENSE file.
"""Boot secret CLI configuration generator."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from pyavd.j2filters import hide_passwords

from .base import CliGenerator, CliSection, cli_config_contributor

if TYPE_CHECKING:
    from pyavd._eos_cli_config_gen.schema import EosCliConfigGen


class BootGenerator(CliGenerator):
    """Generator for boot secret CLI configuration."""

    @cli_config_contributor
    def boot(self) -> None:
        """Render boot secret configuration."""
        self._model.extend(BootBlock(self.inputs).render())


@dataclass
class BootBlock(CliSection):
    """Renders 'boot secret ...' with a leading '!' separator."""

    inputs: EosCliConfigGen

    def _section(self) -> None:
        secret = self.inputs.boot.secret
        if not secret.key:
            return
        # EOS CLI uses "5" for md5; schema default handles "sha512"
        hash_algorithm = "5" if secret.hash_algorithm == "md5" else secret.hash_algorithm
        key = hide_passwords(secret.key, self.inputs.eos_cli_config_gen_configuration.hide_passwords)
        self._section_heading(f"boot secret {hash_algorithm} {key}")
