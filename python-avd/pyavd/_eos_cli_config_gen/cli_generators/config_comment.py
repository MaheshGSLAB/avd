# Copyright (c) 2026 Arista Networks, Inc.
# Use of this source code is governed by the Apache License 2.0
# that can be found in the LICENSE file.
"""Config comment CLI configuration generator."""

from __future__ import annotations

from typing import TYPE_CHECKING

from .base import CliGenerator, CliModel, CliSection, cli_config_contributor

if TYPE_CHECKING:
    from pyavd._eos_cli_config_gen.schema import EosCliConfigGen


class ConfigCommentGenerator(CliGenerator):
    """Generator for config comment CLI configuration."""

    @property
    def _model(self) -> CliModel:
        """Config comment section."""
        return self.cli_config.config_comment

    @cli_config_contributor
    def config_comment(self) -> None:
        """Render config comment CLI configuration."""
        self._model.extend(ConfigComment(self.data).render(indent=0))


class ConfigComment(CliSection):
    """Renders config comment lines at indent 0 (no separator, no block header)."""

    separator = False

    def __init__(self, data: EosCliConfigGen) -> None:
        self.data = data

    def _generate(self) -> None:
        if not self.data.config_comment:
            return
        self._header("!")
        for line in self.data.config_comment.split("\n"):
            self._header(f"!{line}")
