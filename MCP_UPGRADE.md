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
