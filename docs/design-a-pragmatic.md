I verified the ground truth against the machine before designing. One correction dominates everything.

---

# 0. GROUND-TRUTH CORRECTION (verified on disk, today)

**The task brief says "Engine ++Fortnite+Release-41.30". That is wrong.**

```
C:\Program Files\Epic Games\Fortnite\Engine\Build\Build.version
  → "BranchName": "++Fortnite+Release-42.10", Changelist 57566230
```

`G:\UEFN\TheScar\TheScar.uefnproject` says `"compatibilityVersion": "41.30"` — that is the **project's** compat stamp, not the editor. The editor is 42.10.

Consequences I verified directly, not from docs:

| Fact | Evidence |
|---|---|
| Epic's MCP is compiled into the running editor | `UnrealEditorFortnite-Win64-Shipping.modules` contains `ModelContextProtocol`, `ModelContextProtocolEditor`, `ModelContextProtocolEngine`, `ToolsetRegistry`, `ValkyrieToolset` |
| MCP server + meta-tools are real | `StartServer`(9), `StopServer`(2), `RefreshTools`, `bAutoStartServer`, `ServerPortNumber`, `bEnableToolSearch`, `list_toolsets`, `describe_toolset`, `call_tool` all present as strings in the shipped DLLs |
| **`SetDeviceProperty` exists** | grep hit in `UnrealEditorFortnite-Common-Win64-Shipping.dll`, alongside `PlaceDevice`, `ListDeviceProperties`, `GetDeviceProperties`, `GetBindingOptions`, `ListEventBindings`, `AddEventBinding`, `RemoveEventBinding` |
| Session control exists | `StartSession`(11), `StopSession`, `PushChanges`(11), `StartGame`(18), `StopGame`, `GetSessionStatus`, `GetGameState`, `GetClientLogEntries` |
| Verse compile exists | `BuildAll`, `VerseToolsetDiagnostic`(6) |
| C++ toolsets present | `DeviceToolset.h`, `EntityToolset.h`, `SessionToolset.cpp/.h`, `VerseToolset.cpp/.h`, `ValkyriePythonToolset.h`, **plus two the research missed: `DynamicUIToolset.h`, `SpecialEventToolset.h`** |
| Epic's toolset Python is readable on disk | `…\Engine\Plugins\Experimental\Toolsets\` (11 toolsets) and `…\FortniteGame\Plugins\Toolsets\ValkyrieToolset\Content\Python\valkyrie_toolset\registration.py` |
| It is currently OFF | `TheScar.uefnproject` has `pythonExperimental.bEnablePythonForProject: true` but **no `toolsets` block**; nothing is listening on :8000 |
| Live state right now | UEFN **is running** (PID 8292). Verse Workflow Server **is listening on :1962**. Our listener on **:8765 is DOWN**. |

**`SetDeviceProperty` is the single hardest blocked problem in this project — the one the brief calls "still blocked" — and it is sitting in the binary behind a checkbox.** No amount of listener work reaches it. That inverts the design.

---

# 1. PROPOSED TOOL LIST

## Design filter

`execute_python` **already is the consolidated tool.** Every new schema must beat "just write the Python" on one of three grounds: (a) the Python is long/fiddly and easy to get subtly wrong, (b) it runs on nearly every task, (c) it is async and needs the two-phase pattern. "Unity has one" is not a ground. That filter kills about 30 of the 48 Unity tools before we even ask if UEFN can do it.

Ranked by (value × confidence) / effort. Effort in listener-hours for one person.

### Group A — Adopt (zero build effort, largest gain)

| # | Tool | Source | Gain |
|---|---|---|---|
| A1 | `SetDeviceProperty`, `GetDeviceProperties`, `ListDeviceProperties`, `PlaceDevice`, `ListDeviceAssets` | Epic `DeviceToolset` | **Device writes.** Unreachable from Python at any effort. |
| A2 | `AddEventBinding`, `RemoveEventBinding`, `ListEventBindings`, `GetBindingOptions` | Epic `DeviceToolset` | Functions/Events panel wiring. No Python path exists, no Unity analogue. |
| A3 | `BuildAll`, `ReadFile`, `WriteFile`, `Grep`, `ListFiles` | Epic `VerseToolset` | **Verse compile with structured diagnostics.** |
| A4 | `StartSession`, `StartGame`, `StopGame`, `PushChanges`, `GetClientLogEntries`, `GetSessionStatus` | Epic `SessionToolset` | Play-mode parity with Unity's `manage_editor`. |
| A5 | Entity/Actor/Asset/Material/Texture/StaticMesh/Object/Scene toolsets | Epic engine toolsets | ~20 toolsets free. |

**Confidence: HIGH that the binaries are there and the flag exposes them. MEDIUM that every listed function behaves as named** — I read symbol names out of a DLL, not a manifest. Step 1's behavioural test settles it in ten minutes.

### Group B — Sidecar: build these (the real gap list)

Confidence reasons are the load-bearing part.

| # | Tool | Params | Returns | Conf | Reason |
|---|---|---|---|---|---|
| B1 | `execute_python` *(exists — upgrade)* | `code`, `transaction: str = ""`, `budget_ms: int = 200` | `{result, stdout, stderr, elapsed_ms}` | **HIGH** | Works today. Upgrade = wrap in `ScopedEditorTransaction` when `transaction` is set, and log when a handler exceeds `budget_ms`. Epic ships **no** arbitrary-Python tool — `ValkyriePythonToolset` only has `EnablePythonInUEFN` / `IsPythonEnabledInUEFN`. This stays our crown jewel. |
| B2 | `batch` | `commands: [{cmd, params}]`, `transaction: str`, `fail_fast: bool` | `[{ok, result\|error}]` | **HIGH** | Pure listener plumbing over the existing `_dispatch`. Collapses N HTTP round-trips *and* N editor ticks into one, and makes N mutations one undo step. Biggest latency win available and it cannot fail for API reasons. |
| B3 | `job_status` | `job_id` | `{state, progress, result?, error?}` | **HIGH** | Pure Python. Partner for every async tool. Build once, reuse for B4/B8/B9. |
| B4 | `screenshot` | `res_x=1920`, `res_y=1080`, `filename`, `camera_path=""`, `game_view=True`, `inline=False` | `{job_id}` → `{path, width, height, png_b64?}` | **MEDIUM-HIGH** | `AutomationLibrary` confirmed present in the live probe; `take_high_res_screenshot` is documented and returns an `AutomationEditorTask`. Risk is real and specific: **the task flag is consumed on a later engine tick, and `is_task_done()` never flips inside a synchronous script.** Our slate-post-tick pump is exactly the right machine for it. Fallback if it misbehaves: `execute_console_command(world, "HighResShot 1920x1080")`. Second fallback (UNPROVEN): SceneCapture2D, which reportedly works while the editor is unfocused where HighResShot does not. **This is what gives Claude eyes — the difference between "I set the transform" and "it looks right".** |
| B5 | `reflect` | `action ∈ {search, get_type, get_member, list_props, list_funcs}`, `name`, `query`, `instance_path` | class list / property+function tables with types and flags | **HIGH** | Pure `dir()`/`getattr()`/`get_editor_property` introspection over the live `unreal` module. ~80 lines, cannot fail. **208 subsystems are exposed and undocumented** — this is what turns `execute_python` from guesswork into engineering, and it makes every later probe cheap. Highest multiplier per hour on the list. |
| B6 | `dump_object` | `object_path`, `mode ∈ {t3d, props, funcs}` | text dump / structured dict | **HIGH** | The T3D export path is **already proven working on this machine** — a live Barrier exported to 33,161 bytes of T3D at `…\scratchpad\barrier_dev.t3d`, showing `PlayerOptionData.PropertyOverrides` with `PropertyName`/`PropertyData` string pairs. `LevelExporterT3D` and `ObjectExporterT3D` both present. This is a free `/remote/object/describe`, including Blueprint-defined variables that `dir()` hides. |
| B7 | `read_editor_log` | `lines=200`, `level ∈ {error,warning,log,all}`, `filter`, `since_marker`, `cursor` | typed records `{time, category, level, text}` + cursor | **HIGH** | Reads `%LOCALAPPDATA%\UnrealEditorFortnite\Saved\Logs\UnrealEditorFortnite.log` — verified present, 1.2 MB, live. **Put this in `mcp_server.py`, not the listener**: zero game-thread cost, and it works when the editor is busy, hung, or the listener is dead. That last property is worth a lot given how often the listener dies. Current `get_editor_log` returns raw tail; the missing 90% is parsing and paging. |
| B8 | `find_actors` | `query`, `by ∈ {label,name,class,tag,path}`, `limit=200`, `cursor` | **paths + labels + class only** | **HIGH** | Trivial filter over `get_all_level_actors`. The point is what it *doesn't* return. `get_all_actors` today emits a fat blob per actor; on a level with 1092 external actors that is a context bonfire. Unity's split — IDs from search, detail on demand — is the one architectural idea worth stealing wholesale. |
| B9 | `validate` | `scope ∈ {level, selected, asset}`, `path` | `{errors[], warnings[], per_asset}` | **MEDIUM** | `EditorValidatorSubsystem`, `FortEditorValidatorSubsystem` and `FortExposedContentValidationSubsystem` **all acquire successfully** per the live probe, exposing `validate_assets_with_settings` / `is_asset_valid` / `is_object_valid`. Downgraded from HIGH because **"it passes this" ≠ "it will publish"** — the publish gate also builds a sentry manifest and runs upload-time checks. Sell it as a fast pre-flight, never as a publish guarantee. |
| B10 | `console` | `command`, `capture=True` | `{output_lines[]}` | **MEDIUM** | `SystemLibrary` is present (it *is* `UKismetSystemLibrary` — the missing `KismetSystemLibrary` name in the brief is a red herring, the prefix is stripped by the binding generator). `execute_console_command` returns `None`, so capture must be done by bracketing with sentinel `unreal.log()` markers and diffing the log. Reliability in editor Python is genuinely contested in Epic's own forums with no resolution. Test with something loud (`stat fps`), never something silent. |
| B11 | `duplicate_actor` | `source_path`, `offset`, `count=1`, `label_prefix` | `[{path,label}]` | **HIGH** | `EditorActorSubsystem.duplicate_actor` is a full UObject duplication, so **all 23 device options carry across**. Even after Epic's `SetDeviceProperty` lands, "hand-configure one, clone N" stays the fastest authoring loop for repeated devices. Cheap and it never breaks. |
| B12 | `list_devices` | `include_verse=True` | `[{path,label,class,option_count}]` | **HIGH** | Filter to `Device_*_C` + `VerseDevice_C`. The Scar has 4×Barrier, 8×ItemGranter, 3×HUDMessage, 2×MutatorVolume, 9×VerseDevice + 9 singletons. Pairs with B13. |
| B13 | `get_device_options` | `actor_path` | `Map[str,str]` | **HIGH** | **Proven working**: `get_user_option_values()` returned all 23 Barrier options with real values (`BlockWeaponFire=True`, `EnabledOnPhase="Gameplay Only"`, `LabelOverride=TrophyBarrier_W`…). Keep even after adopting Epic's `GetDeviceProperties` — one round trip, no meta-tool walk. |
| B14 | `get_verse_editables` | `actor_path` | `{field: value}` with mangled↔source name mapping | **MEDIUM** | Strong on-disk evidence: a real `VerseDevice_C` OFPA asset carries `__verse_0x2DD0D81D_EliminationManager`, `__verse_0x4630999D_InternalEvent` etc. as genuine reflected properties — **on the Verse instance subobject (`<module>_0`), not on the actor.** That is why naive `get_actor_properties` looked empty. Two traps: the hex is a hash of the fully-qualified Verse path and is **not derivable** from source, so it must be discovered; and UE delta-serializes, so a field left at its Verse default is absent on disk entirely. Live reflection avoids the second trap. Epic's `VerseFieldsToolset` may make this redundant — check before building. |

### Group C — External client, no editor involvement

| # | Tool | Conf | Reason |
|---|---|---|---|
| C1 | `focus_editor` | **MEDIUM-HIGH** | TCP :1962, `focusEditor`. **Port verified listening right now, while our listener is down.** This directly solves the pain point named in `CLAUDE.md`: *"The MCP bridge drops during play-mode entry and may not reconnect until the Unity window regains focus."* Epic's own VS Code extension ships the protocol in readable JS. |
| C2 | `verse_build` / `verse_push` | **MEDIUM** | Same channel, `compileProject` / `pushChanges`. Works with the listener dead. **Hard caveat, from the binary: `"Killing Verse Message Server client connection %d because new client connected from same address."` — one client per source address. Connecting kicks VS Code's Verse panel off.** Whether VS Code auto-reconnects is UNPROVEN. Given Epic's `VerseToolset.BuildAll` does the same thing through a sanctioned path, **C2 is the fallback, not the primary.** Build C1 (which VS Code never uses) regardless. |

### Group D — CUT. Ruthlessly.

| Cut | Why |
|---|---|
| **Play mode via `editor_request_begin_play()`** | `MCP_UPGRADE.md` calls this *"the single biggest gap vs Unity MCP, and it is available"*. **I don't believe it, and I think building it is actively dangerous.** Epic's own toolset policy **explicitly strips `StartPIE`/`StopPIE`/`IsPIERunning` from the UEFN surface** while shipping them everywhere else. Epic removing their own working PIE tools from UEFN is the strongest possible evidence PIE is unsafe here. A community project exists solely to *patch a DLL* to force PIE into UEFN, and its own README says UEFN is not designed for it. The symbol resolving and `is_in_play_in_editor()` returning `False` proves the binding exists, not that the feature works. **Use `SessionToolset`.** |
| Remote Control API | Proven absent five ways (no plugin folder, no module, six live reflection misses, no `UnrealBuildTool`, one whitelisted `.uplugin`). And it would add **zero reach**: `_ObjectBase.call_method()` already invokes UFUNCTIONs by raw name with no Python glue — verified live (`dev.call_method("GetUserOptionValues")` → 23-entry Map). |
| Editor Utility Widget bridge | No reach advantage (same UFunctions), no Python API to author the graph, and it puts a Blutility asset under `/TheScar/` where it can break publishing. |
| T3D clipboard round-trip for device *writes* | Superseded by `SetDeviceProperty`. Keep the **export half** as B6 — it is proven and useful as reconnaissance. |
| `set_device_options` in the listener | `set_user_option_value` needs a `PlayerController`; `None` silently returns `False`. Fabricating one is a two-line experiment worth ten minutes, not a design. |
| UI / VFX / shader / animation / probuilder / physics-config / packages / build / asset-gen / prefab / scene-create-load | No UEFN Python surface, or Epic ships it, or it is outside the permitted content pipeline. ~20 of Unity's 48 die here. |
| Mirroring Epic's toolsets into our namespace | Doubles maintenance, doubles schema cost, adds a hop. Point Claude at Epic's server. |

---

# 2. ARCHITECTURE

## 2a. Consolidation: **no `manage_*` verbs.** Here is the argument.

The token argument is real but it is being applied at the wrong scale. Run the numbers:

- Sidecar at 14 tools ≈ **1.5–2k tokens** of schema. That is under 1% of a 200k context.
- Unity's `manage_gameobject` has ~25 parameters. Any single call uses four. You do not save tokens by unioning twelve operations' parameters into one schema — you *move* them, and you add ambiguity: the model must now infer which of 25 params apply to `action="look_at"`, and a wrong `action`/`param` pairing fails at runtime instead of at schema-validation time.
- The genuine token-efficient pattern is not `manage_*` at all — it is **search/describe/execute**, which is what Epic built (`list_toolsets` / `describe_toolset` / `call_tool`) and what ChiR24's single `unreal` gateway does. That pattern costs a round trip per unknown tool, which at 3 Hz throttle is ~1 second of dead time.

So the rule is scale-dependent, and we sit on the good side of it:

> **Under ~20 tools: one tool per operation.** Typed params, schema-time validation, no dispatch round trip.
> **Over ~100 tools: search/describe/execute.** Epic already did this; do not duplicate it.
> **In between (Unity's 48): `manage_*` is a reasonable compromise.** We are not in between and should not aim to be.

Consolidate only where operations are genuinely one operation with a mode: `screenshot` (not three variants), `reflect(action=…)` (all introspection is one operation over one object graph), `dump_object(mode=…)`. That is it.

**The strongest anti-consolidation argument is the one nobody in the research made: we already have the ultimate consolidated tool.** `execute_python` is a single ~150-token schema that can do anything the listener can reach. Every first-class tool is a *specialisation* of it, justified only by frequency, fiddliness, or asynchrony. That framing tells you exactly which 14 to build and gives you a principled "no" for the rest.

## 2b. Listener changes

The existing pattern (`@_register` → `_HANDLERS` → `_dispatch` → `_run_on_main_thread` → `_serialize`) is good and should be kept. Five surgical changes, all additive:

**(1) Jobs — the async spine.** The current lifecycle is strictly synchronous: `do_POST` → `_command_queue` → one `_tick_handler` pass → `_responses` → reply, with `HTTP_TIMEOUT_SEC = 30`. Screenshots, validation and any Verse work exceed one tick and can exceed 30 seconds. Add:

```python
_JOBS: Dict[str, dict] = {}          # job_id -> {state, gen, result, error, started}

def _register_job(name):             # sibling of _register
    """Handler returns a GENERATOR. Tick pumps it one step per frame."""
```

In `_tick_handler`, after the command loop, pump every live generator one step. `yield` = still running; `return` = done. This is exactly Epic's own documented `AutomationScheduler` shape and it fits the tick pump you already own. `job_status` (B3) polls it. Cost: ~40 lines.

**(2) Transactions — 15 lines, biggest credibility win.** Wrap mutating dispatch:

```python
_MUTATING = {"spawn_actor", "delete_actors", "set_actor_transform",
             "set_actor_properties", "duplicate_actor", "batch"}
if command in _MUTATING:
    with unreal.ScopedEditorTransaction(f"MCP: {command}"):
        result = _dispatch(command, params)
```

Two things that will silently defeat this and must go in with it:
- **`obj.modify()` is mandatory** before mutating, or the transaction records nothing and Ctrl+Z does nothing. This is the single most common cause of "undo doesn't work" in UE Python.
- **Use `set_editor_property()`, not attribute assignment.** Attribute writes skip `PostEditChangeProperty`, leaving stale render/collision state. Epic states this explicitly.

Note `begin_transaction`/`end_transaction` were **absent** in the live probe — the scoped form is the only option here.

**(3) `batch` as a first-class handler**, executing inside one transaction and one tick. Raise `TICK_BATCH_LIMIT` from 5 only with a **time budget** (see risks) — a per-tick wall-clock cap of ~8 ms, breaking out early, so a slow handler cannot stall the editor.

**(4) Serialization discipline.** Add a `_serialize_actor_ref()` returning `{path, label, class}` only, and make list-style handlers use it. Keep the fat `_serialize_actor()` for single-actor detail calls.

**(5) Leave the tick lifecycle alone.** The research recommends `FTSTicker` over Slate tick because double-unregistering a Slate tick crashes the editor. **That risk is already correctly guarded here** — `cleanup()` and the module-level re-run block both null `unreal._mcp_tick_handle` immediately after unregistering, and the handle lives on the `unreal` module so re-executing the script shares it. Do not churn this code; it is one of the few parts that has clearly been debugged.

## 2c. `mcp_server.py` changes

**Move work out of the editor.** Three new tools live entirely in the external process and never touch the game thread: `read_editor_log` (B7), the Verse workflow client (C1/C2), and crash-dump reading. They keep working when the listener is dead — which, given it is dead right now and dies on every domain reload, is a design requirement, not a nicety.

**Wire Epic's server as a second entry, not a proxy.** In `G:\UEFN\TheScar\.mcp.json`:

```json
{ "mcpServers": {
    "unreal-mcp": { "type": "http", "url": "http://127.0.0.1:8000/mcp" }
} }
```

Keep `uefn` at user scope as-is. **Do not build a gateway yet.** A gateway (one curated list fronting both) is the right long-term shape, but it is a day of work whose value you cannot estimate until you know how much of Epic's surface you actually use. Two plain entries work in an hour. Revisit after two weeks of real use.

**Keep the port-scan discovery** (8765–8770) — it is correct and already handles the listener restarting on a different port.

---

# 3. BUILD ORDER

Each step lands something usable and is proved by **driving the editor**, never by reading a value back.

### Step 0 — Restore the baseline (20 min)

UEFN is running (PID 8292); the listener is not. Restart via Tools → Execute Python Script → `G:\UEFN\uefn-mcp-server\uefn_listener.py`.

Then measure latency honestly, because one claim is worth checking and cheap: `bThrottleCPUWhenNotForeground` is **absent** from `…\Saved\Config\WindowsEditor\EditorPerProjectUserSettings.ini`, i.e. defaulted on, which caps the editor main loop to ~3 Hz when unfocused.

> **Behavioural test.** Call `ping` 20 times with the UEFN window focused, then 20 times with it minimised, and print the two medians. If the unfocused median is ~330 ms, write `bThrottleCPUWhenNotForeground=False` under `[/Script/UnrealEd.EditorPerProjectUserSettings]`, restart the editor, and re-measure. Claim to beat: 337 ms → 14–31 ms. **I rate the mechanism plausible and the specific numbers UNPROVEN** — they come from one third-party README. Ten minutes settles it, and if it holds it is a 10–20× speedup on every call you already make.

### Step 1 — Turn on Epic's MCP (1 hour) ← *do this before writing any code*

Project Settings → Beta Access → tick **Python Editor Scripting** (already on) and **UEFN MCP Toolsets**. This writes `toolsets.bEnableToolsetsForProject = true` into `TheScar.uefnproject`. Editor Preferences → Model Context Protocol → set **Auto Start Server**, port 8000. Add the `.mcp.json` entry. New Claude Code session.

> **Behavioural test — the one that matters.** Pick the Barrier device whose `LabelOverride` reads `TrophyBarrier_W`. Call `SetDeviceProperty` to change it to `TrophyBarrier_TEST`. Then **look at the World Outliner and the Details panel in the running editor.** If the label changes on screen, the hardest blocked problem in this project is solved and roughly 60% of the proposed sidecar work evaporates. Set it back. Second test: `AddEventBinding` from the Timer's `Success` event to a HUDMessage's `Show` function, then open the HUDMessage's Functions panel and confirm the row is there. Third: edit a `.verse` file, call `BuildAll`, and confirm the returned diagnostics match what the Verse output panel shows.
>
> Also record: how many tools `tools/list` actually returns, and how large one `describe_toolset` reply is. The research's "~400 tools" and "44 KB per describe" are both **UNPROVEN** and they determine whether a gateway is needed later.

**Known cost, accept it consciously:** enabling MCP Toolsets is reported to silently stop `Content/Python/init_unreal.py` from running (Epic ticket FORT-1143572, unresolved) because toolset plugins initialise Python before UEFN mounts the project plugin. **This costs you nothing** — `STARTUP.md` deliberately rejects the auto-start hook to keep `Content/` clean, and the listener already starts manually. But it does mean that path is permanently closed, so stop treating it as a future option.

### Step 2 — Triage (2 hours, mostly reading)

With Epic's surface live, walk it once and delete from the plan everything it covers. Specifically check whether `GetDeviceProperties` returns the same 23 options as our `get_user_option_values()`, whether `VerseFieldsToolset` already exposes `@editable` values (killing B14), and whether any toolset exposes a screenshot or a console command (I found none — `ExecuteConsoleCommand` and `HighResShot` are in the binary but no toolset wraps them).

> **Behavioural test.** For every listener tool you propose to keep, name the Epic tool that does *not* cover it. If you cannot, delete ours. Write the resulting kill-list into `MCP_UPGRADE.md` — a conversation cannot be read by the next session.

### Step 3 — Listener architecture: jobs + transactions + batch (3–4 hours)

B2, B3, and §2b changes (1)–(4). No new capability, but it is the substrate for everything after and it makes the whole MCP undoable.

> **Behavioural test.** `batch` five `spawn_actor` calls in one transaction. Confirm five actors appear. Then **press Ctrl+Z once in the editor** and confirm all five vanish together. Then Ctrl+Y and confirm all five return. If one Ctrl+Z removes only one actor, `obj.modify()` is missing. This is exactly the kind of thing reading state back would pass and driving catches.

### Step 4 — Eyes: `screenshot` (3 hours)

B4 on the job spine from step 3. Compose with the existing `set_viewport_camera`.

> **Behavioural test.** Drive `set_viewport_camera` to a known landmark in The Scar, fire `screenshot`, poll `job_status`, then **open the returned PNG and describe what is in it.** Pass only if the description matches the landmark. Then fire three screenshots back to back with different filenames and confirm **three distinct files** exist — the documented failure is that batching in one script yields only the last, because the flag is consumed on a later engine tick. Then minimise the editor and repeat; if it fails unfocused, that is the SceneCapture2D fallback's justification and should be written down, not rediscovered.

### Step 5 — Discovery: `reflect` + `dump_object` (2–3 hours)

B5, B6. Small, cannot fail, and it multiplies the value of `execute_python` for every later task.

> **Behavioural test.** Ask `reflect` for the members of `FortExposedContentValidationSubsystem` — a class nobody has documented — and use only its output to write a working `execute_python` call against it, first try, no guessing. Then `dump_object(mode="t3d")` on the Barrier and confirm the output contains the `PlayerOptionData.PropertyOverrides` block with `BlockWeaponFire`. That block is already known to be there from the proven export, so it is a real regression check rather than a tautology.

### Step 6 — `read_editor_log` + `find_actors` (2 hours)

B7 and B8. Both pure context economics.

> **Behavioural test.** Deliberately cause a warning in the editor (rename an actor to a duplicate label, or run a bad `execute_python`). Then `read_editor_log(level="warning", since_marker=...)` and confirm the new warning is returned and nothing older is. For `find_actors`: query `by="class", query="Device_Barrier"` and confirm exactly 4 results and that the response is under ~40 lines — compare byte-for-byte against `get_all_actors` on the same level.

### Step 7 — Remainder, in this order (1 hour each)

`focus_editor` (C1) → `duplicate_actor` (B11) → `list_devices` + `get_device_options` (B12/B13) → `validate` (B9) → `console` (B10) → `get_verse_editables` (B14, only if step 2 shows `VerseFieldsToolset` doesn't cover it).

> **`focus_editor` test:** minimise UEFN, call it, and confirm the window comes forward — then confirm a subsequent `ping` that was previously timing out now returns. That is the documented bridge-reconnect pain point, fixed.
> **`validate` test:** deliberately break something Epic's rules forbid (a Verse digest in the Verse source directory is a documented violation), run `validate`, confirm it is reported, remove it, confirm the report clears.
> **`console` test:** `console("stat fps")` and confirm the FPS overlay **appears in the viewport**. Reading a return value proves nothing here — the call returns `None` by design.

---

# 4. RISKS

## Could destabilise or crash the editor

| Risk | Mechanism | Mitigation |
|---|---|---|
| **PIE entry** | Epic strips `StartPIE`/`StopPIE` from the UEFN toolset surface. UEFN has no in-process PIE; a community project patches a DLL to force it and warns it is unstable. | **Do not call `editor_request_begin_play()`.** Cut from the plan. Use `SessionToolset`. |
| **Slate tick double-unregister** | Unregistering the same handle twice crashes. | Already guarded correctly. Do not refactor that block. |
| **`tk.Tk()` twice** | Two Tk roots crash tcl. Already documented in the server's own instructions. | Keep `_get_tk_root()`; never let a new tool create a root. |
| **Long handlers stall the game thread** | `_tick_handler` runs up to `TICK_BATCH_LIMIT = 5` handlers per tick with **no time budget**. One slow handler (a big `get_all_actors`, a validation pass, a naive `batch`) freezes the editor for its whole duration. Epic warns their own tool calls cause hitching. | Add a per-tick wall-clock budget (~8 ms) and break out. Make `batch` yield across ticks via the job spine rather than looping inside one tick. |
| **Session/play kills the listener** | Domain reload / world change on session entry. Already observed: the listener died mid-session when a parallel session entered play mode. | Design every session tool fire-and-forget + poll. **Never run two Claude sessions against one editor** — this is already a standing rule and it was violated during the probe work. |
| **Off-main-thread `unreal.*`** | Any new code path that skips `_run_on_main_thread` is a crash. | The `@_register` contract already guarantees main-thread execution. Disk readers must live in `mcp_server.py`, not the listener, so this never comes up for them. |
| **Two servers, one game thread** | Epic's server serialises tool calls onto the game thread and warns clients must not overlap calls. Our listener does its own queueing. Nothing coordinates the two. | Prefer one at a time in practice. If contention shows up as hitching, that is the argument for building the gateway. |

## Could contaminate the shipped project

| Risk | Note |
|---|---|
| **`Content/` is bundled at publish.** | Standing rule, correctly enforced — I confirmed **zero `.py` under `G:\UEFN\TheScar\Content\`**. Keep the listener at `G:\UEFN\uefn-mcp-server`. The `init_unreal.py` hook stays uninstalled, and FORT-1143572 now makes that permanent anyway. |
| **The beta flag edits a tracked project file.** | Enabling MCP Toolsets writes `toolsets.bEnableToolsetsForProject` into `TheScar.uefnproject`. That is a real, committed change. Verified safe precedent: `ValkyrieExperimentalPythonSetting` is staged to Epic with `"bShouldBlockPublishing": false`, unlike Scene Graph animation which is `true`. **Confirm the toolsets setting carries the same non-blocking flag before publishing** — do not assume it. |
| **Agent-authored content is real content.** | Anything spawned, duplicated or property-set is in the island. Transactions (step 3) make it reversible; `validate` (step 7) makes it checkable. Epic's own guidance: modifying properties not shown in the UEFN UI **will fail validation**. Device options *are* shown, so writing them is permitted by policy — but a `SubobjectDataSubsystem` component add is exactly the kind of thing that is not. |
| **`.loreignore` does not exclude `.py`.** | A stray script anywhere tracked gets staged. Keeping it out of the project tree entirely means the question is never asked. |
| **Screenshots and dumps.** | Write to `%LOCALAPPDATA%\…\Saved\Screenshots\` or the scratchpad. Never to `Content/` or `Resources/`. |

## Could break on a UEFN version bump

| Fragility | Severity |
|---|---|
| **`__verse_0x…` mangled names** — the hex hashes the fully-qualified Verse path, not the identifier, and is **not derivable**. Rename a Verse module or move a file and every cached name is stale. | **High.** B14 must discover names at runtime every call, never cache them. |
| **Device option key strings** (`BlockWeaponFire`, `EnabledOnPhase`) are per-device-version. A `Device_Barrier_V2` → `V3` migration renames them silently. | High for anything that hardcodes keys. |
| **The :1962 protocol** is undocumented, reverse-engineered from a shipped VS Code extension, and has exactly three commands. Epic owes no compatibility. | Medium — C1/C2 only. |
| **Epic's `ToolsetPolicy` allowlist** is a C++ table. A bump can add or remove toolsets with no notice. | Medium, and it cuts both ways — most bumps will *add*. |
| **`unreal.*` Python surface.** `editor_request_begin_play` did not exist in 5.0–5.4 listings and appears in 5.6. Symbols come and go. | Medium. Every new tool should `hasattr`-guard its entry point and return a clean `{"ok": false, "error": "…not exposed in this build"}` rather than throwing. |
| **Toolset Python on disk** at `C:\Program Files\…` is overwritten by every Fortnite update. | Low — read it, never modify it. |

---

# 5. WHAT IS WRONG OR THAT I DON'T BELIEVE

**1. "Engine ++Fortnite+Release-41.30" — wrong.** It is 42.10. `Build.version` says so. The 41.30 in the brief is the *project's* `compatibilityVersion`. This single error invalidates the framing of the entire task, because it makes Epic's first-party MCP look like something to plan for rather than something already installed and switched off.

**2. The `unity-mcp-benchmark` report is built on that error.** Its whole "if you stay on 41.30, build six tools" branch and its `X → E` verdicts are answering a question that isn't live. The `other-ue-mcp` report contradicts it and is correct. Where the two disagree, believe the second.

**3. "Play mode is the single biggest gap vs Unity MCP, and it is available" (`MCP_UPGRADE.md` §2a) — I don't believe it, and I'd cut it.** The probe proves a *binding* exists, not a *feature*. Against it: Epic explicitly strips `StartPIE`/`StopPIE`/`IsPIERunning` from the UEFN toolset surface while shipping them elsewhere; UEFN's play model is Play-in-Client via `SessionToolset`, not in-process PIE; a third-party project exists solely to patch a DLL to force PIE in and documents it as unstable. Epic deleting their own working tool from this surface is the strongest evidence available that it does not work here. Calling it is a crash experiment, not a capability.

**4. The device-options doc history is self-contradictory and should be settled in writing.** The brief says *"THE READ HALF IS WRONG"*; `MCP_UPGRADE.md` §2b says *"the probe confirms §4 exactly — do not distrust that doc"* and explicitly retracts an earlier "half wrong" note as a conversation compression error. The *facts* are not in dispute (read works, write blocked). The docs are. Fix `MCP_UPGRADE.md` and `TheScar\CLAUDE.md` §4 to say the same thing once, and add the new fact: **write is solved by Epic's `SetDeviceProperty`, not by Python.**

**5. "Verse `@editable` values are invisible" (`MCP_UPGRADE.md` §2c) is too strong.** True as stated — they are not in `get_user_option_values()`. But they *are* real reflected properties, on the Verse instance subobject, under mangled `__verse_0x…` names; the on-disk `.uasset` name table proves it. "Not where we looked" was recorded as "not there". Worth correcting because it changes the authoring recommendation: wrapping behaviour in a Verse device with `@editable`s may be a *more* accessible pattern than configuring a Creative device, not a less accessible one.

**6. "Epic rejects custom Python toolsets" — UNPROVEN, and it is the highest-value open question in this plan.** The shipped `registration.py` says the creator surface *"is decided by `UE::ValkyrieToolset::ToolsetPolicy` alone"* — it does not say unknown registrations are refused. Meanwhile `toolset_registry.Registration` is a public class with a public `register()`, and Epic ships a complete worked template at `…\ToolsetRegistry\Content\Python\toolset_registry\tests\demo_toolset.py` (`@unreal.uclass()` on `unreal.ToolsetDefinition`, `@toolset_registry.tool_call @staticmethod`, type hints → JSON Schema, docstring → descriptions). **If custom toolsets register successfully in UEFN, the correct architecture is not a sidecar at all — our tools live inside Epic's server, on one port, with no listener, no restart-after-every-editor-restart, and no second MCP entry.** That is a strictly better end state than anything else in this document.

> **Exact probe.** With MCP Toolsets on, run from Tools → Execute Python Script (a file outside `Content/`):
> ```python
> import unreal, toolset_registry
> from toolset_registry.registration import Registration
>
> @unreal.uclass()
> class ScarProbeToolset(unreal.ToolsetDefinition):
>     """Probe toolset."""
>     @toolset_registry.tool_call
>     @staticmethod
>     def scar_probe_echo(msg: str) -> str:
>         """Echo a message.
>         Args:
>             msg: text to echo.
>         Returns:
>             The same text.
>         """
>         return f"scar_probe:{msg}"
>
> print(Registration([ScarProbeToolset]).register())
> ```
> Then run `ModelContextProtocol.RefreshTools` in the editor console and call `list_toolsets` / `describe_toolset` on `http://127.0.0.1:8000/mcp`. **If `scar_probe_echo` appears and returns, re-plan the whole sidecar around this path before writing step 3.** Do this in step 1, not later.

**7. "~400 tools" and "one `describe_toolset` reply is ~44 KB" — both UNPROVEN.** No count appears in the binary or the shipped Python; the tool list I reconstructed is plausible but unverified in aggregate, and the 44 KB figure traces to an unsourced forum remark. Both numbers decide whether a gateway is worth a day of work, so measure them in step 1 rather than inheriting them.

**8. The throttle numbers (337 ms → 14–31 ms) — UNPROVEN on this machine.** The mechanism is real UE behaviour and `bThrottleCPUWhenNotForeground` is absent from the ini here (so defaulted on), but the specific figures come from one third-party README. Step 0's A/B measurement settles it in ten minutes and it is the cheapest possible win if it holds.

**9. `validate` ≠ "will this publish".** The `uefn-specific` report calls scripted validation *"your day-one safety net"* and *"the strongest recommendation in this report"*. I'd temper that. `EditorValidatorSubsystem` runs registered `EditorValidatorBase` rules, which is real and useful, but the actual publish gate additionally builds a sentry manifest via `FortExposedContentValidationSubsystem` and runs upload-time checks. Selling it as a publish guarantee is exactly the kind of confident false pass this project has been bitten by. Ship it as a pre-flight.

**10. The third-party servers cited (`novikit/uefn-mcp-pro`, `quangdang46/uefn-verse-mcp`, `dylannalex/uefn-ai-toolkit`) — I did not verify any of them exist.** Their named techniques (CPU-throttle fix, SceneCapture screenshots, disk-first reads, refPath wrapping) are all mechanically plausible on their own merits and I have used them as *ideas*. Do not cite them as evidence.

**11. Two toolsets nobody's research mentioned** appear in the binary: `DynamicUIToolset.h` and `SpecialEventToolset.h`. Unknown scope. Enumerate them in step 2 — `DynamicUIToolset` in particular may be the UEFN HUD/UI surface, which The Scar uses heavily (`hud_manager.verse`, 3× `Device_HUDMessage_V2_C`).

**12. Confirmed accurate, for the record:** the 28-tool list; the `@_register`/`_dispatch`/`_run_on_main_thread`/`_serialize` description; `SubobjectDataSubsystem` having no property read/write methods; the T3D export working (proven artefact on disk); Remote Control being absent; and the `Content/`-hygiene rule (verified: no `.py` under `TheScar\Content`).

---

## Bottom line

The highest-value hour available is not writing a tool. It is ticking **Beta Access → UEFN MCP Toolsets** and confirming `SetDeviceProperty` changes a label you can see in the World Outliner. That one checkbox delivers device writes, device event bindings, Verse compilation with structured diagnostics, and play-session control — the four things this project has correctly concluded Python cannot do — and it is already installed on the machine.

Then keep the listener, deliberately small, for the six things Epic does not ship: **arbitrary Python, eyes, reflection, transactional batching, disk-first log reading, and console access.** Fourteen tools, one per operation, no `manage_*` verbs.

## Key paths

- `G:\UEFN\uefn-mcp-server\uefn_listener.py` — tick pump at line 788, `_register`/`_dispatch` at 187–206, lifecycle at 1160–1252, `TICK_BATCH_LIMIT = 5` at line 33
- `G:\UEFN\uefn-mcp-server\mcp_server.py` — `@mcp.tool()` wrappers from line 198; port discovery at 46
- `G:\UEFN\uefn-mcp-server\MCP_UPGRADE.md` — needs the 42.10 correction and the PIE retraction
- `G:\UEFN\TheScar\TheScar.uefnproject` — add `toolsets` block here (step 1)
- `C:\Program Files\Epic Games\Fortnite\Engine\Plugins\Experimental\ToolsetRegistry\Content\Python\toolset_registry\tests\demo_toolset.py` — the custom-toolset template for probe #6
- `C:\Program Files\Epic Games\Fortnite\FortniteGame\Plugins\Toolsets\ValkyrieToolset\Content\Python\valkyrie_toolset\registration.py` — Epic's registration contract
- `C:\Users\aayus\AppData\Local\UnrealEditorFortnite\Saved\Logs\UnrealEditorFortnite.log` — B7's source
- `C:\Users\aayus\AppData\Local\UnrealEditorFortnite\Saved\Config\WindowsEditor\EditorPerProjectUserSettings.ini` — throttle setting (currently absent/defaulted)
- `…\scratchpad\barrier_dev.t3d` — the proven T3D export showing `PlayerOptionData.PropertyOverrides`