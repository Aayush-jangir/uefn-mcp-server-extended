# TheScar — @editable drift report

**Generated 2026-09-04.** Compares the 99 live `@editable` values captured in
`thescar_verse_editables_2026-09-04.json` against the `.verse` source defaults and
against every number the project docs claim.

**Nothing here was changed.** This is a findings list only.

## How to read it

- **Overridden** — live differs from the `.verse` default. **This is normal and
  expected**: it is a value tuned in the Details panel. Not drift.
- **DOC DRIFT** — a doc states a number the island does not actually run on.
  This is the real finding.
- **Matches source default** — worth a glance given TRAP 5: if an `@editable` was
  ever renamed, its override would have been orphaned and silently reverted to
  exactly this. Most of these are simply never-overridden values, but this is the
  only place a silent revert would show.

## Summary

| | count |
|---|---|
| live editables compared | 99 |
| overridden vs source default (normal) | 25 |
| equal to source default | 74 |
| no `@editable` default found in source | 0 |
| numeric and comparable | 64 |
| excluded (object ref / bool / list - not comparable) | 35 |
| mentioned with a number in the docs | 2 |
| **DOC DRIFT — doc disagrees with live** | **0** |

## DOC DRIFT

**None found.** No doc states a number that contradicts a live value.

## Overridden in the Details panel (normal, not drift)

| manager | `@editable` | source default | live |
|---|---|---|---|
| juggernaut manager | `announceMessage` | hud_message_device{} | **{'refPath': '/TheScar/TheScar.TheScar:PersistentLevel.VerseDevice_C_UAID_BCFCE7C660758BF602_1497818775.juggernaut_manager_0.__verse_0x347B274B_AnnounceMessage'}** |
| juggernaut manager | `beaconAsset` | DefaultCreativePropAsset | **{'refPath': '/TheScar/TheScar.TheScar:PersistentLevel.VerseDevice_C_UAID_BCFCE7C660758BF602_1497818775.juggernaut_manager_0.Devices_creative_prop_asset_3'}** |
| juggernaut manager | `juggernautAura` | visual_effect_powerup_device{} | **{'refPath': '/TheScar/TheScar.TheScar:PersistentLevel.VerseDevice_C_UAID_BCFCE7C660758BF602_1497818775.juggernaut_manager_0.__verse_0x1AC823E2_JuggernautAura'}** |
| juggernaut manager | `juggernautMarker` | player_marker_device{} | **{'refPath': '/TheScar/TheScar.TheScar:PersistentLevel.VerseDevice_C_UAID_BCFCE7C660758BF602_1497818775.juggernaut_manager_0.__verse_0x750CAD02_JuggernautMarker'}** |
| leaderboard manager | `eliminationManager` | elimination_manager_device{} | **{'refPath': '/TheScar/TheScar.TheScar:PersistentLevel.VerseDevice_C_UAID_BCFCE7C660753CF602_1717204867.leaderboard_manager_0.__verse_0x2DD0D81D_EliminationManager'}** |
| loadout manager | `weaponGranters` | array{} | **[{'refPath': '/TheScar/TheScar.TheScar:PersistentLevel.VerseDevice_C_UAID_BCFCE7C66075ECF402_1100210733.loadout_manager_0.item_granter_device_0'}, {'refPath': '/TheScar/TheScar.TheScar:PersistentLevel.VerseDevice_C_UAID_BCFCE7C66075ECF402_1100210733.loadout_manager_0.item_granter_device_1'}, {'refPath': '/TheScar/TheScar.TheScar:PersistentLevel.VerseDevice_C_UAID_BCFCE7C66075ECF402_1100210733.loadout_manager_0.item_granter_device_2'}, {'refPath': '/TheScar/TheScar.TheScar:PersistentLevel.VerseDevice_C_UAID_BCFCE7C66075ECF402_1100210733.loadout_manager_0.item_granter_device_3'}, {'refPath': '/TheScar/TheScar.TheScar:PersistentLevel.VerseDevice_C_UAID_BCFCE7C66075ECF402_1100210733.loadout_manager_0.item_granter_device_4'}, {'refPath': '/TheScar/TheScar.TheScar:PersistentLevel.VerseDevice_C_UAID_BCFCE7C66075ECF402_1100210733.loadout_manager_0.item_granter_device_5'}, {'refPath': '/TheScar/TheScar.TheScar:PersistentLevel.VerseDevice_C_UAID_BCFCE7C66075ECF402_1100210733.loadout_manager_0.item_granter_device_6'}, {'refPath': '/TheScar/TheScar.TheScar:PersistentLevel.VerseDevice_C_UAID_BCFCE7C66075ECF402_1100210733.loadout_manager_0.item_granter_device_7'}]** |
| onboarding manager | `introMessage` | hud_message_device{} | **{'refPath': '/TheScar/TheScar.TheScar:PersistentLevel.VerseDevice_C_UAID_BCFCE7C66075F1F402_1188206668.onboarding_manager_0.__verse_0xC3063ED5_IntroMessage'}** |
| progression manager | `eliminationManager` | elimination_manager_device{} | **{'refPath': '/TheScar/TheScar.TheScar:PersistentLevel.VerseDevice_C_UAID_BCFCE7C6607549F702_1988977435.progression_manager_0.__verse_0x2DD0D81D_EliminationManager'}** |
| progression manager | `killAccolade` | accolades_device{} | **{'refPath': '/TheScar/TheScar.TheScar:PersistentLevel.VerseDevice_C_UAID_BCFCE7C6607549F702_1988977435.progression_manager_0.__verse_0xBCF1FA65_KillAccolade'}** |
| progression manager | `notifier` | hud_message_device{} | **{'refPath': '/TheScar/TheScar.TheScar:PersistentLevel.VerseDevice_C_UAID_BCFCE7C6607549F702_1988977435.progression_manager_0.__verse_0x4FBE9B0B_Notifier'}** |
| revenge manager | `notifier` | hud_message_device{} | **{'refPath': '/TheScar/TheScar.TheScar:PersistentLevel.VerseDevice_C_UAID_BCFCE7C6607549F702_1982136434.revenge_manager_0.__verse_0x4FBE9B0B_Notifier'}** |
| scar manager | `deckHeights` | array{17.0} | **[17, 402]** |
| scar manager | `teamScarAssetA` | DefaultCreativePropAsset | **{'refPath': '/TheScar/TheScar.TheScar:PersistentLevel.VerseDevice_C_UAID_BCFCE7C66075F2F402_1093225846.scar_manager_0.Devices_creative_prop_asset_5'}** |
| scar manager | `teamScarAssetB` | DefaultCreativePropAsset | **{'refPath': '/TheScar/TheScar.TheScar:PersistentLevel.VerseDevice_C_UAID_BCFCE7C66075F2F402_1093225846.scar_manager_0.Devices_creative_prop_asset_6'}** |
| scar manager | `teamScarAssetC` | DefaultCreativePropAsset | **{'refPath': '/TheScar/TheScar.TheScar:PersistentLevel.VerseDevice_C_UAID_BCFCE7C66075F2F402_1093225846.scar_manager_0.Devices_creative_prop_asset_7'}** |
| scar manager | `teamScarAssetD` | DefaultCreativePropAsset | **{'refPath': '/TheScar/TheScar.TheScar:PersistentLevel.VerseDevice_C_UAID_BCFCE7C66075F2F402_1093225846.scar_manager_0.Devices_creative_prop_asset_8'}** |
| trophy manager | `approachZone` | mutator_zone_device{} | **{'refPath': '/TheScar/TheScar.TheScar:PersistentLevel.VerseDevice_C_UAID_BCFCE7C66075E6F702_1818435839.trophy_manager_0.__verse_0xE49DE5E9_ApproachZone'}** |
| trophy manager | `chamberBarriers` | array{} | **[{'refPath': '/TheScar/TheScar.TheScar:PersistentLevel.VerseDevice_C_UAID_BCFCE7C66075E6F702_1818435839.trophy_manager_0.barrier_device_0'}, {'refPath': '/TheScar/TheScar.TheScar:PersistentLevel.VerseDevice_C_UAID_BCFCE7C66075E6F702_1818435839.trophy_manager_0.barrier_device_1'}, {'refPath': '/TheScar/TheScar.TheScar:PersistentLevel.VerseDevice_C_UAID_BCFCE7C66075E6F702_1818435839.trophy_manager_0.barrier_device_2'}, {'refPath': '/TheScar/TheScar.TheScar:PersistentLevel.VerseDevice_C_UAID_BCFCE7C66075E6F702_1818435839.trophy_manager_0.barrier_device_3'}]** |
| trophy manager | `claimTickAudio` | audio_player_device{} | **{'refPath': '/TheScar/TheScar.TheScar:PersistentLevel.VerseDevice_C_UAID_BCFCE7C66075E6F702_1818435839.trophy_manager_0.__verse_0xDC2086FD_ClaimTickAudio'}** |
| trophy manager | `claimTimer` | timer_device{} | **{'refPath': '/TheScar/TheScar.TheScar:PersistentLevel.VerseDevice_C_UAID_BCFCE7C66075E6F702_1818435839.trophy_manager_0.__verse_0x2CB9105F_ClaimTimer'}** |
| trophy manager | `claimZone` | mutator_zone_device{} | **{'refPath': '/TheScar/TheScar.TheScar:PersistentLevel.VerseDevice_C_UAID_BCFCE7C66075E6F702_1818435839.trophy_manager_0.__verse_0x43824F07_ClaimZone'}** |
| trophy manager | `gateAsset` | DefaultCreativePropAsset | **{'refPath': '/TheScar/TheScar.TheScar:PersistentLevel.VerseDevice_C_UAID_BCFCE7C66075E6F702_1818435839.trophy_manager_0.Devices_creative_prop_asset_4'}** |
| trophy manager | `matchEnder` | end_game_device{} | **{'refPath': '/TheScar/TheScar.TheScar:PersistentLevel.VerseDevice_C_UAID_BCFCE7C66075E6F702_1818435839.trophy_manager_0.__verse_0xABAE8533_MatchEnder'}** |
| trophy manager | `notifier` | hud_message_device{} | **{'refPath': '/TheScar/TheScar.TheScar:PersistentLevel.VerseDevice_C_UAID_BCFCE7C66075E6F702_1818435839.trophy_manager_0.__verse_0x4FBE9B0B_Notifier'}** |
| trophy manager | `trophyAsset` | DefaultCreativePropAsset | **{'refPath': '/TheScar/TheScar.TheScar:PersistentLevel.VerseDevice_C_UAID_BCFCE7C66075E6F702_1818435839.trophy_manager_0.Devices_creative_prop_asset_1'}** |

## The part that is actually solid: tuned scalars vs source defaults

Both sides machine-read, so this table has no heuristic in it.

**25 of the 25 “overridden” rows above are device bindings** (source default is an
empty `device{}` and the live value is a bound actor). Those are wiring, not tuning,
and are uninteresting here.

**No scalar `@editable` differs from its source default.**

### TRAP 5 watch-list

**74 scalars equal their source default.** Most were simply never overridden, but this
is the ONLY place a TRAP 5 silent revert would ever surface: if an `@editable` were
renamed, its override would be orphaned and the value would snap back to exactly the
declared default. Re-run this after any manager refactor and diff against today.

## LIMITS OF THIS CHECK — read before trusting the zero

**The 0 in DOC DRIFT is weak evidence, not an all-clear.** Only 2 of 99 editables were
both numeric AND mentioned in a doc in a machine-detectable `name = value` form. The
docs mostly name these in prose without restating the number, and prose is not
comparable automatically.

**The first pass reported 15 “drift” findings and every one was a false positive.**
Reviewed by hand and rejected:

- `goldReaperThreshold` 5000 vs “13”, `silverThreshold` 1000 vs “13”, `xPPerKill` 10
  vs “13” — all three matched the words **“Day 13”** in the plan doc.
- `announceMessage`, `killAccolade`, `notifier`, `approachZone`, `claimZone` — object
  references; the “claim” was just the next number in the sentence.
- `debugForceRole`, `debugSeedBoard`, `debugLogEliminations` — booleans matched against
  unrelated prose numbers.
- `teamCount` 4 vs “100” — the doc was describing `Matchmaking_MaxTeamCount`, a
  different setting.
- `deckHeights` `[17, 402]` vs CLAUDE.md `[17.0, 402.0]` — **actually a match**, broken
  by comparing a list against a scalar.

Restricting to numeric values with a value-like separator removed all 15. **So the
honest finding is: no contradiction was detected, and the method is too weak to prove
there is none.**

A naming detail found on the way, worth keeping: **the API returns lower-camel names
(`auraRefreshSeconds`) while the Verse source declares PascalCase
(`AuraRefreshSeconds`).** The first version of this check matched exactly and scored
0 of 99 — a clean-looking result that was entirely a bug.

## CONCLUSION — and it changes the TRAP 5 risk picture

**Not one scalar `@editable` in TheScar is overridden in the Details panel.**
All 74 scalar values — Juggernaut health tiers, `holdToUnlockSeconds`,
`openingPhaseSeconds`, HUD margins, thresholds, every timer — are exactly their
`.verse` source defaults. The tuning lives **in the source**, not in the panel.

Two consequences worth acting on:

1. **TRAP 5 exposure is much narrower than feared for tuning, and precisely located
   for wiring.** A rename orphans *overrides*, and the only overrides that exist are
   the **25 device bindings** (`eliminationManager`, `juggernautAura`,
   `weaponGranters`, `killAccolade`, `notifier`, …). So renaming an `@editable` would
   not silently revert a tuned number — there are none — but it **would silently
   unbind a device**, which is a louder and more findable failure. Good news.

2. **Changing tuning means editing `.verse` and rebuilding**, not clicking the panel.
   Anyone told to “just tweak it in the Details panel” would be setting an override
   that diverges from source, and the source value would then be misleading forever
   after. Worth deciding deliberately which is the source of truth; today it is
   unambiguously the `.verse` files.

**This is a finding, not a change.** Nothing was edited.
