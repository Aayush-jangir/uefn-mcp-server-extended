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
| 1 | Denylist | **DONE** |
| 2 | Capability manifest | **DONE** |
| 3 | Result shaping | **DONE** |
| 4 | Discovery triad | **DONE** |
| 5 | Sidecar tools | **PARTIAL** — `raycast`, `find_actors`, `batch` shipped; `reflect`, `dump_object`, `job_status` not built |
| 6 | `--supported-only` fallback | **DONE** |
| 7 | Drift check | **DONE** |
| 8 | Docs + draft PR | **DONE** (PR written, **not submitted**) |

All eight items touched, seven complete. **48 MCP tools / 50 listener handlers**, up from
41/42 at session start. Nine commits, all pushed to `extended-editor-control`.

---

## THE SEAM IS CLOSED — verified 2026-09-05

The overnight work was all hot-patched, and this section used to say so and ask for a
cold-start check. **Aayush restarted the listener and it has now been verified from the
committed file.**

- Listener probed for `_is_device` — a symbol that only ever existed in the hot-patched
  namespace. **Absent.** Verdict: **FRESH FROM DISK**.
- **50 handlers**, and all eight new commands present (`denylist`, `capability_manifest`,
  `ue_tool_call`, `raycast`, `batch`, `find_actors`, `supported_only`, `set_verse_editable`).
- Independently exercised since the restart: a real Verse compile driven through the bridge
  (`1 packages compiled in 1079.0 ms, SUCCESS`), plus read-only device and project reads.

**Everything in this log is now shipped code, not session state.**

## Needs Aayush — current, 2026-09-05

1. **Lore check-in**, then **publish the private version** of TheScar and playtest it.
   That private version IS the real P15 gate — build/cook/validation/upload on the actual
   target, with Lore as the undo.
2. **The cold join from Discover** (design Phase 0d). Sits on 244 of the 252 missing clicks
   and no in-island device can ever see it.
3. Optional, whenever: `DRAFT_PR.md` decisions; deleting the sandbox's `p14_probe.verse` and
   its placed actor.

**Retired since the overnight run:** the cold-start verification (done, above) and the
Ecosystem poller (built elsewhere by Aayush).

## What broke, and what I stopped on

- **`raycast` hit detail is unavailable.** The `HitResult` struct exposes no fields to
  Python in this build — not via `get_editor_property`, not via direct attributes, and
  `GameplayStatics.break_hit_result` does not exist. Two probes, both empty, cause not
  understood. **I hit the stop condition and stopped** rather than guessing more names.
  The tool ships reporting hit/no-hit with `detail_available: false`, which is the useful
  half. Returning nulls labelled `location` would have been a false pass.
- **Three no-op Verse compiles** before a real one during the P14 work — `sed -i` does not
  trigger the file watcher, a full rewrite does.
- **The drift check's first run scored a perfect, meaningless zero** because the API returns
  lower-camel names while the source declares PascalCase. Caught it, fixed it, and recorded
  it — a tidy all-zero result that was entirely a matching bug.
- **The drift check's second run produced 15 "findings", all false positives.** Reviewed and
  rejected by hand; the report lists every one so my review can be checked.

## What I deliberately did not build

- **`reflect`.** The plan wants it on `dir()`. Blind reflection enumeration is what crashed
  the editor before, and with nobody able to restart it that was the wrong trade tonight.
  It needs a capped, non-recursive, never-call design and a human present.
- **`dump_object`, `job_status`.** Time. Neither is blocking anything.
- **PIE anything.** Standing decision.

## What I would do next, in order — revised 2026-09-05

1. **Nothing that does not need Aayush's hands.** Publishing, the private version, the
   playtest and the cold join are all his. Said plainly rather than inventing work.
2. When there is something to exercise: **drive one write tool through `ue_tool_call`** and
   record it in the write allow-list. That list ships EMPTY, so the write half of the triad
   is **built but never exercised** — still the biggest untested surface here. Do it in a
   throwaway project, never on TheScar.
3. **`reflect`, designed safely** — hard cap, no recursion, never call a listed member.
4. Instrumentation is **DEFERRED**, not forgotten — see `instrumentation-design.md`. The
   trigger to revisit is the Ecosystem poller recording a non-zero `plays`.

## The one finding worth reading even if you skip everything else

**Not one scalar `@editable` in TheScar is overridden in the Details panel.** All 74 scalars
equal their `.verse` source defaults; the only 25 overrides are device bindings. The tuning
lives in the source, not the panel.

That is good news for TRAP 5 — a rename cannot silently revert a tuned number, because
there are none to revert; it would silently unbind a device instead, which is louder and
more findable. It also means **tuning changes belong in `.verse`**, and anyone "just
tweaking it in the Details panel" would create a divergence that makes the source value
misleading from then on. Worth deciding deliberately.

---

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
- **20:05** — **Item 8 DONE.** `TOOLS.md` documents all 48 tools, leading with
  the two-write-paths rule and including a "deliberately not provided" and an
  "unproven — do not claim these" section. README gained a fork summary.
  `DRAFT_PR.md` written for KirChuvakov — **NOT SUBMITTED**, and it ends with
  five things to decide first, including reverting the port split, stripping
  the TheScar-specific `snapshots/` directory, and fixing hard-coded absolute
  paths in the manifest and write-allow-list. **That last one is a real defect
  in what I shipped today** — see Needs Aayush.
- **20:20** — **Fixed the defect I had just flagged** rather than only listing it.
  The capability manifest and write allow-list hard-coded `G:/UEFN/...`, which
  breaks for anyone else cloning the fork. Both now resolve via `_repo_path()`
  from the listener's own directory, with fallbacks because `__file__` is not
  always set under UEFN's Execute Python Script. Verified live: paths resolve,
  manifest still reads its baseline (`ok: true`), write allow-list still refuses
  `CreateCollection`, and read dispatch still works.
- **20:35** — **Session verification.** Exec'd the entire committed
  `uefn_listener.py` into an isolated throwaway namespace (auto-start block
  sliced off so it could not disturb the running listener): loads cleanly,
  all 50 handlers defined, no ordering errors. This proves the file is
  internally consistent; it does NOT prove it starts a listener from cold.
  See "the seam" at the top. Queue complete. Repo clean and pushed.
- **2026-09-05** — **Session continued.** Shipped the opening-phase gate to TheScar
  (`juggernaut_manager.verse`), verified by a real Verse compile through the bridge. Recorded
  the tuning-location rule and closed the raycast dead end in `MCP_UPGRADE.md` §0. Corrected
  `instrumentation-design.md` twice — an unsupported mechanism and a resolved Phase 0a — and
  marked the whole instrument **DEFERRED** with reasoning. Corrected TheScar's pre-publish
  debug-flag checklist, which claimed 2 flags when there are **10**. Closed the cold-start
  seam above.
