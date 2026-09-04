"""P4 harness - what actually WRITES a Creative device option?

RUN ONLY IN A THROWAWAY PROJECT (Blank_Test_Project / TestProject /
Test_Optimization_Project). It mutates devices on purpose and saves the level.
It refuses to run if the editor world looks like TheScar.

WHY IT EXISTS
-------------
`ToolsetLibrary.set_object_properties` returns True and reads back changed
through `ToolsetLibrary.get_object_properties`, while
`device.get_user_option_value()` still returns the OLD value. The two
representations disagree (MCP_UPGRADE.md section 0, Trap 1). This harness
therefore NEVER treats a read-back through the writing API as evidence: it
reads every representation and reports whether they AGREE, and the caller
greps the saved .uasset on disk for the per-variant marker.

VARIANTS - one device each, so they cannot contaminate one another
    A  set_object_properties, plain
    B  ToolsetLibrary.modify(component) first, then set
    C  set, then post_edit_change() on component and actor
    D  set with bypass_container_check = YES
    E  set_user_option_value(None, k, v)          negative control, expected no-op
    F  set_editor_property('label_override', v)   the native-UPROPERTY route

Variant F exists because probe 6 (MCP_UPGRADE.md section 13) showed the device
OPTION layer is a *view* over native UPROPERTYs: writing a native property on
the Island Settings actor propagated to its device options, to the saved
.uasset, and even into the .uefnproject. If that generalises, F is the write
path and the whole ToolsetLibrary route is a dead end.

USAGE
    exec(open(r"G:/UEFN/uefn-mcp-server-extended/tests/probe_p4_device_write.py").read())
    result = run_p4()            # write only
    result = run_p4(save=True)   # write and save, so disk can be grepped
"""

import json

import unreal

MARKER_PREFIX = "MCP_P4_"
OPTION = "LabelOverride"
NATIVE = "label_override"

# variant id -> actor label to use
ASSIGNMENT = [
    ("A", "Button"),
    ("B", "Button2"),
    ("C", "Button3"),
    ("D", "Button4"),
    ("E", "Button5"),
    ("F", "Item Granter"),
]


def _safe_project() -> bool:
    world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
    return "thescar" not in world.get_name().lower()


def _find(label):
    actor_sub = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    for a in actor_sub.get_all_level_actors():
        if a.get_actor_label() == label:
            return a
    return None


def _overrides(component):
    return unreal.ToolsetLibrary.get_object_properties(component, ["PlayerOptionData"])


def _payload(original_json, new_value):
    """Full override array with only OPTION changed - never write a partial array."""
    parsed = json.loads(original_json)
    found = False
    for o in parsed["PlayerOptionData"]["propertyOverrides"]:
        if o["propertyName"] == OPTION:
            o["propertyData"] = new_value
            found = True
    if not found:
        parsed["PlayerOptionData"]["propertyOverrides"].append(
            {"propertyScope": "", "propertyName": OPTION, "propertyData": new_value}
        )
    return json.dumps(parsed)


def _read_all(actor, component, marker):
    """Read every representation and say whether they agree."""
    try:
        vals = [
            o["propertyData"]
            for o in json.loads(_overrides(component))["PlayerOptionData"]["propertyOverrides"]
            if o["propertyName"] == OPTION
        ]
        toolset = vals[0] if vals else None
    except Exception as e:
        toolset = "ERR:%s" % e
    try:
        option = str(actor.get_user_option_value(OPTION))
    except Exception as e:
        option = "ERR:%s" % e
    try:
        native = str(actor.get_editor_property(NATIVE))
    except Exception:
        native = "<absent>"

    return {
        "read_toolset": toolset,
        "read_option": option,
        "read_native": native,
        "toolset_took": toolset == marker,
        "option_took": option == marker,
        "native_took": native == marker,
        "all_agree": toolset == option == native,
    }


def run_p4(save: bool = False) -> dict:
    if not _safe_project():
        return {"ABORTED": "editor world looks like TheScar - refusing"}

    report = {"marker_prefix": MARKER_PREFIX, "variants": {}}

    for vid, label in ASSIGNMENT:
        marker = MARKER_PREFIX + vid
        row = {"marker": marker, "actor_label": label}
        try:
            actor = _find(label)
            if actor is None:
                row["FAILED"] = "actor not found: %s" % label
                report["variants"][vid] = row
                continue

            comp = actor.get_user_option_definitions()
            original = _overrides(comp)
            payload = _payload(original, marker)

            with unreal.ScopedEditorTransaction("P4 %s" % vid):
                if vid == "A":
                    row["returned"] = unreal.ToolsetLibrary.set_object_properties(comp, payload)

                elif vid == "B":
                    try:
                        unreal.ToolsetLibrary.modify(comp)
                        row["modify"] = True
                    except Exception as e:
                        row["modify"] = "ERR:%s" % str(e)[:80]
                    row["returned"] = unreal.ToolsetLibrary.set_object_properties(comp, payload)

                elif vid == "C":
                    row["returned"] = unreal.ToolsetLibrary.set_object_properties(comp, payload)
                    for obj, tag in ((comp, "component"), (actor, "actor")):
                        try:
                            obj.post_edit_change()
                            row["pec_" + tag] = True
                        except Exception as e:
                            row["pec_" + tag] = "ERR:%s" % str(e)[:60]

                elif vid == "D":
                    try:
                        row["returned"] = unreal.ToolsetLibrary.set_object_properties(
                            comp, payload, unreal.BypassContainerCheck.YES
                        )
                    except Exception as e:
                        row["returned"] = "ERR:%s" % str(e)[:120]

                elif vid == "E":
                    try:
                        row["returned"] = actor.set_user_option_value(None, OPTION, marker)
                    except Exception as e:
                        row["returned"] = "ERR:%s" % str(e)[:120]

                elif vid == "F":
                    try:
                        actor.set_editor_property(NATIVE, marker)
                        row["returned"] = "set_editor_property ok"
                    except Exception as e:
                        row["returned"] = "ERR:%s" % str(e)[:120]

            row.update(_read_all(actor, comp, marker))
            row["package"] = actor.get_outermost().get_name()

        except Exception as e:
            row["FAILED"] = repr(e)[:300]

        report["variants"][vid] = row

    if save:
        try:
            report["saved"] = unreal.get_editor_subsystem(
                unreal.LevelEditorSubsystem
            ).save_current_level()
        except Exception as e:
            report["save_error"] = str(e)

    report["NEXT"] = "grep the saved .uasset files for %s - disk is the arbiter" % MARKER_PREFIX
    return report
