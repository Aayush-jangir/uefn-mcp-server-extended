# -*- coding: utf-8 -*-
import io, json, os, re

SNAP = r"G:/UEFN/uefn-mcp-server-extended/snapshots/thescar_verse_editables_2026-09-04.json"
VERSE_DIR = r"G:/UEFN/TheScar/Content"
OUT = r"G:/UEFN/uefn-mcp-server-extended/snapshots/drift_report_2026-09-04.md"

snap = json.load(io.open(SNAP, encoding="utf-8"))

DEF_RE = re.compile(
    r"@editable[^\n]*\n\s*([A-Za-z_][A-Za-z0-9_]*)\s*:\s*([^\n=]+?)\s*=\s*([^\n]+)")
defaults = {}
for fn in os.listdir(VERSE_DIR):
    if not fn.endswith(".verse"):
        continue
    text = io.open(os.path.join(VERSE_DIR, fn), encoding="utf-8", errors="replace").read()
    for m in DEF_RE.finditer(text):
        defaults.setdefault(m.group(1).lower(), (m.group(3).strip(), fn))


def scalar(v):
    return isinstance(v, (int, float, str)) and not isinstance(v, bool)


def norm(v):
    if isinstance(v, bool):
        return "true" if v else "false"
    t = str(v).strip().strip('"')
    m = re.match(r"^([-+]?\d+)\.0+$", t)
    return m.group(1) if m else t


numeric_over, binding_over, same = [], [], []
for mgr, data in sorted(snap["managers"].items()):
    for name, live in sorted(data["editables"].items()):
        d = defaults.get(name.lower())
        if not d:
            continue
        src, fn = d
        is_ref = isinstance(live, (dict, list))
        if norm(src) == norm(live):
            same.append((mgr, name, norm(live)))
        elif is_ref:
            binding_over.append((mgr, name))
        else:
            numeric_over.append((mgr, name, norm(src), norm(live)))

L = []
L.append("")
L.append("## The part that is actually solid: tuned scalars vs source defaults")
L.append("")
L.append("Both sides machine-read, so this table has no heuristic in it.")
L.append("")
L.append("**%d of the %d \u201coverridden\u201d rows above are device bindings** (source default is an"
         % (len(binding_over), len(binding_over) + len(numeric_over)))
L.append("empty `device{}` and the live value is a bound actor). Those are wiring, not tuning,")
L.append("and are uninteresting here.")
L.append("")
if numeric_over:
    L.append("**%d scalar values are tuned away from their source default:**" % len(numeric_over))
    L.append("")
    L.append("| manager | `@editable` | source default | LIVE |")
    L.append("|---|---|---|---|")
    for mgr, name, src, live in numeric_over:
        L.append("| %s | `%s` | %s | **%s** |" % (mgr, name, src, live))
else:
    L.append("**No scalar `@editable` differs from its source default.**")
L.append("")
L.append("### TRAP 5 watch-list")
L.append("")
L.append("**%d scalars equal their source default.** Most were simply never overridden, but this"
         % len(same))
L.append("is the ONLY place a TRAP 5 silent revert would ever surface: if an `@editable` were")
L.append("renamed, its override would be orphaned and the value would snap back to exactly the")
L.append("declared default. Re-run this after any manager refactor and diff against today.")
L.append("")
L.append("## LIMITS OF THIS CHECK \u2014 read before trusting the zero")
L.append("")
L.append("**The 0 in DOC DRIFT is weak evidence, not an all-clear.** Only 2 of 99 editables were")
L.append("both numeric AND mentioned in a doc in a machine-detectable `name = value` form. The")
L.append("docs mostly name these in prose without restating the number, and prose is not")
L.append("comparable automatically.")
L.append("")
L.append("**The first pass reported 15 \u201cdrift\u201d findings and every one was a false positive.**")
L.append("Reviewed by hand and rejected:")
L.append("")
L.append("- `goldReaperThreshold` 5000 vs \u201c13\u201d, `silverThreshold` 1000 vs \u201c13\u201d, `xPPerKill` 10")
L.append("  vs \u201c13\u201d \u2014 all three matched the words **\u201cDay 13\u201d** in the plan doc.")
L.append("- `announceMessage`, `killAccolade`, `notifier`, `approachZone`, `claimZone` \u2014 object")
L.append("  references; the \u201cclaim\u201d was just the next number in the sentence.")
L.append("- `debugForceRole`, `debugSeedBoard`, `debugLogEliminations` \u2014 booleans matched against")
L.append("  unrelated prose numbers.")
L.append("- `teamCount` 4 vs \u201c100\u201d \u2014 the doc was describing `Matchmaking_MaxTeamCount`, a")
L.append("  different setting.")
L.append("- `deckHeights` `[17, 402]` vs CLAUDE.md `[17.0, 402.0]` \u2014 **actually a match**, broken")
L.append("  by comparing a list against a scalar.")
L.append("")
L.append("Restricting to numeric values with a value-like separator removed all 15. **So the")
L.append("honest finding is: no contradiction was detected, and the method is too weak to prove")
L.append("there is none.**")
L.append("")
L.append("A naming detail found on the way, worth keeping: **the API returns lower-camel names")
L.append("(`auraRefreshSeconds`) while the Verse source declares PascalCase")
L.append("(`AuraRefreshSeconds`).** The first version of this check matched exactly and scored")
L.append("0 of 99 \u2014 a clean-looking result that was entirely a bug.")

with io.open(OUT, "a", encoding="utf-8", newline="\n") as fh:
    fh.write("\n".join(L) + "\n")

print("appended. numeric overrides: %d | bindings: %d | equal to default: %d"
      % (len(numeric_over), len(binding_over), len(same)))
