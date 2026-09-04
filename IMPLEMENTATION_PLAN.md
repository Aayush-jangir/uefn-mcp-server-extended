# UEFN MCP — Implementation Plan

I re-ran ground truth in the **live editor** before writing this. The listener was up on 8765 (both research agents reported it down; it is not). Every claim marked **VERIFIED** below was produced by a probe I ran today, in `++Fortnite+Release-42.10`, PID 8292, with **Beta Access → UEFN MCP Toolsets OFF**.

That matters, because the single most important finding invalidates the central recommendation of *both* designs.

---

## 0. VERIFIED TODAY — the facts the plan is built on

| # | Fact | Probe that produced it |
|---|---|---|
| V1 | Editor is `++Fortnite+Release-42.10`, CL 57566230. The brief's "41.30" is `compatibilityVersion` in `TheScar.uefnproject`. | `cat "C:\Program Files\Epic Games\Fortnite\Engine\Build\Build.version"` |
| V2 | `TheScar.uefnproject` has **no `toolsets` block** (`grep -c toolsets` → 0). Python is on. Scene Graph is allowed (`bIsSceneGraphSystemAllowed: true`). | file read |
| V3 | **`unreal.ToolsetLibrary` is present with the beta flag OFF**, exposing 31 members incl. `get_object_properties`, `set_object_properties`, `list_struct_properties`, `get_derived_classes`, `get_derived_structs`, `undo_transaction`, `get_active_undo_count`, `set_editor_properties`, `modify`. | `execute_python` reflection dump |
| V4 | `SystemLibrary.begin_transaction` **and** `end_transaction` **and** `unreal.ScopedEditorTransaction` all exist. | same |
| V5 | `AutomationLibrary.take_high_res_screenshot` exists. `SystemLibrary.execute_console_command` exists. | same |
| V6 | `LevelEditorSubsystem` exposes all five play methods (`editor_request_begin_play`, `editor_request_end_play`, `editor_play_simulate`, `is_in_play_in_editor`, `editor_set_game_view`). | same |
| V7 | `EditorValidatorSubsystem` exposes `is_asset_valid`, `is_object_valid`, `validate_assets_with_settings`, `validate_changelist(s)`, `add_validator`. `FortExposedContentValidationSubsystem` class present. | same |
| V8 | **All of Epic's native toolset classes are exposed as `unreal.*` types**: `DeviceToolset`, `EntityToolset`, `SessionToolset`, `VerseToolset`, `ValkyriePythonToolset`, `EditorAppToolset`, `LogsToolset`, `VerseFieldsToolset`, `DynamicUIToolset`, `AgentSkillToolset`, + ~30 more. They have **no Python glue** (only base `UObject` methods) — but they have `call_method`. | `dir()` on each |
| V9 | **Their tool functions execute from plain Python via `call_method` on the CDO — flag off, Epic's MCP server not running, port 8000 dead.** Working calls, real data returned: `DeviceToolset.ListDeviceAssets()` → 392 device assets; `DeviceToolset.GetBindingOptions(device_path=SoftObjectPath)` → `target_functions: ("Enable","Disable","AddPlayerToIgnoreList",…)` for the actual Barrier; `SessionToolset.GetSessionStatus()` → `DISCONNECTED`; `SessionToolset.GetGameState()` → `UNCONNECTED`; `EditorAppToolset.IsPIERunning()` → `False`; `EntityToolset.ListEntityClasses()` → real Scene Graph classes; `LogsToolset.GetLogEntries()` → real log lines; `ValkyriePythonToolset.IsPythonEnabledInUEFN()` → `True`. | `unreal.get_default_object(unreal.DeviceToolset).call_method("ListDeviceAssets", args=())` etc. |
| V10 | **`EditorAppToolset.IsPIERunning` is one of the three functions Epic's `ToolsetPolicy` explicitly strips from UEFN — and it answered anyway.** The policy allowlist gates *the MCP server's tool list*. It does **not** gate `call_method`. | V9 |
| V11 | **`unreal.ToolsetRegistry` has real Python glue**: `get_all_toolset_json_schemas()`, `get_toolset_json_schema()`, `execute_tool()`, `register_toolset_class()`, `unregister_toolset_class()`, `is_toolset_registered()`, `is_toolset_class_registered()`, `is_available()`. `is_available()` → `True`. | `dir(unreal.ToolsetRegistry)` |
| V12 | `get_all_toolset_json_schemas()` returns **470,110 bytes of JSON: 12 toolsets, 168 tools**, each with full `inputSchema`. Registered right now, flag off: `EditorAppToolset`, `LogsToolset`, `GameplayTagsToolset`, `MVVMToolset`, 4× `NiagaraToolset_*`, `PhysicsAssetToolset`, `VerseFieldsToolset`, `WidgetAnimationToolset`, `UMGToolSet`. | `json.loads(...)` |
| V13 | The Valkyrie toolsets are **not registered** (`is_toolset_registered("DeviceToolset")` → `False`) and absent from V12's list — yet still callable per V9. Registration is what the beta flag buys; **capability is not.** | V11/V12 |
| V14 | **`DeviceToolset` is a *Verse-device* toolset, not a Creative-device toolset.** `ListDeviceProperties(device=<VerseDevice_C>)` returns a JSON Schema of the **real, unmangled Verse `@editable` names**: `eliminationManager`, `rowsToShow`, `objectiveLine`, `boardLeftMargin`, `boardTopMargin`, `debugSeedBoard`, `debugLogEliminations`. `GetDeviceProperties` returns their live values (`rowsToShow: 5`, `boardTopMargin: 270`, `debugSeedBoard: false`) and resolves object refs to `{"refPath": "…leaderboard_manager_0.__verse_0x2DD0D81D_EliminationManager"}`. Passing a **Creative** device (`Device_Barrier_V2_Placed_C`) is rejected: `Cannot nativize 'FortCreativeDeviceProp' as 'Device' (ObjectProperty)`. All 392 rows of `ListDeviceAssets` are `is_verse_device: True`. | direct calls |
| V15 | **Creative device options ARE readable as structured, writable-shaped data through `ToolsetLibrary`.** `unreal.ToolsetLibrary.get_object_properties(toy_options_component, ["PlayerOptionData"])` → `{"PlayerOptionData":{"propertyOverrides":[{"propertyScope":"","propertyName":"BlockWeaponFire","propertyData":"True"},…]}}`. The component's own class reflects fine via `list_struct_properties`. The symmetric `set_object_properties(obj, json)` exists (V3). | direct calls |
| V16 | `G:\UEFN\TheScar\CLAUDE.md:910` **already** says device options are readable via `get_user_option_values()` and that the setter needs a `PlayerController`. | grep |
| V17 | Listener anchors confirmed: `TICK_BATCH_LIMIT = 5` @33, `HTTP_TIMEOUT_SEC = 30.0` @34, `_run_on_main_thread` @112, `_serialize` @122, `_serialize_actor` @170, `_HANDLERS` @187, `_register` @190, `_dispatch` @198, `_cmd_execute_python` @296, `_tick_handler` @788, drain loop @802, `register_slate_post_tick_callback` @1171, unregisters @1213/@1243. `mcp_server.py`: `_discover_port` @47, `_send_command` @92, first `@mcp.tool()` @198. | grep |

**The consequence, stated plainly:** the entire capability set that both designs said requires enabling Epic's MCP server — device work, entity/Scene Graph work, session control, Verse compile, log reading, UMG, Niagara, physics assets, plus 168 fully schema-documented tools — is **already reachable from the listener we own**, today, through `execute_python`. Epic's server is a *transport* for capabilities that are sitting in the address space of the process our listener already runs inside.

---

## 1. Epic's first-party MCP: adopt, extend, or ignore?

**Decision: harvest it in-process; do not run it as a second MCP server; do not build a gateway.**

Concretely:
- **Do NOT** tick Beta Access → UEFN MCP Toolsets (as the default posture).
- **Do NOT** add `unreal-mcp` to `.mcp.json`.
- **DO** treat `unreal.ToolsetRegistry` + `call_method` on toolset CDOs as a first-class backend inside `uefn_listener.py`.

Why, in order of weight:

1. **Adopting the server buys transport, not capability** (V9/V13). We would gain an HTTP endpoint and lose arbitrary Python.
2. **The server's policy layer subtracts.** `ToolsetPolicy` strips `StartPIE`/`StopPIE`/`IsPIERunning` and excludes `BlueprintTools`, `data_asset`, `string_table` from UEFN. `call_method` reaches them (V10). Adopting the server means accepting a narrower surface than we already have.
3. **One game thread, one writer.** Epic's docs say its server serialises tool calls onto the game thread and clients must not overlap. Our listener does its own tick-queued marshalling. Two independent queues on one thread is a hang waiting to happen, and *nothing* coordinates them. Design B correctly identified this and then proposed a gateway mutex to solve it. The cheaper solution is to not create the problem.
4. **Enabling the flag has real costs**: it writes `toolsets.bEnableToolsetsForProject` into a tracked project file, and it permanently breaks `Content/Python/init_unreal.py` auto-start (FORT-1143572). We pay those for a transport we do not need.
5. **Agent ergonomics.** With `bEnableToolSearch` on, `tools/list` returns three meta-tools and every lookup costs a `describe_toolset` round trip. We can do the same discovery locally against a 470 KB JSON blob we can index once, in-process, with zero round trips (V12).

**The one thing the flag would buy** is *registration* of the Valkyrie toolsets so their JSON schemas appear in `get_all_toolset_json_schemas()` (V13). We have a cheaper candidate: `ToolsetRegistry.register_toolset_class(unreal.DeviceToolset)` has Python glue (V11). See probe **P1**. If that works, the flag buys us nothing at all and we get the Valkyrie schemas for free. If it does not, Phase 1 falls back to hand-written param maps for the ~35 Valkyrie functions, which is an afternoon.

**Revisit trigger, written down now:** if a future release adds toolset functions that are `AIRuntimeCallable`-only, or if `call_method` starts refusing un-allowlisted toolsets, we adopt the server and accept the gateway. Phase 0's capability manifest (below) detects this automatically on every listener start.

---

## 2. Disagreement ledger — A vs B, resolved

| # | Dispute | Ruling |
|---|---|---|
| 1 | Engine is 41.30 (brief) vs 42.10 (A and B) | **A and B both right, brief wrong.** VERIFIED V1. |
| 2 | Gateway fronting two servers (B) vs two plain `.mcp.json` entries, defer gateway (A) | **A right on the decision, B right on the reason.** B's "one game thread, one writer" is the correct analysis and is precisely why we run **one** server, not two. Neither's architecture survives §1 — there is no second backend to front. |
| 3 | Consolidate into 12 `manage_*` verbs (B) vs flat one-tool-per-operation (A) | **A right.** See §4. B's *other* point — that result payloads, not schemas, dominate token cost — is correct and I adopt it wholesale. |
| 4 | "The highest-value hour is ticking the beta checkbox" (A) vs "probe `ToolsetLibrary` before touching the flag" (B) | **B right, decisively.** VERIFIED V3/V9/V13: the capabilities are present with the flag off. A's headline recommendation would have mutated a tracked project file and broken `init_unreal.py` to obtain something we already had. |
| 5 | `DeviceToolset.SetDeviceProperty` is the answer to Creative-device option writes (A asserts as fact; B ranks it route 1 of 4) | **Both wrong.** VERIFIED V14: `DeviceToolset` operates on **Verse** devices; it rejects `FortCreativeDeviceProp`. A stated this as settled from a DLL string grep — exactly the "plausible web/binary-sourced API became an assumed fact" failure the brief warns about. |
| 6 | The Creative-device write path | **B's route 2 is the lead candidate and B deserves the credit.** VERIFIED V15: `ToolsetLibrary.get_object_properties` reads `PlayerOptionData.propertyOverrides` as clean JSON; `set_object_properties` is the symmetric writer. B rated this "UNPROVEN, and the cheapest thing on this list" — correct call, correct priority. |
| 7 | `SystemLibrary.begin_transaction`/`end_transaction` absent (A) vs present (B) | **B right.** VERIFIED V4. Both plus `ScopedEditorTransaction` exist. |
| 8 | No native Python undo trigger, use `EDIT UNDO` console (A) vs `ToolsetLibrary.undo_transaction()` (B) | **B right.** VERIFIED V3. |
| 9 | Cut PIE entirely (A) vs ship behind `hasattr` with a warning (B) | **A right on the decision.** But A's *reasoning* — "Epic stripped StartPIE, therefore it is broken" — is now known to be a bad inference: the strip is server-side policy and `IsPIERunning` answers fine via `call_method` (V10). The correct reason to cut it stands regardless: UEFN's play model is Play-in-Client via `SessionToolset`, and PIE entry triggers the world change/domain reload that kills the in-process listener. Don't build it. |
| 10 | Verse compile: `VerseToolset.BuildAll` primary, port 1962 fallback (A) vs 1962 primary (B) | **A right, and now stronger.** `VerseToolset` is callable via `call_method` (V8/V9), so `BuildAll` needs no flag, no reverse-engineered protocol, and does not kick VS Code off port 1962 (one client per source address). Keep a 1962 client for `focusEditor` only — it is the documented fix for the "bridge won't reconnect until the window regains focus" note in `CLAUDE.md`, and VS Code never uses that command. |
| 11 | Validation is a pre-flight (A) vs "the day-one safety net, ship it first" (B) | **A right on the claim, B right on the ordering.** `EditorValidatorSubsystem` runs registered validators (V7); the publish gate additionally builds a sentry manifest. Ship it early (B), sell it as pre-flight and never as a publish guarantee (A). |
| 12 | `bThrottleCPUWhenNotForeground` 337 ms → 14–31 ms | **Both right to distrust it.** Measure (A's A/B). Do **not** ship B's-rejected 15 s re-apply loop; if the ini resets, set *Editor Preferences → Use Less CPU when in Background* by hand once. |
| 13 | Slate tick vs `FTSTicker` | **Both right: don't churn.** @1171/@1213/@1243 already null the handle after unregister. Add an assert, change nothing. |
| 14 | "~400 tools" | **Both wrong for current state.** VERIFIED V12: **168 tools across 12 toolsets** registered right now. |
| 15 | "Fix `TheScar\CLAUDE.md` §4, it contradicts the brief" (A) vs "it is already correct, do not touch it" (B) | **B right.** VERIFIED V16 — line 910 already says readable. A was about to "fix" a correct doc based on the brief's stale correction. |
| 16 | Custom toolset registration: "Epic rejects custom Python toolsets" (research) vs "UNPROVEN, highest-value open question" (A) / "half right" (B) | **A right to flag it.** And better than either knew: `register_toolset_class` has Python glue (V11). Probe **P1**. |
| 17 | Third-party servers (`novikit`, `quangdang46`, `dylannalex`) | **A right to disclaim them.** I did not verify any of them exist either. Their *techniques* are ideas, not evidence. Nothing in this plan cites them as authority. |

---

## 3. UNPROVEN register — everything not in §0, with the probe that settles it

Nothing below may be written into code, a doc, or a commit message as fact until its probe passes. Each probe is one `execute_python` call.

| ID | Claim | UNPROVEN because | One-line probe |
|---|---|---|---|
| **P1** | We can register our own / the Valkyrie toolsets from Python | `register_toolset_class` exists but has never been called here | `unreal.ToolsetRegistry.register_toolset_class(unreal.DeviceToolset); print(unreal.ToolsetRegistry.is_toolset_registered("DeviceToolset"))` |
| **P2** | `ToolsetRegistry.execute_tool` is a usable generic dispatcher | glue exists, signature unknown | `try: unreal.ToolsetRegistry.execute_tool()\nexcept TypeError as e: print(e)` — the arg-name error reveals the signature |
| **P3** | **`set_object_properties` writes Creative device options and they persist** | read proven (V15), write never attempted | `unreal.ToolsetLibrary.set_object_properties(toy, json.dumps({"PlayerOptionData":{"propertyOverrides":[{"propertyScope":"","propertyName":"LabelOverride","propertyData":"MCP_PROBE_1"}]}}))` → then save → `grep -r MCP_PROBE_1 G:\UEFN\TheScar\Content\__ExternalActors__\` |
| **P4** | `set_object_properties` on a device fires `PostEditChangeProperty` / the Details panel redraws | reflection writers can skip edit-change plumbing | after P3, **look at the Details panel** without reselecting the actor |
| **P5** | `DeviceToolset.SetDeviceProperty` writes a Verse `@editable` | returns `void`; a bogus name returned `None` with no error, so return value carries zero signal | set `rowsToShow` to 7 on `leaderboard manager`, then `GetDeviceProperties` **and** grep the OFPA `.uasset` |
| **P6** | `VerseToolset.BuildAll` compiles and returns structured diagnostics | never called | `unreal.get_default_object(unreal.VerseToolset).call_method("BuildAll", args=())` |
| **P7** | `VerseToolset.ListFiles/ReadFile/WriteFile/Grep` param shapes | `ListFiles` needs `path` (error message, V9) — the rest unknown | call each with no args and read the `required argument '<name>' (pos N) not found` error |
| **P8** | `SessionToolset.StartSession`/`StartGame` work and survive the listener | status/state read fine; nothing driven | Phase 6 only, and only with the user watching |
| **P9** | `AutomationLibrary.take_high_res_screenshot` produces a file in UEFN | class + method exist (V5); task is latent, `is_task_done()` never flips inside a synchronous script | fire it, then check `Saved\Screenshots\` on the **next** tick |
| **P10** | `execute_console_command` actually executes in UEFN editor Python | present (V5); reliability contested in Epic's own forums with no resolution | `execute_console_command(world, "stat fps")` → **the FPS overlay appears in the viewport**. Return value is `None` by design and proves nothing |
| **P11** | `EditorValidatorSubsystem` catches a known-bad UEFN state | framework present (V7); coverage unknown | create a known violation, run it, confirm it is reported, revert, confirm it clears |
| **P12** | `bThrottleCPUWhenNotForeground` matters here | setting absent from `EditorPerProjectUserSettings.ini` (defaulted on); the 337→14 ms figures are third-party | 20 `ping`s focused vs minimised, median both ways, before/after the ini change |
| **P13** | `ToolsetLibrary.set_object_properties` respects transactions / is undoable | `require_editable` + `modify` exist in Epic's own wrapper; ours would bypass them | write inside `ScopedEditorTransaction`, Ctrl+Z in the editor, confirm the value reverts **on screen** |
| **P14** | Verse `@editable` writes survive a Verse rebuild | mangled `__verse_0x…` hashes the fully-qualified Verse path and is not derivable | P5, then `BuildAll`, then re-read |
| **P15** | UEFN publish accepts content authored this way | validation ≠ publish gate | out of scope until the user is ready to publish; **never claim it** |

**Explicitly demoted to UNPROVEN despite appearing as fact in the research:** "~400 tools" (V12 says 168 now); "one `describe_toolset` is ~44 KB" (unsourced); `RealTimeThumbnailSubsystem` does screenshots (name/lineage says Content Browser thumbnails); `PushChangesAndStartGameResults` implies push can start the game (symbol absent from binaries, explicitly labelled an inference by its own author); SceneCapture2D screenshots work while unfocused (third-party README).

---

## 4. Tool-surface shape

**Ruling: flat, one-tool-per-operation for the ~14 sidecar tools; plus a three-tool discovery/dispatch triad over `ToolsetRegistry` for the 168+ engine tools. No `manage_*` verbs anywhere.**

The token argument, run properly:

- 14 flat tools with tight schemas ≈ **1.5–2 k tokens**, under 1 % of a 200 k window. This is not a budget worth optimising.
- `manage_*` does not save 90 %; it saves maybe 40–50 %, because every parameter description survives and now has to additionally say *which actions it applies to*. Unity's `manage_gameobject` carries ~25 params and any real call uses four.
- `manage_*` moves failure from schema-validation time to deep inside a handler. `action="look_at"` with the wrong companion param is a runtime error the model cannot see coming. B's proposed mitigation (`action="capabilities"`) is an extra round trip to recover information a flat schema gives for free.
- **The genuinely token-efficient pattern is search/describe/execute, and we can build it better than Epic can**, because `get_all_toolset_json_schemas()` hands us the whole 470 KB corpus in one in-process call (V12). Index it once at listener start; `ue_tools_search` answers from RAM with no round trip. Epic's `describe_toolset` costs a network hop per lookup. That triad is ~600 tokens of schema and exposes 168 tools.

So the rule, scale-dependent and now grounded:

> **≤ ~20 first-party tools → flat.** **> ~100 → search/describe/execute over a machine-readable registry.** We are both, at once, and each half gets the shape that fits it.

**And the point that outranks the whole schema debate — B's, and it is correct:** the dominant token cost is **results**, not schemas. `get_all_actors` on The Scar (1092 external actors) fat-serialises every actor and can outweigh the entire tool list in one call. Every list-style tool returns `{path, label, class}` and nothing else; detail comes from a separate call on the handful you actually want. That change lands in Phase 2, before any consolidation argument would have mattered.

We already own the ultimate consolidated tool: `execute_python`. Every first-class tool is a *specialisation* of it and must earn its schema on one of three grounds — (a) the Python is fiddly and easy to get subtly wrong, (b) it runs on nearly every task, (c) it is latent and needs the two-phase pattern. "Unity has one" is not a ground. That filter kills ~30 of Unity's 48 before we ask whether UEFN can do them.

### The surface

**Discovery / dispatch (3)**
- `ue_tools_search(query, limit)` — ranked hits over the indexed 470 KB schema corpus; returns tool id + one-line description.
- `ue_tool_describe(tool_id)` — the exact `inputSchema` for one tool.
- `ue_tool_call(tool_id, args)` — dispatch. Backed by `ToolsetRegistry.execute_tool` if **P2** passes, else by `call_method` on the toolset CDO with a generated param map. **Carries the denylist (§7).**

**Sidecar first-class (14)** — the things `ue_tool_call` cannot or should not do:

| Tool | Why it earns a schema |
|---|---|
| `execute_python` *(exists — upgrade)* | Epic ships no arbitrary-Python tool. Add `transaction: str` and a `budget_ms` warning. Crown jewel; do not weaken it. |
| `batch(commands[], transaction, fail_fast)` | Collapses N HTTP round trips **and** N editor ticks into one, and makes N mutations one Ctrl+Z. |
| `job_status(job_id)` | Partner for every latent tool. Build once, reuse three times. |
| `screenshot(res, filename, camera, game_view)` → job | Latent (P9). Gives Claude eyes — the difference between "I set the transform" and "it looks right". |
| `reflect(action, target)` | `dir`/`getattr`/`ToolsetLibrary.list_struct_properties`/`get_derived_classes`. 208 subsystems are exposed and undocumented; this is what makes `execute_python` engineering instead of guessing. |
| `dump_object(path, mode)` | T3D export (proven working on this machine) + `ToolsetLibrary.get_object_properties`. Free `/remote/object/describe`, reaches Blueprint vars `dir()` hides. |
| `read_log(level, filter, since, cursor)` | **In `mcp_server.py`, off disk.** Zero game-thread cost, and it works when the editor is busy, hung, or the listener is dead. |
| `read_crashes(limit)` | Same, off `Saved\Crashes\UECC-*`. Tells us why the editor died last time. |
| `find_actors(query, by, cursor)` | Paths + labels only. The single cheapest context win available. |
| `get_device_options(target)` / `set_device_options(target, values)` | Creative devices, via `ToolsetLibrary` (V15/P3). No engine tool covers these. |
| `get_verse_editables(target)` / `set_verse_editables(target, values)` | Verse devices, via `DeviceToolset` (V14/P5). Thin, named wrappers because the schema/value split and refPath wrapping are exactly the fiddly bits (a). |
| `validate(scope, targets)` | Pre-flight. Ships early, sold honestly. |
| `focus_editor()` | TCP 1962 `focusEditor`, from `mcp_server.py`. Fixes the documented bridge-reconnect problem; VS Code never uses this command. |
| `raycast(start, end)` | The behavioural-verification primitive. Prove the prop is actually solid where you put it, instead of reading the transform back. |

That is **17 tools** total. `ping`/`status` stay. The other 26 existing tools stay as-is and get result-shaped in Phase 2.

---

## 5. Concrete changes

### `uefn_listener.py`

Keep the architecture. `@_register` @190 → `_HANDLERS` @187 → `_dispatch` @198 → `_tick_handler` @788 is good, and the tick lifecycle at @1171/@1213/@1243 is one of the few parts that has clearly been debugged. Six surgical, additive changes:

**5.1 — Capability manifest (new, ~30 lines, do this first).** At import, build `_CAPS: dict[str, bool]` by `hasattr`-probing every entry point this plan depends on (`ToolsetLibrary`, `ToolsetRegistry`, each toolset class, `AutomationLibrary.take_high_res_screenshot`, `SystemLibrary.begin_transaction`, …). Every handler guards on it and returns `{"ok": false, "error": "<X> not exposed in this build"}` rather than throwing. `status` returns the manifest. **This is the version-bump tripwire**: the day Epic changes the surface, the manifest says so on the next listener start instead of a tool failing mysteriously three weeks later.

**5.2 — Toolset bridge module** (`_toolsets.py`, in `G:\UEFN\uefn-mcp-server`, never in `TheScar\Content\`). Owns: the schema index built from `get_all_toolset_json_schemas()`, the `tool_id → (class, UFunction, param map)` table, the `SoftObjectPath`/`refPath` auto-wrap on the way in and unwrap on the way out (V9/V14 prove both conventions are load-bearing), and the denylist. `ue_tool_call` is 20 lines on top of this.

**5.3 — Latent jobs.** `_dispatch` currently runs a handler to completion inside one tick (@788–802), with `HTTP_TIMEOUT_SEC = 30.0` @34. Screenshots, validation and `BuildAll` exceed one tick and can exceed 30 s. Add a `@_register_job` sibling whose handler returns a **generator**; `_tick_handler` pumps every live generator one step per frame after the command drain. `yield` = running, `return` = done. ~40 lines, and it is exactly the shape of Epic's own documented `AutomationScheduler` pattern.

**5.4 — Transactions.** Wrap mutating dispatch:

```python
_MUTATING = {"spawn_actor","delete_actors","set_actor_transform","set_actor_properties",
             "duplicate_actor","set_device_options","set_verse_editables","batch","ue_tool_call"}
prior = unreal.ToolsetLibrary.get_active_undo_count()
unreal.SystemLibrary.begin_transaction("MCP", f"MCP: {command}", None)
try:    result = _dispatch(command, params)
finally: unreal.SystemLibrary.end_transaction()
committed = unreal.ToolsetLibrary.get_active_undo_count() > prior
```

Two details that silently defeat this and must land in the same commit, both lifted from Epic's own `programmatic.py:966–999`: **`obj.modify()` is mandatory** before mutating or the transaction records nothing and Ctrl+Z does nothing; and **`UTransBuffer::End` silently drops a transaction with no UObject modifications**, so the count snapshot is what tells you whether a record actually committed. Also: **use `set_editor_property`, never attribute assignment** — attribute writes skip `PostEditChangeProperty` and leave stale render/collision state.

**5.5 — Time budget on the tick.** @802 drains up to `TICK_BATCH_LIMIT = 5` handlers per tick with **no wall-clock cap**. One slow handler (a big `get_all_actors`, a validation pass, a naive `batch`) freezes the editor for its whole duration; the editor does not tick during Python execution. Add an ~8 ms budget and break out. `batch` yields across ticks via 5.3 rather than looping inside one.

**5.6 — Result shaping.** Add `_serialize_actor_ref(actor) -> {path,label,class}` beside `_serialize_actor` @170 and switch every list-style handler to it. Add `page_size`/`cursor` to `get_all_actors`, `list_assets`, `search_assets`.

### `mcp_server.py`

Three tools live entirely in the external process and never touch the game thread — `read_log`, `read_crashes`, `focus_editor`. They keep working when the listener is dead, which given domain reloads is a design requirement, not a nicety. `_discover_port` @47 and `_send_command` @92 are correct; leave them. New: a `VerseWorkflowClient` (TCP 1962, `Content-Length` framing, **connect-per-call and close immediately** so VS Code is kicked for milliseconds, `focusEditor` only). No `EpicClient`. No gateway. No mutex — there is only one writer.

### Docs

`MCP_UPGRADE.md` needs: the 42.10 correction; the PIE retraction; §5 of this document; and the capability manifest as the standing source of truth. **`G:\UEFN\TheScar\CLAUDE.md` §4 is correct as written (V16) — do not "fix" it.** Append only: Creative device options are *structured*-readable via `ToolsetLibrary.get_object_properties(toy, ["PlayerOptionData"])`, and Verse `@editable`s are readable by their real names via `DeviceToolset`.

---

## 6. Build order

Every phase ends with something usable and a test that **drives the thing**. No phase passes on a read-back of the value just written.

### Phase 0 — Tripwire and baseline *(2 h)*
Ship 5.1 (capability manifest) and run **P1, P2, P7, P12**.

> **Test.** Restart the listener; `status` returns a manifest listing every entry point with a boolean. Deliberately misspell one probe target in the source, restart, and confirm the manifest reports `false` and the dependent tool returns a clean `not exposed in this build` instead of a traceback. Then: 20 `ping`s focused, 20 minimised, print both medians; apply the ini change; re-measure. **Record all four numbers.** If the gap does not move materially, drop the throttle change entirely.

### Phase 1 — The registry triad *(4 h)*
5.2 + `ue_tools_search` / `ue_tool_describe` / `ue_tool_call`, with the denylist.

> **Test.** Without reading any documentation and without `execute_python`: `ue_tools_search("niagara component")` → pick a tool → `ue_tool_describe` → `ue_tool_call` it and get real data back, first try. Then `ue_tool_call("ValkyrieToolset.DeviceToolset.GetBindingOptions", {"device_path": "<barrier path>"})` and confirm it returns the same `("Enable","Disable","AddPlayerToIgnoreList",…)` I got today — a real regression check against a known-good result, not a tautology. Then confirm a denylisted id (`ModelContextProtocol.StopServer`, anything PIE) is **refused by the dispatcher**, not by the engine.

### Phase 2 — Result shaping *(3 h)*
5.6 + `find_actors`.

> **Test.** `find_actors(by="class", query="Device_Barrier")` returns exactly **4** rows and a response under 4 KB. Byte-count it against `get_all_actors` on the same level and put both numbers in the commit message. Measured, not estimated.

### Phase 3 — Transactions, batch, jobs *(4 h)*
5.3 + 5.4 + 5.5 + `batch` + `job_status` + `raycast`. No new capability; this is the substrate.

> **Test.** `batch` five `spawn_actor` calls in one transaction. `raycast` from 500 units above each spawn point straight down and confirm **five hits**. Press **Ctrl+Z once in the editor**. Raycast the same five rays and confirm **zero hits**. Ctrl+Y, confirm five hits again. If one Ctrl+Z removes only one actor, `obj.modify()` is missing. This is precisely the failure a read-back would pass and driving catches.

### Phase 4 — Eyes and ears *(4 h)*
`screenshot` on the job spine (**P9**), `read_log`, `read_crashes`, `focus_editor`.

> **Test.** Drive `set_viewport_camera` to a named landmark in The Scar, fire `screenshot`, poll `job_status`, **open the PNG and describe what is in it** — pass only if the description matches the landmark. Then fire three shots back-to-back with different filenames and confirm **three distinct files**; the documented failure is that a synchronous batch yields only the last, because the flag is consumed on a later tick, so this is the proof that 5.3 works. Then minimise the editor and repeat; if it fails unfocused, write that down as the SceneCapture2D justification rather than rediscovering it later. For `read_log`: cause a warning on purpose, confirm `read_log(level="warning", since=…)` returns it and nothing older. For `focus_editor`: minimise UEFN, call it, confirm the window comes forward **and** that a `ping` which was previously timing out now returns.

### Phase 5 — Device and Verse properties *(6 h — the payload)*
`get_device_options` / `set_device_options` (**P3, P4, P13**), `get_verse_editables` / `set_verse_editables` (**P5, P14**), `validate` (**P11**).

> **Test — and the oracle is disk, never the read-back.** Set `LabelOverride` on a Barrier to `MCP_PROBE_<timestamp>`. Then: (a) **look at the World Outliner and the Details panel** without reselecting — does the label change on screen (P4)? (b) `save_current_level`, then from Bash `grep -r MCP_PROBE_<timestamp> "G:\UEFN\TheScar\Content\__ExternalActors__\"` — is it on disk (P3)? (c) `validate` clean (P11)? (d) Ctrl+Z in the editor — does it revert **on screen** (P13)? Then the Verse half: set `rowsToShow` to 7 on `leaderboard manager`, same four checks, then `BuildAll` and re-read to confirm the mangled-name binding survived a rebuild (P14). Revert everything.
>
> If P3 fails, fall back in this order: `component.call_method("SetOptionValue", …)` with the real UFunction name recovered from `OBJ DUMP`, then T3D round-trip. **Do not ship the T3D route without a reference audit** — it deletes and recreates the actor, producing a new OFPA GUID, and The Scar has 9 `VerseDevice_C` actors whose `@editable` object refs point at devices by soft path (V14 shows exactly such a ref).

### Phase 6 — Verse build and session *(4 h, with the user present)*
`ue_tool_call` into `VerseToolset.BuildAll` (**P6**) and `SessionToolset` (**P8**).

> **Test.** Introduce a known syntax error at a known line in a scratch `.verse` file → `BuildAll` returns `numErrors ≥ 1` with a diagnostic whose `StartLine` matches the line broken → fix → `numErrors == 0` **and** the editor log shows `VerseBuild: Build complete.` (cross-check; never report green on the tool alone). Then session: `StartSession` → `StartGame` → confirm from `GetClientLogEntries` that a `Print` string which only executes at game start appears. Session status is state; a log line from our own Verse code is behaviour. **Expect the listener to die here** — that is the domain-reload risk, and it is why this phase is last and supervised.

### Phase 7 — Long tail *(as needed)*
`reflect`, `dump_object`, `execute_console_command` (**P10** — `stat fps`, confirm the overlay appears in the viewport; the return value is `None` by design and proves nothing), `duplicate_actor` from hand-configured templates.

---

## 7. The single highest-risk item

**We are building the entire plan on `call_method` / `execute_tool` against native toolsets that Epic's own `ToolsetPolicy` has not allow-listed for UEFN — a reflection path that provably bypasses their policy layer (V10).**

Two ways it hurts:

1. **It can crash or hang the editor.** Epic stripped `StartPIE`/`StopPIE`/`IsPIERunning` from the UEFN surface for a reason we do not know. `call_method` will happily invoke them, and any of ~35 un-vetted Valkyrie functions, on the game thread with no policy check. UEFN's PIE is not designed to exist; a community project patches a DLL to force it and calls it unstable.
2. **It can vanish without warning.** A version bump that renames a UFunction, changes a param type, or moves the toolsets out of the Python-visible `unreal` module breaks every dependent tool at once, silently, with a `Failed to find function` deep in a handler.

**What to do about it — four things, all in Phase 0/1, none optional:**

- **A hard denylist in `ue_tool_call`, enforced in `_toolsets.py` before dispatch.** Deny by explicit id: anything PIE (`StartPIE`, `StopPIE`, `IsPIERunning`), anything on `ModelContextProtocol.*` (`StopServer`), `ValkyriePythonToolset.EnablePythonInUEFN`, `ToolsetRegistry.unregister_toolset_class`, plus a console-command denylist (`quit`, `exit`, `crash`, `obj gc`). Refuse at the dispatcher so the model gets a clean error, never at the engine.
- **`ue_tool_call` is allow-list-first for writes.** Reads: anything not denied. **Writes: only tool ids we have driven at least once and recorded.** An unrecorded write id returns "not yet validated on this build; run it through `execute_python` first and add it."
- **The capability manifest (5.1) is the tripwire.** It snapshots the exact set of entry points this plan depends on at every listener start and reports diffs. That converts "mysteriously broken three weeks from now" into "the manifest says `DeviceToolset` went away".
- **A `--supported-only` fallback mode.** One flag that restricts the listener to documented `unreal.*` APIs plus `execute_python`. If a bump breaks the bypass, we degrade to the 28-tool baseline plus result shaping and transactions rather than to nothing. Write this in Phase 1 while the shape is fresh; it is 30 lines and it is the difference between a bad afternoon and a rebuild.

**Tight second:** writing device/`@editable` properties through an unofficial reflection path that succeeds in memory but does not persist, does not fire `PostEditChangeProperty`, or produces content that fails publish validation. Mitigated entirely by Phase 5's disk-grep oracle — the read-back is not evidence, and neither is the Details panel alone.

---

## 8. WHAT WE SHOULD NOT BUILD

- **A gateway.** Its only real justification was cross-server game-thread arbitration (B's best argument). There is one server, so there is nothing to arbitrate. A day of work for a mutex protecting a race we chose not to create.
- **A second MCP entry for Epic's `unreal-mcp`.** §1. Buys transport, costs arbitrary Python, a policy layer that subtracts, a tracked project-file mutation, FORT-1143572, and an uncoordinated second writer on the game thread.
- **Mirrors of engine tools in our namespace.** Do not write `manage_material`, `manage_ui`, `manage_vfx`, `manage_physics`, `manage_entity`, `manage_asset` wrappers around toolsets `ue_tool_call` already reaches. Doubles maintenance, doubles schema cost, adds a hop, and goes stale on every bump.
- **PIE control.** §2 row 9. Not because the binding is missing — it is present and `IsPIERunning` answers — but because UEFN's play model is Play-in-Client and PIE entry triggers the domain reload that kills the listener. `SessionToolset` is the sanctioned path.
- **Remote Control API.** Proven absent five ways, and **moot**: `call_method` (V9) plus `ToolsetLibrary.get/set_object_properties` (V3/V15) already provide both of its supposed superpowers.
- **An Editor Utility Widget / Blutility bridge.** No reach advantage (same UFunctions), no Python API to author K2 graphs, and it puts an asset under `/TheScar/` that can break publishing for zero benefit.
- **`uefn_docs` / any web-scraped documentation tool.** Epic's own digests at `Saved\VerseProject\TheScar\Digests\*.digest.verse` are the authoritative API surface *for this exact build*, already on disk. A grep over them beats scraped docs, and Claude has WebFetch anyway.
- **A 15-second background loop rewriting `EditorPerProjectUserSettings.ini`.** If something resets that ini we do not understand it, and fighting it in a loop is a smell. One manual toggle of *Use Less CPU when in Background*, and only if P12 shows a real gain.
- **`manage_tools` / tool groups.** Unity needs it at 48 tools. We are at 17 plus a search triad.
- **Unity's genuinely inapplicable half — ~20 of 48:** `manage_build`, `manage_packages`, `run_tests`/`get_test_job` (UEFN has no test framework and Verse has no unit tests), `manage_shader`, `manage_probuilder`, `manage_animation`, `manage_scriptable_object`, `manage_scene(create/load/close)` (a UEFN island is one persistent level), `generate_image`/`generate_model`/`generate_audio`, `import_model` (generated meshes will usually fail content validation), `set_active_instance` (one editor, one listener, by standing rule), `debug_request_context`, `execute_custom_tool`.
- **Caching mangled `__verse_0x…` names anywhere.** The hex hashes the fully-qualified Verse path, not the identifier. Rename a module or move a file and every cached name is stale. Re-enumerate through `DeviceToolset` every call — which is now cheap, because it returns the clean names (V14).
- **Anything at all under `G:\UEFN\TheScar\Content\`.** `.loreignore` does not exclude `.py`, and UEFN Supplemental Terms §2 covers shipped content that opens connections to non-Epic servers — which is the exact shape of a listener binding `127.0.0.1:8765`. Keeping it out means the question is never asked. FORT-1143572 makes the `init_unreal.py` auto-start path moot anyway.

---

## Three things worth saying unprompted

1. **The brief's framing — "a lot of things are not accessible from the MCP connection" — was true of the *tools*, not of the *editor*.** Everything Unity's benchmark has that UEFN can meaningfully have was already sitting inside the process the listener runs in. The work is plumbing and discipline, not capability acquisition. That is good news and it should change how the next session estimates this kind of task.

2. **Design A's headline recommendation would have been an unforced error.** "The highest-value hour available is ticking Beta Access → UEFN MCP Toolsets" would have mutated a tracked project file, permanently broken `init_unreal.py`, and introduced a second uncoordinated writer on the game thread — to obtain capabilities we demonstrably already had. It reached that conclusion by grepping symbol names out of a DLL and treating them as a working API. That is exactly the failure mode the brief warned about, and it is why P1–P15 exist as gates rather than as notes.

3. **`DeviceToolset` being Verse-only (V14) is the most consequential single correction in this document, and it cuts both ways.** The bad news: Epic did not solve Creative-device writes for us. The good news is bigger — it hands us the real, unmangled `@editable` names and values for Verse devices, which kills the whole `__verse_0x…` name-derivation problem. Combined with V15, it means **the accessible authoring path in UEFN is a Verse device with `@editable`s, not a hand-configured Creative device.** That is a design conclusion about The Scar, not just about the MCP, and it belongs in the island's design doc before the next content push — not just in this plan.

**Key paths:** `G:\UEFN\uefn-mcp-server\uefn_listener.py` (anchors in V17) · `G:\UEFN\uefn-mcp-server\mcp_server.py` · `G:\UEFN\uefn-mcp-server\MCP_UPGRADE.md` (needs §5's corrections) · `G:\UEFN\TheScar\CLAUDE.md:910` (correct — append only) · `G:\UEFN\TheScar\TheScar.uefnproject` (leave the `toolsets` block absent) · `C:\Users\aayus\AppData\Local\UnrealEditorFortnite\Saved\Logs\UnrealEditorFortnite.log` (`read_log` source) · `C:\Users\aayus\AppData\Local\UnrealEditorFortnite\Saved\Config\WindowsEditor\EditorPerProjectUserSettings.ini` (throttle, currently absent/defaulted) · `C:\Program Files\Epic Games\Fortnite\Engine\Plugins\Experimental\ToolsetRegistry\Content\Python\toolset_registry\` (registration contract for P1) · `C:\Program Files\Epic Games\Fortnite\Engine\Plugins\Experimental\Toolsets\EditorToolset\Content\Python\editor_toolset\toolsets\programmatic.py:966-999` (the transaction pattern to copy verbatim).