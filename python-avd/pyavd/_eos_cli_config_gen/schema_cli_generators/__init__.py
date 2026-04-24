# Copyright (c) 2023-2026 Arista Networks, Inc.
# Use of this source code is governed by the Apache License 2.0
# that can be found in the LICENSE file.
"""Schema-driven CLI generators for EOS configuration."""

from .base import SchemaCliGenerator, render_from_schema, render_schema_field, resolve_template
from .router_bgp import RouterBgpBlock

__all__ = ["RouterBgpBlock", "SchemaCliGenerator", "render_from_schema", "render_schema_field", "resolve_template"]
