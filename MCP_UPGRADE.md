# UEFN MCP Upgrade — working document

**Started 2026-09-04.** Read this before touching anything. Everything in §2 was
measured in a live UEFN editor on that date, not inferred from docs.

---

## 0. TWO TRAPS THAT PRODUCE CONFIDENT FALSE PASSES

Both were hit in this project. Both look like success. Read these before writing a probe.

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
Save, then grep the `.uasset` under `__ExternalActors__`. Verified 2026-09-04 - see §11 P4.

### TRAP 2 - a dropped screenshot task cancels the capture silently

`AutomationLibrary.take_high_res_screenshot` returns an `AutomationEditorTask`. **Discard it and
Python garbage-collects it, which cancels the capture.** No exception, no error, no log line,
no file - the call simply "succeeds" and nothing is ever written.

The listener keeps every task in `unreal._mcp_screenshot_tasks` for exactly this reason.
**A future cleanup that deletes that registry as a pointless variable will silently break all
screenshots.** It is load-bearing. See `_screenshot_tasks()` in `uefn_listener.py`.

### The general form of both

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

### 9c. §2b's "write path unknown" — a CANDIDATE, **NOT CONFIRMED**

> **STATUS 2026-09-04: REFUTED AS A DIRECT WRITE.** Probe P4 (§11) ran it. The call
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

**Sharpened hypothesis: a `force_game_view=False` request wedges the `AutomationLibrary`
screenshot path, and every later `take_high_res_screenshot` queues behind it forever. The console
`HighResShot` path is a different code path and is unaffected** - #5 completed normally after the
wedge. Not a frozen editor: frame count advanced 18793 -> 18836 over ~8 s (~5 fps) throughout.

**Also learned: captures are SLOW when the editor is unfocused** - 26 s, 30 s, and once a full
**3 minutes** between request and file. Every "it produced no file" conclusion earlier in this
session was checked too early at least once. Poll for minutes, not seconds.

**Next step:** on a clean editor, call `take_high_res_screenshot` with `force_game_view=False`
first and see whether it alone reproduces the wedge. Until then `take_screenshot` should be
considered unreliable, and console `HighResShot` is the working fallback.

### Known pre-existing defect, not introduced here

`get_editor_log` returns **stale** content — during this session it served lines ending
37 minutes in the past, and its `filter_str` argument did not filter. Anything reasoning from
that tool's output is reasoning from a stale snapshot. `IMPLEMENTATION_PLAN.md` §4 already plans
to replace it with a disk reader in `mcp_server.py`; that is the fix.

### Hot-patching the running listener

The listener's globals are reachable without a restart:
`unreal._mcp_server.RequestHandlerClass._send_json.__globals__`. `exec`ing new handler source
into that dict registers handlers into the live `_HANDLERS` with no server restart and no tick
re-registration. This is how all six tools were loaded into a live editor this session.
