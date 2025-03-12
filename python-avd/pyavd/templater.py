# Copyright (c) 2023-2025 Arista Networks, Inc.
# Use of this source code is governed by the Apache License 2.0
# that can be found in the LICENSE file.
from __future__ import annotations

import logging
from pathlib import Path
from typing import TYPE_CHECKING

from jinja2 import ChoiceLoader, Environment, FileSystemLoader, ModuleLoader, StrictUndefined

from .constants import JINJA2_EXTENSIONS, RUNNING_FROM_SRC

if TYPE_CHECKING:
    import os
    from collections.abc import Sequence

LOGGER = logging.getLogger(__name__)


class Undefined(StrictUndefined):
    """
    Allow nested checks for undefined instead of having to check on every level.

    Example "{% if var.key.subkey is arista.avd.undefined %}" is ok.

    Without this it we would have to test every level, like
    "{% if var is arista.avd.undefined or var.key is arista.avd.undefined or var.key.subkey is arista.avd.undefined %}"
    """

    def __getattr__(self, _name: str) -> Undefined:
        # Return original Undefined object to preserve the first failure context
        return self

    def __getitem__(self, _key: str) -> Undefined:
        # Return original Undefined object to preserve the first failure context
        return self

    def __repr__(self) -> str:
        return f"Undefined(hint={self._undefined_hint}, obj={self._undefined_obj}, name={self._undefined_name})"

    def __contains__(self, _item: int) -> Undefined:
        # Return original Undefined object to preserve the first failure context
        return self


class Templar:
    def __init__(self, precompiled_templates_path: str | Path, searchpaths: list[str | Path] | None = None) -> None:
        if not RUNNING_FROM_SRC:
            self.loader = ModuleLoader(precompiled_templates_path)
        else:
            searchpaths = searchpaths or []
            self.loader = ChoiceLoader(
                [
                    ModuleLoader(precompiled_templates_path),
                    FileSystemLoader(searchpaths),
                ],
            )

        # Accepting SonarLint issue: No autoescaping is ok, since we are not using this for a website, so XSS is not applicable.
        self.environment = Environment(  # NOSONAR # noqa: S701
            extensions=JINJA2_EXTENSIONS,
            loader=self.loader,
            undefined=Undefined,
            trim_blocks=True,
        )
        # Backward-compatible compilation for Jinja 3.0.0 to 3.1.x
        if not hasattr(self.environment, "concat"):
            self.environment.concat = "".join

        self.import_filters_and_tests()

    def import_filters_and_tests(self) -> None:
        # pylint: disable=import-outside-toplevel
        from .j2filters import (
            add_md_toc,
            decrypt,
            default,
            encrypt,
            hide_passwords,
            is_in_filter,
            list_compress,
            natural_sort,
            range_expand,
            snmp_hash,
            status_render,
        )
        from .j2tests.contains import contains
        from .j2tests.defined import defined

        # pylint: enable=import-outside-toplevel

        self.environment.filters.update(
            {
                "arista.avd.add_md_toc": add_md_toc,
                "arista.avd.decrypt": decrypt,
                "arista.avd.default": default,
                "arista.avd.encrypt": encrypt,
                "arista.avd.hide_passwords": hide_passwords,
                "arista.avd.is_in_filter": is_in_filter,
                "arista.avd.list_compress": list_compress,
                "arista.avd.natural_sort": natural_sort,
                "arista.avd.range_expand": range_expand,
                "arista.avd.snmp_hash": snmp_hash,
                "arista.avd.status_render": status_render,
            },
        )
        self.environment.tests.update(
            {
                "arista.avd.defined": defined,
                "arista.avd.contains": contains,
            },
        )

    def render_template_from_file(self, template_file: str, template_vars: dict) -> str:
        return self.environment.get_template(template_file).render(template_vars)

    def compile_templates_in_paths(self, precompiled_templates_path: str | Path, searchpaths: list[str | Path]) -> None:
        """
        Compile the Jinja2 templates in the given path and preserve template names.

        Parameters
        ----------
            searchpaths: The list of path to search templates in.
        """
        self.environment.loader = ExtensionFileSystemLoader(searchpaths)

        # Ensure the compiled templates directory exists
        precompiled_templates_path = Path(precompiled_templates_path)
        precompiled_templates_path.mkdir(parents=True, exist_ok=True)

        for searchpath in searchpaths:
            searchpath = Path(searchpath).resolve()  # Ensure absolute paths

            # ✅ Process templates listed by Jinja2 (subdirectories)
            for template_name in self.environment.loader.list_templates():
                template_path = searchpath / template_name
                if not template_path.exists():
                    continue  # Skip if template doesn't exist in this searchpath

                parent_folder = template_path.parent.name if template_path.parent != searchpath else "root"

                # Read the template source
                with open(template_path, "r", encoding="utf-8") as f:
                    template_source = f.read()

                # Compile the Jinja2 template source
                compiled_code = self.environment.compile(template_source, raw=True)

                # Extract base filename and apply prefix
                base_filename = Path(template_name).stem  # Remove `.j2` extension
                compiled_filename = f"{parent_folder}_{base_filename}.py"
                output_path = precompiled_templates_path / compiled_filename

                # Write compiled template (Fix: ensure it's bytes)
                with open(output_path, "wb") as f:
                    f.write(compiled_code.encode("utf-8"))  # Encode to bytes

            # ✅ Manually find `.j2` files at the root of `searchpath`
            for template_path in searchpath.glob("*.j2"):
                parent_folder = "root"  # Since these are directly inside `j2templates/`

                # Read the template source
                with open(template_path, "r", encoding="utf-8") as f:
                    template_source = f.read()

                # Compile the Jinja2 template source
                compiled_code = self.environment.compile(template_source, raw=True)

                # Extract base filename and apply prefix
                base_filename = template_path.stem  # Remove `.j2` extension
                compiled_filename = f"{parent_folder}_{base_filename}.py"
                output_path = precompiled_templates_path / compiled_filename

                # Write compiled template (Fix: ensure it's bytes)
                with open(output_path, "wb") as f:
                    f.write(compiled_code.encode("utf-8"))  # Encode to bytes

        # Reset loader after compilation
        self.environment.loader = self.loader


class ExtensionFileSystemLoader(FileSystemLoader):
    """Custom Jinja2 loader that filters on extensions."""

    def __init__(
        self,
        searchpath: str | os.PathLike[str] | Sequence[str | os.PathLike[str]],
        encoding: str = "utf-8",
        followlinks: bool = False,
        extensions: list[str] | None = None,
    ) -> None:
        self.extensions = extensions or [".j2"]
        super().__init__(searchpath, encoding, followlinks)

    def list_templates(self) -> list[str]:
        """Filter found files from FileSystemLoader using extensions."""
        found = super().list_templates()
        return [file for file in found if Path(file).suffix in self.extensions]
