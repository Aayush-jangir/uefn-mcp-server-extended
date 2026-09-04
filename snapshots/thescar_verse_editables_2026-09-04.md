# TheScar — Verse `@editable` tuning snapshot

**Captured 2026-09-04** from the live editor via `get_verse_editables`, which reads
`DeviceToolset.GetDeviceProperties`. These are the values the island actually runs on —
not what a doc or a source comment says they should be.

**99 tuned constants across 9 Verse managers.**

## Why this file exists

1. **There was no authoritative record.** This tuning was scattered across `CLAUDE.md`,
   the design doc and source comments, and had never been captured in one place from
   the live island.
2. **TRAP 5 (`MCP_UPGRADE.md` §0) makes it load-bearing.** Verse overrides serialise
   under a mangled name that hashes the fully-qualified Verse path. Renaming an
   `@editable`, renaming its class, or moving it between modules **orphans the override
   and silently reverts the value to its declared default** — no error, no warning.
   **A dated snapshot is the only way anyone would ever notice that happened.**

Re-capture after any manager refactor and diff against this file.

## Contents

- [leaderboard manager](#leaderboard-manager) — 7
- [scar manager](#scar-manager) — 12
- [revenge manager](#revenge-manager) — 4
- [hud manager](#hud-manager) — 14
- [juggernaut manager](#juggernaut-manager) — 19
- [loadout manager](#loadout-manager) — 2
- [trophy manager](#trophy-manager) — 28
- [onboarding manager](#onboarding-manager) — 3
- [progression manager](#progression-manager) — 10

## leaderboard manager

`VerseDevice_C` — 7 editables

| `@editable` | value | type |
|---|---|---|
| `boardLeftMargin` | 60 | number |
| `boardTopMargin` | 270 | number |
| `debugLogEliminations` | False | boolean |
| `debugSeedBoard` | False | boolean |
| `eliminationManager` | {"refPath": "/TheScar/TheScar.TheScar:PersistentLevel.VerseDevice_C_UAID_BCFCE7C660753C… | object |
| `objectiveLine` | "TOP THE BOARD - EVERY DEATH SCARS THE GROUND" | object |
| `rowsToShow` | 5 | integer |

## scar manager

`VerseDevice_C` — 12 editables

| `@editable` | value | type |
|---|---|---|
| `characterCentreOffset` | 88 | number |
| `debugFillArena` | False | boolean |
| `deckHeights` | [17, 402] | array |
| `deckTolerance` | 60 | number |
| `groundHeight` | 17 | number |
| `parkDepth` | -5000 | number |
| `scarsPerTeam` | 25 | integer |
| `teamCount` | 4 | integer |
| `teamScarAssetA` | {"refPath": "/TheScar/TheScar.TheScar:PersistentLevel.VerseDevice_C_UAID_BCFCE7C66075F2… | object |
| `teamScarAssetB` | {"refPath": "/TheScar/TheScar.TheScar:PersistentLevel.VerseDevice_C_UAID_BCFCE7C66075F2… | object |
| `teamScarAssetC` | {"refPath": "/TheScar/TheScar.TheScar:PersistentLevel.VerseDevice_C_UAID_BCFCE7C66075F2… | object |
| `teamScarAssetD` | {"refPath": "/TheScar/TheScar.TheScar:PersistentLevel.VerseDevice_C_UAID_BCFCE7C66075F2… | object |

## revenge manager

`VerseDevice_C` — 4 editables

| `@editable` | value | type |
|---|---|---|
| `notifier` | {"refPath": "/TheScar/TheScar.TheScar:PersistentLevel.VerseDevice_C_UAID_BCFCE7C6607549… | object |
| `pingRangeMetres` | 30 | number |
| `proximityCheckSeconds` | 1 | number |
| `revengeXP` | 50 | integer |

## hud manager

`VerseDevice_C` — 14 editables

| `@editable` | value | type |
|---|---|---|
| `dailyDoneLingerSeconds` | 8 | number |
| `debugForceRole` | 0 | integer |
| `labelTextSize` | 38 | number |
| `mainBottomMargin` | 200 | number |
| `numberTextSize` | 130 | number |
| `refreshSeconds` | 0.25 | number |
| `secondaryRightMargin` | 40 | number |
| `secondaryTextSize` | 34 | number |
| `secondaryTopMargin` | 330 | number |
| `showDebugOverlay` | False | boolean |
| `taskLeftMargin` | 60 | number |
| `timerLabelTextSize` | 56 | number |
| `timerTopMargin` | 60 | number |
| `verboseLog` | False | boolean |

## juggernaut manager

`VerseDevice_C` — 19 editables

| `@editable` | value | type |
|---|---|---|
| `announceMessage` | {"refPath": "/TheScar/TheScar.TheScar:PersistentLevel.VerseDevice_C_UAID_BCFCE7C660758B… | object |
| `auraRefreshSeconds` | 8 | number |
| `baseHealth` | 100 | number |
| `beaconAsset` | {"refPath": "/TheScar/TheScar.TheScar:PersistentLevel.VerseDevice_C_UAID_BCFCE7C660758B… | object |
| `beaconHeight` | 420 | number |
| `beaconParkDepth` | -5400 | number |
| `beaconScale` | 0.35 | number |
| `beaconTickSeconds` | 0.12 | number |
| `bonusHealth` | 300 | number |
| `bonusShield` | 200 | number |
| `debugLogAura` | False | boolean |
| `holdToUnlockSeconds` | 90 | number |
| `juggernautAura` | {"refPath": "/TheScar/TheScar.TheScar:PersistentLevel.VerseDevice_C_UAID_BCFCE7C660758B… | object |
| `juggernautMarker` | {"refPath": "/TheScar/TheScar.TheScar:PersistentLevel.VerseDevice_C_UAID_BCFCE7C660758B… | object |
| `openingPhaseSeconds` | 120 | number |
| `survivorHealth` | 200 | number |
| `survivorShield` | 100 | number |
| `takedownXP` | 100 | integer |
| `verboseLog` | False | boolean |

## loadout manager

`VerseDevice_C` — 2 editables

| `@editable` | value | type |
|---|---|---|
| `grantDebounceSeconds` | 2 | number |
| `weaponGranters` | [{'refPath': '/TheScar/TheScar.TheScar:PersistentLevel.VerseDevice_C_UAID_BCFCE7C66075E… | array |

## trophy manager

`VerseDevice_C` — 28 editables

| `@editable` | value | type |
|---|---|---|
| `approachZone` | {"refPath": "/TheScar/TheScar.TheScar:PersistentLevel.VerseDevice_C_UAID_BCFCE7C66075E6… | object |
| `chamberBarriers` | [{'refPath': '/TheScar/TheScar.TheScar:PersistentLevel.VerseDevice_C_UAID_BCFCE7C66075E… | array |
| `claimHoldSeconds` | 10 | number |
| `claimTickAudio` | {"refPath": "/TheScar/TheScar.TheScar:PersistentLevel.VerseDevice_C_UAID_BCFCE7C66075E6… | object |
| `claimTimer` | {"refPath": "/TheScar/TheScar.TheScar:PersistentLevel.VerseDevice_C_UAID_BCFCE7C66075E6… | object |
| `claimZone` | {"refPath": "/TheScar/TheScar.TheScar:PersistentLevel.VerseDevice_C_UAID_BCFCE7C66075E6… | object |
| `gateAsset` | {"refPath": "/TheScar/TheScar.TheScar:PersistentLevel.VerseDevice_C_UAID_BCFCE7C66075E6… | object |
| `gateBaseHeight` | 786 | number |
| `gateDropDepth` | 380 | number |
| `gateDropSpeed` | 300 | number |
| `gateRingRadius` | 768 | number |
| `gateRunScale` | 1.25 | number |
| `gateTickSeconds` | 0.05 | number |
| `matchEnder` | {"refPath": "/TheScar/TheScar.TheScar:PersistentLevel.VerseDevice_C_UAID_BCFCE7C66075E6… | object |
| `notifier` | {"refPath": "/TheScar/TheScar.TheScar:PersistentLevel.VerseDevice_C_UAID_BCFCE7C66075E6… | object |
| `plinthTopHeight` | 978 | number |
| `tickSeconds` | 0.25 | number |
| `trophyAsset` | {"refPath": "/TheScar/TheScar.TheScar:PersistentLevel.VerseDevice_C_UAID_BCFCE7C66075E6… | object |
| `trophyCentreX` | 0 | number |
| `trophyCentreY` | 0 | number |
| `trophyClearance` | 50 | number |
| `trophyHoldSeconds` | 1.5 | number |
| `trophyNaturalHeight` | 50.5 | number |
| `trophyRiseSpeed` | 320 | number |
| `trophyRiseTickSeconds` | 0.05 | number |
| `trophyScale` | 6 | number |
| `trophySpinDegreesPerSecond` | 140 | number |
| `verboseLog` | False | boolean |

## onboarding manager

`VerseDevice_C` — 3 editables

| `@editable` | value | type |
|---|---|---|
| `introDelay` | 1.5 | number |
| `introMessage` | {"refPath": "/TheScar/TheScar.TheScar:PersistentLevel.VerseDevice_C_UAID_BCFCE7C66075F1… | object |
| `showIntroMessage` | False | boolean |

## progression manager

`VerseDevice_C` — 10 editables

| `@editable` | value | type |
|---|---|---|
| `accoladeEveryNKills` | 3 | integer |
| `dailyBonusXP` | 150 | integer |
| `dailyKillTarget` | 3 | integer |
| `eliminationManager` | {"refPath": "/TheScar/TheScar.TheScar:PersistentLevel.VerseDevice_C_UAID_BCFCE7C6607549… | object |
| `goldReaperThreshold` | 5000 | integer |
| `killAccolade` | {"refPath": "/TheScar/TheScar.TheScar:PersistentLevel.VerseDevice_C_UAID_BCFCE7C6607549… | object |
| `notifier` | {"refPath": "/TheScar/TheScar.TheScar:PersistentLevel.VerseDevice_C_UAID_BCFCE7C6607549… | object |
| `silverThreshold` | 1000 | integer |
| `xPPerKill` | 10 | integer |
| `xPPerMatch` | 25 | integer |
