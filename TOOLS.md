# Tool reference — uefn-mcp-server-extended

**48 tools.** 28 came from upstream; 20 are new in this fork. Every new tool below
was verified against a live UEFN editor, and where a claim is unproven it says so.

Read `MCP_UPGRADE.md` §0 first if you are going to write anything. It lists five traps
that produce confident false passes, all of which were hit during development.

---

## The one rule that matters most

**There are TWO device write paths and they do not cross over.**

| Device kind | What you write | Tool |
|---|---|---|
| Creative device (`Device_*`, Island Settings, spawners) | Creative options | `set_device_option` |
| Verse device (`VerseDevice_C`) | Verse `@editable`s | `set_verse_editable` |

Using the wrong one **fails silently** at the engine level, so each tool refuses the
other's device kind by construction and names the right one.

---

## New in this fork

### Devices

| Tool | What it does |
|---|---|
| `list_devices` | Every configurable Creative actor, excluding the ~1000 static props. `kind` separates first-class devices from other option-bearing actors like player spawners. |
| `get_device_options` | All Details-panel options on a Creative device, with values. |
| `set_device_option` | **Writes** a Creative device option, via the native property behind it. Verified on disk for string, float, int and bool. |
| `get_verse_editables` | A Verse device's `@editable` names, types and live values. |
| `set_verse_editable` | **Writes** one Verse `@editable`. JSON-encodes for you, and verifies by reading back — it raises rather than reporting a success that did not happen. |

### Seeing and verifying

| Tool | What it does |
|---|---|
| `take_screenshot` | High-res viewport capture. Waits for the file to land, so `exists: true` means it is really on disk. |
| `raycast` | Traces a line and reports whether solid geometry is there. The behavioural-verification primitive. **Limit:** this build's `HitResult` exposes no fields to Python, so it reports hit/no-hit but not where or what. |
| `validate_assets` | Runs Fortnite's own validators. `PRE_SUBMIT` is the strictest. A pre-flight, **not** a publish guarantee. |
| `read_log` | Reads the editor log **off disk**, from the MCP process. Never stale, costs the editor nothing, and works when the editor is hung or the listener is dead. |
| `read_crashes` | Recent crash reports with call stacks. Works after the editor has died, which is the only time it matters. |

### Finding things without blowing your context

| Tool | What it does |
|---|---|
| `find_actors` | Substring search by label / class / path. Returns `{path, label, class}`. |
| `get_all_actors` | Now slim by default, with `summary_only`, `limit`/`offset` and opt-in `detail`. |

> Measured on TheScar: the old fat shape returned **655 KB (~164k tokens)** for 1108
> actors. `summary_only` is **1.9 KB**. Prefer summaries and filters; a full listing is
> still ~250 KB and should basically never be requested.

### Reaching the engine's own 168 tools

| Tool | What it does |
|---|---|
| `ue_tools_search` | Ranked search over 12 toolsets / 168 tools. Indexed once at startup, answered from RAM. |
| `ue_tool_describe` | One tool's full `inputSchema`. |
| `ue_tool_call` | Dispatches it. Carries the denylist and the write allow-list. |

Reaches UMG, Niagara, physics assets, gameplay tags, editor-app operations and Verse
fields — capability with no dedicated tool here, for ~600 tokens of schema.

### Safety and durability

| Tool | What it does |
|---|---|
| `denylist` | Shows what is refused before reaching the engine: PIE control, `StopServer`, `EnablePythonInUEFN`, toolset unregistration, and console commands that quit or force GC. |
| `capability_manifest` | Snapshots ~40 named entry points and diffs against a stored baseline. Run it first when something that used to work stops working. |
| `supported_only` | Fallback mode. Disables the reflection-backed tools while documented ones keep working. Turns itself on if the manifest reports losses. |

### Efficiency

| Tool | What it does |
|---|---|
| `batch` | Runs several commands in one editor tick, optionally as a single undo step. |
| `console_command` | Runs an Unreal console command. Read output with `read_log`. |
| `pilot_actor` | Attaches the viewport camera to an actor. |

---

## Deliberately not provided

- **`play_mode` / PIE.** The API exists, and entering play mode triggers the world change
  that kills the in-process listener. Availability is not a reason to ship it.
- **A `.uefnproject` writer.** The editor overwrites that file within ~100 ms while open,
  **and** regenerates it from actor state on save. Write the actor instead.
- **Anything built on `ToolsetLibrary.set_object_properties`.** It returns `True`, and with
  `bypass_container_check=YES` it even makes two separate read APIs agree — and it still
  does not survive the save. Refuted four ways; see `MCP_UPGRADE.md` §13e.
- **`reflect`.** Blind reflection enumeration crashed the editor once. It needs a capped,
  never-call design and a human present.

## Unproven — do not claim these

- That a write survives a Verse rebuild that **renames** an `@editable` or moves its class.
  Only code-body rebuilds are proven safe (§0 TRAP 5).
- That UEFN's **publish** pipeline accepts an island authored this way. Validation is a
  pre-flight, not the publish gate.
