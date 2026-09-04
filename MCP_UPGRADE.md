# UEFN MCP Upgrade — working document

**Started 2026-09-04.** Read this before touching anything. Everything in §2 was
measured in a live UEFN editor on that date, not inferred from docs.

---

## 0. TRAPS AND HARD RULES — READ BEFORE WRITING A PROBE

Every one of these was hit in this project. They all look like success.

### TRAP 1 - `set_object_properties` lies. Read-back through the writing API is NOT evidence.

`ToolsetLibrary.set_object_properties` on a Creative device's `ToyOptionsComponent`:

| What you check | What it says |
|---|---|
| the return value | **`True`** |
| read back via `ToolsetLibrary.get_object_properties` | **changed** |
| read back via `device.get_user_option_value(name)` | **STILL THE OLD VALUE** |
| `actor.get_actor_label()` | **STILL THE OLD VALUE** |

**THE TWO REPRESENTATIONS DISAGREE.** `set_object_properties` writes a parallel property bag
that the device's real option state never reads. Verify through the API you wrote with and you
will report a working write path that does not exist.

**Rule: the writing API's own read-back is worth nothing. Disk is the only arbiter.**

**The write path that DOES work:** `actor.set_editor_property(<native name>, value)` then save.
See §2b and the `set_device_option` tool.
Save, then grep the `.uasset` under `__ExternalActors__`. Verified 2026-09-04 - see §11 P4.

### TRAP 1b - EVEN TWO APIs AGREEING IS NOT EVIDENCE

The worst case measured in this project. `ToolsetLibrary.set_object_properties` with
`bypass_container_check=YES` (§13e, variant D):

| What you check | What it says |
|---|---|
| the return value | **`True`** |
| read back via `ToolsetLibrary.get_object_properties` | **changed** |
| read back via `device.get_user_option_value()` | **changed** |
| the label shown in the editor | **visibly changed** |
| **the saved `.uasset` after save** | **UNCHANGED - the value silently reverted** |

Two independent APIs agreed, and the editor UI agreed, and it still did not persist.

**Rule: cross-API agreement is not evidence. A visible editor change is not evidence.
Save, then grep the `.uasset`.**

### TRAP 2 - a dropped screenshot task cancels the capture silently

`AutomationLibrary.take_high_res_screenshot` returns an `AutomationEditorTask`. **Discard it and
Python garbage-collects it, which cancels the capture.** No exception, no error, no log line,
no file - the call simply "succeeds" and nothing is ever written.

The listener keeps every task in `unreal._mcp_screenshot_tasks` for exactly this reason.
**A future cleanup that deletes that registry as a pointless variable will silently break all
screenshots.** It is load-bearing. See `_screenshot_tasks()` in `uefn_listener.py`.

### TRAP 3 - the `.uefnproject` is an OUTPUT, not an input

**Do not build a `.uefnproject` writer.** Two independent reasons, both measured:

1. **UEFN rewrites `*.uefnproject` while the editor is open** - an edit made with UEFN running was
   overwritten **97 milliseconds later**. Project-file edits only stick with the editor **fully
   closed**.
2. **It is generated from actor state anyway.** The direction of authority is:

   `native UPROPERTY` -> `device-option view` -> saved `.uasset` -> `.uefnproject`

   Writing the Island Settings actor and saving rewrote `maxPlayers`, `maxSocialPartySize`,
   `maxTeamCount` and `maxTeamSize` in the project file by itself (§13d).

**Write the actor, not the file.**

### ENVIRONMENT RULE - Python is PER-PROJECT

Gated by `dataSets.experimental.pythonExperimental.bEnablePythonForProject` in the
`.uefnproject`. Without it **Tools -> Execute Python Script does not exist** and the listener
cannot start. The Tools menu's "Enable Python" checkbox does **not** persist it - it must be added
to the file by hand, **with the editor closed** (see Trap 3). Any new sandbox project needs this
step first.

### HARD RULE - publishing is NOT scriptable from this bridge

Checked properly on 2026-09-04, so the next session does not repeat the search:

- The `ToolsetRegistry` corpus (470 KB, 12 toolsets, **168 tools**) contains **no publish tool**.
  Searching every tool name and description for publish/upload/version returned 4 hits, **all
  false positives** matching "conversion" (`ListConversionFunctions`, `FixupMVVMData`, …).
- Named subsystem candidates **all absent**: `FortCreativePublishSubsystem`,
  `FortPublishSubsystem`, `ValkyriePublishSubsystem`, `FortUGCPublishSubsystem`,
  `FortProjectSubsystem`.

Publishing is a GUI wizard, and it is outward-facing and account-affecting, so it stays a human
action. **Do not go looking for a scripted publish path; there isn't one.**

**And know what a private version does and does not prove.** Publishing a *private version* runs
the real build, cook, validation and upload pipeline - which is the actual risk surface for
MCP-authored actors, and settles "does the publish pipeline accept them". It does **NOT** run
Epic's human content review; that happens only on public release. So a clean private build must
never be written up as "publish accepts this" without that qualifier. Provenance of a property
value is not something moderation inspects; the build pipeline is.

### The general form of all of these

Both traps share one shape: **the call reports success and something reads back correct, while
the thing you actually wanted never happened.** This is what `CLAUDE.md`'s "verify behaviourally,
never by reading state back" is defending against. Drive the result through a *different* path
than the one that produced it - a second API, the disk, the Details panel, the viewport.

---

## 1. The goal, in Aayush's words

> "change the MCP or update it by ourselves in a way that our UEFN is more connected and
> accessible as Unity as right now a lot of things are not accessible from the MCP connection."

**The benchmark is the Unity MCP server.** This is the sole priority — nothing else on
The Scar proceeds until Claude can do "almost everything in UEFN" through this bridge.

**Hard constraints:**
- **Nothing may be added to `G:\UEFN\TheScar\Content\`.** That folder gets bundled at publish.
  This is a standing decision (see `project_uefn_mcp` memory) — the `init_unreal.py` auto-start
  hook was rejected for exactly this reason. Do not re-propose it.
- The upgraded server must keep the island **safe under Epic's publishing rules from day one**.
- One Editor, one bridge. **Never run two Claude sessions against UEFN at once.**

## 2. VERIFIED probe results — 2026-09-04

Measured by calling the live editor. Trust these over any web-sourced API list.

### 2a. CONFIRMED AVAILABLE — these are the upgrade

| Capability | API | Note |
|---|---|---|
| **Play mode** | `LevelEditorSubsystem.editor_request_begin_play()` / `editor_request_end_play()` / `is_in_play_in_editor()` / `editor_play_simulate()` | **The single biggest gap vs Unity MCP, and it is available.** `is_in_play_in_editor()` returned `False` cleanly |
| **Pilot/possess actor** | `pilot_level_actor()` / `eject_pilot_level_actor()` / `get_pilot_level_actor()` | |
| **Console commands** | `SystemLibrary.execute_console_command(world_context_object, command, specific_player=None)` | needs a valid world context |
| **Screenshots** | `AutomationLibrary.take_high_res_screenshot(res_x, res_y, filename, camera=None, …)` | also `take_automation_screenshot` |
| **Undo / transactions** | `unreal.ScopedEditorTransaction` | present. `begin_transaction`/`end_transaction` are **absent** — use the scoped form |
| **Validation** | `FortEditorValidatorSubsystem` and `FortExposedContentValidationSubsystem` both **acquire successfully**; expose `validate_assets_with_settings`, `is_asset_valid`, `is_object_valid`, `show_validation_report`, `create_editor_validation_world` | This is the route to scripted pre-publish checks |
| **Map check** | `MapCheckSubsystem` — `log_map_check_error/warning/info` | |
| **Subsystems generally** | 208 `*Subsystem` classes exposed, incl. `SubobjectDataSubsystem`, `EditorUtilitySubsystem`, `LayersSubsystem`, `ContentBrowserDataSubsystem`, `WorldPartitionSubsystem`, `DataLayerEditorSubsystem`, `AssetEditorSubsystem` | |
| **UEFN-specific** | `FabricIslandSettingsWorldSubsystem`, `FabricGlobalVariablesSubsystem`, `FortExposedAssetSubsystem`, `FortGlobalActorRegistrySubsystem`, `RealTimeThumbnailSubsystem` | unexplored, likely valuable |

### 2b. DEVICE OPTIONS — **SOLVED 2026-09-04. Read AND write.**

> **THE RECIPE:** write the **native UPROPERTY** behind the option with
> `actor.set_editor_property(native_name, value)`, then **save the level**. The device-option
> layer is a *view* over native properties, so the option, the Details panel, the saved
> `.uasset` and (for Island Settings) the `.uefnproject` all follow. Shipped as the
> **`set_device_option`** tool. 92% of options map to a native property; the rest are
> function-style events with nothing to write. Full evidence in §13d/§13e/§13h.
>
> **Do NOT use `ToolsetLibrary.set_object_properties`** — refuted four ways (§13e).

The original 2026-09-04 finding is kept below for the record. Its reading half is still
correct; its writing half is **wrong** and is struck through.

`TheScar\CLAUDE.md` §4 already states this precisely: readable via `get_user_option_values()`,
not writable. **The probe confirms §4 exactly — do not distrust that doc.** (An earlier note in
this file wrongly called §4 "half wrong"; that was a compression error in conversation, not an
error in §4.)

Every Creative device actor exposes:

```python
device.get_user_option_values()       # -> Map[str, str]  ALL options + values.  WORKS.
device.get_user_option_value(key)     # -> str            WORKS.
device.get_user_option_definitions()  # -> the ToyOptionsComponent
device.set_user_option_value(player_controller, key, value)     # -> bool
device.set_user_option_values(player_controller, Map[str,str])  # -> bool
```

Reading a `Device_Barrier_V2_Placed_C` returned **all 23 options with real values** —
`BlockWeaponFire=True`, `BaseVisibleDuringGame=False`, `EnabledOnPhase="Gameplay Only"`,
`ZoneShape=Box`, `LabelOverride=TrophyBarrier_W`, plus function-style options
(`Enable`, `Disable`, `AddPlayerToIgnoreList`, …).

~~**Writing is genuinely blocked.**~~ **WRONG — corrected §13.** `set_user_option_value` does
take a `PlayerController` and does no-op with `None`, and the `ToyOptionsComponent` does expose no
data properties. But the conclusion drawn from that was false: **the option values ARE mirrored in
native UPROPERTYs on the actor** — `LabelOverride` → `label_override`, `Matchmaking_MaxPlayersPerSession`
→ `mms_player_count`, and so on for 529 of 572 measured options. That mirror is the write path.

This sentence is the exact claim that kept the problem open, so it is left visible rather than
deleted: *"the option values are not mirrored in any native UPROPERTY on the actor"* was inferred
from `ToyOptionsComponent` having no properties, without checking the **actor** itself.

### 2c. ~~CONFIRMED BLOCKED~~ — SUPERSEDED BY §11 (P2). The Verse claim below is WRONG.

- **Verse `@editable` values are invisible.** A `VerseDevice_C` returns only the three base
  Creative options — `Enabled at Game Start`, `LabelOverride`, `VisibleInGame`. The Verse
  `@editable`s set in the Details panel are **not** in `get_user_option_values()`.
  CLAUDE.md §4 is **correct** on this one.
- **No Verse classes exposed at all:** `VerseSubsystem`, `VerseCompiler`, `VerseDevice`,
  `FortVerseDevice` all absent. Also absent: `FortCreativeDevice`, `CreativeDeviceBase`,
  `KismetSystemLibrary`.

### 2d. Island Settings read cleanly (native properties, not device options)

`Device_ExperienceSettings_V2_UEFN_C` gave: `mms_player_count=16`, `max_players=16`,
`use_custom_matchmaking_settings=False`, `join_in_progress_behavior=SPAWN_DURING_NEW_ROUND`,
`mms_backfill=ENABLED`, `teams=TeamIndex/4`.

### 2e. Devices present in The Scar

`Device_Barrier_V2_Placed_C` ×4, `Device_ItemGranter_V2_C` ×8, `Device_HUDMessage_V2_C` ×3,
`Device_MutatorVolume_V2_C` ×2, `VerseDevice_C` ×9, and one each of
`Device_ExperienceSettings_V2_UEFN_C`, `Device_Timer_V2_C`, `Device_EliminationManager_V3_C`,
`Device_ScoreManager_V2_C`, `Device_Accolades_V2_C`, `Device_GameEnd_C`,
`Device_Powerup_VisualEffect_V2_C`, `Device_PlayerMarker_V2_C`, `Device_CRD_AudioPlayer_C`.

## 3. Current architecture

```
Claude Code --stdio--> mcp_server.py (605 lines, external)
                            |
                          HTTP :8765
                            |
                       uefn_listener.py (1252 lines, INSIDE the UEFN editor process)
```

Listener pattern is clean and easy to extend:
`@_register("name")` decorator → `_HANDLERS` dict → `_dispatch(command, params)`, with
`_run_on_main_thread()` marshalling every `unreal.*` call through an editor tick callback, and a
`_serialize()` helper. **Adding a tool = one `_cmd_*` function in the listener + one `@mcp.tool()`
wrapper in `mcp_server.py`.**

28 tools today: ping, status, shutdown, get_log, execute_python, get_all_actors,
get_selected_actors, spawn_actor, delete_actors, set_actor_transform, get_actor_properties,
set_actor_properties, select_actors, focus_selected, get_editor_log, list_assets, get_asset_info,
get_selected_assets, rename_asset, delete_asset, duplicate_asset, does_asset_exist, save_asset,
search_assets, get_project_info, save_current_level, get_level_info, get_viewport_camera,
set_viewport_camera.

**The listener is not persistent** — restart it inside UEFN after every editor restart via
Tools → Execute Python Script → `G:\UEFN\uefn-mcp-server\uefn_listener.py`.

**Register the MCP server by absolute venv path, never bare `python`** — this machine has three
`python.exe` on PATH and the wrong one gives an opaque `-32000: Connection closed`:

```bash
claude mcp add --scope user uefn -- G:/UEFN/uefn-mcp-server/.venv/Scripts/python.exe G:/UEFN/uefn-mcp-server/mcp_server.py
```

Real stderr behind any `-32000` lives in
`%LOCALAPPDATA%\claude-cli-nodejs\Cache\<project-slug>\mcp-logs-<server>\*.jsonl`.

## 4. Open questions for the research workflow

Launched 2026-09-04 in the originating session (run `wf_7b249d41-79f`). It covers:

1. **Epic's first-party "Unreal MCP" for UEFN** — announced in a Fortnite news post Aug 2026.
   **If this is real and capable it changes everything downstream** — adopt, extend, or ignore?
2. Full Unity MCP tool inventory, mapped to UEFN equivalents.
3. Other UE MCP servers and their techniques.
4. **A write path for device options** — `SubobjectDataSubsystem`, Editor Utility Blueprint bridge,
   Remote Control API, direct asset serialization, Slate automation.
5. UEFN-specific: Verse build triggering, Push Changes, scripted validation, playtest launch.

## 5. Design questions not yet decided

- **Consolidated `manage_*` verbs (Unity style) vs one-tool-per-operation.** Every tool schema
  costs client tokens, which argues for consolidation. Not yet decided.
- How much to gate behind `execute_python` (already a universal escape hatch) versus first-class
  tools. First-class tools are discoverable and typed; `execute_python` is unlimited but opaque.
- Whether to fork upstream or maintain a local divergence. Currently a local clone with
  uncommitted modifications to `uefn_listener.py`.

## 6. Testing rule

From `CLAUDE.md`: **verify behaviourally, never by reading state back.** For this project that
means: enter play mode and confirm `is_in_play_in_editor()` flips *and* the editor visibly changes;
take a screenshot and open the file; run validation and read the report. Reading a value back has
produced confident false passes repeatedly on this project.

---

## 7. THE DEV FORK — set up 2026-09-04

**Repo:** https://github.com/Aayush-jangir/uefn-mcp-server-extended (fork of KirChuvakov/uefn-mcp-server)
**Local:** `G:\UEFN\uefn-mcp-server-extended`
**Branch:** `extended-editor-control` (pushed)
**Remotes:** `origin` = the fork, `upstream` = KirChuvakov's original

### Two servers now run side by side

| | Original (fallback) | Extended (where we work) |
|---|---|---|
| Folder | `G:\UEFN\uefn-mcp-server` | `G:\UEFN\uefn-mcp-server-extended` |
| MCP name | `uefn` | `uefn-extended` |
| Port range | **8765–8770** | **8775–8780** |

The port split is deliberate: the listener picks the first free port in its range and
`mcp_server.py` scans that same range, so **without the split the two servers would discover each
other's listener.** Do not "tidy" them back to the same range.

`.venv` is Python **3.13.14** with **mcp 1.29.1** (2.x drops `mcp.server.fastmcp.FastMCP`).
Registered with:

```bash
claude mcp add --scope user uefn-extended -- G:/UEFN/uefn-mcp-server-extended/.venv/Scripts/python.exe G:/UEFN/uefn-mcp-server-extended/mcp_server.py
```

**`claude mcp list` showing `✔ Connected` only means the stdio process launched.** It does NOT
mean a listener was found inside UEFN. The real check is calling `ping` on that server.

### Running the extended listener

Inside UEFN: **Tools → Execute Python Script →**
`G:\UEFN\uefn-mcp-server-extended\uefn_listener.py`
Needed after **every** UEFN restart — the listener is not persistent.
Running both listeners at once is fine; they take different ports.

## 8. CRASH — 2026-09-04, read before probing

UEFN crashed during the capability probing. Crash report
`UECC-Windows-81EA66F740921428E2FA6EB3D32D86D0_0000`:

```
Unhandled Exception: EXCEPTION_ACCESS_VIOLATION reading address 0x00005f5f7365738b
CallStack: python311 / ntdll
```

Top frame is UEFN's **embedded Python interpreter**, 49 minutes into a probing run.

**Cause: blind `dir()` reflection sweeps.** The probes enumerated hundreds of reflected UObject
members and called `get_editor_property` / `get_editor_subsystem` across them. `TheScar\CLAUDE.md`
§4 already recorded that this pattern was abandoned once before; it was repeated anyway.

**RULE: never enumerate arbitrary reflected members through the embedded interpreter.**
Probe named candidates only, with `hasattr` / `getattr`, in small batches, and read the docstring
rather than calling the function to learn its signature. Enumerating UObject reflection is **not**
a safe read-only operation — it can and did take the editor down.

---

## 9. CORRECTIONS — 2026-09-04, after the research workflow

A 12-agent research workflow ran, and its judge **re-probed the live editor independently**.
It contradicts §2 in three places. **Its claims are NOT yet verified by this session** — the
listener died before I could re-check them. Treat everything here as HIGH-CONFIDENCE-UNVERIFIED
and re-run the probes in §9d before building on them.

Full plan: `IMPLEMENTATION_PLAN.md`. Losing designs: `docs/design-a-pragmatic.md`,
`docs/design-b-completeness.md`.

### 9a. Engine version was wrong

**The editor is `++Fortnite+Release-42.10`, CL 57566230** — not 41.30. "41.30" is the
`compatibilityVersion` inside `TheScar.uefnproject`, which is a different thing.
Source: `C:\Program Files\Epic Games\Fortnite\Engine\Build\Build.version`.

### 9b. §2c is WRONG — Verse `@editable` values ARE readable

§2c says Verse `@editable`s are invisible because `get_user_option_values()` on a `VerseDevice_C`
returns only three base options. **That conclusion was right about the API I tried and wrong about
the editor.** There is another path:

```python
unreal.get_default_object(unreal.DeviceToolset).call_method("ListDeviceProperties", args=(verse_device,))
unreal.get_default_object(unreal.DeviceToolset).call_method("GetDeviceProperties",  args=(verse_device,))
```

Reported to return the **real, unmangled `@editable` names and live values** off
`leaderboard manager` — `rowsToShow: 5`, `boardTopMargin: 270`, `debugSeedBoard: false`,
`eliminationManager`, `objectiveLine`, `boardLeftMargin`, `debugLogEliminations` — with object
refs resolved to `{"refPath": "…__verse_0x2DD0D81D_EliminationManager"}`.

**`DeviceToolset` is Verse-device-only.** Passing a Creative device is rejected with
`Cannot nativize 'FortCreativeDeviceProp' as 'Device'`.

### 9c. §2b's "write path unknown" — **REFUTED. The real answer is in §13e (variant F).**

> **STATUS 2026-09-04: REFUTED. Do not build on this.** Probe P4 was run four ways in a
> sandbox (§13e) — plain, with `modify()`, with `post_edit_change()`, and with
> `bypass_container_check=YES`. **None persisted to disk.** The confirmed write path is
> `set_editor_property` on the native UPROPERTY instead (§13d/§13e variant F).
> The original note below is kept for the record. Probe P4 (§11) first ran it. The call
> returns `True` and reads back changed through `ToolsetLibrary`, but
> `get_user_option_value()` still returns the old value. Do NOT read this section as
> solved. See §0 Trap 1.

`unreal.ToolsetLibrary` **exists with the Beta Access flag OFF** and exposes
`get_object_properties`, **`set_object_properties`**, `list_struct_properties`,
`get_derived_classes`, `undo_transaction`. Reported working:

```python
unreal.ToolsetLibrary.get_object_properties(toy_options_component, ["PlayerOptionData"])
# -> {"PlayerOptionData":{"propertyOverrides":[{"propertyName":"BlockWeaponFire","propertyData":"True"}, ...]}}
```

The symmetric `set_object_properties` is the candidate write path for Creative device options —
**the hardest open problem in §2b.** Unproven that a write persists, fires
`PostEditChangeProperty`, or survives publish validation. **Verify on disk, not by read-back.**

### 9d. The bigger finding, and the recommendation

`unreal.ToolsetRegistry` is available and `get_all_toolset_json_schemas()` reportedly returns
**~470 KB describing 12 toolsets and 168 tools**, each with a full `inputSchema`. Epic's native
toolset classes (`DeviceToolset`, `EntityToolset`, `SessionToolset`, `VerseToolset`, `LogsToolset`,
`EditorAppToolset`, …) are callable via `call_method` on the CDO **without enabling the beta flag**.

**Recommendation: do NOT tick Beta Access → UEFN MCP Toolsets, and do NOT register Epic's
`unreal-mcp` as a second server.** Reasons: it buys transport, not capability; its `ToolsetPolicy`
*subtracts* (it strips PIE functions that `call_method` reaches anyway); and a second MCP server
means **two uncoordinated writers on one game thread**.

**The one-line summary:** *"a lot of things are not accessible from the MCP connection" was true of
the TOOLS, not of the EDITOR.* Everything the Unity benchmark offers that UEFN can meaningfully
have is already inside the process the listener runs in. This is plumbing and discipline, not
capability acquisition.

**Probes to re-run first (in this order, targeted, small):**
1. `unreal.ToolsetRegistry.is_available()` and `len(get_all_toolset_json_schemas())`
2. `DeviceToolset.GetDeviceProperties` on a `VerseDevice_C`
3. `ToolsetLibrary.get_object_properties` on a Creative device's `ToyOptionsComponent`
4. Only then, a `set_object_properties` write — **verified by grepping the saved level on disk**

### 9e. The highest risk, per the plan

Everything above rides on `call_method` against toolsets Epic has **not allow-listed for UEFN** —
a reflection path that provably bypasses their policy layer. It can crash the editor, and it can
vanish silently on a version bump. The plan's mitigations are a **hard denylist** (all PIE
functions, `StopServer`, `EnablePythonInUEFN`, `unregister_toolset_class`), **allow-list-first for
writes**, a **capability manifest** checked at every listener start, and a **`--supported-only`
fallback mode**.

## 10. RULE — never give subagents the UEFN bridge

The 12:09 crash and the listener dying again at ~13:00 both happened while **workflow subagents had
access to the `uefn` MCP tools and were driving the live editor at the same time as the main
session.** That is a direct violation of the standing rule in `G:\Claude Local\CLAUDE.md`:
**one Editor, one bridge, never two Claude sessions against it at once.**

Subagents inherit the session's MCP tools. **A research workflow must be told, in its prompt, not
to touch the `uefn` tools** — or it will, because the tools are right there and the task invites it.
Web research and file reading only. The live editor belongs to the main session alone.

## 11. §9d PROBE RESULTS — 2026-09-04, run in the live editor

All four §9d probes were run in this session against `uefn-extended` on port 8775,
Beta Access flag OFF. §9 was labelled HIGH-CONFIDENCE-UNVERIFIED. **Three of its four
claims are now VERIFIED; the fourth is REFUTED as stated.**

### P1 — ToolsetRegistry — **VERIFIED, exact match**

`unreal.ToolsetRegistry.is_available()` → `True`.
`get_all_toolset_json_schemas()` → **470,110 bytes**, a JSON *list* of 12 toolsets,
**168 tools** total. Byte-for-byte agreement with V12.

`NiagaraToolset_System` 46, `EditorAppToolset` 37, `UMGToolSet` 21, `PhysicsAssetToolset` 17,
`MVVMToolset` 15, `WidgetAnimationToolset` 10, `VerseFieldsToolset` 6, `LogsToolset` 4,
`GameplayTagsToolset` 4, `NiagaraToolset_Component` 4, `NiagaraToolset_Assets` 3,
`NiagaraToolset_Info` 1.

`is_toolset_registered("DeviceToolset")` → `False`, confirming **V13**: the Valkyrie toolsets
are callable while unregistered. Registration is what the beta flag buys; capability is not.

### P2 — Verse `@editable`s — **VERIFIED. §2c is WRONG and is now superseded.**

`DeviceToolset.GetDeviceProperties` needs **two** args — the error
`required argument 'property_names' (pos 2) not found` reveals the signature. Call
`ListDeviceProperties(device)` first for the schema, then `GetDeviceProperties(device, names)`.

On `leaderboard manager` (`VerseDevice_C`), unmangled names **and** live values came back:

```
rowsToShow: 5            boardTopMargin: 270      boardLeftMargin: 60
debugSeedBoard: false    debugLogEliminations: false
objectiveLine: "TOP THE BOARD - EVERY DEATH SCARS THE GROUND"
eliminationManager: {"refPath": "...leaderboard_manager_0.__verse_0x2DD0D81D_EliminationManager"}
```

**§2c's conclusion was right about `get_user_option_values()` and wrong about the editor.**
The nine Verse devices in The Scar are: leaderboard, scar, revenge, hud, juggernaut, loadout,
trophy, onboarding, progression manager.

### P3 — `ToolsetLibrary` read — **VERIFIED, exact match with V15**

Signatures read from `__doc__`, not by calling:
```
get_object_properties(object, property_names) -> str
set_object_properties(object, properties_json, bypass_container_check=BypassContainerCheck.NO) -> bool
```
`barrier.get_user_option_definitions()` → `ToyOptionsComponent_C`. Reading `PlayerOptionData`
off it returned **18 `propertyOverrides`** as clean JSON (`BlockWeaponFire: "True"`,
`BaseVisibleDuringGame: "False"`, …) — the writable-shaped form V15 described.
18 overrides, not 23: the five function-style options carry no override entry.

### P4 — the write — **REFUTED AS STATED. `set_object_properties` is NOT a working write path.**

On `TrophyBarrier_W`, writing the full 18-entry array back with only `LabelOverride`
changed to `MCP_PROBE_1`, inside a `ScopedEditorTransaction`:

| Check | Result |
|---|---|
| `set_object_properties` return | **`True`** |
| read back via `ToolsetLibrary.get_object_properties` | **`MCP_PROBE_1`** — changed |
| read back via `device.get_user_option_value("LabelOverride")` | **`TrophyBarrier_W`** — UNCHANGED |
| `actor.get_actor_label()` | **`TrophyBarrier_W`** — UNCHANGED |

**The two representations diverge.** `set_object_properties` writes a parallel property bag that
the device's actual option state never reads. A caller who verified with the same API it wrote
through would have declared success — this is precisely the false pass
`CLAUDE.md` warns about, and it is why §9c's "candidate write path" must not be promoted to fact.

**Not disproven:** that some additional step (a `PostEditChangeProperty` broadcast, `modify()`,
`bypass_container_check`, or a save+reload) makes it take. **Disproven:** that the call alone
writes a device option. P3/P4 in §3 stay UNPROVEN; §9c must not be read as "solved".

**Disk evidence:** the level save was refused by the permission layer, so **nothing reached disk**.
The in-memory change was then restored from a verbatim copy of the original JSON and confirmed
byte-identical, with both APIs agreeing on `TrophyBarrier_W`. `grep -rl MCP_PROBE_1` over
`TheScar\Content\__ExternalActors__\` returns nothing; `TrophyBarrier_W` still appears 4× in
`__ExternalActors__\TheScar\1\8W\FLT01UIF23Q9PCGJOY1B56.uasset`. **The Scar is unmodified.**
Completing P4 needs a level save, which requires the user's approval.

### Corrections applied to §2 as a result

- **§2c is superseded by P2.** Verse `@editable`s are readable. The claim that they are
  invisible was carried into `uefn_listener.py` and `mcp_server.py` docstrings this session
  and has been corrected in both.
- **§2b's "writing is genuinely blocked"** stands as *no proven write path*, now with a second
  refuted candidate (`set_object_properties`) rather than one.
- Engine is **`++Fortnite+Release-42.10`, CL 57566230** (§9a). "41.30" is `compatibilityVersion`.

---

## 12. WHAT SHIPPED THIS SESSION

Six new first-class tools, flat one-per-operation per `IMPLEMENTATION_PLAN.md` §4.
34 MCP tools total (was 28); 37 listener handlers.

| Tool | Status | Evidence |
|---|---|---|
| `list_devices` | **WORKING** | 51 configurable actors found; the 35 `Device_*`/`VerseDevice_C` match §2e's independent inventory exactly, plus 16 player spawners. 1038 static props correctly excluded. |
| `get_device_options` | **WORKING** | `TrophyBarrier_W` → 23 options; `BlockWeaponFire=True`, `BaseVisibleDuringGame=False`, `EnabledOnPhase="Gameplay Only"`, `ZoneShape=Box`, `LabelOverride=TrophyBarrier_W` — all five match §2b. Props rejected with a useful message. |
| `console_command` | **WORKING** | `HighResShot 1280x720` produced `HighresScreenshot00028.png` on disk. Settles **P10** for the file-producing case. |
| `validate_assets` | **BUILT, UNTESTED** | signatures verified; no validation run yet. |
| `pilot_actor` | **BUILT, UNTESTED** | signatures verified. |
| `take_screenshot` | **PARTIAL — see below** | |
| `play_mode` | **DELIBERATELY NOT EXPOSED** | `IMPLEMENTATION_PLAN.md` §2 ruling 9. Built, then withdrawn from the client surface before ever being invoked. Handler remains for manual `execute_python` use. |

### The screenshot bug worth remembering (P9)

`AutomationLibrary.take_high_res_screenshot` returns an `AutomationEditorTask`. **If you discard
that object, Python garbage-collects it and the capture is silently cancelled** — the call
succeeds, no error is raised, no file is ever written. The first implementation dropped the task
and produced nothing. The listener now holds tasks in `unreal._mcp_screenshot_tasks`; do not
"simplify" that registry away.

**Still unresolved, but now with log evidence** (from the new disk-backed `read_log`):

| # | Call | Result |
|---|---|---|
| 1 | `take_high_res_screenshot`, task **dropped**, `force_game_view=False` | no file - the GC bug above |
| 2 | `take_high_res_screenshot`, defaults, task held | **saved 07:19:00** (`probe_task.png`) |
| 3 | `take_high_res_screenshot`, task held, `force_game_view=False` | **never completed** |
| 4 | `take_high_res_screenshot`, defaults, task held - identical to #2 | **never completed** |
| 5 | console `HighResShot 800x450`, issued after #3 | **saved 07:26:40** (`HighresScreenshot00029.png`) |

#2 and #4 were the same call, and only the earlier one worked. #3 sits between them and is the
only call that ever passed `force_game_view=False`.

**DISPROVED 2026-09-04 — see §13b.** On a clean editor `force_game_view=False`, fired first
and alone, landed in under 8 seconds, and three further captures with both flag values all
landed. The flag is innocent; the real variable is almost certainly editor focus / CPU
throttling. `take_screenshot` is WORKING.

**Also learned: captures are SLOW when the editor is unfocused** - 26 s, 30 s, and once a full
**3 minutes** between request and file. Every "it produced no file" conclusion earlier in this
session was checked too early at least once. Poll for minutes, not seconds.

**Next step:** on a clean editor, call `take_high_res_screenshot` with `force_game_view=False`
first and see whether it alone reproduces the wedge. Until then `take_screenshot` should be
considered unreliable, and console `HighResShot` is the working fallback.

### Known pre-existing defect, not introduced here

`get_editor_log` returns **stale** content — during this session it served lines ending
37 minutes in the past while the file on disk was current to the second, and its `filter_str`
argument did not filter. Anything reasoning from that tool's output is reasoning from a stale
snapshot.

**FIXED, per `IMPLEMENTATION_PLAN.md` §4 — in `mcp_server.py`, NOT the listener.** New tools
`read_log(lines, filter, level, since, cursor, log)` and `read_crashes(limit, context_lines)`
read the `Saved\Logs` and `Saved\Crashes` trees directly from the MCP process. Zero
game-thread cost, never stale, and they still work when the editor is hung or the listener is
dead — which is exactly when the log matters. `cursor`/`next_cursor` give incremental polling.
**The old `get_editor_log` handler is deliberately left untouched.**

It paid for itself within a minute of existing: it produced the `Cmd: HighResShot` lines that
settled **P10**, and the `LogClient: High resolution screenshot saved as …` timestamps that
turned the screenshot guess above into an evidenced hypothesis.

### Hot-patching the running listener

The listener's globals are reachable without a restart:
`unreal._mcp_server.RequestHandlerClass._send_json.__globals__`. `exec`ing new handler source
into that dict registers handlers into the live `_HANDLERS` with no server restart and no tick
re-registration. This is how all six tools were loaded into a live editor this session.

## 13. SANDBOX SESSION — 2026-09-04, Blank_Test_Project

Everything here was run in a throwaway project so the writes could be destructive.
**The headline: there IS a confirmed, disk-verified write path for device settings, and it is
NOT the one §9c proposed.**

### 13a. Getting a sandbox running — three environment findings

1. **Python is PER-PROJECT.** It is gated by
   `dataSets.experimental.pythonExperimental.bEnablePythonForProject` in the `.uefnproject`.
   TheScar has it; a fresh project does not, so **Tools → Execute Python Script does not even
   exist** there and the listener cannot start. The Tools menu's "Enable Python" checkbox does
   **not** persist it — it has to be added to the file by hand.
   **Any new sandbox project needs this step first.**
2. **UEFN rewrites `*.uefnproject` while the editor is open.** An edit made with UEFN running was
   overwritten **97 milliseconds later**. Project-file edits only stick with the editor **fully
   closed**. Treat this as a hard rule for any tool that writes project files.
3. **Some "Details panel" settings are plain JSON in the `.uefnproject`** — see 13c. This also
   corrected a wrong diagnosis: `mms_player_count = 16` is a **maximum**; the real minimum is
   `minPlayers`, which was 2 on The Scar. **The island never demanded sixteen players.**

### 13b. Screenshots — the wedge hypothesis is DISPROVED

§12 guessed that `force_game_view=False` wedged the `AutomationLibrary` capture path. **It does
not.** On a clean editor, `force_game_view=False` fired *first and alone* landed in **under 8
seconds**, and three further back-to-back captures with both flag values all landed. The image
was opened and inspected: a correct render of the sandbox island.

**`take_screenshot` is WORKING.** The real variable is almost certainly **editor focus / CPU
throttling** — the earlier session was running at ~5 fps unfocused, where captures took 26 s, 30 s
and once a full 3 minutes. Poll for minutes, not seconds, when the window is in the background.

### 13c. The `.uefnproject` audit — full `dataSets` enumeration

| Key | Blank | TheScar |
|---|---|---|
| `experimental.pythonExperimental.bEnablePythonForProject` | True | True |
| `experimental.sceneGraph.bIsSceneGraphSystemAllowed` | True | True |
| `experimental.sceneGraph.bEnableOneFilePerEntity` | False | False |
| `matchmaking.maxPlayers` | 16 | 16 |
| `matchmaking.minPlayers` | **1** | **2** |
| `matchmaking.maxTeamCount` | **16** | **4** |
| `matchmaking.maxTeamSize` / `maxSocialPartySize` | 16 | 16 |
| `matchmaking.overtimePlayerTarget` | **1** | **2** |
| `matchmaking.queueMainDuration` / `queueOvertimeDuration` | 5 | 5 |
| `matchmaking.islandQueuePrivacy` | Public | Public |
| `matchmaking.allowJoinInProgress` | True | True |
| `matchmaking.useSkillBasedMatchmaking` / `allowSquadFillOption` / `splitscreenDisabled` | False | False |
| `autoLocalization.*`, `ugcLocalization.*` | absent | present (18 cultures) |

**Are they mirrored on the Island Settings actor? YES — as device options, exactly.**

| `.uefnproject` | Island Settings device option | Blank value (both) |
|---|---|---|
| `maxPlayers` | `Matchmaking_MaxPlayersPerSession` | 16 |
| `minPlayers` | `Matchmaking_MinPlayers` | **1** |
| `maxTeamCount` | `Matchmaking_MaxTeamCount` | **16** |
| `maxTeamSize` | `Matchmaking_MaxTeamSize` | 16 |
| `maxSocialPartySize` | `Matchmaking_MaxSocialPartySize` | 16 |
| `overtimePlayerTarget` | `Matchmaking_OvertimePlayerTarget` | **1** |
| `queueMainDuration` / `queueOvertimeDuration` | `Matchmaking_QueueMainDuration` / `…Overtime…` | 5 |
| `islandQueuePrivacy` | `MatchmakingPrivacy`, `CreativeMatchmakingPrivacy` | Public |

This is **differential** confirmation, not coincidence: the three values where Blank differs from
TheScar (`minPlayers`, `maxTeamCount`, `overtimePlayerTarget`) differ on the actor in exactly the
same way. The Island Settings actor exposes **299** options in total.

### 13d. PROBE 6 — native property write. **CONFIRMED, and it propagates everywhere.**

`islandSettings.set_editor_property("mms_player_count", 4)` then save:

| Representation | Before | After |
|---|---|---|
| native `mms_player_count` | 16 | **4** |
| native `max_players` | 16 | **4** (a second native property followed) |
| option `Matchmaking_MaxPlayersPerSession` | 16 | **4** |
| option `MaxPlayers` | 16 | **4** |

**Disk-verified by differential**, not by read-back: the saved `.uasset` stores the ANSI string
`'4'` after `Matchmaking_MaxPlayersPerSession`; re-saving at 16 stores `'16'` at the same place.
(A raw byte diff is useless here — the whole package re-serialises, 28 355 bytes differ.)

**And it round-trips into the `.uefnproject`.** Setting the actor to 8 and saving rewrote the
project file: `maxPlayers`, `maxSocialPartySize`, `maxTeamCount`, `maxTeamSize` all → 8. The
editor also silently upgraded `compatibilityVersion` 41.30 → 42.10 on save.

**So the authority chain is: native UPROPERTY → device-option view → saved `.uasset` → `.uefnproject`.**
The project file is an **output**, not an input, while the editor is open. Combined with 13a.2,
this settles the tool-surface question: **do NOT build a `.uefnproject` writer for matchmaking
settings — write the actor instead.** A file writer would be overwritten within 100 ms, and the
setting it targets is a projection of actor state anyway.

### 13e. P4 — six write variants, one device each. **§9c is REFUTED.**

| V | Method | `ToolsetLibrary` read | option read | native read | **ON DISK AFTER SAVE** |
|---|---|---|---|---|---|
| A | `set_object_properties` plain | changed | old | old | **absent** |
| B | `modify()` then set | changed | old | old | **absent** |
| C | set then `post_edit_change()` | changed | old | old | **absent** |
| D | set, `bypass_container_check=YES` | **changed** | **changed** | old | **absent** |
| E | `set_user_option_value(None,…)` | old | old | old | **absent** (correct negative, returned False) |
| F | **`set_editor_property('label_override', …)`** | old | **changed** | **changed** | **PRESENT, 4×** |

**`ToolsetLibrary.set_object_properties` is not a write path in any variant.** It populates an
in-memory property bag the serialiser ignores. After the save, A–D had all silently reverted to
their original values.

**Variant D is the most dangerous result in this project so far.** With
`bypass_container_check=YES`, **two independent APIs agreed on the new value** —
`ToolsetLibrary.get_object_properties` *and* `device.get_user_option_value()` — the Details-panel
label visibly changed, and **it still did not persist.** Cross-API agreement was not enough.
Only the disk was.

**Variant F is the confirmed write path**, consistent with probe 6: write the native UPROPERTY,
and the device-option view follows. The actor's displayed label became `MCP_P4_F` and the marker
appears 4× in its saved `__ExternalActors__` `.uasset`.

### 13f. Validation of the modified sandbox — CLEAN

`validate_assets(directory="/Blank_Test_Project/", usecase="PRE_SUBMIT")` after the F write:
**71 assets checked, 71 VALID, 0 invalid, 0 errors, 1 warning** — and that warning
(`_Verse Asset $Digest has an invalid name`) pre-dates the write and is unrelated.

**So the F recipe survives Epic's own pre-submit validators.** That is a necessary condition
before it goes near The Scar, not a sufficient one — validation is not the publish gate (§2/A11).

Fixed while doing this: `validate_assets` was returning `"VALID: 1>"` as its result state,
because `str(enum)` is `"<DataValidationResult.VALID: 1>"` and only the last `.` was stripped.
Every `== "VALID"` comparison a caller made would have failed. Now returns `"VALID"`.

### 13g. What this means for the tool surface

- **DONE — `set_device_option` ships, built on `set_editor_property`.** See 13h.
- **Do NOT add anything built on `ToolsetLibrary.set_object_properties`.** Refuted four ways.
- **Do NOT add a `.uefnproject` writer** for matchmaking settings (13d).
- The name mapping (option → native) is the open question: `LabelOverride` → `label_override` and
  `mms_player_count` are known; the general rule is UpperCamel → snake_case, unverified at scale.

### 13h. SHIPPED — `set_device_option`, the confirmed write path as a tool

The mapping question in 13g is answered by measurement, not assumption. Resolving each option
name to a native UPROPERTY with a small set of **named candidates** (snake_case, `b`-prefix
stripped, lowercase, verbatim — never a reflection sweep):

| Device | options | mapped | |
|---|---|---|---|
| Island Settings | 299 | 297 | 99% |
| Item Granter / End Game | 31 / 26 | 31 / 26 | 100% |
| Button ×5 | 18 | 17 | 94% |
| Damage Volume / HUD Message / Tracker | 32 / 38 / 56 | 24 / 28 / 38 | 68–75% |
| **TOTAL** | **572** | **529** | **92%** |

The unmapped 8% is almost entirely **function-style options** — `On Player Entering Zone`,
`Reset Progress`, `Assign to All` — which are events, not data, and correctly have nothing to
write. The genuine data gap is small and consists of space-named options like `Interaction Text`.

**Generalisation test — F is not a one-off.** Five options, five devices, four types, all
**verified on disk** after save:

| Device | Option | Wrote | On disk |
|---|---|---|---|
| Button | `InteractionRadius` (float) | 7.77 | `7.770000` PRESENT |
| Button2 | `Delay` (float) | 3.33 | `3.330000` PRESENT |
| Button3 | `TimesCanTrigger` (int) | 37 | `37` PRESENT |
| Button4 | `InteractTime` (float) | 9.99 | `9.990000` PRESENT |
| Button5 | `EnabledAtGameStart` (bool) | False | `False` PRESENT |

**`set_device_option(actor_path, option, value, save=False)` now ships.** End-to-end check:
writing `LabelOverride="SHIPPED_TOOL_TEST"` on the HUD Message device with `save=true` put the
marker in the saved `.uasset` **4×**, and `validate_assets` still returns **71/71 VALID, 0
errors**. It refuses function-style options with a message explaining why.

`get_device_options` no longer reports `writable: False` — that is now wrong. It reports
`writable_via: "set_device_option"` and names the refuted route so nobody rebuilds it.

**Not yet proven, and deliberately not claimed:** that a write survives a *Verse rebuild*, or that
UEFN's publish pipeline accepts an island authored this way (§3 P15). Validation is a pre-flight,
never a publish guarantee.

## 14. HONEST RE-TEST + P14 — 2026-09-04

### 14a. The committed file, not the hot-patch — **PASSES**

Everything in §13h was tested against a **hot-patched** listener, i.e. code living only in that
session. That is not a shipped tool. Re-tested properly:

- The listener was reloaded from disk. Confirmed fresh, not by trusting the reload but by probing
  for `_is_device` — a symbol that only ever existed in the hot-patched namespace. **Absent.**
- `set_device_option` was then driven **through the real MCP tool**, not raw HTTP.
- `LabelOverride="DISK_PROOF_1"` on the End Game device with `save=true` → **present 4× in the
  saved `.uasset`.**

**The committed file alone reproduces the result.** The tools are also visible as real MCP tools
now, so the server process has reloaded too.

### 14b. P14 — Verse rebuild survival. **PASSES**, and the first attempt was worthless

`VerseToolset.BuildAll` via `call_method` on the CDO works with no arguments — **P6 settled**.
The log confirms a genuine build: `Verse compile starting (instigator=User)` →
`Compilation complete` → `Linking complete` → `SUCCESS -- Build complete`.

**But the first run proved nothing and was nearly reported as a pass.** The sandbox had **no
`.verse` files at all**, so the compile was a no-op:
`Global Verse compile finished: No packages found requiring compilation.` Markers "surviving" a
build that never rebuilt anything is not evidence.

Fixed by giving the sandbox real Verse code (`Content/p14_probe.verse`, a trivial
`creative_device` with one `@editable`) and rebuilding. That produced a genuine incremental
compile: **`Global Verse compile (incremental, 1 packages compiled in 917.9 ms) finished: SUCCESS`.**

After that real compile, **every marker survived on disk**: `DISK_PROOF_1`, `MCP_P4_F`,
`SHIPPED_TOOL_TEST`, and the numeric writes `7.770000`, `9.990000`, `3.330000` — and the live
editor still reads `LabelOverride = DISK_PROOF_1`.

**Conclusion: a Verse rebuild does not regenerate device external-actor assets and does not
clobber native property writes.**

**Residual limit, stated rather than hidden:** the package that recompiled was the probe file, and
none of the written devices are Verse devices bound to that code. A Verse device whose own
`@editable`s are rewritten by a rebuild is not covered by this test.

### 14c. P15 — publish. **NOT SETTLED. Not scriptable from here.**

There is **no publish path through this bridge**, and this was checked rather than assumed:

- The 470 KB / 168-tool schema corpus contains **no publish tool**. Searching every tool name and
  description for publish/upload/version returned 4 hits, all false positives matching
  "conversion" and "ListConversionFunctions".
- Named subsystem candidates `FortCreativePublishSubsystem`, `FortPublishSubsystem`,
  `ValkyriePublishSubsystem`, `FortUGCPublishSubsystem`, `FortProjectSubsystem` — **all absent**.

Publishing is a GUI wizard, and it is outward-facing and account-affecting, so it is a human
action by design. **P15 stays UNPROVEN until a private version is published by hand.**

**Scope of what a private version proves** (qualifier added 2026-09-04): it runs build, cook,
validation and upload - the real risk surface for MCP-authored actors - but **not** Epic's human
content review, which happens only on public release. Never write a clean private build up as
"publish accepts this" without that qualifier.

**Nothing may be written to The Scar until it is** — a write path that passes validation but
breaks at publish would be the worst thing to discover on a live island.

### 14d. Prepared for The Scar (NOT applied)

The two settings and their resolved native properties, confirmed on the sandbox actor:

| Option | Native property | TheScar now | Target |
|---|---|---|---|
| `Matchmaking_MinPlayers` | `matchmaking_minplayers` | 2 | **1** |
| `Matchmaking_OvertimePlayerTarget` | `matchmaking_overtimeplayertarget` | 2 | **1** |

Supporting evidence that the target state is safe: **Blank_Test_Project already runs at
`minPlayers=1`, `overtimePlayerTarget=1`** and validates **71/71 VALID, 0 errors**.

Rationale: at ~63 clicks/day split across regions, a two-stranger queue bar is rarely met — 244 of
252 clicks never became a session. Setting both to 1 lets a lone player start a match.

**Sequence when P15 clears: Lore check-in FIRST, then write both via `set_device_option`, save,
verify on disk, change NOTHING else, and stop at "ready to publish."** Any second change in the
same release makes the clicks-to-plays before/after uninterpretable.
