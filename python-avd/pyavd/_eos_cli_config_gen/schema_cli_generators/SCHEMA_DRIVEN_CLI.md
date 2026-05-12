# Schema-driven CLI rendering — design & cookbook

This document walks through how the schema-driven CLI renderer works, what each
`cli.*` annotation key does, and shows real worked examples taken from the
`router_bgp` block (which is now 100% schema-driven — see
[`router_bgp.py`](router_bgp.py) for the orchestration and
[`schema_fragments/router_bgp.schema.yml`](../schema/schema_fragments/router_bgp.schema.yml)
for the annotations).

---

## 1. The big picture

Every BGP CLI line you see in a generated config comes from one place:

1. The **schema YAML** (`schema_fragments/*.schema.yml`) declares each field's
   shape AND its rendering rules under a `cli:` block.
2. The **build script** (`make compile-schemas`) merges `$ref`s and writes
   `eos_cli_config_gen.schema.pickle`.
3. At runtime, [`render_schema_field()`](base.py) walks the resolved schema
   alongside the structured-config model, dispatching on each field's `cli`
   annotation to produce CLI lines.
4. A thin orchestrator class (`RouterBgpBlock`) decides the **order** in
   which top-level fields are emitted, but does no rendering of its own.

```
   schema YAML (cli: annotations)         structured config (AvdModel)
            │                                       │
            ▼                                       ▼
   ┌──────────────────────────────────────────────────┐
   │              render_schema_field()                │
   │   dispatch on cli.* keys → CLI line(s)            │
   └──────────────────────────────────────────────────┘
                            │
                            ▼
                   ["router bgp 65000",
                    "   router-id 1.1.1.1", ...]
```

The renderer reads from the **pickled** schema (where `$ref`s are merged), not
the raw YAML. If you put a `cli:` annotation on a `$def` fragment and load the
YAML directly in a test, the renderer will silently see no annotation —
always load `eos_cli_config_gen.schema.pickle`.

---

## 2. Dispatch order

[`render_schema_field()`](base.py) tries annotations in this order. The first
one that matches handles the field:

```
1. cli.gate              skip whole field if any gate fails
2. bool_true_line / bool_false_line   bool fields
3. cli.line              one body line resolved from PARENT context
4. cli.section           open a section block (header + body)
5. cli.line_fragments    one composite line + recurse into children
6. cli.lines             multiple body lines + recurse into children
7. cli.line_switch       pick one of N templates by sibling field value
8. list + cli.item_lines           flat lines per list item
9. list + cli.item_line_fragments  composite line per list item
10. list + items.cli               recurse render_schema_field per item
11. str + cli.raw_lines  emit each split-line of a string verbatim
12. dict (no cli)        transparently recurse into annotated children
```

`section` jumped above `lines` because a dict can have BOTH (the section uses
`lines` as its body).

---

## 3. The annotation keys, one by one

Each example is taken verbatim from
`schema_fragments/router_bgp.schema.yml` so you can grep for it.

### `cli.line` — one line from the parent context

For simple "set this scalar" cases. Placeholders resolve from the **parent**
dict (sibling keys), not the field's own value.

```yaml
router_id:
  type: str
  cli:
    line: "router-id {router_id}"
```

```
router-id 1.1.1.1
```

### `cli.line_fragments` — one composite line, optional suffixes

The first fragment is the **anchor**; each subsequent fragment is appended
only when its placeholders resolve and any `?guard` passes.

```yaml
maximum_paths:
  type: dict
  cli:
    line_fragments:
      - "maximum-paths {paths}"
      - " ecmp {ecmp}"
```

```
maximum-paths 64 ecmp 64
```

If `ecmp` is unset, the second fragment's `{ecmp}` doesn't resolve → it's
skipped, leaving `maximum-paths 64`.

### `cli.lines` — multiple body lines on one dict

Each entry is rendered independently. Entries can be **strings** OR **arrays
of strings** (treated as `line_fragments` for one composite line).

```yaml
graceful_restart_helper:
  type: dict
  cli:
    lines:
      - "no graceful-restart-helper?enabled == false"
      - "graceful-restart-helper restart-time {restart_time}?enabled == true?restart_time"
      - "graceful-restart-helper long-lived?enabled == true?long_lived?!restart_time"
```

The chained `?guards` (multiple `?...` at the end of one template) are all
ANDed. The third line emits ONLY when `enabled is True` AND `long_lived` is
truthy AND `restart_time` is NOT set.

### `cli.lines` with composite (array) entries

When a single line has multiple optional suffix fragments, use the array form
inside `lines`:

```yaml
# from peer_groups.items.cli.lines
- ["neighbor {name} default-originate?default_originate.enabled == true",
   " route-map {default_originate.route_map}?default_originate.route_map",
   " always?default_originate.always"]
```

Possible outputs depending on data:
```
neighbor PG default-originate
neighbor PG default-originate route-map RM-DO
neighbor PG default-originate always
neighbor PG default-originate route-map RM-DO always
```

This is far cleaner than enumerating all 4 combinations as separate `lines`
entries.

### `cli.line_switch` — pick one template by sibling value

For "switch on a string value" patterns. The case matching the resolved
value of `field` is tried first; if its template fails to render
(placeholder unresolved or guard fails), `default` is tried.

```yaml
# from defs_bgp_additional_paths.schema.yml
bgp_additional_paths:
  type: dict
  cli:
    line_switch:
      field: send
      cases:
        disabled: "no bgp additional-paths send"
        ecmp: "bgp additional-paths send ecmp limit {send_limit}?send_limit"
        limit: "bgp additional-paths send limit {send_limit}?send_limit"
      default: "bgp additional-paths send {send}?send"
```

| `send`     | `send_limit` | output                                       |
| ---------- | ------------ | -------------------------------------------- |
| `disabled` | —            | `no bgp additional-paths send`               |
| `ecmp`     | 8            | `bgp additional-paths send ecmp limit 8`     |
| `ecmp`     | unset        | `bgp additional-paths send ecmp` *(default)* |
| `any`      | —            | `bgp additional-paths send any` *(default)*  |
| unset      | —            | *(skipped)*                                  |

### `cli.gate` — skip the whole field

Truthy guards on the field or its parent. Multiple gates AND together;
`||` inside one expression is OR.

```yaml
labeled_unicast.rib:
  type: dict
  cli:
    gate: "ip.enabled || tunnel.enabled"
    line_fragments:
      - "bgp labeled-unicast rib"
      - " ip?ip.enabled"
      - " route-map {ip.route_map}?ip.enabled"
      - " tunnel?tunnel.enabled"
      - " route-map {tunnel.route_map}?tunnel.enabled"
```

Without the gate the bare `bgp labeled-unicast rib` would render even when
both ip and tunnel are disabled.

### `cli.bool_true_line` / `cli.bool_false_line` — bool fields

```yaml
redistribute_internal:
  type: bool
  cli:
    bool_true_line: "bgp redistribute-internal"
    bool_false_line: "no bgp redistribute-internal"
```

### `cli.item_lines` — flat lines per list item

Templates resolve against each item's context. `{_item}` is the value for
scalar list items.

```yaml
both:
  type: list
  cli:
    item_lines:
      - "route-target both {_item}"
  items: { type: str }
```

```
route-target both 100:100
route-target both 200:200
```

### `cli.item_line_fragments` — one composite line per item

Per-item version of `line_fragments`. Used heavily by `aggregate_addresses`
and `listen_ranges`.

```yaml
aggregate_addresses:
  type: list
  cli:
    item_line_fragments:
      - "aggregate-address {prefix}"
      - " as-set?as_set"
      - " summary-only?summary_only"
      - " attribute-map {attribute_map}"
      - " attribute rcf {attribute.rcf}"
      - " match-map {match_map}"
      - " advertise-only?advertise_only"
```

### `items.cli` — recurse into each item as its own render context

The big one. When a list's `items` schema has its own `cli` block, the
renderer iterates the list and calls `render_schema_field` recursively with
each item as the data context. This lets each item open a section, emit a
multi-line body, recurse further — anything available to a top-level dict.

```yaml
vlans:
  type: list
  primary_key: id
  cli:
    item_gate: id           # skip vlans without an id
  items:
    type: dict
    cli:
      section: "vlan {id}"
      section_only_if_content: false
      lines:
        - "rd {rd}?rd"
        - "rd evpn domain {rd_evpn_domain.domain} {rd_evpn_domain.rd}?rd_evpn_domain.domain?rd_evpn_domain.rd"
    keys:
      route_targets:        # children with their own cli render under the section
        type: dict
        keys:
          both:
            type: list
            cli: { item_lines: ["route-target both {_item}"] }
          ...
      eos_cli:
        type: str
        cli: { raw_lines: { separator: "!" } }
```

```
!
vlan 100
   rd 100:100
   rd evpn domain remote 100:101
   route-target both 100:100
   !
   address-family ipv4
      no neighbor X activate
```

`peer_groups` and `neighbors` use the same recursion to render every per-entity
line as `lines` templates with `neighbor {name} ...` typed in.

`item_lines` / `item_line_fragments` on the LIST take precedence over
`items.cli` if both are present.

### `cli.section` — open a sub-block with header + body

```yaml
items:
  type: dict
  cli:
    section: "vlan {id}"             # the header line
    separator: true                   # emit "!" before header (default true)
    section_only_if_content: false    # render header even with empty body (default true)
    lines:
      - "rd {rd}?rd"
```

Body order: any sibling `lines` / `line_fragments` / `line_switch` fire first,
then annotated children.

### `cli.raw_lines` — emit a string verbatim

For free-text user content like `eos_cli`. Each `\n`-split line is emitted
at the current indent. Optional `separator` literal is inserted before.

```yaml
eos_cli:
  type: str
  cli:
    raw_lines:
      separator: "!"
```

```
!
address-family ipv4
   no neighbor X activate
```

### `cli.item_gate` / `cli.sort_key` — list filtering & ordering

Modifiers for any list-iterating annotation:

```yaml
peer_groups:
  type: list
  primary_key: name        # AvdIndexedList — natural-sorted by name
  cli:
    item_gate: name        # skip peer-groups missing a name
```

`sort_key` is for non-indexed lists; AvdIndexedList always sorts by primary
key.

---

## 4. Template syntax

### Placeholders

- `{var}` — current model attribute
- `{parent.child.grandchild}` — dot-notation traversal
- `{var|filter_name}` — pipe filter. Built-in: `hide_passwords`. Register
  more via `register_template_filter(name, fn)`.

```yaml
# Real example: renders "neighbor PG password 7 <removed>" when masking is on
- "neighbor {name} password {password_type} {password|hide_passwords}?password?password_type"
```

### Guards (suffix `?...`)

Trail at the end of any template; chain multiple with consecutive `?`s. All
must pass for the line to render.

| syntax                    | meaning                                  |
| ------------------------- | ---------------------------------------- |
| `?path`                   | `path` is truthy                         |
| `?!path`                  | `path` is NOT truthy                     |
| `?path == 'literal'`      | string equality                          |
| `?path != 'literal'`      | string non-equality                      |
| `?enabled == true`        | bool equality                            |
| `?enabled != false`       | bool non-equality                        |
| `?path == 42`             | integer equality                         |
| `?path == null`           | explicit None check                      |
| `?a || b || c`            | OR within one guard                      |
| `?guard1?guard2?guard3`   | chained — all ANDed                      |

The `?path` form supports dot-notation: `?bfd_timers.interval`.

### Gate expressions (in `cli.gate` and `cli.item_gate`)

Same syntax as guards, plus:
- `^path` evaluates against the **parent** context: `^enabled`, `!^enabled`
- A list of expressions ANDs them: `gate: ["enabled", "!^enabled"]`

---

## 5. Worked example end-to-end

Given this structured config:

```yaml
router_bgp:
  as: "65000"
  router_id: "1.1.1.1"
  bgp:
    additional_paths: { receive: true, send: ecmp, send_limit: 8 }
  peer_groups:
    - name: PG-FABRIC
      remote_as: "65000"
      send_community: all
      password: "deadbeef"
      rib_in_pre_policy_retain: { enabled: true, all: true }
  neighbors:
    - { ip_address: "10.0.0.10", peer_group: PG-FABRIC, bfd: false }
  vlans:
    - id: 100
      rd: "100:100"
      route_targets: { both: ["100:100"] }
```

The renderer produces:

```
!
router bgp 65000
   router-id 1.1.1.1
   bgp additional-paths send ecmp limit 8
   bgp additional-paths receive
   neighbor PG-FABRIC peer group
   neighbor PG-FABRIC remote-as 65000
   neighbor PG-FABRIC rib-in pre-policy retain all
   neighbor PG-FABRIC password 7 deadbeef
   neighbor PG-FABRIC send-community
   neighbor 10.0.0.10 peer group PG-FABRIC
   no neighbor 10.0.0.10 bfd
   !
   vlan 100
      rd 100:100
      route-target both 100:100
```

Walking through what fired:

| line                                     | annotation                                                                |
| ---------------------------------------- | ------------------------------------------------------------------------- |
| `router bgp 65000`                       | hardcoded in `RouterBgpBlock.render()` (orchestrator)                     |
| `router-id 1.1.1.1`                      | `router_id.cli.line: "router-id {router_id}"`                             |
| `bgp additional-paths send ecmp limit 8` | `bgp_additional_paths.cli.line_switch` case `ecmp`                        |
| `bgp additional-paths receive`           | `receive.cli.bool_true_line`                                              |
| `neighbor PG-FABRIC peer group`          | `peer_groups.items.cli.lines[0]` — bare anchor                            |
| `neighbor PG-FABRIC remote-as 65000`     | `peer_groups.items.cli.lines[N]` — `?remote_as` guard passed              |
| `neighbor PG-FABRIC rib-in ...all`       | composite entry — anchor + ` all` fragment because `.all` is true         |
| `neighbor PG-FABRIC password 7 deadbeef` | `?!password_type` branch (no explicit type → default `7`)                 |
| `neighbor PG-FABRIC send-community`      | `?send_community == 'all'` branch                                         |
| `neighbor 10.0.0.10 peer group PG-FABRIC` | `neighbors.items.cli.lines[0]` — `?peer_group` guard passed              |
| `no neighbor 10.0.0.10 bfd`              | `?bfd == false?peer_group` — only emitted because peer_group is set      |
| `! / vlan 100`                           | `vlans.items.cli.section: "vlan {id}"` (`!` from `separator: true`)       |
| `rd 100:100`                             | `vlans.items.cli.lines` — `?rd` guard                                     |
| `route-target both 100:100`              | `route_targets.both.cli.item_lines` — recursion into vlan's children      |

---

## 6. Adding a new field — the checklist

When you add a new BGP CLI line:

1. **Add the field** to `schema_fragments/router_bgp.schema.yml` under the
   right parent.
2. **Add a `cli:` block** using the simplest annotation that fits (see
   §2 dispatch order to pick).
3. **Run** `cd avd/python-avd && make compile-schemas` to rebuild the pickle.
4. **Verify** by loading the pickle and running `RouterBgpBlock` on a test
   config.

If you're adding a NEW `cli.X` key (not just a new field), you must also
update three files together:

- the engine: `pyavd/_eos_cli_config_gen/schema_cli_generators/base.py`
- the IDE meta-schema: `pyavd/_schema/avd_meta_schema.json`
- the build-time Pydantic model: `schema_tools/metaschema/meta_schema_model.py`

Skip any of these and the build fails (Pydantic forbids extras) or your IDE
flags every use site.

---

## 7. Anti-patterns to avoid

- **Don't put `cli:` on a `$def` fragment if its CLI text differs across use
  sites.** The annotation is shared by every reference. If the global vs
  per-entity rendering of the same field differs (e.g. `bgp additional-paths
  send X` vs `neighbor X additional-paths send Y`), put the annotation at the
  use site instead.
- **Don't enumerate all 2^N combinations** of optional suffixes as separate
  `lines` templates. Use the composite array form (`["anchor", " opt?guard",
  ...]`) — the engine appends fragments conditionally.
- **Don't write a custom render method** until you've checked whether the
  pattern fits an existing annotation. Most "switch on a value with optional
  suffixes" cases are `line_switch` + composite lines.
- **Don't load the YAML in tests** — load the pickle. Annotations on `$def`
  fragments are invisible in the unresolved YAML.
