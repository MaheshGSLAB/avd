# Copyright (c) 2026 Arista Networks, Inc.
# Use of this source code is governed by the Apache License 2.0
# that can be found in the LICENSE file.
"""Config comment CLI configuration generator."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from .base import CliGenerator, CliSection, cli_config_contributor

if TYPE_CHECKING:
    from pyavd._eos_cli_config_gen.schema import EosCliConfigGen


class ConfigCommentGenerator(CliGenerator):
    """Generator for config comment CLI configuration."""

    @cli_config_contributor
    def config_comment(self) -> None:
        """Render config comment CLI configuration."""
        self._model.extend(ConfigComment(self.inputs).render())


@dataclass
class ConfigComment(CliSection):
    """Renders config comment lines at indent 0 (no separator, no block header)."""

    separator = False

    inputs: EosCliConfigGen

    def _section(self) -> None:
        if not self.inputs.config_comment:
            return
        self._section_heading("!")
        for line in self.inputs.config_comment.split("\n"):
            self._section_heading(f"!{line}")
