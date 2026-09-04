# Unattended session log — 2026-09-04

Started ~16:30 local. Aayush away ~5 hours. Updated as work completes, so it is
accurate at any moment the session might end.

## Ground state at start

- Listener alive on **8775**, loaded fresh from the committed file, 40 handlers.
- Editor open on **TheScar**, **zero dirty packages**.
- **The Scar matchmaking change is DONE and saved** — `Matchmaking_MinPlayers` and
  `Matchmaking_OvertimePlayerTarget` both 2 → 1, confirmed on API + disk + Details panel.
  **Not touched again this session.** Lore check-in and publishing wait for Aayush.
- Repo clean at `65db34b`, pushed.

## Status board

| # | Item | Status |
|---|---|---|
| 1 | Denylist | **DONE, pushed** |
| 2 | Capability manifest | **DONE, pushed** |
| 3 | Result shaping | **DONE, pushed** |
| 4 | Discovery triad | **DONE, pushed** |
| 5 | Sidecar tools | **PARTIAL** — raycast/find_actors/batch shipped; reflect, dump_object, job_status deferred |
| 6 | `--supported-only` fallback | **DONE, pushed** |
| 7 | Drift check (no editor needed) | **DONE, pushed** |
| 8 | Docs + draft upstream PR (no editor needed) | IN PROGRESS |

## Needs Aayush

- Nothing yet.

## Log

- **16:30** — Session start. Verified ground state above. Beginning item 1.
- **16:45** — **Item 1 DONE.** Denylist enforced at the listener's dispatcher.
  Refuses by tool id (PIE: StartPIE/StopPIE/IsPIERunning; StopServer;
  EnablePythonInUEFN; unregister_toolset_class; the whole
  `ModelContextProtocol.*` namespace) and by console command (quit, exit,
  crash, obj gc, gc, r.setres…). Tested live: 6/6 denied ids refused, 2/2
  legitimate ids allowed, `quit` and `obj gc` refused, `stat none` still
  works. Deliberately NOT enforced for `execute_python` — a denylist there
  is theatre, since arbitrary Python reaches the same symbols; noted in the
  code. New `denylist` tool reports what is blocked. Beginning item 2.
- **17:10** — **Item 2 DONE.** Capability manifest: 40 named entry points
  probed (no reflection sweeps), baseline stored at
  `snapshots/capability_manifest.json`, diffed on every listener start and
  logged loudly on loss. All 40 present today. Engine reports
  `6.0.0-57566230+++Fortnite+Release-42.10`, independently confirming §9a.
  **Verified the alarm actually fires** rather than assuming: seeded the
  baseline with two entries that cannot exist, got `ok: false, lost_count: 2`
  with both named, then restored the real baseline and reconfirmed clean.
  Beginning item 3.
- **17:35** — **Item 3 DONE.** Result shaping, measured on TheScar:


  | call | before | after | saved |
  |---|---|---|---|
  | `get_all_actors` full list | 655,393 B | 249,191 B | **62.0%** |
  | `get_all_actors summary_only` | 655,393 B | 1,966 B | **99.7%** |
  | `get_all_actors limit=5` | 655,393 B | 1,400 B | **99.8%** |
  | `list_devices` | 32,500 B | 14,103 B | **56.6%** |


  Honest caveat: 62% off the fat shape still leaves 249 KB for all 1108
  actors, because the path string is most of the remaining payload and is
  needed for addressing. **A full unfiltered listing should basically never
  be requested** — the real win is that `summary_only` and `limit` make the
  common cases ~99.7% smaller, and the tool description now says so.
  Added paging (`limit`/`offset`/`has_more`), a `by_class` histogram, and
  opt-in `detail`. Verified `detail=true`, `class_filter` and
  `get_selected_actors` all still work. Beginning item 4.
- **18:05** — **Item 4 DONE.** Discovery triad live over all 168 engine tools.
  **P2 settled:** `execute_tool(toolset_name, tool_name, json_input) ->`
  `ToolCallAsyncResultString`, signature revealed by argument-name errors.
  Index built once at 168 tools / 12 toolsets and answered from RAM.
  Verified live, not assumed: search (`log` -> 19 matches, `gameplay tag` -> 7),
  describe (full inputSchema for `LogsToolset.GetLogEntries`), and **real
  dispatch** — `GetLogEntries` returned actual log lines in an 874-byte
  payload. Both guards fire: `EditorAppToolset.StartPIE` refused by the
  denylist, `EditorAppToolset.CreateCollection` refused as an unlisted WRITE
  tool. Write allow-list seeded empty at
  `snapshots/tool_write_allowlist.json` — reads run freely, writes must be
  driven deliberately once and recorded. Beginning item 5.
- **18:40** — **Item 5 PARTIAL.** Shipped `raycast`, `find_actors`, `batch`
  (49 listener handlers, 47 MCP tools). All three tested live: raycast hits a
  known floor at z=8 and correctly misses in empty sky; find_actors finds 11
  "manager" labels; batch ran 3 commands in one tick, 3/3 succeeded.


  **HIT A STOP CONDITION on raycast detail, and stopped.** The HitResult
  struct exposes NO fields to Python in this build — `location`,
  `impact_point`, `impact_normal`, `distance`, `hit_actor` and the rest are
  absent via BOTH `get_editor_property` and direct attribute access, and
  `GameplayStatics.break_hit_result` is absent too. Two independent probes,
  both empty, cause not understood. Per the stop rule I did not keep guessing
  names. **raycast ships reporting hit/no-hit only**, with
  `detail_available: false` and an explanation, rather than returning nulls
  labelled "location" — which would be a false pass of exactly the kind this
  project keeps catching. Hit/miss is still the useful half: it answers "is
  something solid actually there?".


  **Deliberately deferred: `reflect`.** The plan wants it built on `dir()`.
  Blind reflection enumeration is what crashed the editor before, and with
  nobody available to restart it, shipping a dir()-based tool tonight is the
  wrong trade. Needs a capped, non-recursive, never-call design and a human
  present. `dump_object` and `job_status` deferred for time. Moving to item 7
  (needs no editor).
- **19:20** — **Item 7 DONE.** `snapshots/drift_report_2026-09-04.md`,
  reproducible via `tools/drift_check.py`.


  **Headline finding: not one scalar `@editable` in TheScar is overridden.**
  All 74 scalars equal their `.verse` defaults; the only 25 overrides are
  device bindings. So the tuning lives in the SOURCE, not the Details panel.
  That narrows TRAP 5 usefully: a rename cannot silently revert a tuned
  number (there are none), but it WOULD silently unbind a device — a louder,
  more findable failure. It also means tuning changes belong in `.verse`, and
  anyone "just tweaking it in the panel" would create a divergence that makes
  the source misleading from then on.


  **DOC DRIFT: 0 — and I do not present that as an all-clear.** The first pass
  reported **15 findings and every one was a false positive**: `goldReaperThreshold`
  5000 vs "13" was matching the words *Day 13*; object refs and booleans matched
  stray prose numbers; `deckHeights [17,402]` vs `[17.0, 402.0]` was actually a
  MATCH my comparator broke. All 15 are listed and rejected in the report.
  Only 2 of 99 editables are numeric AND stated in a doc in comparable form, so
  the method is too weak to prove absence — the report says so in its own
  "LIMITS" section.


  **Also caught a bug that would have faked a clean pass:** the first run scored
  0/99 because the API returns lower-camel (`auraRefreshSeconds`) while the
  source declares PascalCase (`AuraRefreshSeconds`). A tidy-looking all-zero
  result that was entirely a matching bug. Beginning item 8.
- **19:40** — **Item 6 DONE.** `--supported-only` fallback mode. Disables the
  six reflection-backed commands (the triad + the two Verse tools + reindex)
  while every documented `unreal.*` tool and `execute_python` keeps working.
  Enabled by `UEFN_MCP_SUPPORTED_ONLY=1`, by the `supported_only` tool, or
  **automatically when the capability manifest reports losses** — so a broken
  build degrades on its own with nobody present. Verified live: with it on,
  `ue_tools_search` refuses with a clear message while `find_actors` still
  works; turning it off restores 19 search matches.
