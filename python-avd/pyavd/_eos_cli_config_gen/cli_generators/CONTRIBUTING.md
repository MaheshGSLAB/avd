<!--
  ~ Copyright (c) 2026 Arista Networks, Inc.
  ~ Use of this source code is governed by the Apache License 2.0
  ~ that can be found in the LICENSE file.
  -->

# Contributing: porting a Jinja2 template to Python

This guide walks through migrating one `.j2` file under `j2templates/eos/` into
a Python generator under `cli_generators/`.

For the high-level architecture read [`DEMO.md`](DEMO.md) first.

---

## TL;DR — the recipe

1. Pick a template, e.g. `j2templates/eos/snmp-server.j2`.
2. Create `cli_generators/snmp_server.py` (kebab-case → snake_case).
3. Write a `SnmpServerGenerator(CliGenerator)` with one `@cli_config_contributor`
   method. Delegate rendering to one or more `@dataclass class …Block(CliSection)` classes.
4. Export `SnmpServerGenerator` from `cli_generators/__init__.py` (`__all__`).
5. In `j2templates/eos-intended-config.j2`, replace
   `{% include 'eos/snmp-server.j2' %}` with `__PYTHON_GENERATOR__SnmpServerGenerator__`.
6. Run the molecule diff tests to confirm byte-for-byte equivalence.
7. Delete the `.j2` template once nothing references it.

---

## 1. Setup

### Naming

| Asset | Convention | Example |
| ----- | ---------- | ------- |
| Jinja template | `kebab-case.j2` | `local-users.j2` |
| Python module | `snake_case.py` | `local_users.py` |
| Generator class | `PascalCase + Generator` | `LocalUsersGenerator` |
| Section block class | `PascalCase + Block` (or descriptive) | `LocalUsersBlock`, `Ipv4SubnetBlock` |
| Contributor method | matches the EOS root key | `def local_users(self)` |

### File skeleton

```python
# Copyright (c) 2026 Arista Networks, Inc.
# Use of this source code is governed by the Apache License 2.0
# that can be found in the LICENSE file.
"""<feature> CLI configuration generator."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from .base import CliGenerator, CliSection, cli_config_contributor

if TYPE_CHECKING:
    from pyavd._eos_cli_config_gen.schema import EosCliConfigGen


class <Feature>Generator(CliGenerator):
    """Generator for <feature> CLI configuration."""

    @cli_config_contributor
    def <feature>(self) -> None:
        self._model.extend(<Feature>Block(self.inputs).render())


@dataclass
class <Feature>Block(CliSection):
    inputs: EosCliConfigGen

    def _section(self) -> None:
        ...
```

---

## 2. The framework cheat sheet

- **Start a block** (`router bgp 65001`, `vrf PROD`) — `self._section_heading(text)` at the current indent.
- **Emit a body line** (`router-id 1.1.1.1`) — `self._cli_line(template, *values)` at indent +1.
- **Compose a child block** — `self._sub_section(ChildBlock(…))` at indent +1.
- **Suppress the leading `!`** — set `separator = False` as a class attribute.
- **Skip `!` before the first repeated child** — `self._sub_section(child, skip_separator=(i == 0))`.

`_cli_line()` skips the line automatically when any value is `None`/falsy:

```python
self._cli_line("router-id {}", bgp.router_id)   # emits nothing if router_id is None
self._cli_line("disabled")                        # unconditional — no values
```

This replaces the ubiquitous `{% if x is arista.avd.defined %}` pattern.

---

## 3. `!` separators and indentation

### How it works

Every `CliSection` subclass follows the same lifecycle when `render(indent=N)` is called.

**Step 1 — collect output.**
`_section()` runs. Every call to `_section_heading()`, `_cli_line()`, or
`_sub_section()` inside it appends lines to an internal buffer (`_output_lines`),
with indentation derived automatically from `N`.

**Step 2 — decide the separator.**
After `_section()` returns, `render()` inspects the buffer:

- If the buffer is **empty** (every field was `None`, every list was empty, or you
  returned early) — nothing is emitted at all, not even a `!`.
- If the buffer has **content** and `separator is True` (the class default) — a
  leading `!` is prepended.
- If the buffer has **content** and `separator is False` — the lines are emitted
  as-is, with no `!` injected.

The key consequence: **you never get a stray `!` from a block that produced nothing.**
The separator is decided after the fact, so you don't need to guard it yourself.

### Three "no `!`" cases

**Case 1 — block should never have a leading `!`:** set `separator = False` as a class attribute. Use for inline sub-sections or blocks that emit raw `!`-prefixed lines themselves.

**Case 2 — `!` between repeated children, not before the first:**

```python
for i, res in enumerate(natural_sort(self.reservations, sort_key="mac_address")):
    self._sub_section(MacReservation(res, ipv6=self.ipv6), skip_separator=(i == 0))
```

**Case 3 — siblings share a single leading `!` (bootstrap pattern):** only the first block that actually emits content owns it.

```python
for block_cls in (Block1, Block2, Block3):
    block = block_cls(self.inputs)
    block.separator = not bool(self._model)   # only first non-empty block keeps separator=True
    self._model.extend(block.render())
```

### Don't emit `!` manually

If you find yourself writing `self._cli_line("!")` in a loop, the item should be
a `CliSection` subclass instead. Each `render()` call gets its own automatic `!`.

```python
# Anti-pattern
for range_ in ...:
    self._cli_line("!")
    self._cli_line(f"range {range_.start} {range_.end}")

# Correct — each range is its own CliSection
for range_ in ...:
    self._sub_section(RangeBlock(range_))

@dataclass
class RangeBlock(CliSection):
    range_: EosCliConfigGen.DhcpServersItem.Ipv4SubnetsItem.RangesItem

    def _section(self) -> None:
        self._section_heading(f"range {self.range_.start} {self.range_.end}")
```

---

## 4. Worked examples

### Example A — simple section: `enable-password.py`

```python
@dataclass
class EnablePasswordBlock(CliSection):
    inputs: EosCliConfigGen

    def _section(self) -> None:
        enable_password = self.inputs.enable_password
        if enable_password.disabled:
            self._section_heading("no enable password")
            return
        if not enable_password.key:
            return
        if enable_password.hash_algorithm == "md5":
            algorithm_token = "5"
        elif enable_password.hash_algorithm == "sha512":
            algorithm_token = "sha512"
        else:
            return
        key = hide_passwords(enable_password.key, self.inputs.eos_cli_config_gen_configuration.hide_passwords)
        self._section_heading(f"enable password {algorithm_token} {key}")
```

Key points:
- `is arista.avd.defined` → truthiness on the Pydantic field.
- `is arista.avd.defined(true)` → equality check.
- Jinja `{% if %}` early-exits become `return` statements.
- The leading `!` is automatic (`separator = True` default).

---

### Example B — list iteration with optional fields: `local-users.py`

```python
@dataclass
class LocalUsersBlock(CliSection):
    inputs: EosCliConfigGen

    def _section(self) -> None:
        if not self.inputs.local_users:
            return
        hide = self.inputs.eos_cli_config_gen_configuration.hide_passwords
        for user in natural_sort(self.inputs.local_users, sort_key="name", ignore_case=False):
            if user.disabled:
                self._section_heading(f"no username {user.name}")
                continue
            parts = [f"username {user.name}"]
            if user.privilege is not None:   # note: 0 is a valid privilege level
                parts.append(f"privilege {user.privilege}")
            if user.role:
                parts.append(f"role {user.role}")
            ...
            self._section_heading(" ".join(parts))
```

Use `parts` list + join to replace Jinja's `set cli = cli ~ …` pattern.

---

### Example C — `separator = False`: `config_comment.py`

```python
@dataclass
class ConfigComment(CliSection):
    separator = False    # suppress the automatic '!' prefix

    inputs: EosCliConfigGen

    def _section(self) -> None:
        if not self.inputs.config_comment:
            return
        self._section_heading("!")
        for line in self.inputs.config_comment.split("\n"):
            self._section_heading(f"!{line}")
```

---

### Example D — shared leading `!`: `aaa_security_bootstrap.py`

EOS expects exactly one `!` before several independent blocks.

```python
class AaaSecurityBootstrapGenerator(CliGenerator):
    @cli_config_contributor
    def aaa_security_bootstrap(self) -> None:
        for block_cls in (
            EnablePasswordBlock,
            AaaRootBlock,
            AaaAuthenticationPolicyNopasswordBlock,
            AaaAuthorizationDefaultRoleBlock,
        ):
            block = block_cls(self.inputs)
            block.separator = not bool(self._model)   # only first non-empty block gets '!'
            self._model.extend(block.render())
```

The four block classes are pure `CliSection` subclasses — no `Generator` of their own.

---

### Example E — deep nesting: `dhcp_servers.py`

Each nesting level is its own `CliSection`; the parent composes with `_sub_section()`.

```python
@dataclass
class DhcpServerBlock(CliSection):
    dhcp_server: EosCliConfigGen.DhcpServersItem

    def _section(self) -> None:
        ds = self.dhcp_server
        header = "dhcp server" if ds.vrf == "default" else f"dhcp server vrf {ds.vrf}"
        self._section_heading(header)
        if ds.disabled is True:
            self._cli_line("disabled")
        for subnet in natural_sort(ds.ipv4_subnets or [], sort_key="subnet"):
            self._sub_section(Ipv4SubnetBlock(subnet))


@dataclass
class Ipv4SubnetBlock(CliSection):
    subnet: EosCliConfigGen.DhcpServersItem.Ipv4SubnetsItem

    def _section(self) -> None:
        self._section_heading(f"subnet {self.subnet.subnet}")
        if self.subnet.reservations:
            self._sub_section(ReservationsBlock(self.subnet.reservations, ipv6=False))
        for range_ in natural_sort(self.subnet.ranges or [], sort_key="start"):
            self._sub_section(RangeBlock(range_))
```

Use proper schema types in dataclass fields (`EosCliConfigGen.DhcpServersItem`), not `Any`.
For keyword-only constructor args use `KW_ONLY` from `dataclasses`.

---

## 5. Wiring it up

### 5a. Export from `__init__.py`

```python
from .snmp_server import SnmpServerGenerator

__all__ = [
    ...
    "SnmpServerGenerator",
]
```

### 5b. Replace the include in `eos-intended-config.j2`

```jinja2
{# before #}
{% include 'eos/snmp-server.j2' %}

{# after #}
__PYTHON_GENERATOR__SnmpServerGenerator__
```

Keep the line at the **same position** — that governs section order in the final config.

### 5c. Delete the `.j2` once tests pass

```bash
rm j2templates/eos/snmp-server.j2
```

---

## 6. Verifying parity

Run the `eos_cli_config_gen` molecule scenario and confirm there is no diff in the
generated `.cfg` files:

```bash
molecule test -s eos_cli_config_gen
```

The generated configs are compared against the committed expected files. Any difference
in the `.cfg` output means the port is not yet equivalent — no diff means the migration
is correct.

### Common diff causes

| Symptom | Check |
| ------- | ----- |
| Trailing/leading newlines | `CliSection` guarantees one `\n` between lines; Jinja2 may have added extras |
| Wrong indent level | `_section_heading` = current indent; `_cli_line` = indent+1; `_sub_section` = +1 for child |
| Wrong sort order | Match the original `arista.avd.natural_sort(…, ignore_case=…)` call exactly |
| Passwords not masked | Thread `hide_passwords` flag from `inputs.eos_cli_config_gen_configuration.hide_passwords` |

---

## 7. Style conventions

- **`@dataclass` always.** Never write a manual `__init__`. Use proper schema types.
- **One section per nesting level.** Factor blocks > ~50 lines into child `CliSection` subclasses.
- **Don't emit `!` manually.** Promote repeated items to `CliSection`; the framework handles separators.
- **Use `_cli_line` for conditional fields.** Write `self._cli_line("x {}", x)`, not `if x: self._cli_line(...)`.
- **Field name `inputs`, not `data`** — matches `structured_config_generator` in `_eos_designs`.
- **`from __future__ import annotations`** in every file.
- **Schema imports under `TYPE_CHECKING`** to avoid import-time cost and cycles.

---

## 9. Reference

- Framework: [`base.py`](base.py)
- Examples (increasing complexity):
  [`boot.py`](boot.py),
  [`config_comment.py`](config_comment.py),
  [`local_users.py`](local_users.py),
  [`hardware.py`](hardware.py),
  [`aaa_security_bootstrap.py`](aaa_security_bootstrap.py),
  [`dhcp_servers.py`](dhcp_servers.py),
  [`router_bgp.py`](router_bgp.py)
- Orchestrator: [`get_device_config_python.py`](../../get_device_config_python.py)
- Architecture overview: [`DEMO.md`](DEMO.md)
