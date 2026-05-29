<!--
  ~ Copyright (c) 2026 Arista Networks, Inc.
  ~ Use of this source code is governed by the Apache License 2.0
  ~ that can be found in the LICENSE file.
  -->

# CLI Generators: Migrating from Jinja2 to Python

## Context

AVD generates EOS device configurations from structured YAML data. Historically every
section was rendered by a Jinja2 template (`.j2`) — 208 templates under
`j2templates/eos/`. This package replaces them, one section at a time, with **Python
generator classes** that consume the typed `EosCliConfigGen` model and emit the same CLI text.

**Migration progress:** 8 generators ported (`config_comment`, `boot`, the four-block
`aaa_security_bootstrap` group, `local_users`, `hardware`, `dhcp_servers`,
`ethernet_interfaces`, `router_bgp`). The remaining templates continue to render
through Jinja2 and are stitched into the right position by the orchestrator (see
[Orchestration](#orchestration)).

---

## Directory Structure

```
cli_generators/                           ← Python generators
├── base.py                               ← Framework (CliGenerator, CliSection, @cli_config_contributor)
├── config_comment.py                     ← Migrated: config_comment.j2
├── boot.py                               ← Migrated: boot.j2
├── aaa_security_bootstrap.py             ← Group orchestrator for the 4 blocks below
├── enable_password.py                    ← Migrated: enable-password.j2  (block, no contributor)
├── aaa_root.py                           ← Migrated: aaa-root.j2        (block, no contributor)
├── aaa_authentication_policy_nopassword.py
├── aaa_authorization_default_role.py
├── local_users.py                        ← Migrated: local-users.j2
├── hardware.py                           ← Combines 3 hardware-* templates
├── dhcp_servers.py                       ← Migrated: dhcp-servers.j2 (deep nesting)
├── ethernet_interfaces.py                ← Migrated: ethernet-interfaces.j2
├── router_bgp.py                         ← Migrated: router-bgp.j2 (largest example)
└── __init__.py                           ← Exports all generators in __all__

j2templates/eos/                          ← Remaining Jinja2 templates
└── … 208 .j2 files still to migrate

j2templates/eos-intended-config.j2        ← Canonical section order. Includes either
                                            a {% include 'eos/X.j2' %} or a
                                            __PYTHON_GENERATOR__ClassName__ placeholder.
```

---

## Core framework (`base.py`)

The framework is intentionally small — three pieces.

### 1. `CliSection` — one block of CLI output

A subclass renders a single named block (e.g. `vrf PROD`, `router bgp 65001`) by
implementing `_section()`. Output is built with three helpers:

| Helper | Indent | Skips on falsy? | Purpose |
|---|---|---|---|
| `self._section_heading(text)` | current indent | no | Write the block header line |
| `self._cli_line(template, *values)` | +1 | yes — drops if any value is falsy | Write a body line; `template.format(*values)` |
| `self._sub_section(child, *, skip_separator=False)` | +1 | n/a | Render a child `CliSection` |

`CliSection.render(indent=0)` calls `_section()`, captures the lines, and prepends a `!`
when `separator = True` (the default) and the section produced any output. Setting
`separator = False` on a subclass suppresses that — useful for inline sub-blocks like
`reservations` inside a DHCP subnet.

### 2. `@cli_config_contributor` — discovered render method

Marks a method on a `CliGenerator` subclass as a contributor. `render()` discovers
all decorated methods via `dir(cls)` and calls them in attribute order. A contributor
appends lines to `self._model` (the generator's `list[str]` accumulator) — typically by
extending it with the result of a `CliSection.render()` call.

### 3. `CliGenerator` + `CliGeneratorProtocol`

`CliGeneratorProtocol` defines the contract (typed `inputs: EosCliConfigGen`,
`_model: list[str]`, `render()`, `cli_config_methods()`). `CliGenerator` is the
concrete base subclasses inherit from — its `__init__` accepts either a dict
(converted via `EosCliConfigGen._from_dict`) or an already-built model, and
initializes `self._model = []`.

```python
class CliGenerator(CliGeneratorProtocol):
    def __init__(self, structured_config: EosCliConfigGen | dict) -> None:
        if isinstance(structured_config, dict):
            self.inputs = EosCliConfigGen._from_dict(structured_config)
        else:
            self.inputs = structured_config
        self._model: list[str] = []
```

The protocol's `render()` is inherited:

```python
def render(self) -> str:
    for method in self.cli_config_methods():
        method(self)
    return "\n".join(self._model)
```

---

## Execution flow

```
BootGenerator(structured_config)
    │
    ├── __init__: stores inputs (EosCliConfigGen), creates empty self._model
    │
    └── render()
        ├── cli_config_methods() — reflection over dir(cls)
        ├── for each contributor method: method(self) appends to self._model
        └── return "\n".join(self._model)
```

Each generator is **single-use by design** — one instance, one `render()`.

---

## Side-by-side: `boot.j2` → `boot.py`

### Jinja2 (`j2templates/eos/boot.j2`)

```jinja2
{% if boot is arista.avd.defined %}
!
{%     if boot.secret.key is arista.avd.defined %}
{%         if boot.secret.hash_algorithm is arista.avd.defined('md5') %}
{%             set hash_algorithm = 5 %}
{%         endif %}
boot secret {{ hash_algorithm | arista.avd.default('sha512') }} {{ boot.secret.key | arista.avd.hide_passwords(hide_passwords) }}
{% endif %}
```

### Python (`cli_generators/boot.py`)

```python
class BootGenerator(CliGenerator):
    @cli_config_contributor
    def boot(self) -> None:
        self._model.extend(BootBlock(self.inputs).render())


@dataclass
class BootBlock(CliSection):
    inputs: EosCliConfigGen

    def _section(self) -> None:
        secret = self.inputs.boot.secret
        if not secret.key:
            return
        hash_algorithm = "5" if secret.hash_algorithm == "md5" else secret.hash_algorithm
        key = hide_passwords(secret.key, self.inputs.eos_cli_config_gen_configuration.hide_passwords)
        self._section_heading(f"boot secret {hash_algorithm} {key}")
```

Same output. Standard Python, no custom template syntax, fully typed access into
`self.inputs.boot.secret` via the schema.

---

## Why we did this

| Pain point in Jinja2 | Python solution |
|---|---|
| `arista.avd.defined`, `arista.avd.default` everywhere | Standard `if x is None`, `or default` |
| No IDE autocomplete on `boot.secret.key` | Full type hints + Pydantic models |
| Runtime template errors | Type errors at import/lint time |
| Templates aren't directly unit-testable | Each `CliGenerator` / `CliSection` is a plain class — instantiate and call `.render()` |
| Nested `{% if %}{% for %}` becomes unreadable | Plain Python control flow |
| No debugger | `pdb` / breakpoints work normally |
| String concatenation is positional and silent | `_cli_line()` skips on falsy; `_sub_section()` composes blocks cleanly |

---

## Orchestration

`get_device_config_python.py` is the entry point. It instantiates every generator
listed in `cli_generators.__all__`, renders each one, and stitches the outputs into
the legacy Jinja2 output via `__PYTHON_GENERATOR__<ClassName>__` placeholder lines
in `eos-intended-config.j2`.

```
eos-intended-config.j2
─────────────────────────────────────────
__PYTHON_GENERATOR__ConfigCommentGenerator__   ← replaced with ConfigCommentGenerator output
__PYTHON_GENERATOR__BootGenerator__            ← replaced with BootGenerator output
__PYTHON_GENERATOR__AaaSecurityBootstrapGenerator__
{% include 'eos/vlan-internal-order.j2' %}     ← still Jinja2
{% include 'eos/transceiver-qsfp-default-mode.j2' %}
…
__PYTHON_GENERATOR__RouterBgpGenerator__       ← replaced inline at the BGP position
{% include 'eos/management-…' %}
```

This means a section's position in the final config is governed by `eos-intended-config.j2`,
not by whether it has been migrated yet. Migrating a template is a two-step swap:
delete the `{% include %}` line, add the `__PYTHON_GENERATOR__…__` placeholder in
the same position.

If a generator's output isn't empty and its placeholder is missing, the orchestrator
falls back to **prepending** the output — see
[`get_device_config_python.py`](../../get_device_config_python.py).

---

## Examples by complexity

| Generator | Why it's interesting |
|---|---|
| [`boot.py`](boot.py) | Smallest end-to-end example. One contributor, one `CliSection`. |
| [`config_comment.py`](config_comment.py) | `separator = False` — emits raw lines, no `!` prefix. |
| [`local_users.py`](local_users.py) | Iterates over a sorted list, builds variable-length headers. |
| [`hardware.py`](hardware.py) | One contributor that renders three independent blocks in order, each with its own `!`. |
| [`aaa_security_bootstrap.py`](aaa_security_bootstrap.py) | Four blocks sharing a single leading `!` — uses `bool(self._model)` to decide which block prepends it. |
| [`dhcp_servers.py`](dhcp_servers.py) | Deeply nested: server → subnet → reservations → mac. Uses `_sub_section()` and `skip_separator=` for ordering. |
| [`ethernet_interfaces.py`](ethernet_interfaces.py) | Largest single-block migration. Many small sub-section classes for distinct interface features. |
| [`router_bgp.py`](router_bgp.py) | The reference example. Top-level `RouterBgpBlock` composes ~30 sub-section classes covering every BGP knob, VRF, address-family, VPWS, etc. |

---

## Where to look for what

| File | Purpose |
|---|---|
| `cli_generators/base.py` | `CliSection`, `CliGenerator`, `@cli_config_contributor` |
| `cli_generators/CONTRIBUTING.md` | **Step-by-step guide for porting a Jinja2 template** |
| `cli_generators/__init__.py` | Exports — add new generators to `__all__` |
| `pyavd/get_device_config_python.py` | Orchestrator — placeholder substitution + prepend fallback |
| `pyavd/get_device_config.py` | Pure-Jinja2 renderer (still used for un-migrated sections) |
| `pyavd/j2filters/hide_passwords.py` | Password masking; reused unchanged |
| `pyavd/_eos_cli_config_gen/schema/__init__.py` | Pydantic models (`EosCliConfigGen`) |
| `pyavd/_eos_cli_config_gen/j2templates/eos/` | Remaining Jinja2 templates |
| `pyavd/_eos_cli_config_gen/j2templates/eos-intended-config.j2` | Canonical section order; placeholders live here |
