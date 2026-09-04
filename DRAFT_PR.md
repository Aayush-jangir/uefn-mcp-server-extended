# DRAFT pull request — NOT SUBMITTED

**Status: draft only. Do not open this PR without Aayush's say-so.**

Target: `KirChuvakov/uefn-mcp-server`
Source: `Aayush-jangir/uefn-mcp-server-extended`, branch `extended-editor-control`

Open questions to settle before sending — see the bottom of this file.

---

## Title

Extended editor control: device writes, Verse `@editable`s, engine tool discovery, and safety rails

## Body

Hi — thanks for this server. The listener design (the `@_register` decorator, the
tick-queued main-thread marshalling, `_serialize`) made all of the below straightforward
to build, and I did not have to change any of it.

I have been using it to drive a published island and ended up adding 20 tools. Happy to
split this into smaller PRs, drop parts, or just leave it as a fork if it is more than you
want to maintain — no expectations either way.

Everything below was verified against a live UEFN editor on `++Fortnite+Release-42.10`,
CL 57566230. Where something is unproven, it says so in the code and the docs.

### The headline: Creative device options are writable

The README currently treats device options as read-only, and `set_user_option_value` does
indeed no-op without a `PlayerController`. But the options are **mirrored on native
UPROPERTYs on the actor**, and writing those works and persists:

```python
actor.set_editor_property("label_override", "NewLabel")   # then save the level
```

`set_device_option` wraps this and resolves the option name to its native property. **529
of 572 options (92%)** across 11 devices resolve; the rest are function-style options
(events like `Reset Progress`) which correctly have nothing to write.

Verified on disk, not by read-back: written, saved, then the marker was found in the
saved `__ExternalActors__` `.uasset`. On Island Settings it even propagates out into the
`.uefnproject`.

### Verse `@editable`s are readable and writable too

`get_user_option_values()` does not surface them — a `VerseDevice_C` returns only its three
base Creative options — but `DeviceToolset` does, via `call_method` on the CDO:

```python
cdo.call_method("GetDeviceProperties", args=(device, ["rowsToShow"]))   # -> {"rowsToShow": 5}
cdo.call_method("SetDeviceProperty",  args=(device, "rowsToShow", "7")) # JSON-encoded value
```

`get_verse_editables` / `set_verse_editable` wrap this. **The value must be JSON-encoded** —
a bare string is silently discarded with no error — and `SetDeviceProperty` returns `None`
whether or not it worked, so the tool encodes for you and verifies by reading back rather
than trusting the return.

**The two write paths do not cross over**, and using the wrong one fails silently, so each
tool refuses the other's device kind and names the correct one.

### Engine tool discovery — 168 more tools for ~600 tokens

`unreal.ToolsetRegistry` is available with the Beta Access flag **off** and
`get_all_toolset_json_schemas()` returns 470 KB describing 12 toolsets and 168 tools, each
with a full `inputSchema`. `ue_tools_search` / `ue_tool_describe` / `ue_tool_call` index it
once at startup and answer from RAM. That reaches UMG, Niagara, physics assets, gameplay
tags and Verse fields without adding 168 tool definitions to every client's context.

### Result shaping — the token fix

List tools were fat-serialising every actor. On my island `get_all_actors` returned **655 KB
(~164k tokens) for 1108 actors**, most of a context window in one call. List tools now
return `{path, label, class}` with opt-in `detail`, plus paging and a `summary_only` mode
that costs 1.9 KB. This is the change I would most encourage you to take even if you take
nothing else.

### Safety rails

Because `call_method` reaches tools Epic's own `ToolsetPolicy` excludes, this adds:

- a **denylist** refusing PIE control, `StopServer`, `EnablePythonInUEFN` and toolset
  unregistration at the dispatcher, never at the engine;
- **allow-list-first for writes** in `ue_tool_call` — reads run freely, mutating tools must
  be recorded deliberately;
- a **capability manifest** that snapshots ~40 named entry points and diffs them at startup,
  so a version bump reads as "DeviceToolset went away" rather than a mystery;
- **`--supported-only` fallback**, which disables the reflection-backed tools and keeps the
  documented ones working — and turns itself on automatically when the manifest reports
  losses.

### Other additions

`take_screenshot` (waits for the file, and keeps the `AutomationEditorTask` referenced —
dropping it silently cancels the capture), `raycast`, `find_actors`, `batch`,
`validate_assets`, `console_command`, `pilot_actor`, and `read_log` / `read_crashes` which
read the `Saved/` tree **from the MCP process** rather than the listener, so they work when
the editor is hung or the listener is dead.

### Two things I deliberately did not add

- **PIE control.** The API is right there and entering play mode triggers the world change
  that kills the in-process listener.
- **A `reflect` tool built on `dir()`.** Enumerating reflected UObject members crashed my
  editor during development. If you want one, it needs a hard cap and must never call the
  members it lists.

### Compatibility notes

- Ports moved to **8775–8780** in my fork so both servers can run side by side; that is a
  fork-local choice and should be reverted to 8765 before merging.
- Requires `mcp<2.0.0` (2.x drops `mcp.server.fastmcp.FastMCP`).
- `DeviceToolset` and `ToolsetRegistry` are UEFN-specific. The tools that use them degrade
  cleanly via the capability manifest, but I have not tested this against vanilla UE5.

---

## Before sending — decide these

1. **Revert the port split to 8765–8770?** Almost certainly yes for upstream.
2. **Split into smaller PRs?** Result shaping alone is a clean, uncontroversial first PR;
   the device-write work is the big one; the triad is the most speculative.
3. **Absolute paths.** `snapshots/` paths and `G:/UEFN/...` are hard-coded in the manifest
   and write-allow-list. Must be made relative to the repo root before submitting.
4. **The `snapshots/` directory** contains TheScar-specific data (99 `@editable`s, drift
   report, unattended log). **Strip it from the PR** — it is project data, not server code.
5. Confirm the tone reads as a contribution rather than a rewrite. It is a lot of surface
   area for a maintainer to take on.
