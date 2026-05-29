<!--
  ~ Copyright (c) 2026 Arista Networks, Inc.
  ~ Use of this source code is governed by the Apache License 2.0
  ~ that can be found in the LICENSE file.
  -->

# Contributing: porting a Jinja2 template to Python

This guide walks through migrating one `.j2` file under
`j2templates/eos/` into a Python generator under `cli_generators/`.

For the high-level architecture (framework, orchestration, file layout) read
[`DEMO.md`](DEMO.md) first. This document is the step-by-step recipe.

---

## TL;DR — the recipe

1. Pick a template, e.g. `j2templates/eos/snmp-server.j2`.
2. Create `cli_generators/snmp_server.py` (kebab-case → snake_case).
3. Write a `SnmpServerGenerator(CliGenerator)` with one `@cli_config_contributor`
   method. Delegate the actual rendering to one or more `@dataclass class
   …Block(CliSection)` classes.
4. Export `SnmpServerGenerator` from `cli_generators/__init__.py` (`__all__`).
5. In `j2templates/eos-intended-config.j2`, replace
   `{% include 'eos/snmp-server.j2' %}` with `__PYTHON_GENERATOR__SnmpServerGenerator__`.
6. Run the molecule diff tests to confirm byte-for-byte equivalence.
7. Delete the `.j2` template once nothing references it.

The rest of this document explains each step with worked examples drawn from
generators already in the tree.

---

## 1. Setup

### Naming

| Asset | Convention | Example |
|---|---|---|
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
    """Renders the '<feature> …' block with a leading '!' separator."""

    inputs: EosCliConfigGen

    def _section(self) -> None:
        ...
```

Use `from __future__ import annotations` so schema types (`EosCliConfigGen.…`) can
stay under `TYPE_CHECKING` while still being valid in dataclass field annotations.

---

## 2. The framework cheat sheet

| You want to… | Use | Indent |
|---|---|---|
| Start a block (`router bgp 65001`, `vrf PROD`, `subnet 10.0.0.0/24`) | `self._section_heading(text)` | current |
| Emit one body line (`router-id 1.1.1.1`) | `self._cli_line(template, *values)` | +1 |
| Compose a child block (`address-family ipv4` under `router bgp`) | `self._sub_section(ChildBlock(…))` | +1 |
| Render a repeated item that needs its own `!` separator | promote it to its own `CliSection` — see §3 "Don't emit `!` manually" |
| Suppress the leading `!` for this block | class attr `separator = False` |
| Skip the `!` between repeated children (first one only) | `self._sub_section(child, skip_separator=(i == 0))` |

> Never emit `!` with `self._cli_line("!")` if the line introduces a repeated
> entry — promote that entry to its own `CliSection` subclass instead. See
> §3 "Don't emit `!` manually".

### `_cli_line()` shortcut for "skip if value is None / falsy"

```python
self._cli_line("router-id {}", bgp.router_id)
```

If `bgp.router_id` is `None`, `""`, `0`, etc., nothing is written. This replaces the
ubiquitous Jinja2 pattern:

```jinja2
{% if bgp.router_id is arista.avd.defined %}
router-id {{ bgp.router_id }}
{% endif %}
```

For multiple values, all must be truthy:

```python
self._cli_line("graceful-restart restart-time {}", gr.restart_time)
```

If the line is unconditional, omit values entirely:

```python
self._cli_line("disabled")
```

---

## 3. How `!` separators and indentation work

This is the part of the framework that trips people up most often. Once you've
internalized this section, everything else is mechanical.

### The contract `CliSection.render()` provides

When you call `block.render(indent=N)`, three things happen:

1. **A fresh `_output_lines: list[str]` is created on the instance.**
2. **`_section()` is called.** Inside it, every `_section_heading()`,
   `_cli_line()`, and `_sub_section()` appends one or more lines to
   `_output_lines`. Each helper prepends the right amount of indent for you.
3. **The leading `!` is decided after `_section()` returns** by looking at
   whether `_output_lines` is non-empty AND `self.separator is True`.

Result:

| Condition | Output |
|---|---|
| `_output_lines` is empty (block produced nothing) | `[]` — nothing emitted, no `!` |
| `_output_lines` has lines AND `separator is True` (default) | `["<indent>!", *lines]` |
| `_output_lines` has lines AND `separator is False` | `[*lines]` — raw, no `!` |

This is **why empty sections never leave a stray `!` behind** — the separator is
appended only when the section actually produced content.

### How indentation flows

`CliSection._INDENT_STR = "   "` (three spaces). Each helper uses the current
`self._indent` and adjusts:

```
indent N      ← passed in via render(indent=N)
│
├── _section_heading(text)         writes at indent N      (block header)
├── _cli_line(template, *values)   writes at indent N+1    (body line)
└── _sub_section(child)            calls child.render(indent=N+1)
                                       └── child's _section_heading goes at N+1
                                       └── child's _cli_line goes at N+2
```

The contributor at the top of every generator passes `indent=0` implicitly when
it calls `Block(...).render()`. From then on, every nested level adds one.

### Worked trace — what gets emitted, line by line

Take this small generator:

```python
class FooGenerator(CliGenerator):
    @cli_config_contributor
    def foo(self) -> None:
        self._model.extend(FooBlock(self.inputs).render())


@dataclass
class FooBlock(CliSection):
    inputs: EosCliConfigGen

    def _section(self) -> None:
        self._section_heading("foo")               # appends "foo"            (indent 0)
        self._cli_line("name {}", "alpha")         # appends "   name alpha"  (indent 1)
        self._sub_section(BarBlock())              # delegates to child at indent 1


@dataclass
class BarBlock(CliSection):
    def _section(self) -> None:
        self._section_heading("bar")               # appends "   bar"         (indent 1)
        self._cli_line("color red")                # appends "      color red" (indent 2)
```

`FooBlock(...).render()` returns:

```text
!                    ← injected by render() because FooBlock has separator=True and produced output
foo                  ← _section_heading at indent 0
   name alpha        ← _cli_line at indent 1
   !                 ← injected by BarBlock.render() at indent 1
   bar               ← BarBlock _section_heading at indent 1
      color red      ← BarBlock _cli_line at indent 2
```

Note that the **child's `!` is also indented** — it goes at the child's indent
level, not at the root.

### When you don't want the leading `!`

There are three distinct "no `!`" cases — make sure you pick the right one.

#### Case 1 — the block should never have a leading `!`

Set `separator = False` as a **class attribute** on the subclass. The framework
will never inject a `!` regardless of whether the block produces output.

Use this for inline sub-sections — e.g. `reservations` inside a DHCP subnet — where
the parent's body and the child's header should flow together without a separator
between them.

```python
@dataclass
class ReservationsBlock(CliSection):
    separator = False                              # ← key line

    reservations: Any
    _: KW_ONLY
    ipv6: bool

    def _section(self) -> None:
        self._section_heading("reservations")
        ...
```

Also use it for `ConfigComment`, which emits raw `!`-prefixed lines as-is and
must not have an *additional* leading `!` injected by the framework.

#### Case 2 — repeated children: `!` between entries, not before the first

Default behaviour for siblings is "every block gets its own `!`". When you render
a list of N children with `separator=True`, you get N+1 `!` lines, one before each
child:

```
!            ← parent
parent-header
   !
   child 1
   !
   child 2
   !
   child 3
```

The Jinja2 originals usually want the `!` only **between** entries, not before
the first one — like this:

```
!
parent-header
   child 1
   !
   child 2
   !
   child 3
```

Pass `skip_separator=(i == 0)` on each `_sub_section()` call:

```python
for i, res in enumerate(natural_sort(self.reservations, sort_key="mac_address")):
    self._sub_section(MacReservation(res, ipv6=self.ipv6), skip_separator=(i == 0))
```

The child still has `separator = True` as its class default — `skip_separator`
just suppresses it for that one specific render call.

#### Case 3 — siblings share a single leading `!` (the bootstrap pattern)

When several independent blocks must share one `!` — only the first one that
actually emits content owns it — set `block.separator` per-instance based on
whether earlier blocks already produced output. See
[`aaa_security_bootstrap.py`](aaa_security_bootstrap.py) and Example E below.

```python
for block_cls in (Block1, Block2, Block3, Block4):
    block = block_cls(self.inputs)
    block.separator = not bool(self._model)        # only the first non-empty block keeps separator=True
    self._model.extend(block.render())
```

### Don't emit `!` manually — promote the repeated item to its own `CliSection`

If you find yourself writing `self._cli_line("!")` to separate repeated lines,
that's a sign the item should be a `CliSection` of its own. Each render call
gets its own automatic `!` via the `separator = True` default — that's the same
machinery used for top-level blocks.

**Anti-pattern** — manual `!` between items:

```python
for range_ in natural_sort(subnet.ranges or [], sort_key="start"):
    self._cli_line("!")                            # ← don't do this
    self._cli_line(f"range {range_.start} {range_.end}")
```

**Correct** — each `range` is its own `CliSection`, framework injects the `!`:

```python
for range_ in natural_sort(subnet.ranges or [], sort_key="start"):
    self._sub_section(RangeBlock(range_))


@dataclass
class RangeBlock(CliSection):
    range_: EosCliConfigGen.DhcpServersItem.Ipv4SubnetsItem.RangesItem | \
            EosCliConfigGen.DhcpServersItem.Ipv6SubnetsItem.RangesItem

    def _section(self) -> None:
        self._section_heading(f"range {self.range_.start} {self.range_.end}")
```

Same output, but now the indent and `!` are managed by the framework, the empty
case is handled automatically (no ranges → no `!`), and `RangeBlock` is
independently testable.

If even after this you still need a literal `!` *inside* a block body —
genuinely rare — `self._cli_line("!")` is available. Reach for it only after
convincing yourself the repeated item really isn't a section.

---

## 4. Why one class per section?

A reasonable question on first read is: *why isn't this just one big method per
generator? Why are there so many small `CliSection` subclasses?*

The reason isn't aesthetic — it's **mechanical**. The class is what gives
us `!` separators and indentation for free.

### What a class buys you that a function doesn't

| Concern | If you wrote it as one big function | What `CliSection` does for you |
|---|---|---|
| Indentation | You'd thread an `indent` integer through every nested call manually | The class tracks `self._indent`; helpers compute indent automatically |
| Leading `!` | You'd check "did I emit anything? if so, prepend `!`" at every nesting level | `render()` checks `_output_lines` after `_section()` returns |
| Conditional emission | You'd carry a `lines: list[str]` buffer through every helper | The buffer is `self._output_lines`, scoped to one render call |
| Empty-block elision | You'd manually check before adding `!` separators | If `_output_lines` is empty after `_section()`, nothing — including the `!` — is emitted |
| Per-section flags (`separator`, future extensions) | You'd add boolean parameters to every helper | They're class attributes; subclasses override them declaratively |

### Why subclass, not compose?

We considered passing a callback (`def render(emit_fn, indent_fn)`) but the class
approach is cleaner because:

- `_section_heading` / `_cli_line` / `_sub_section` are **methods that share state**
  (`_indent`, `_output_lines`). With functions you'd be passing three context
  objects around.
- `@dataclass` gives us free `__init__` for the inputs the section needs — every
  section ends up as roughly five lines: field declarations + `_section()`.
- Inheritance lets a section override one knob (`separator = False`) without
  reimplementing render logic.

### Why a *separate* class for each section, not one with branches?

You *could* write one giant `RouterBgpBlock._section()` with a 3000-line
if-chain. Don't. Each EOS block — `vrf X`, `address-family ipv4`, `neighbor X.X.X.X`
— has its own indentation level and its own leading-`!` rule. Putting each in a
dedicated `CliSection` subclass means:

- **Indent is implicit.** `RouterBgpVrf._section()` writes at indent 1 because it
  was invoked via `_sub_section()` from `RouterBgpBlock`. The `vrf`-level code
  doesn't have to know it's nested.
- **The `!` between siblings is automatic.** Each VRF block gets its own `!` because
  each is its own `CliSection.render()` call.
- **Reuse.** `RouterBgpAddressFamilyIpv4` can be rendered both at the top level
  (under `router bgp`) and inside a VRF — same class, different parent.
- **Testability.** You can instantiate `RouterBgpVrf(vrf=…, inputs=…).render()` in
  isolation and assert on the lines. No need to spin up the whole generator.
- **Reviewability.** Each class is ~30 lines focused on one EOS construct. A 3000-line
  method is impossible to review meaningfully.

### When *not* to introduce a class

If a chunk of CLI output is purely a flat list of lines with no nested block —
e.g. the body of `router bgp` between the header and the first sub-block — keep
it inside the parent's `_section()` or split into a `_render_xxx()` helper
method on the same class. See `RouterBgpBlock._render_global_settings()` for an
example. The rule is: **new `CliSection` per nesting level, helper method per
logical chunk within a level**.

---

## 5. Worked examples

### Example A — single-line section: `enable-password.j2`

Original Jinja2 (12 useful lines):

```jinja2
{% if enable_password is arista.avd.defined %}
{%     if enable_password.disabled is arista.avd.defined(true) %}
!
no enable password
{%     elif enable_password.key is arista.avd.defined %}
!
{%         if enable_password.hash_algorithm is arista.avd.defined('md5') %}
enable password 5 {{ enable_password.key | arista.avd.hide_passwords(hide_passwords) }}
{%         elif enable_password.hash_algorithm is arista.avd.defined('sha512') %}
enable password sha512 {{ enable_password.key | arista.avd.hide_passwords(hide_passwords) }}
{%         endif %}
{%     endif %}
{% endif %}
```

Ported Python (`enable_password.py`):

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

Talking points:
- `is arista.avd.defined` → just truthiness on the Pydantic field.
- `is arista.avd.defined(true)` → equality check on the field.
- The Jinja `{% if %}` early-exits become `return` statements.
- The leading `!` is supplied automatically by `CliSection` (default `separator = True`).
- This block has no `Generator` class of its own — it's part of the
  [`AaaSecurityBootstrapGenerator`](aaa_security_bootstrap.py) group (see Example E).

---

### Example B — list iteration with optional fields: `local-users.j2`

Original Jinja2 builds the line by string concatenation:

```jinja2
{% for local_user in local_users | arista.avd.natural_sort('name', ignore_case=false) %}
{%     set cli = "username " ~ local_user.name %}
{%     if local_user.disabled is arista.avd.defined(true) %}
no {{ cli }}
{%         continue %}
{%     endif %}
{%     if local_user.privilege is arista.avd.defined %}
{%         set cli = cli ~ " privilege " ~ local_user.privilege %}
{%     endif %}
{%     if local_user.role is arista.avd.defined %}
{%         set cli = cli ~ " role " ~ local_user.role %}
{%     endif %}
…
{{ cli }}
{% endfor %}
```

Ported Python (`local_users.py`):

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
            if user.privilege is not None:
                parts.append(f"privilege {user.privilege}")
            if user.role:
                parts.append(f"role {user.role}")
            if user.shell:
                parts.append(f"shell {user.shell}")
            if user.sha512_password:
                parts.append(f"secret sha512 {hide_passwords(user.sha512_password, hide)}")
            elif user.no_password:
                parts.append("nopassword")
            self._section_heading(" ".join(parts))
            …
```

Talking points:
- `natural_sort` is reused from `pyavd.j2filters` — no need to re-implement.
- Building a `parts` list and joining is the right replacement for the Jinja
  `set cli = cli ~ …` pattern.
- Note `if user.privilege is not None` rather than `if user.privilege` — `0` is a
  valid privilege level.

---

### Example C — `separator = False` for inline blocks: `config_comment.j2`

The config-comment template emits raw `!…` lines and has no surrounding block.

```python
@dataclass
class ConfigComment(CliSection):
    """Renders config comment lines at indent 0 (no separator, no block header)."""

    separator = False     # ← suppress the automatic '!' prefix

    inputs: EosCliConfigGen

    def _section(self) -> None:
        if not self.inputs.config_comment:
            return
        self._section_heading("!")
        for line in self.inputs.config_comment.split("\n"):
            self._section_heading(f"!{line}")
```

When `separator = False`, the section's lines are emitted exactly as written, with no
leading `!` injected by `render()`.

---

### Example D — three independent sub-blocks: `hardware.py`

`hardware-port-groups.j2`, `hardware-counters.j2`, and `hardware-access-list.j2` are
three separate sections in the EOS output — each prepends its own `!` and is
independent. We combine them into a single generator that runs three blocks in order.

```python
class HardwareGenerator(CliGenerator):
    @cli_config_contributor
    def hardware(self) -> None:
        for block_cls in (HardwarePortGroupBlock, HardwareCounterFeatureBlock, HardwareAccessListMechanismBlock):
            self._model.extend(block_cls(self.inputs).render())


@dataclass
class HardwarePortGroupBlock(CliSection):
    inputs: EosCliConfigGen

    def _section(self) -> None:
        port_groups = self.inputs.hardware.port_groups
        if not port_groups:
            return
        for port_group in port_groups:
            if not port_group.select:
                continue
            self._section_heading(f"hardware port-group {port_group.port_group} select {port_group.select}")

# … HardwareCounterFeatureBlock, HardwareAccessListMechanismBlock similar
```

Talking points:
- The contributor method iterates over block classes, calls `.render()` on each, and
  extends `self._model`. Each block independently decides whether to emit a `!` —
  blocks that produce nothing skip the separator.
- Each sub-block can stay focused on one input subtree.

---

### Example E — shared leading `!` across siblings: `aaa_security_bootstrap.py`

EOS expects exactly **one** `!` before the enable-password / aaa-root /
aaa-authentication-policy / aaa-authorization group — even though the four blocks are
logically independent. Whichever block first emits content owns the `!`.

The trick: set `separator` per-block based on whether `self._model` already has lines.

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
            # Only the first block to actually emit anything gets the leading '!'.
            block.separator = not bool(self._model)
            self._model.extend(block.render())
```

The four block files (`enable_password.py`, `aaa_root.py`, etc.) have no `Generator`
of their own — they're pure `CliSection` subclasses that this orchestrator
instantiates.

---

### Example F — deep nesting and child blocks: `dhcp_servers.py`

The DHCP template nests four levels: `dhcp server` → `subnet` → `reservations`
→ `mac-address`. Each level becomes its own `CliSection`; the parent composes with
`self._sub_section(child)`.

```python
class DhcpServersGenerator(CliGenerator):
    @cli_config_contributor
    def dhcp_servers(self) -> None:
        for dhcp_server in natural_sort(self.inputs.dhcp_servers or [], sort_key="vrf", ignore_case=False):
            self._model.extend(DhcpServerBlock(dhcp_server).render())


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
        …


@dataclass
class Ipv4SubnetBlock(CliSection):
    subnet: EosCliConfigGen.DhcpServersItem.Ipv4SubnetsItem

    def _section(self) -> None:
        self._section_heading(f"subnet {self.subnet.subnet}")
        if self.subnet.reservations:
            self._sub_section(ReservationsBlock(self.subnet.reservations, ipv6=False))
        for range_ in natural_sort(natural_sort(self.subnet.ranges or [], sort_key="end"), sort_key="start"):
            self._sub_section(RangeBlock(range_))           # ← each range its own CliSection
        …


@dataclass
class RangeBlock(CliSection):
    """One 'range X Y' line. Default separator=True gives each entry its own '!'."""

    range_: EosCliConfigGen.DhcpServersItem.Ipv4SubnetsItem.RangesItem | \
            EosCliConfigGen.DhcpServersItem.Ipv6SubnetsItem.RangesItem

    def _section(self) -> None:
        self._section_heading(f"range {self.range_.start} {self.range_.end}")
```

Talking points:
- Each block has a **proper schema type** in its dataclass field — not `Any`. Use the
  nested path on `EosCliConfigGen` (here `EosCliConfigGen.DhcpServersItem.Ipv4SubnetsItem`).
- `_sub_section()` bumps the indent by one and concatenates the child's lines.
- **Repeated items get their own `CliSection`.** Even a one-line block like
  `RangeBlock` is worth its own class — the framework injects the `!` between
  entries automatically (default `separator = True`). Don't manually emit `!`
  with `_cli_line("!")` in a loop; see §3.
- Keyword-only constructor args use `KW_ONLY` from `dataclasses`:

  ```python
  from dataclasses import KW_ONLY, dataclass

  @dataclass
  class ReservationsBlock(CliSection):
      separator = False
      reservations: Any
      _: KW_ONLY
      ipv6: bool
  ```

  Caller side: `ReservationsBlock(subnet.reservations, ipv6=False)`.

- For repeated child sections where you want `!` *between* entries but not *before*
  the first, pass `skip_separator=(i == 0)`:

  ```python
  for i, res in enumerate(natural_sort(self.reservations, sort_key="mac_address")):
      self._sub_section(MacReservation(res, ipv6=self.ipv6), skip_separator=(i == 0))
  ```

---

### Example G — the big one: `router_bgp.py`

The largest single migrated template. Worth reading end-to-end as the canonical
example for any non-trivial section. Top-level structure:

```python
class RouterBgpGenerator(CliGenerator):
    @cli_config_contributor
    def router_bgp(self) -> None:
        self._model.extend(RouterBgpBlock(self.inputs.router_bgp, self.inputs).render())


@dataclass
class RouterBgpBlock(CliSection):
    bgp: EosCliConfigGen.RouterBgp
    inputs: EosCliConfigGen        # only kept for password masking — see below

    def _section(self) -> None:
        if get_v2(self.bgp, "as") is None:
            return
        self._section_heading(f"router bgp {self.bgp.as_}")
        self._render_global_settings(self.bgp)
        …
        self._sub_section(RouterBgpAddressFamilyIpv4(self.bgp))
        self._sub_section(RouterBgpAddressFamilyIpv4LabeledUnicast(self.bgp))
        …
        for vrf in natural_sort(self.bgp.vrfs or [], sort_key="name"):
            self._sub_section(RouterBgpVrf(vrf, self.inputs))
```

There are ~30 sub-section classes covering each BGP knob, address-family, VPWS service,
VRF, etc. Each one is a small focused `@dataclass class XxxBlock(CliSection)`.

Two patterns worth calling out:
- **Helper methods inside a section** — `_render_global_settings`, `_render_neighbors`,
  etc. are plain methods on the `CliSection` class, not contributors. Use them to keep
  `_section()` readable.
- **Passing `inputs` down** is fine when a child needs the global `hide_passwords`
  flag. Don't reach for `self.data`-style shortcuts; just declare an `inputs:
  EosCliConfigGen` field on the child dataclass.

---

## 6. Wiring it up

### 6a. Export from `__init__.py`

```python
from .snmp_server import SnmpServerGenerator

__all__ = [
    …
    "SnmpServerGenerator",
]
```

Order in `__all__` is the order generators are instantiated by the orchestrator;
keep it grouped by EOS section order for readability, but the placeholder
substitution does the real positioning.

### 6b. Replace the include in `eos-intended-config.j2`

Find:

```jinja2
{% include 'eos/snmp-server.j2' %}
```

Replace with:

```jinja2
__PYTHON_GENERATOR__SnmpServerGenerator__
```

Keep the line in the **same position** — that's what governs the section's order in
the final config.

### 6c. (Eventually) delete the `.j2`

Once the placeholder is in place and tests pass, the template is no longer included
anywhere. Delete `j2templates/eos/snmp-server.j2`.

---

## 7. Verifying parity

### Run the device-config tests

```bash
cd avd/python-avd
python -m pytest tests/pyavd/molecule_scenarios/test_get_device_config.py -k "<scenario>" -vv
```

These tests render every molecule scenario through both paths and diff against the
expected `intended/configs/*.cfg`. Any byte difference fails the test — that's your
signal that the port isn't equivalent yet.

### Quick local smoke test

```python
from pyavd._eos_cli_config_gen.cli_generators import SnmpServerGenerator
print(SnmpServerGenerator(my_structured_config_dict).render())
```

### What to check when there's a diff

1. **Trailing/leading newlines** — Jinja2 adds them aggressively. `CliSection`
   guarantees exactly one `\n` between adjacent lines and prepends one `!` when
   `separator = True` and the section emitted output.
2. **Indent level** — `_section_heading` writes at the current indent; `_cli_line`
   writes at indent + 1; `_sub_section` increases indent by 1 for the child. If you
   need to render a literal-indented line, use `_cli_line` from within a child block,
   not from the parent.
3. **Sort order** — match the Jinja `arista.avd.natural_sort(…, ignore_case=…)` call
   exactly. The default `ignore_case` differs between the filter (`true`) and how we
   often want it (case-sensitive). Read the original template.
4. **Truthiness vs defined** — Jinja `is arista.avd.defined` allows `0` and `""` but
   excludes `None`/missing. Python `if x:` excludes both. When the field can legitimately
   be `0` or `""`, write `if x is not None`.
5. **Hidden passwords** — always thread the `hide_passwords` flag through to any
   `hide_passwords(secret, flag)` call. The flag lives on
   `inputs.eos_cli_config_gen_configuration.hide_passwords`.

---

## 8. Style conventions used in this package

- **`@dataclass` always.** Every `CliSection` subclass is a dataclass — never write
  a manual `__init__`. Use proper schema types in field annotations, not `Any`.
- **Field names match constructor names.** If the caller passes `subnet`, the field
  is `subnet`, not `_subnet`.
- **One section per nesting level.** When a block has more than ~50 lines of
  `_section()`, factor a chunk into its own `CliSection` subclass and compose with
  `_sub_section()`.
- **Don't emit `!` manually.** If a repeated line needs a `!` between entries,
  promote the line to its own `CliSection` and call `_sub_section()` in the loop.
  Never `self._cli_line("!")` in a loop. See §3.
- **No `data` attribute.** Use `inputs` — matches `structured_config_generator` in
  `_eos_designs`.
- **Use `_cli_line` for conditional fields.** Don't write `if x: self._cli_line(f"x {x}")` —
  write `self._cli_line("x {}", x)` and let `_cli_line` drop the line if `x` is falsy.
- **`from __future__ import annotations`** in every file.
- **Schema imports under `TYPE_CHECKING`** to keep import-time cost down and avoid
  cycles.

---

## 9. Common pitfalls

| Symptom | Likely cause |
|---|---|
| `NotImplementedError: _section()` | You forgot to override `_section()` in the subclass. |
| Block output is empty but should have content | A `self._cli_line(template, value)` call where `value` is falsy. Check whether `0`/`""` are valid. |
| Extra `!` between repeated children | Use `skip_separator=(i == 0)` on the first `_sub_section()` call in the loop. |
| Missing leading `!` for the block | Did you set `separator = False` accidentally? |
| Section appears at the wrong position in the final config | Placeholder line in `eos-intended-config.j2` is in the wrong spot, or you prepended instead of substituting in place. |
| `TypeError: __init__() takes 2 positional arguments but 3 were given` | You added a dataclass field after a `KW_ONLY` marker but passed it positionally. |
| Manual `self._cli_line("!")` calls scattered in a loop body | Promote the loop body to its own `CliSection` and call `_sub_section()` — the framework will emit the `!` between entries automatically. |

---

## 10. Reference

- Framework: [`base.py`](base.py)
- Existing examples (read in this order for increasing complexity):
  [`boot.py`](boot.py),
  [`config_comment.py`](config_comment.py),
  [`local_users.py`](local_users.py),
  [`hardware.py`](hardware.py),
  [`aaa_security_bootstrap.py`](aaa_security_bootstrap.py),
  [`dhcp_servers.py`](dhcp_servers.py),
  [`ethernet_interfaces.py`](ethernet_interfaces.py),
  [`router_bgp.py`](router_bgp.py)
- Orchestrator: [`get_device_config_python.py`](../../get_device_config_python.py)
- Architecture overview: [`DEMO.md`](DEMO.md)
