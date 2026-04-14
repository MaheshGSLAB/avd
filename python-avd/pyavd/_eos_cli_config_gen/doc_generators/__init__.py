# Copyright (c) 2023-2026 Arista Networks, Inc.
# Use of this source code is governed by the Apache License 2.0
# that can be found in the LICENSE file.
"""
Documentation generators for EOS CLI Config Gen.

This package contains Python-based documentation generators that replace Jinja2 templates.
Each generator is a class that inherits from DocGenerator and uses @doc_contributor
decorator to mark methods that generate markdown documentation sections.
"""

from __future__ import annotations

from .router_bgp import RouterBgpDocGenerator

__all__ = [  # noqa: RUF022
    "RouterBgpDocGenerator",
]
