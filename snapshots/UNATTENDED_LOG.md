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
| 4 | Discovery triad | IN PROGRESS |
| 5 | Sidecar tools | not started |
| 6 | `--supported-only` fallback | not started |
| 7 | Drift check (no editor needed) | not started |
| 8 | Docs + draft upstream PR (no editor needed) | not started |

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
