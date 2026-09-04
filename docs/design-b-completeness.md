# UEFN MCP — upgraded tool surface and architecture

**Ground-truth correction before anything else.** The brief says the editor is `++Fortnite+Release-41.30`. It is not. `C:\Program Files\Epic Games\Fortnite\Engine\Build\Build.version` reads `"BranchName": "++Fortnite+Release-42.10"`, CL 57566230. The `41.30` in the brief is `"compatibilityVersion": "41.30"` inside `G:\UEFN\TheScar\TheScar.uefnproject` — the *project's* compat stamp, not the editor's version. Everything downstream changes, because Epic's first-party MCP shipped in 42.00 and its Programmatic toolset in 42.10, and **both are physically installed on this machine right now**:

- `C:\Program Files\Epic Games\Fortnite\Engine\Plugins\Experimental\Toolsets\` — 11 toolset plugins, **Python source readable on disk**
- `C:\Program Files\Epic Games\Fortnite\FortniteGame\Plugins\Toolsets\ValkyrieToolset\Content\Python\valkyrie_toolset\registration.py` — read it, it explains the whole gating model
- `C:\Program Files\Epic Games\Fortnite\Engine\Plugins\Experimental\ToolsetRegistry\Content\Python\toolset_registry\` — the registry, `helpers.py`, `tool_call_impl.py`

Live port state as I write: `127.0.0.1:1962 LISTENING (PID 8292)` — the editor is **open**. Ports 8000 and 8765 are not listening — Epic's MCP is not started and our listener is down.

And a second correction that matters more than it looks. Reading Epic's shipped 42.10 Python I found **`unreal.ToolsetLibrary`**, a native function library used throughout `editor_toolset`:

```
ToolsetLibrary.get_object_properties(obj, [names])   -> JSON string
ToolsetLibrary.set_object_properties(obj, json)      -> bool
ToolsetLibrary.list_struct_properties(struct)        -> str
ToolsetLibrary.get_derived_classes(cls) / get_derived_structs(struct)
ToolsetLibrary.undo_transaction()                    -> None
ToolsetLibrary.get_active_undo_count()               -> int
```
(`editor_toolset/toolsets/object.py:94,115,116`; `toolsets/programmatic.py:972,979`)

This is a reflection-grade property get/set that does **not** go through Python bindings, plus a native programmatic **undo**. Three research conclusions die on it (§7). It is also the strongest untried candidate for the device-options write path.

---

## 1. Architecture — three layers, and why

**Plain English:** we stop trying to hand-build a Unity-sized tool set inside one Python file. Epic already shipped ~400 tools that do the four things Python provably cannot (write device Details settings, wire device events, compile Verse, control play sessions). We put those to work, keep our listener for the things Epic does *not* cover, and put one thin translator in front so Claude sees a single clean tool list instead of three servers.

```
Claude Code
   │ stdio
   ▼
mcp_server.py  →  becomes the GATEWAY  (curated ~30 tools, one game-thread mutex)
   ├── HTTP 127.0.0.1:8000/mcp   Epic unreal-mcp (in-process, ~400 tools, 29 toolsets)
   ├── HTTP 127.0.0.1:8765       uefn_listener.py  (SIDECAR — the gaps)
   ├── TCP  127.0.0.1:1962       Verse Workflow Server (compileProject / pushChanges / focusEditor)
   └── local disk                logs, crashes, .verse, OFPA .uasset name tables, ini
```

Four load-bearing claims:

**(a) The sidecar is not obsolete.** Epic's toolsets contain **no screenshot tool** (I grepped all 11 plugins — only a doc mention in `skills/default_outdoor_lighting.py`), no arbitrary-Python tool, no console-command tool, no off-disk log reader, no crash reader, and no transaction *bundling* across many mutations. Those are exactly what we keep.

**(b) The sidecar can import Epic's own toolset Python.** `registration.py` says in its own docstring: *"the creator surface is decided by `UE::ValkyrieToolset::ToolsetPolicy` alone."* That policy governs **what the MCP server exposes**. It says nothing about what an in-editor Python script may `import`. The packages sit on disk as plain `.py`. If `sys.path` includes those `Content/Python` folders, `from editor_toolset.toolsets.object import ObjectTools` should work and give us `ObjectTools.set_properties`, `SceneTools.trace_world`, `ActorTools.add_component` — including the toolsets Epic **excludes** from UEFN (`blueprint.BlueprintTools`, 79 tools). **UNPROVEN.** Exact probe:
```python
import unreal, sys, os
p = r"C:\Program Files\Epic Games\Fortnite\Engine\Plugins\Experimental"
sys.path += [os.path.join(p,"ToolsetRegistry","Content","Python"),
             os.path.join(p,"Toolsets","EditorToolset","Content","Python")]
print(hasattr(unreal,"ToolsetLibrary"))          # expect True — module is compiled in
unreal.load_module("BlueprintEditorLibrary")
from editor_toolset.toolsets.object import ObjectTools
print(ObjectTools.list_properties(unreal.get_editor_subsystem(unreal.EditorActorSubsystem)))
```
If `hasattr(unreal,"ToolsetLibrary")` is True with the beta flag **off**, we get Epic's reflection engine without touching `.uefnproject` at all. That is the single highest-value probe in this document.

**(c) One game thread, one writer.** Epic's docs say its server *"serialises tool calls onto the game thread — clients must not overlap calls."* Our listener does the same via `register_slate_post_tick_callback`. Two servers driving one game thread concurrently is a hang or a crash. **The gateway must hold a single mutex across all four backends.** No research source raised this; it is the most likely cause of a mysterious editor freeze once both are live.

**(d) Do not turn on "UEFN MCP Toolsets" until (b) is answered.** The flag writes `toolsets.bEnableToolsetsForProject` into `TheScar.uefnproject` (currently absent — the project has only `pythonExperimental.bEnablePythonForProject: true`) and it permanently breaks `Content/Python/init_unreal.py` auto-start (Epic ticket FORT-1143572). That costs us nothing — the standing rule already forbids anything in `TheScar\Content\` — but it is a project-file mutation, so it is a decision, not a default.

---

## 2. Proposed tool list

Backing key: **[S]** sidecar listener · **[E]** proxied Epic toolset · **[W]** Verse workflow server (TCP 1962) · **[G]** gateway-local, no editor needed.
Confidence: **high** = mechanism verified on this machine or plain file I/O · **medium** = API present, UEFN path unproven · **low** = speculative bridge.

### A. Session, system, meta

| Tool | Params | Returns | Backing | Confidence |
|---|---|---|---|---|
| `ue_status` | — | which backends are live (8000 / 8765 / 1962), editor PID, project, level, dirty flags, listener uptime, throttle state | S+G | **high** — extension of existing `status` |
| `ue_search_tools` | `query`, `limit` | ranked tool ids + one-line descriptions across Epic's ~400 and ours | G | **high** — background-index Epic's schemas once at startup; pure gateway logic |
| `ue_call` | `toolset`, `tool`, `args{}` | raw result | G→E | **medium** — escape hatch onto any Epic tool not curated; depends on `call_tool` meta-tool shape holding |
| `execute_python` | `code` | stdout/stderr/result | S | **high** — exists today; keep it, Epic has no equivalent |
| `batch` | `commands[{tool,params}]`, `fail_fast`, `transaction_label` | per-command results + one undo entry | S+G | **high** — one tick, one `begin_transaction`/`end_transaction` pair |
| `ue_reflect` | `action∈{search_classes,list_properties,get_properties,describe}`, `target`, `filter` | class/property listing | S | **high** — `ToolsetLibrary.get_derived_classes` + `list_struct_properties`; fallback `dir()`/`getattr()` |

### B. Editor control, play, undo

| Tool | Params | Returns | Backing | Confidence |
|---|---|---|---|---|
| `manage_session` | `action∈{start,stop,status,push_changes,start_game,stop_game,game_state,client_log}`, `verse_only`, `path_glob`, `max_results`, `start_line` | session status enum, game state enum, log entries | E (`ValkyrieToolset.SessionToolset`) | **medium** — the function names are extracted from the shipped binary, not yet driven. This is Unity's `manage_editor(play)` equivalent and the biggest single parity win |
| `push_changes` | `verse_only: bool` | `{message}` or error | W | **medium** — protocol verified live (1962 is listening); `pushChanges` takes a **bare boolean** param, not an object |
| `undo` / `redo` | `count` | `{active_undo_count_before, after}` | S | **medium** — `ToolsetLibrary.undo_transaction()` + `get_active_undo_count()`; redo has no equivalent found, likely needs `execute_console_command("TRANSACTION REDO")` |
| `editor_play` | `action∈{begin,end,simulate,state}` | `is_in_play_in_editor` | S | **low** — `LevelEditorSubsystem.editor_request_begin_play` *is* exposed, but Epic explicitly **strips `StartPIE`/`StopPIE`/`IsPIERunning`** from the UEFN toolset policy, and `bc2424/uefn-util` patches a DLL to force PIE. My prediction: no-op or crash. Ship it behind `hasattr` + a big warning, or not at all |
| `execute_console_command` | `command`, `capture_log: bool` | log delta between sentinel markers | S | **medium** — `unreal.SystemLibrary.execute_console_command(world, cmd)`; returns `None`, so output must be recovered from the log. Needs a **denylist** (`quit`, `exit`, `crash`, `debug crash`, `obj gc`) |

### C. Actors and entities

| Tool | Params | Returns | Backing | Confidence |
|---|---|---|---|---|
| `find_actors` | `query`, `by∈{name,label,class,tag,folder,path}`, `include_children`, `page_size`, `cursor` | **paths + labels only**, never full blobs | S | **high** — filter over existing `get_all_actors`. Biggest context win available |
| `manage_actor` | `action∈{spawn,delete,duplicate,transform,move_relative,look_at,set_label,set_folder,attach,detach,select,focus}`, `target`/`targets[]`, `class_or_asset`, `location/rotation/scale`, `world_space`, `offset` | changed paths | S (+E `ActorTools`) | **high** — 8 of 12 actions exist today; `look_at`/`set_parent` mirror `ActorTools.look_at`, `set_parent_component` |
| `manage_actor_tags` | `action∈{get,add,remove,has}`, `target`, `tag` | tag list | S | **high** — `AActor.tags` is a plain UPROPERTY |
| `manage_entity` | `action∈{list_classes,find,create,delete,get_transform,set_transform,get_components,add_component,remove_component,list_component_properties,get_component_property,set_component_property}`, `parent_entity`, `root_entity`, `name_filter`, `is_prefab` | entity refs / property JSON | E (`ValkyrieToolset.EntityToolset`) | **medium** — Scene Graph is enabled on this project (`bIsSceneGraphSystemAllowed: true`). Unproven only because nothing has driven it |
| `raycast` | `start[3]`, `end[3]` | hit distance or null | S (+E `SceneTools.trace_world`) | **high** — `SceneTools.trace_world(start,end) -> float\|None` exists verbatim in `scene.py:378`. This is the behavioural-verification primitive: prove a prop is *actually* solid where you put it |

### D. Components and properties

| Tool | Params | Returns | Backing | Confidence |
|---|---|---|---|---|
| `manage_properties` | `action∈{list,get,set,reset}`, `target` (actor/component/asset path), `properties[]` or `values{}` | JSON of property values / bool | S | **high** — `ToolsetLibrary.get_object_properties` / `set_object_properties`, which reach properties with no Python glue. Falls back to `get_editor_property` / `call_method` |
| `manage_components` | `action∈{list,add,remove,get_property,set_property}`, `target`, `component_type`, `component_index` | component refs | S (+E `ActorTools`) | **medium** — `SubobjectDataSubsystem` is exposed; `ActorTools.add_component` shows the working call shape. **Adding components to Creative devices will fail UEFN validation** — gate behind a `force` flag |

### E. Devices — the UEFN-specific core

| Tool | Params | Returns | Confidence |
|---|---|---|---|
| `get_device_options` | `target` or `targets[]` | `{key: value}` per device, all options | **high** — `get_user_option_values()` verified working (CLAUDE.md line 909, verified 2026-08-14) |
| `set_device_options` | `target`, `values{}`, `verify: bool` | per-key `{ok, before, after, verified_on_disk}` | **medium** — see the four-route plan below. This is the hardest problem in the project and I now rate it likely-solvable |
| `list_device_catalog` | `filter` | placeable `Device_*_C` classes + whether Verse-backed | **high** — `ToolsetLibrary.get_derived_classes` |
| `manage_device_bindings` | `action∈{options,list,add,remove}`, `source_device`, `source_event`, `target_device`, `target_function` | binding list | **medium** — `DeviceToolset.GetBindingOptions/ListEventBindings/AddEventBinding/RemoveEventBinding` [E]. **No Python route exists at all** for Functions/Events wiring; this is Epic-only, and it is a capability we have never had |
| `get_island_settings` / `set_island_settings` | native property names | values | **high** — native UPROPERTYs on `Device_ExperienceSettings_V2_UEFN_C` already read (`mms_player_count=16`, `teams=TeamIndex/4`) |

**`set_device_options` — four routes, tried in this order:**

1. **`DeviceToolset.SetDeviceProperty` via Epic's MCP.** Epic built a native tool precisely because the Python setter needs a `PlayerController`. Highest odds. Requires the beta flag.
2. **`ToolsetLibrary.set_object_properties` on the `ToyOptionsComponent`.** The T3D export proves the storage is a real serialized property — `PlayerOptionData.PropertyOverrides[{PropertyName, PropertyData}]`, both plain strings. The "zero properties" finding almost certainly came from `dir()`, which lists only *bound* properties. `set_object_properties` is Epic's own reflection writer. **UNPROVEN, and the cheapest thing on this list.**
3. **`component.call_method("SetOptionValue", args=(...))`.** `_ObjectBase.call_method` explicitly *"allows calling methods that don't have Python glue"*. Recover the real UFunction name first with `OBJ DUMP` or `ToolsetLibrary.list_struct_properties`, do not guess.
4. **T3D clipboard round-trip.** `AssetExportTask` + `ObjectExporterT3D` already works in UEFN (33KB export captured). Export → regex-patch → clipboard → `EDIT PASTE`. Ugly, loses actor identity, and **will break Verse `@editable` object references that point at the original actor**. Last resort only.

**The behavioural proof for all four is the same and it is not a read-back:** set `LabelOverride` to a unique token → save the level → **grep the OFPA `.uasset` under `Content\__ExternalActors__\` for that token on disk** → run validation → screenshot the Details panel. Disk is an independent oracle; `get_user_option_values()` is not.

### F. Verse

| Tool | Params | Returns | Backing | Confidence |
|---|---|---|---|---|
| `verse_list` / `verse_read` | `path_glob` / `uri` | file list / text + sha256 | S/G | **high** — plain UTF-8 files in `TheScar\Content\*.verse`, no `unreal` API needed. Read them off disk from the **gateway**, zero game-thread cost |
| `verse_write` | `uri`, `contents` or `old_string`/`new_string`/`replace_all`, `precondition_sha256` | new sha | G | **high** — file I/O. Copy Epic's `VerseToolset.WriteFile` param shape so we can swap backends later |
| `verse_apply_edits` | `uri`, `edits[{startLine,startCol,endLine,endCol,newText}]`, `precondition_sha256` | new sha, applied count | G | **high** — Unity's `apply_text_edits` verbatim, language-agnostic |
| `verse_grep` | `pattern`, `path_glob`, `ignore_case`, `max_results` | line/col matches | G | **high** |
| `verse_build` | — | `{message, numErrors, numWarnings, diagnostics[]}` | W | **high on mechanism** — port 1962 is live now; framing is `Content-Length:` + `{"seq","type","command","params"}`; `compileProject` returns `{message,numWarnings,numErrors}` directly. **Caveat: one client per source address — connecting will disconnect VS Code.** Reconnect-on-demand and close immediately |
| `verse_diagnostics` | `since_line` | structured `[VerseBuild:]` lines from the editor log | G | **high** — cross-check against `verse_build`; never report green if the log disagrees |
| `get_verse_editables` | `target` | `{editable_name: value}` on the Verse instance subobject | S | **medium** — they are real UPROPERTYs with mangled names `__verse_0x2DD0D81D_EliminationManager`, on the `<module>_0` subobject, **not on the actor**. The hash is not derivable from source — it must be enumerated by reflection. This is why `get_actor_properties` on a `VerseDevice_C` looked empty |
| `set_verse_editables` | `target`, `values{}` | per-key ok | **medium** — if they are genuine UPROPERTYs, `ToolsetLibrary.set_object_properties` should write them. **If this works it reframes the whole authoring approach: wrap behaviour in a Verse device with `@editable`s rather than configuring a Creative device** |

### G. Assets

| Tool | Params | Returns | Confidence |
|---|---|---|---|
| `manage_asset` | `action∈{list,search,info,create_folder,rename,duplicate,delete,move,save,exists}`, `path`, `class_filter`, `page_size`, `cursor` | paths + metadata | **high** — consolidates 9 existing tools; only `move`/`create_folder` are new |
| `import_file` | `source_path`, `dest_folder`, `type∈{texture,audio,mesh}` | new asset path | **medium** — `ImportSubsystem` + `AssetToolsHelpers` present; **meshes will usually fail UEFN validation**, textures and audio are the sanctioned path |
| `manage_material_instance` | `action∈{get,set_scalar,set_vector,set_texture,create_instance}`, `target`, `param`, `value` | param values | **medium** — `MaterialInstanceTools` [E]; UEFN forbids authoring base materials, instances of Epic parents only |

### H. Level, world, validation

| Tool | Params | Returns | Confidence |
|---|---|---|---|
| `manage_level` | `action∈{info,save,hierarchy,folders,get_data_layers,actors_in_data_layer}`, `max_depth`, `cursor` | tree with node caps | **high** — `WorldPartitionSubsystem` + `DataLayerEditorSubsystem` exposed; `SceneTools` shows the exact calls |
| `validate_island` | `scope∈{selection,level,project}`, `targets[]` | `[{package, errors[], warnings[]}]` | **high on mechanism, medium on coverage** — `EditorValidatorSubsystem.validate_assets_with_settings` / `is_asset_valid` are exposed and UEFN registers its publish rules as ordinary `EditorValidatorBase` subclasses, so the standard framework runs them. **This is the day-one safety net and it should ship first among the risky tools** |
| `map_check` | — | map-check errors/warnings | **medium** — `MapCheckSubsystem` exposed; only the `log_*` methods are confirmed |

### I. Vision and diagnostics — the things Epic does not have

| Tool | Params | Returns | Confidence |
|---|---|---|---|
| `screenshot` | `res_x`, `res_y`, `filename`, `camera`, `hide_gizmos`, `wait: bool` | path (+ inline base64 if small) | **medium** — `AutomationLibrary.take_high_res_screenshot` returns an `AutomationEditorTask`; it is **latent**, sets a viewport flag consumed on a later tick. Must be two-phase (`fire` → poll `is_task_done()` on the tick callback) or it returns before the file exists. novikit's SceneCapture variant is the fallback that works while the editor is unfocused |
| `frame_and_shoot` | `targets[]` or `location`+`rotation`, `res` | path | **medium** — composes existing `set_viewport_camera` + `focus_selected` + `screenshot`. This is what turns "I set the transform" into "it looks right" |
| `read_console` | `types[]`, `filter`, `since`, `page_size`, `cursor`, `include_callstack` | typed records | **high** — parse `%LOCALAPPDATA%\UnrealEditorFortnite\Saved\Logs\UnrealEditorFortnite.log` **from the gateway, off disk**, zero game-thread cost. Optionally add an in-editor `unreal.log` output-device hook into a ring buffer for live capture |
| `read_crashes` | `limit` | latest `Saved\Crashes\UECC-*` summaries | **high** — file I/O; tells us why the editor died last time |
| `set_editor_throttle` | `enabled: bool` | prior value | **medium** — write `bThrottleCPUWhenNotForeground=False` to `EditorPerProjectUserSettings.ini`. novikit measured 337ms → 14-31ms per call. **UNPROVEN here**; probe: time 20 `ping` round trips with the editor focused vs. behind another window, before and after |

**Total: ~30 gateway tools**, against Unity's 48 and Epic's ~400.

---

## 3. Consolidate into `manage_*`, or one tool per operation?

**Consolidate — but along object-type boundaries, and not for the reason usually given.**

The token argument is real but smaller than people claim. Our 28 flat tools are ~3-4k tokens of schema. A consolidated `manage_actor` with a 12-value action enum and 14 optional params is not 12× cheaper than 12 small tools — it is maybe 2× cheaper, because the parameter descriptions still have to exist and now each must explain *which actions it applies to*. Unity's `manage_gameobject` schema is enormous. Realistic saving from consolidating 30 flat tools into 12 verbs: **40-50%, not 90%**.

The stronger arguments for consolidation are not about tokens:

1. **Discoverability.** `manage_device(action=...)` puts the whole device vocabulary in one place. A model that finds `get_device_options` has to guess that `set_device_options` exists; a model that finds `manage_device` sees the enum.
2. **Room to grow without renegotiating the surface.** Adding `action="set_binding"` costs one enum value. Adding a 31st top-level tool costs a full schema and re-reads by every client.
3. **It matches the backend.** Epic's tools are already grouped by toolset; a `manage_entity` verb maps 1:1 onto `EntityToolset` and the gateway becomes a thin translator instead of a 13-way switch.

The arguments against, which I am honouring:

1. **High-traffic, low-arity tools stay flat.** `ping`, `screenshot`, `raycast`, `verse_build`, `undo`, `find_actors`, `execute_python`, `batch`. These are called constantly and in chains; forcing `action=` on them adds a token to every call and a decision to every plan.
2. **An action enum hides a failure mode.** With flat tools, an unsupported operation is "tool not found". With verbs, it is a runtime error deep inside the handler. Mitigate: every `manage_*` supports `action="capabilities"` returning which actions are live on this editor build — cheap, and it makes an unproven bridge self-describing.

**And the honest point that outranks both:** the dominant token cost in this system is not schemas, it is **results**. `get_all_actors` on The Scar serialises every actor with location/rotation/scale/class/path. One call can outweigh the entire tool list. Unity solved this by splitting reads onto resources and having `find_gameobjects` return **instance IDs only**. Copy that: every list-style tool returns paths + labels, with a separate `manage_properties(action="get")` to fetch detail for the handful you actually want. **Do this before consolidating anything** — it is a bigger win, and it is a one-afternoon change.

Final shape: **12 `manage_*` verbs + ~14 flat tools + `ue_search_tools`/`ue_call` for Epic's long tail.**

---

## 4. Concrete changes to the listener and `mcp_server.py`

The existing pattern is good and I would not replace it. `@_register("name")` → `_HANDLERS` → `_dispatch(command, params)` → `_tick_handler` drains `_command_queue` on `register_slate_post_tick_callback`. Changes, in dependency order:

**4.1 — Latent-aware handlers (blocking, must be first).** Today `_dispatch` runs a handler to completion inside one tick and stores the response. Screenshots, PIE entry and validation are *latent* — Epic's own docs say the editor does not tick during Python execution. Add a second return convention: a handler may return `_Pending(poll_fn, timeout_s)`, and `_tick_handler` keeps it in a `_pending` list, calling `poll_fn()` each tick until it returns a result or times out. ~40 lines. Without it, `screenshot` returns a path to a file that does not exist yet, and no amount of retrying fixes it.

**4.2 — Transactions around every mutation.** Wrap the `_dispatch` call in `_tick_handler`:
```python
if command in _MUTATING:
    prior = unreal.ToolsetLibrary.get_active_undo_count()
    unreal.SystemLibrary.begin_transaction("MCP", f"MCP: {command}", None)
    try:    result = _dispatch(command, params)
    finally: unreal.SystemLibrary.end_transaction()
    committed = unreal.ToolsetLibrary.get_active_undo_count() > prior
```
Two non-obvious details, both taken from Epic's shipped `programmatic.py:966-993`: `obj.modify()` is **mandatory** before mutating or the transaction records nothing; and `UTransBuffer::End` silently drops a transaction with no UObject modifications, so a blind `undo_transaction()` would pop an unrelated entry — hence the count snapshot. `batch` opens **one** transaction for the whole list, so a 40-actor layout is one Ctrl+Z.

**4.3 — Result shaping.** Add `_serialize_actor_ref(actor) -> {path, label, class}` and switch all list-style handlers to it. Add `page_size`/`cursor` to `get_all_actors`, `list_assets`, `search_assets`, `read_console`. Keep the fat `_serialize_actor` behind `manage_properties`.

**4.4 — Tick-callback lifecycle.** The listener already unregisters the old handle on reload (`uefn_listener.py:1240-1244`) — good, because double-unregistering a Slate tick crashes the editor. Harden it: store the handle on the `unreal` module (already done), and add a guard that refuses to register if `unreal._mcp_tick_handle is not None`. novikit switched to `FTSTicker` for this reason; **I would not switch** — the current code already survives reload and `FTSTicker` is not obviously exposed here. Revisit only if a crash is traced to the Slate tick.

**4.5 — Epic-toolset bridge module.** New `_toolsets.py` in the repo (never in `TheScar\Content\`) that puts Epic's `Content/Python` dirs on `sys.path`, `unreal.load_module('BlueprintEditorLibrary')`, imports `editor_toolset.toolsets.*`, and exposes them to handlers. Every import wrapped in try/except so a version bump that moves the path degrades to "that tool is unavailable" rather than a listener that will not start.

**4.6 — `mcp_server.py` becomes the gateway.** It already has `_send_command()` over HTTP and `_discover_port()`. Add: an `EpicClient` (HTTP+SSE to `:8000/mcp`, MCP framing), a `VerseWorkflowClient` (TCP 1962, `Content-Length` framing, connect-per-call so VS Code is only kicked for a moment), a `DiskReader` (logs/crashes/verse/ini), and — critically — **one `threading.Lock` held across every backend call**, since all four ultimately drive one game thread. Tool wrappers stay `@mcp.tool()`; only their bodies change to route.

**4.7 — Keep `uefn_listener.py` and everything new out of `G:\UEFN\TheScar\Content\`.** Standing rule, and the research gives it a sharper justification than "hygiene": `.loreignore` does not exclude `.py`, and UEFN Supplemental Terms §2 prohibits shipped content that opens connections to non-Epic servers. A listener binding `127.0.0.1:8765` is exactly that shape. Staged publish bundles are `.uasset`-only in practice, so it would almost certainly never ship — keeping it out means the question is never asked.

---

## 5. Build order, each with a behavioural test

Rule throughout, per `CLAUDE.md`: **drive the thing; do not read a value back.** Every test below has an oracle independent of the tool being tested.

**Step 0 — restart the listener and take a baseline.** The editor is running (PID 8292 holds 1962) but 8765 is dead. Tools → Execute Python Script → `G:\UEFN\uefn-mcp-server\uefn_listener.py`.
*Test:* `ping` returns; `execute_python("1+1")` returns 2; time 20 pings with the editor focused, then behind another window. That second number is the throttle baseline for step 8.

**Step 1 — the `ToolsetLibrary` probe (§1b).** Nothing else is scheduled until this is answered, because a True changes the plan for steps 4, 5 and 6.
*Test:* `ObjectTools.list_properties` on a live actor returns a property list, **with the beta flag still off**. If it fails, record the exact exception — "module not loaded" and "policy denied" imply different futures.

**Step 2 — result shaping + pagination.** No new capability, pure token work.
*Test:* `find_actors(by="class", query="Device_")` on The Scar returns ~35 rows of `{path,label,class}` and the response is under 4KB. Compare against today's `get_all_actors` byte count. Measured, not estimated.

**Step 3 — transactions and `undo`.**
*Test:* spawn a cube at a known location → `raycast` from 500 units above straight down and confirm a hit → `undo` → raycast the same ray again and confirm **no hit** → `manage_actor(action="transform")` on the returned path and confirm it errors with "actor not found". Three independent oracles, none of them "read the property back".

**Step 4 — `validate_island`.** Ships early because it is the safety net every later step is checked against.
*Test:* deliberately break something validation must catch (place a prop, then set a property not shown in the Details panel via `manage_properties`) → validation reports it → revert → validation is clean. If validation cannot catch a known-bad state, the tool is decorative and we should know that before trusting it.

**Step 5 — `screenshot` + `frame_and_shoot`.**
*Test:* frame a specific building actor, shoot, **open the PNG and look at it**. Then delete the actor, shoot again, and confirm the two files differ. Then shoot twice in one batch and confirm **both** files exist — that is the specific documented failure of `HighResShot` (the flag is consumed on the next tick, so a synchronous double-shot produces only the last one) and it is the proof that step 4.1's latent handling actually works.

**Step 6 — `verse_build` over port 1962.**
*Test:* introduce a known syntax error at a known line in a scratch `.verse` file → `verse_build` returns `numErrors >= 1` and a diagnostic whose `StartLine` matches the line we broke → fix it → `numErrors == 0` and the editor log shows `VerseBuild: Build complete.` Then confirm VS Code's Verse panel reconnects afterwards (the one-client-per-address kick).

**Step 7 — device options write.** Routes in the order given in §2E, stopping at the first that works.
*Test:* set `LabelOverride` on `Device_Barrier_V2_Placed_C` to `MCP_PROBE_<timestamp>` → save the level → **grep `Content\__ExternalActors__\` on disk for that string** → `validate_island` clean → screenshot the Details panel showing the new value. Only the disk grep proves persistence; the read-back proves nothing.

**Step 8 — throttle fix + timing.**
*Test:* re-run step 0's timing with the editor unfocused. If it does not move materially, drop the change rather than carrying a 15-second re-apply loop that fights the editor for no measured gain.

**Step 9 — turn on "UEFN MCP Toolsets", wire the gateway to `:8000`.** This mutates `TheScar.uefnproject` and is a decision (Question 1).
*Test:* `manage_session(action="start")` boots a client; `start_game` reaches `Running`; `client_log` contains a `Print` string that only executes at game start. That last one is the real proof — session status is state, a log line from our own Verse code is behaviour.

**Step 10 — `manage_device_bindings`.**
*Test:* wire Timer→Barrier via `AddEventBinding`, push changes, start a session, let the timer fire, and confirm from the **client log** that the barrier's function ran. Nothing short of a running game proves an event binding.

---

## 6. Risks

**Can crash or hang the editor**
- **Two writers on one game thread.** Epic's server and our listener both marshal to it, and Epic's docs say clients must not overlap calls. Mitigation: one gateway mutex; the listener should also refuse a second HTTP client. The existing rule "never two Claude sessions against UEFN" must be enforced in code, not just written down — it was violated during this research and the listener died.
- **Double-registered / double-unregistered Slate tick callbacks.** Already handled on reload; keep the guard and never call `unregister` on a `None` handle.
- **`tk.Tk()`.** The listener owns a shared root. Any new UI must use `tk.Toplevel(get_tk_root())`. A second `Tk()` crashes the editor — this is in the server's own MCP instructions for a reason.
- **PIE.** `editor_request_begin_play` exists but Epic strips PIE from UEFN's tool policy and a community project patches a DLL to force it. Treat entering PIE as "the bridge will drop and may not come back". Domain reload kills the in-process listener.
- **Long loops inside a handler.** The editor does not tick during Python execution. Any handler doing thousands of actor operations must yield across ticks or the editor appears frozen and Windows may offer to kill it. `batch` needs a per-tick work budget, not just a command count.
- **Console commands.** `execute_console_command` will happily run `quit`. Denylist it.

**Can contaminate the shipped project**
- **Anything written into `G:\UEFN\TheScar\Content\`.** Standing rule; `.loreignore` does not exclude `.py`; Supplemental Terms §2 covers content that opens external connections.
- **Properties not shown in the UEFN UI.** Epic's own guidance: modifying them *"will fail validation"*. `manage_properties` and `manage_components` are the two tools that can do this silently. Gate non-UI properties behind `force=true` and run `validate_island` after every device write.
- **The T3D paste route** (device write route 4) deletes and recreates the actor. New OFPA GUID, new actor name — **any Verse `@editable` object reference pointing at the original device breaks**, and The Scar has 9 `VerseDevice_C` actors. Do not ship this route without a reference audit.
- **Creating Blutility / Editor Utility assets** under `/TheScar/`. UEFN supports a subset of UE asset types; a stray `EditorUtilityWidgetBlueprint` is a plausible way to break publishing for zero benefit. The research is right to rule this out — I agree and would go further: do not create *any* asset type in the project that the UEFN content browser cannot itself create.
- **`bEnableToolsetsForProject`** written into `.uefnproject` by the beta flag. It is a tracked project file. It also permanently kills `Content/Python/init_unreal.py` auto-start (FORT-1143572, unresolved).
- **Auto-save / auto-commit.** `save_current_level` inside a `batch` that later fails leaves a half-applied level on disk. Saves should be explicit tools, never implicit steps.

**Can break on a version bump**
- **Epic toolset Python paths.** `...\Engine\Plugins\Experimental\Toolsets\<Name>\Content\Python\` is not a stable API. Every import guarded; `ue_status` reports which bridges loaded.
- **`ToolsetPolicy` allowlist.** Epic can add or remove toolsets per release — `StartPIE` is already stripped, `BlueprintTools` already excluded. A tool that works today can vanish with no error, just an empty tool list.
- **Verse `__verse_0x…` mangled names.** The hash covers the fully-qualified Verse path, not the identifier. Rename a Verse module or move a file and every cached mangled name is stale. Never cache them across a build; re-enumerate.
- **Port 1962 protocol.** Three commands today (`focusEditor`, `compileProject`, `pushChanges`). `EVKPlayButtonState` already lives in that module, so Epic is likely to add play control there — good news, but it means the command set is not frozen.
- **`compatibilityVersion: 41.30` on a 42.10 editor.** The project is a version behind the editor. A future open or publish may auto-upgrade it, and that is a content change we did not author.
- **Delta serialization.** An `@editable` left at its Verse default is not written to the `.uasset` at all. Any on-disk reader must treat "absent" as "default", resolved from `.verse` source — not as "unset" or "missing".

---

## 7. What in the research is wrong, or I do not believe

1. **"You are on 41.30."** Wrong, and it invalidates the entire framing of the `unity-mcp-benchmark` report — its recommendation ("if you stay on 41.30, build six tools"), its Question 1, and every `X → E` verdict that assumes Epic's MCP is out of reach. Verified: `Build.version` says `++Fortnite+Release-42.10`.

2. **"`begin_transaction`/`end_transaction` are absent — use the scoped form"** (`MCP_UPGRADE.md` §2a). Contradicted by Epic's own shipped 42.10 Python: `editor_toolset/toolsets/programmatic.py:980` calls `unreal.SystemLibrary.begin_transaction(context, description, None)` and `:993` calls `end_transaction()`. Re-probe; I suspect the original check looked at the wrong class.

3. **"There is no native Python undo trigger; `EDIT UNDO` via console is the candidate."** Wrong on 42.10. `unreal.ToolsetLibrary.undo_transaction()` and `get_active_undo_count()` exist and Epic uses both. No console command needed.

4. **"CLAUDE.md says device settings are not readable — THE READ HALF IS WRONG."** The brief's own premise is wrong about what the doc says. `G:\UEFN\TheScar\CLAUDE.md` line 909-914 already reads: *"They are readable — `actor.get_user_option_values()` returns the whole Details panel… but `set_user_option_value` requires a live `PlayerController`."* Verified 2026-08-14, in the doc. `MCP_UPGRADE.md` is right and the brief is repeating a stale correction. **Do not "fix" CLAUDE.md §4 — it is already correct.**

5. **"The `ToyOptionsComponent` exposes zero data properties to Python."** I do not believe this as stated. It is a `dir()` result, and `dir()` lists only *bound* properties. The T3D export shows `PlayerOptionData.PropertyOverrides` is a real serialized property, and we now have `ToolsetLibrary.get_object_properties`, which is a reflection reader, not a binding reader. The conclusion may survive a proper probe — but it has not had one.

6. **"Verse `@editable` values are invisible."** Half-true and misleading as written. They are absent from `get_user_option_values()` — correct. They are *not* invisible: they are real UPROPERTYs named `__verse_0x…` on the Verse instance subobject, which is why actor-level property reads came back empty. Two different claims, and the second one is the useful one.

7. **"Blueprint / Editor Utility Widget is a viable bridge."** I agree with the `remote-control` research that it is not, and I would state the reason more simply than it did: Python cannot author K2 node graphs, so the bridge would have to be hand-built in a UI UEFN does not expose for custom logic. Dead end. Drop it.

8. **"Remote Control API"** — dead end, agreed, five independent confirmations. I would add that it is *moot*: `call_method` plus `ToolsetLibrary` already give both of Remote Control's supposed superpowers, so even if it existed it would add nothing.

9. **novikit's throttle numbers (337ms → 14-31ms, and re-apply every 15s).** Plausible, unverified here, and the re-apply loop is a smell — something in the editor is resetting the ini, which means we are fighting a system we do not understand. Do the one-line ini change, measure it (step 8), and if the gain is real, prefer setting *Editor Preferences → Use Less CPU when in Background* off once by hand over a background loop that rewrites a settings file every 15 seconds.

10. **"Epic rejects custom Python toolsets, therefore a sidecar is the only option."** Half right. `registration.py` is explicit that `ToolsetPolicy` decides the *creator surface* — i.e. what the MCP server exposes. That is not the same as forbidding a Python script from importing those modules. If §1b's probe comes back True, we get Epic's reflection engine *and* the toolsets Epic excludes from UEFN (`BlueprintTools`, `data_asset`, `string_table`) without touching the beta flag. Nobody in the research tested this.

11. **The `unity-mcp-benchmark` claim that `unity_docs` is "largely redundant".** Agreed, and I would extend it: **do not build `uefn_docs`.** Epic's shipped digests (`Saved\VerseProject\TheScar\Digests\*.digest.verse`) are the authoritative API surface for this exact build, they are already on disk, and `verse_grep` over them beats any web-scraped documentation tool.

---

## Questions

**Question 1.** Do I have your go-ahead to tick **Project Settings → Beta Access → UEFN MCP Toolsets**? It writes a `toolsets` block into `TheScar.uefnproject` and permanently breaks `Content/Python/init_unreal.py` auto-start (which we already do not use). It is the only route to `SetDeviceProperty`, `AddEventBinding`, `BuildAll` and session control. My recommendation: **yes, but not until the §1b probe is run** — if `unreal.ToolsetLibrary` is already reachable with the flag off, we get most of the reflection value for free and can decide about the flag on its own merits.

**Question 2.** The project stamps `compatibilityVersion: "41.30"` while the editor is 42.10. Was that pinned deliberately, or has the project simply not been re-saved since the update? It affects whether Scene Graph and 42.x device revisions are safe to use in The Scar.

**Question 3.** Gateway (one curated ~30-tool surface, more work, one thing to configure) versus two plain `.mcp.json` entries (Epic's `unreal-mcp` alongside our `uefn`, working today, but Claude faces three meta-tools plus 28 flat tools with no shared naming and **no cross-server game-thread lock**). I recommend the gateway, mainly for the lock — but the two-entry version is a legitimate one-hour stopgap if you want device writes working this week.

**Question 4.** `verse_build` over port 1962 will disconnect VS Code's Verse extension each time it connects (one client per source address, enforced in the binary). Acceptable, or should the tool refuse to run while VS Code is open?

**Question 5.** Build order — do you want me to run steps 0-3 (restart, `ToolsetLibrary` probe, result shaping, transactions/undo) as one pass and report before touching anything device- or session-related? That is where I would start: it is all reversible, it is all inside the sidecar, and step 1's answer changes the plan for half the remaining work.

**Files referenced:** `G:\UEFN\uefn-mcp-server\uefn_listener.py` (46KB; `_register`/`_dispatch` at lines 190-206, `_run_on_main_thread` at 112, `_tick_handler` at 788, tick lifecycle at 1170/1212/1240) · `G:\UEFN\uefn-mcp-server\mcp_server.py` (20KB; `_send_command` at 92) · `G:\UEFN\uefn-mcp-server\MCP_UPGRADE.md` · `G:\UEFN\TheScar\TheScar.uefnproject` · `G:\UEFN\TheScar\CLAUDE.md` (device options at 909-914) · `C:\Program Files\Epic Games\Fortnite\Engine\Plugins\Experimental\Toolsets\EditorToolset\Content\Python\editor_toolset\toolsets\` (`object.py`, `actor.py`, `scene.py`, `programmatic.py`) · `C:\Program Files\Epic Games\Fortnite\Engine\Plugins\Experimental\ToolsetRegistry\Content\Python\toolset_registry\helpers.py` (`require_editable` at 203) · `C:\Program Files\Epic Games\Fortnite\FortniteGame\Plugins\Toolsets\ValkyrieToolset\Content\Python\valkyrie_toolset\registration.py`