# Copyright (c) 2023-2025 Arista Networks, Inc.
# Use of this source code is governed by the Apache License 2.0
# that can be found in the LICENSE file.

from __future__ import annotations

from functools import cache
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .templater import Templar


# The cached factory should be in this file
@cache
def _get_templar() -> Templar:
    """Creates and returns a cached instance of the Templar."""
    from .constants import EOS_CLI_CONFIG_GEN_JINJA2_PRECOMPILED_TEMPLATE_PATH, EOS_CLI_CONFIG_GEN_JINJA2_TEMPLATE_PATH
    from .templater import Templar

    # Create the Templar instance with all the required paths for tests
    return Templar(
        precompiled_templates_path=EOS_CLI_CONFIG_GEN_JINJA2_PRECOMPILED_TEMPLATE_PATH,
        searchpaths=[EOS_CLI_CONFIG_GEN_JINJA2_TEMPLATE_PATH],
    )


def get_device_doc(structured_config: dict, add_md_toc: bool = False) -> str:
    """
    Render and return the device documentation using AVD eos_cli_config_gen templates.

    Args:
        structured_config: Dictionary with structured configuration.
            Variables should be converted and validated according to AVD `eos_cli_config_gen` schema first using `pyavd.validate_structured_config`.
        add_md_toc: Add a table of contents for markdown headings.

    Returns:
        Device documentation in Markdown format.
    """
    # pylint: disable=import-outside-toplevel
    from .constants import EOS_CLI_CONFIG_GEN_JINJA2_DOCUMENTAITON_TEMPLATE
    from .j2filters import add_md_toc as filter_add_md_toc

    # pylint: enable=import-outside-toplevel

    templar = _get_templar()
    result: str = templar.render_template_from_file(EOS_CLI_CONFIG_GEN_JINJA2_DOCUMENTAITON_TEMPLATE, structured_config)
    if add_md_toc:
        return filter_add_md_toc(result, skip_lines=3)

    return result
