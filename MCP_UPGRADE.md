# UEFN MCP Upgrade — working document

**Started 2026-09-04.** Read this before touching anything. Everything in §2 was
measured in a live UEFN editor on that date, not inferred from docs.

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

### 2b. DEVICE OPTIONS — read yes, write no (CLAUDE.md §4 is CORRECT here)

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

**Writing is genuinely blocked.** `set_user_option_value` takes a `PlayerController` as arg 1;
passing `None` returns `False` — no exception, no write. The `ToyOptionsComponent` exposes
**zero** data properties to Python, and the option values are **not** mirrored in any native
UPROPERTY on the actor. Finding a write path is the hardest open problem in this project.

### 2c. CONFIRMED BLOCKED

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

### 9c. §2b's "write path unknown" — there is a candidate

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
