"""P4 harness - does anything actually WRITE a Creative device option?

RUN THIS ONLY IN A THROWAWAY PROJECT (Blank_Test_Project / TestProject /
Test_Optimization_Project). It spawns actors and dirties the level on purpose.
Never point it at TheScar.

WHY IT EXISTS
-------------
`ToolsetLibrary.set_object_properties` returns True and reads back changed
through `ToolsetLibrary.get_object_properties`, while
`device.get_user_option_value()` still returns the OLD value. The two
representations disagree (MCP_UPGRADE.md section 0, Trap 1). So this harness
never trusts a read-back through the writing API. It writes a DISTINCT marker
per variant, and the caller greps the saved .uasset files on disk to see which
markers - if any - actually persisted.

METHOD
------
One barrier per variant, so the variants cannot contaminate each other and a
single level save settles all of them at once. Each variant writes marker
"MCP_P4_<ID>" into LabelOverride, preserving every other propertyOverride.

Variants:
  A  set_object_properties, plain
  B  ToolsetLibrary.modify(component) first, then set
  C  set, then post_edit_change() on the component and the actor
  D  set with bypass_container_check = YES
  E  set via the actor's own set_user_option_value(None, k, v) - the known
     no-op, kept as the negative control

USAGE (from execute_python, or paste into Tools > Execute Python Script):
    exec(open(r"G:/UEFN/uefn-mcp-server-extended/tests/probe_p4_device_write.py").read())
    result = run_p4()          # spawns, writes, reports - does NOT save
    result = run_p4(save=True) # also saves the level so disk can be grepped

Then grep the project's Content folder for MCP_P4_ to see what truly landed.
"""

import json

import unreal

BARRIER_ASSET = "/CRD_VolumetricRegion/Device_Barrier_V2_Placed.Device_Barrier_V2_Placed_C"
MARKER_PREFIX = "MCP_P4_"
VARIANTS = ["A", "B", "C", "D", "E"]


def _safe_project() -> bool:
    """Refuse to run against TheScar."""
    world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
    return "thescar" not in world.get_name().lower()


def _spawn_barrier(index: int):
    """Spawn one barrier, spaced out so they are easy to see and select."""
    cls = unreal.EditorAssetLibrary.load_blueprint_class(BARRIER_ASSET)
    loc = unreal.Vector(index * 500.0, 0.0, 100.0)
    actor_sub = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    actor = actor_sub.spawn_actor_from_class(cls, loc, unreal.Rotator(0, 0, 0))
    actor.set_actor_label("P4_Barrier_%s" % VARIANTS[index])
    return actor


def _overrides_json(component) -> str:
    return unreal.ToolsetLibrary.get_object_properties(component, ["PlayerOptionData"])


def _with_label(original_json: str, new_label: str) -> str:
    """Return the full override array with only LabelOverride changed.

    Writing a single-entry array could drop the other options; always write
    back the complete set.
    """
    parsed = json.loads(original_json)
    found = False
    for o in parsed["PlayerOptionData"]["propertyOverrides"]:
        if o["propertyName"] == "LabelOverride":
            o["propertyData"] = new_label
            found = True
    if not found:
        parsed["PlayerOptionData"]["propertyOverrides"].append(
            {"propertyScope": "", "propertyName": "LabelOverride", "propertyData": new_label}
        )
    return json.dumps(parsed)


def _read_both(actor, component, marker: str) -> dict:
    """Read the value through BOTH representations and say whether they agree."""
    try:
        via_toolset = [
            o["propertyData"]
            for o in json.loads(_overrides_json(component))["PlayerOptionData"]["propertyOverrides"]
            if o["propertyName"] == "LabelOverride"
        ]
        via_toolset = via_toolset[0] if via_toolset else None
    except Exception as e:
        via_toolset = "ERR: %s" % e

    try:
        via_option = str(actor.get_user_option_value("LabelOverride"))
    except Exception as e:
        via_option = "ERR: %s" % e

    return {
        "toolset_read": via_toolset,
        "user_option_read": via_option,
        "actor_label": actor.get_actor_label(),
        "toolset_took": via_toolset == marker,
        "user_option_took": via_option == marker,
        "representations_agree": via_toolset == via_option,
    }


def run_p4(save: bool = False) -> dict:
    """Run every write variant on its own barrier. Returns a compact report."""
    if not _safe_project():
        return {"ABORTED": "editor world looks like TheScar - refusing to run"}

    report = {"variants": {}, "marker_prefix": MARKER_PREFIX}

    for i, vid in enumerate(VARIANTS):
        marker = MARKER_PREFIX + vid
        row = {"marker": marker}
        try:
            actor = _spawn_barrier(i)
            comp = actor.get_user_option_definitions()
            original = _overrides_json(comp)
            payload = _with_label(original, marker)

            with unreal.ScopedEditorTransaction("P4 variant %s" % vid):
                if vid == "A":
                    row["call_returned"] = unreal.ToolsetLibrary.set_object_properties(comp, payload)

                elif vid == "B":
                    try:
                        unreal.ToolsetLibrary.modify(comp)
                        row["modify_called"] = True
                    except Exception as e:
                        row["modify_error"] = str(e)
                    row["call_returned"] = unreal.ToolsetLibrary.set_object_properties(comp, payload)

                elif vid == "C":
                    row["call_returned"] = unreal.ToolsetLibrary.set_object_properties(comp, payload)
                    for obj, tag in ((comp, "component"), (actor, "actor")):
                        try:
                            obj.post_edit_change()
                            row["post_edit_change_" + tag] = True
                        except Exception as e:
                            row["post_edit_change_" + tag] = "ERR: %s" % e

                elif vid == "D":
                    try:
                        row["call_returned"] = unreal.ToolsetLibrary.set_object_properties(
                            comp, payload, unreal.BypassContainerCheck.YES
                        )
                    except Exception as e:
                        row["call_error"] = str(e)

                elif vid == "E":
                    # Negative control: documented to no-op with a None controller.
                    try:
                        row["call_returned"] = actor.set_user_option_value(
                            None, "LabelOverride", marker
                        )
                    except Exception as e:
                        row["call_error"] = str(e)

            row.update(_read_both(actor, comp, marker))
            row["actor_path"] = actor.get_path_name()

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

    report["NEXT"] = (
        "grep the project's Content folder for %s - disk is the only arbiter. "
        "A variant is proven ONLY if its marker appears in a saved .uasset."
        % MARKER_PREFIX
    )
    return report
