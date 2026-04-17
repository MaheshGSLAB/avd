# Copyright (c) 2026 Arista Networks, Inc.
# Use of this source code is governed by the Apache License 2.0
# that can be found in the LICENSE file.
"""Boot secret CLI configuration generator."""

from __future__ import annotations

from pyavd.j2filters import hide_passwords

from .base import CliGenerator, CliModel, cli_config_contributor


class BootGenerator(CliGenerator):
    """
    Generator for boot secret CLI configuration.

    Migrated from j2templates/eos/boot.j2
    """

    @property
    def _model(self) -> CliModel:
        """Boot config section."""
        return self.cli_config.boot

    @cli_config_contributor
    def boot(self) -> None:
        """
        Render boot secret configuration.

        Generates CLI commands for:
        - Boot secret with hash algorithm (md5 -> 5, default -> sha512)
        - Password hiding support via eos_cli_config_gen_configuration.hide_passwords
        """
        secret = self.data.boot.secret
        if not secret.key:
            return

        # EOS CLI uses "5" for md5; schema default handles "sha512"
        hash_algorithm = "5" if secret.hash_algorithm == "md5" else secret.hash_algorithm
        key = hide_passwords(secret.key, self.data.eos_cli_config_gen_configuration.hide_passwords)

        with self._block(f"boot secret {hash_algorithm} {key}"):
            pass
