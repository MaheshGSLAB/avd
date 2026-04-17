# Copyright (c) 2026 Arista Networks, Inc.
# Use of this source code is governed by the Apache License 2.0
# that can be found in the LICENSE file.
"""Config comment CLI configuration generator."""

from __future__ import annotations

from .base import CliGenerator, CliModel, cli_config_contributor


class ConfigCommentGenerator(CliGenerator):
    """
    Generator for config comment CLI configuration.

    Renders the config comment section that appears at the beginning of the configuration.
    """

    @property
    def _model(self) -> CliModel:
        """Config comment section."""
        return self.cli_config.config_comment

    @cli_config_contributor
    def config_comment(self) -> None:
        """Render config comment CLI configuration using self.cli_config."""
        if not self.data.config_comment:
            return

        self._add("!")
        for comment_line in self.data.config_comment.split("\n"):
            self._add(f"!{comment_line}")
