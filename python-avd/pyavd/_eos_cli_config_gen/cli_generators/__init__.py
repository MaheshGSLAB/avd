# Copyright (c) 2026 Arista Networks, Inc.
# Use of this source code is governed by the Apache License 2.0
# that can be found in the LICENSE file.
"""
CLI configuration generators for EOS CLI Config Gen.

This package contains Python-based CLI configuration generators that replace Jinja2 templates.
Each generator is a class that inherits from CliGenerator and uses @cli_contributor
decorator to mark methods that generate CLI configuration snippets.

"""

from __future__ import annotations

from .aaa_security_bootstrap import AaaSecurityBootstrapGenerator
from .boot import BootGenerator
from .config_comment import ConfigCommentGenerator
from .ethernet_interfaces import EthernetInterfacesGenerator
from .hardware import HardwareGenerator
from .local_users import LocalUsersGenerator
from .router_bgp import RouterBgpGenerator

__all__ = [  # noqa: RUF022
    "ConfigCommentGenerator",
    "BootGenerator",
    "AaaSecurityBootstrapGenerator",
    "LocalUsersGenerator",
    "HardwareGenerator",
    "EthernetInterfacesGenerator",
    "RouterBgpGenerator",
]
