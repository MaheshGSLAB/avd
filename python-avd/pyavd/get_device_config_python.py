# Copyright (c) 2023-2026 Arista Networks, Inc.
# Use of this source code is governed by the Apache License 2.0
# that can be found in the LICENSE file.
"""
Python-based device configuration generator.

This module provides an alternative to the Jinja2-based get_device_config
that uses native Python generators for better performance and maintainability.

It can coexist with the Jinja2 version during the migration period, using
Python generators where available and falling back to Jinja2 templates for
sections that haven't been migrated yet.

## Ordering contract

Python generators are integrated with the Jinja2 template in two ways:

1. **Prepend** (default): the generator's output is placed *before* the full
   Jinja2 output.  Use this for sections that appear at the very top of
   ``eos-intended-config.j2`` (e.g. ``config_comment``, ``boot``).

2. **Inline injection**: the generator's output is substituted in-place for a
   placeholder line inside the Jinja2 output.  Use this for sections that
   appear in the *middle* of ``eos-intended-config.j2`` so that EOS output
   order is preserved.

   To opt in, add the following line to ``eos-intended-config.j2`` at the
   position where the ``{% include %}`` used to be::

       __PYTHON_GENERATOR__ < ClassName > __

   For example, ``RouterBgpGenerator`` uses::

       __PYTHON_GENERATOR__RouterBgpGenerator__

   The orchestrator replaces that line with the Python generator output,
   keeping everything before and after it in the correct order.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .api.schemas import EOSConfig

_PLACEHOLDER_PREFIX = "__PYTHON_GENERATOR__"
_PLACEHOLDER_SUFFIX = "__"


def get_device_config_python(structured_config: EOSConfig | dict) -> str:
    """
    Render and return device configuration using Python generators with Jinja2 fallback.

    Generators that have a placeholder in the Jinja2 template are injected
    at the correct position (inline).  Generators without a placeholder are
    prepended before the Jinja2 output (legacy prepend behaviour).

    Args:
        structured_config:
            EOSConfig instance or dictionary with the validated structured configuration.

    Returns:
        Device configuration in EOS CLI format.
    """
    from ._eos_cli_config_gen import cli_generators  # noqa: PLC0415
    from .get_device_config import get_device_config  # noqa: PLC0415

    python_outputs: dict[str, str] = {class_name: getattr(cli_generators, class_name)(structured_config).render() for class_name in cli_generators.__all__}

    j2_output = get_device_config(structured_config)

    prepend_sections: list[str] = []
    for class_name, output in python_outputs.items():
        placeholder = f"{_PLACEHOLDER_PREFIX}{class_name}{_PLACEHOLDER_SUFFIX}"
        if placeholder in j2_output:
            # Replace the placeholder (and its trailing newline) with the output.
            # When output is empty the whole placeholder line is removed cleanly.
            j2_output = j2_output.replace(placeholder + "\n", (output + "\n") if output else "")
        elif output:
            prepend_sections.append(output)

    all_sections = [*prepend_sections, j2_output]
    return "\n".join(section for section in all_sections if section)
