# -*- coding: utf-8 -*-
"""Item 7 - drift check.

Compare the 99 LIVE @editable values against:
  (a) the @editable DEFAULTS declared in the .verse source
  (b) any value the docs claim

An (a) difference is NOT drift - it is an intentional Details-panel override,
and is reported as informational. A (b) difference IS drift: a doc asserting a
number the island does not actually run on.

Given TRAP 5 (a rename orphans an override and silently reverts it to the
declared default), a live value that has snapped back to its source default is
exactly what this would surface.
"""
import io, json, os, re

SNAP = r"G:/UEFN/uefn-mcp-server-extended/snapshots/thescar_verse_editables_2026-09-04.json"
VERSE_DIR = r"G:/UEFN/TheScar/Content"
DOCS = [
    r"G:/UEFN/TheScar/CLAUDE.md",
    r"G:/UEFN/TheScar/handover-days-5-14.md",
    r"G:/UEFN/TheScar/publishing-prep.md",
    r"G:/UEFN/TheScar/the-scar-14-day-plan.md",
]
OUT = r"G:/UEFN/uefn-mcp-server-extended/snapshots/drift_report_2026-09-04.md"


def norm(v):
    """Normalise a value for comparison."""
    if isinstance(v, bool):
        return "true" if v else "false"
    if isinstance(v, float) and v == int(v):
        return str(int(v))
    t = str(v).strip().strip('"')
    m2 = re.match(r"^([-+]?\d+)\.0+$", t)
    return m2.group(1) if m2 else t


snap = json.load(io.open(SNAP, encoding="utf-8"))
managers = snap["managers"]

# ---- source defaults -------------------------------------------------------
verse_src = {}
for fn in os.listdir(VERSE_DIR):
    if fn.endswith(".verse"):
        verse_src[fn] = io.open(os.path.join(VERSE_DIR, fn), encoding="utf-8",
                                errors="replace").read()

# `@editable  Name : type = value`
DEF_RE = re.compile(
    r"@editable[^\n]*\n\s*([A-Za-z_][A-Za-z0-9_]*)\s*:\s*([^\n=]+?)\s*=\s*([^\n]+)")
defaults = {}
for fn, text in verse_src.items():
    for m in DEF_RE.finditer(text):
        defaults.setdefault(m.group(1).lower(), []).append(
            {"file": fn, "type": m.group(2).strip(), "default": m.group(3).strip(),
             "source_name": m.group(1)})

# ---- doc text --------------------------------------------------------------
doc_text = {}
for p in DOCS:
    if os.path.isfile(p):
        doc_text[os.path.basename(p)] = io.open(
            p, encoding="utf-8", errors="replace").read()

rows = []
for mgr, data in sorted(managers.items()):
    for name, live in sorted(data["editables"].items()):
        live_n = norm(live)

        # source default
        src = defaults.get(name.lower())
        src_default = src[0]["default"] if src else None
        src_file = src[0]["file"] if src else None
        src_name = src[0]["source_name"] if src else None
        overridden = (src_default is not None
                      and norm(src_default) != live_n)
        reverted_to_default = (src_default is not None
                               and norm(src_default) == live_n)

        # Only NUMERIC live values can meaningfully drift against a doc number.
        # Object refs, booleans and lists produce nothing but prose-number
        # false positives - the first pass matched "Day 13" as a claim about
        # goldReaperThreshold. Excluded rather than reported.
        comparable = isinstance(live, (int, float)) and not isinstance(live, bool)

        # doc claims: find "name ... number" within a short window
        claims = []
        if not comparable:
            rows.append({
                "manager": mgr, "name": name, "live": live_n,
                "src_default": src_default, "src_file": src_file,
                "src_name": src_name, "overridden": overridden,
                "reverted_to_default": reverted_to_default,
                "doc_claims": [], "doc_drift": [], "excluded": True,
            })
            continue
        for dname, text in doc_text.items():
            for m in re.finditer(re.escape(name), text, re.IGNORECASE):
                window = text[m.end(): m.end() + 40]
                if not re.match(r"\s*(?:[=:→]|is|of|to|at|\()", window):
                    continue
                nums = re.findall(r"[-+]?\d+(?:\.\d+)?", window)
                if nums:
                    claims.append({"doc": dname, "claim": nums[0],
                                   "context": " ".join(
                                       text[max(0, m.start() - 40): m.end() + 60].split())[:150]})
                    break

        doc_drift = [c for c in claims if norm(c["claim"]) != live_n]

        rows.append({
            "manager": mgr, "name": name, "live": live_n,
            "src_default": src_default, "src_file": src_file,
            "src_name": src_name,
            "overridden": overridden,
            "reverted_to_default": reverted_to_default,
            "doc_claims": claims, "doc_drift": doc_drift,
            "excluded": False,
        })

n_total = len(rows)
n_no_src = [r for r in rows if r["src_default"] is None]
n_over = [r for r in rows if r["overridden"]]
n_drift = [r for r in rows if r["doc_drift"]]
n_docd = [r for r in rows if r["doc_claims"]]
n_excl = [r for r in rows if r.get("excluded")]

L = []
L.append("# TheScar — @editable drift report")
L.append("")
L.append("**Generated 2026-09-04.** Compares the %d live `@editable` values captured in"
         % n_total)
L.append("`thescar_verse_editables_2026-09-04.json` against the `.verse` source defaults and")
L.append("against every number the project docs claim.")
L.append("")
L.append("**Nothing here was changed.** This is a findings list only.")
L.append("")
L.append("## How to read it")
L.append("")
L.append("- **Overridden** — live differs from the `.verse` default. **This is normal and")
L.append("  expected**: it is a value tuned in the Details panel. Not drift.")
L.append("- **DOC DRIFT** — a doc states a number the island does not actually run on.")
L.append("  This is the real finding.")
L.append("- **Matches source default** — worth a glance given TRAP 5: if an `@editable` was")
L.append("  ever renamed, its override would have been orphaned and silently reverted to")
L.append("  exactly this. Most of these are simply never-overridden values, but this is the")
L.append("  only place a silent revert would show.")
L.append("")
L.append("## Summary")
L.append("")
L.append("| | count |")
L.append("|---|---|")
L.append("| live editables compared | %d |" % n_total)
L.append("| overridden vs source default (normal) | %d |" % len(n_over))
L.append("| equal to source default | %d |" % (n_total - len(n_over) - len(n_no_src)))
L.append("| no `@editable` default found in source | %d |" % len(n_no_src))
L.append("| numeric and comparable | %d |" % (n_total - len(n_excl)))
L.append("| excluded (object ref / bool / list - not comparable) | %d |" % len(n_excl))
L.append("| mentioned with a number in the docs | %d |" % len(n_docd))
L.append("| **DOC DRIFT — doc disagrees with live** | **%d** |" % len(n_drift))
L.append("")

if n_drift:
    L.append("## DOC DRIFT — the actual findings")
    L.append("")
    L.append("| manager | `@editable` | live | doc says | doc | context |")
    L.append("|---|---|---|---|---|---|")
    for r in n_drift:
        for c in r["doc_drift"]:
            L.append("| %s | `%s` | **%s** | %s | %s | %s |" % (
                r["manager"], r["name"], r["live"], c["claim"], c["doc"],
                c["context"].replace("|", "\\|")[:90]))
    L.append("")
else:
    L.append("## DOC DRIFT")
    L.append("")
    L.append("**None found.** No doc states a number that contradicts a live value.")
    L.append("")

L.append("## Overridden in the Details panel (normal, not drift)")
L.append("")
L.append("| manager | `@editable` | source default | live |")
L.append("|---|---|---|---|")
for r in sorted(n_over, key=lambda x: (x["manager"], x["name"])):
    L.append("| %s | `%s` | %s | **%s** |" % (
        r["manager"], r["name"], r["src_default"], r["live"]))
L.append("")

if n_no_src:
    L.append("## No `@editable` default found in source")
    L.append("")
    L.append("Either declared without an initialiser, or the name differs between the")
    L.append("compiled property and the source. Worth an eye.")
    L.append("")
    L.append("| manager | `@editable` | live |")
    L.append("|---|---|---|")
    for r in sorted(n_no_src, key=lambda x: (x["manager"], x["name"])):
        L.append("| %s | `%s` | %s |" % (r["manager"], r["name"], r["live"][:60]))
    L.append("")

io.open(OUT, "w", encoding="utf-8", newline="\n").write("\n".join(L))
print("drift report written")
print("  live compared      :", n_total)
print("  overridden         :", len(n_over))
print("  no source default  :", len(n_no_src))
print("  doc-mentioned      :", len(n_docd))
print("  DOC DRIFT          :", len(n_drift))
