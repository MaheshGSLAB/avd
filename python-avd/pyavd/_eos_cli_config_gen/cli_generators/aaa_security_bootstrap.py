# Copyright (c) 2026 Arista Networks, Inc.
# Use of this source code is governed by the Apache License 2.0
# that can be found in the LICENSE file.
"""
Combined CLI configuration generator for the early security-bootstrap group.

Covers, in EOS output order:
    enable password ...                                            (enable_password.py)
    aaa root secret ...                                            (aaa_root.py)
    aaa authentication policy local allow-nopassword-remote-login  (aaa_authentication_policy_nopassword.py)
    aaa authorization policy local default-role ...                (aaa_authorization_default_role.py)

These four sections share a single leading ``!`` separator: only the first
block that actually emits content prepends the ``!``. To make that decision
without checking inputs twice or re-rendering, all four blocks write into the
generator's shared ``self._model`` list; each block's ``separator`` is set based on
whether that shared list already has any lines.
"""

from __future__ import annotations

from .aaa_authentication_policy_nopassword import AaaAuthenticationPolicyNopasswordBlock
from .aaa_authorization_default_role import AaaAuthorizationDefaultRoleBlock
from .aaa_root import AaaRootBlock
from .base import CliGenerator, cli_config_contributor
from .enable_password import EnablePasswordBlock


class AaaSecurityBootstrapGenerator(CliGenerator):
    """Generator for the enable-password / aaa-root / aaa-authentication-policy / aaa-authorization-default-role group."""

    @cli_config_contributor
    def aaa_security_bootstrap(self) -> None:
        """Render the four group sections in order, sharing one leading '!' separator."""
        for block_cls in (
            EnablePasswordBlock,
            AaaRootBlock,
            AaaAuthenticationPolicyNopasswordBlock,
            AaaAuthorizationDefaultRoleBlock,
        ):
            block = block_cls(self.inputs)
            # Only the first block to actually emit anything gets the leading '!'.
            block.separator = not bool(self._model)
            self._model.extend(block.render())
