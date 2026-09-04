"""MCP Server for UEFN Editor.

External process that bridges Claude Code (stdio) to the UEFN HTTP listener.
Requires: pip install mcp

Usage:
    python mcp_server.py
    python mcp_server.py --port 8775

Claude Code config (~/.claude/settings.json or project .mcp.json):
    {
      "mcpServers": {
        "uefn": {
          "command": "python",
          "args": ["/path/to/mcp_server.py"]
        }
      }
    }
"""

import json
import os
import sys
import threading
import time
import urllib.error
import urllib.request
from typing import Any, Optional

from mcp.server.fastmcp import FastMCP

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

DEFAULT_PORT = int(os.environ.get("UEFN_MCP_PORT", "8775"))
MAX_PORT = 8780
REQUEST_TIMEOUT = 30.0

_discovered_port: Optional[int] = None

# ---------------------------------------------------------------------------
# Port discovery
# ---------------------------------------------------------------------------


def _discover_port() -> int:
    """Find the listener by scanning the port range.

    Tries the last known port first, then scans DEFAULT_PORT..MAX_PORT.
    Caches the result so subsequent calls are instant.
    """
    global _discovered_port

    # Fast path: already discovered and still alive
    if _discovered_port is not None:
        if _ping_port(_discovered_port):
            return _discovered_port
        _discovered_port = None

    # Scan the range
    for port in range(DEFAULT_PORT, MAX_PORT + 1):
        if _ping_port(port):
            _discovered_port = port
            return port

    raise ConnectionError(
        f"UEFN listener not found on ports {DEFAULT_PORT}-{MAX_PORT}. "
        "Start it in the UEFN editor console: py \"path/to/uefn_listener.py\""
    )


def _ping_port(port: int) -> bool:
    """Quick check if a listener responds on the given port."""
    try:
        req = urllib.request.Request(
            f"http://127.0.0.1:{port}",
            method="GET",
        )
        with urllib.request.urlopen(req, timeout=1.0) as resp:
            body = json.loads(resp.read().decode())
            return body.get("status") == "ok"
    except Exception:
        return False


# ---------------------------------------------------------------------------
# HTTP client
# ---------------------------------------------------------------------------


def _send_command(command: str, params: Optional[dict] = None, timeout: float = REQUEST_TIMEOUT) -> dict:
    """Send a command to the UEFN listener and return the result.

    Auto-discovers the listener port by scanning the range.

    Raises:
        ConnectionError: Listener is not running.
        RuntimeError: Command failed on the UEFN side.
        TimeoutError: Command timed out.
    """
    global _discovered_port

    port = _discover_port()
    url = f"http://127.0.0.1:{port}"

    payload = json.dumps({"command": command, "params": params or {}}).encode()
    req = urllib.request.Request(
        url,
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = json.loads(resp.read().decode())
    except urllib.error.URLError as e:
        # Port may have changed — invalidate cache and retry once
        if _discovered_port is not None:
            _discovered_port = None
            return _send_command(command, params, timeout)
        raise ConnectionError(
            "UEFN listener is not running. "
            "Start it in the UEFN editor console: py \"path/to/uefn_listener.py\""
        ) from e
    except Exception as e:
        if "timed out" in str(e).lower():
            raise TimeoutError(f"Command '{command}' timed out after {timeout}s") from e
        raise

    if not body.get("success", False):
        error_msg = body.get("error", "Unknown error")
        tb = body.get("traceback", "")
        raise RuntimeError(f"UEFN command '{command}' failed: {error_msg}\n{tb}".strip())

    return body.get("result", {})


def _check_connection() -> str:
    """Quick connection check, returns status message."""
    try:
        port = _discover_port()
        return f"Connected to UEFN on port {port}"
    except ConnectionError:
        return "NOT CONNECTED - UEFN listener is not running"
    except Exception as e:
        return f"Connection error: {e}"


# ---------------------------------------------------------------------------
# Heartbeat — periodic ping so the listener knows we're alive
# ---------------------------------------------------------------------------

_HEARTBEAT_INTERVAL = 10.0


def _heartbeat_loop() -> None:
    """Ping the listener periodically."""
    time.sleep(3.0)  # wait for listener to be ready
    while True:
        try:
            port = _discover_port()
            req = urllib.request.Request(
                f"http://127.0.0.1:{port}",
                method="GET",
            )
            urllib.request.urlopen(req, timeout=2.0)
        except Exception:
            pass
        time.sleep(_HEARTBEAT_INTERVAL)


threading.Thread(target=_heartbeat_loop, daemon=True).start()


# ---------------------------------------------------------------------------
# MCP Server
# ---------------------------------------------------------------------------

mcp = FastMCP(
    "uefn-mcp",
    instructions=(
        "MCP server for controlling UEFN (Unreal Editor for Fortnite). "
        "Provides tools to manage actors, assets, levels, and viewport in the UEFN editor. "
        "The 'execute_python' tool is the most powerful — it runs arbitrary Python code "
        "inside the editor with full access to the `unreal` module. "
        "Use structured tools for common operations and execute_python for everything else.\n\n"
        "IMPORTANT: When creating tkinter UI windows via execute_python, NEVER call tk.Tk(). "
        "Use `root = get_tk_root()` to get the shared root, then `tk.Toplevel(root)` for windows. "
        "Multiple tk.Tk() instances will crash the editor."
    ),
)


# -- System tools ------------------------------------------------------------


@mcp.tool()
def ping() -> str:
    """Check if the UEFN editor listener is running and responsive."""
    result = _send_command("ping")
    return json.dumps(result, indent=2)


@mcp.tool()
def execute_python(code: str) -> str:
    """Execute arbitrary Python code inside the UEFN editor.

    The code runs on the main editor thread with full access to the `unreal` module.
    Pre-populated variables: unreal, actor_sub, asset_sub, level_sub, tk, get_tk_root.
    Assign to `result` variable to return a value. Use print() for stdout output.

    IMPORTANT — tkinter windows:
        Use get_tk_root() to get the shared tk.Tk() root, then create windows with
        tk.Toplevel(root). NEVER create a new tk.Tk() — multiple Tk instances crash
        the editor. The root is shared across all scripts in the process.

    Examples:
        # Get world name
        result = unreal.EditorLevelLibrary.get_editor_world().get_name()

        # List all static mesh actors
        actors = actor_sub.get_all_level_actors()
        result = [a.get_actor_label() for a in actors if a.get_class().get_name() == 'StaticMeshActor']

        # Create a material
        mat = unreal.AssetToolsHelpers.get_asset_tools().create_asset(
            'M_Test', '/Game/Materials', unreal.Material, unreal.MaterialFactoryNew()
        )
        result = str(mat.get_path_name())

        # Create a tkinter window (ALWAYS use Toplevel, never tk.Tk!)
        import threading
        def show_window():
            root = get_tk_root()
            win = tk.Toplevel(root)
            win.title("My Tool")
            win.attributes("-topmost", True)
            tk.Label(win, text="Hello from UEFN").pack(padx=20, pady=20)
            root.mainloop()
        threading.Thread(target=show_window, daemon=True).start()
        result = "Window opened"
    """
    result = _send_command("execute_python", {"code": code})
    parts = []
    if result.get("stdout"):
        parts.append(f"stdout:\n{result['stdout']}")
    if result.get("stderr"):
        parts.append(f"stderr:\n{result['stderr']}")
    if result.get("result") is not None:
        parts.append(f"result: {json.dumps(result['result'], indent=2)}")
    return "\n".join(parts) if parts else "(no output)"


@mcp.tool()
def get_log(last_n: int = 50) -> str:
    """Get recent MCP listener log entries from the UEFN editor."""
    result = _send_command("get_log", {"last_n": last_n})
    return "\n".join(result.get("lines", []))


@mcp.tool()
def shutdown() -> str:
    """Gracefully stop the UEFN listener, freeing the port.

    The listener will finish the current request, then shut down.
    After this call the listener must be restarted from the UEFN console.
    """
    result = _send_command("shutdown", timeout=5.0)
    return json.dumps(result, indent=2)


# -- Actor tools -------------------------------------------------------------


@mcp.tool()
def get_all_actors(class_filter: str = "") -> str:
    """List all actors in the current level.

    Args:
        class_filter: Optional class name to filter by (e.g. 'StaticMeshActor', 'PointLight').
    """
    result = _send_command("get_all_actors", {"class_filter": class_filter})
    return json.dumps(result, indent=2)


@mcp.tool()
def get_selected_actors() -> str:
    """Get currently selected actors in the UEFN viewport."""
    result = _send_command("get_selected_actors")
    return json.dumps(result, indent=2)


@mcp.tool()
def spawn_actor(
    asset_path: str = "",
    actor_class: str = "",
    location: Optional[list[float]] = None,
    rotation: Optional[list[float]] = None,
) -> str:
    """Spawn an actor in the current level.

    Provide either asset_path OR actor_class (not both).

    Args:
        asset_path: Asset path to spawn from (e.g. '/Engine/BasicShapes/Cube').
        actor_class: Unreal class name (e.g. 'PointLight', 'CameraActor').
        location: [x, y, z] coordinates. Defaults to origin.
        rotation: [pitch, yaw, roll] in degrees. Defaults to zero.
    """
    params: dict[str, Any] = {}
    if asset_path:
        params["asset_path"] = asset_path
    if actor_class:
        params["actor_class"] = actor_class
    if location is not None:
        params["location"] = location
    if rotation is not None:
        params["rotation"] = rotation
    result = _send_command("spawn_actor", params)
    return json.dumps(result, indent=2)


@mcp.tool()
def delete_actors(actor_paths: list[str]) -> str:
    """Delete actors from the current level by path or label.

    Args:
        actor_paths: List of actor path names or labels to delete.
    """
    result = _send_command("delete_actors", {"actor_paths": actor_paths})
    return json.dumps(result, indent=2)


@mcp.tool()
def set_actor_transform(
    actor_path: str,
    location: Optional[list[float]] = None,
    rotation: Optional[list[float]] = None,
    scale: Optional[list[float]] = None,
) -> str:
    """Set an actor's transform (location, rotation, and/or scale).

    Args:
        actor_path: Actor path name or label.
        location: [x, y, z] world coordinates.
        rotation: [pitch, yaw, roll] in degrees.
        scale: [x, y, z] scale factors.
    """
    params: dict[str, Any] = {"actor_path": actor_path}
    if location is not None:
        params["location"] = location
    if rotation is not None:
        params["rotation"] = rotation
    if scale is not None:
        params["scale"] = scale
    result = _send_command("set_actor_transform", params)
    return json.dumps(result, indent=2)


@mcp.tool()
def get_actor_properties(actor_path: str, properties: list[str]) -> str:
    """Read specific properties from an actor.

    Note: UEFN uses Fort*-prefixed actor classes (e.g. FortStaticMeshActor instead of
    StaticMeshActor). Some standard UE5 property names may not exist on Fort* actors.
    Properties that fail to read will return an error string instead of a value.

    Args:
        actor_path: Actor path name or label.
        properties: List of property names to read (e.g. ['static_mesh_component', 'mobility']).
    """
    result = _send_command("get_actor_properties", {"actor_path": actor_path, "properties": properties})
    return json.dumps(result, indent=2)


@mcp.tool()
def set_actor_properties(actor_path: str, properties: dict[str, Any]) -> str:
    """Set properties on an actor via set_editor_property().

    Note: UEFN uses Fort*-prefixed actor classes (e.g. FortStaticMeshActor instead of
    StaticMeshActor). Not all properties are writable — some are read-only or don't exist
    on Fort* actors. For methods like set_actor_hidden_in_game(), use execute_python instead.
    Each property reports 'ok' or an error individually.

    Args:
        actor_path: Actor path name or label.
        properties: Dict of property names to values (e.g. {'cast_shadow': False}).
    """
    result = _send_command("set_actor_properties", {"actor_path": actor_path, "properties": properties})
    return json.dumps(result, indent=2)


@mcp.tool()
def select_actors(actor_paths: list[str], add_to_selection: bool = False) -> str:
    """Select actors in the UEFN viewport.

    Args:
        actor_paths: List of actor path names or labels to select.
        add_to_selection: If True, add to current selection instead of replacing.
    """
    result = _send_command("select_actors", {"actor_paths": actor_paths, "add_to_selection": add_to_selection})
    return json.dumps(result, indent=2)


@mcp.tool()
def focus_selected() -> str:
    """Move the viewport camera to focus on the currently selected actors (like pressing F)."""
    result = _send_command("focus_selected")
    return json.dumps(result, indent=2)



@mcp.tool()
def get_editor_log(last_n: int = 100, filter_str: str = "") -> str:
    """Read recent lines from the Unreal Editor Output Log.

    Args:
        last_n: Number of recent lines to return.
        filter_str: Optional filter — only lines containing this string (case-insensitive).
    """
    result = _send_command("get_editor_log", {"last_n": last_n, "filter_str": filter_str})
    lines = result.get("lines", [])
    if result.get("error"):
        return f"Error: {result['error']}"
    return "\n".join(lines)


# -- Asset tools -------------------------------------------------------------


@mcp.tool()
def list_assets(directory: str = "/Game/", recursive: bool = True, class_filter: str = "") -> str:
    """List assets in a directory.

    Args:
        directory: Content directory path (e.g. '/Game/', '/Game/Materials/').
        recursive: Include subdirectories.
        class_filter: Optional class name filter (e.g. 'Material', 'StaticMesh').
    """
    result = _send_command("list_assets", {"directory": directory, "recursive": recursive, "class_filter": class_filter})
    return json.dumps(result, indent=2)


@mcp.tool()
def get_asset_info(asset_path: str) -> str:
    """Get detailed info about an asset.

    Args:
        asset_path: Full asset path (e.g. '/Game/Materials/M_Base').
    """
    result = _send_command("get_asset_info", {"asset_path": asset_path})
    return json.dumps(result, indent=2)


@mcp.tool()
def get_selected_assets() -> str:
    """Get assets currently selected in the Content Browser."""
    result = _send_command("get_selected_assets")
    return json.dumps(result, indent=2)


@mcp.tool()
def rename_asset(old_path: str, new_path: str) -> str:
    """Rename or move an asset.

    Args:
        old_path: Current asset path.
        new_path: New asset path.
    """
    result = _send_command("rename_asset", {"old_path": old_path, "new_path": new_path})
    return json.dumps(result, indent=2)


@mcp.tool()
def delete_asset(asset_path: str) -> str:
    """Delete an asset.

    Args:
        asset_path: Asset path to delete.
    """
    result = _send_command("delete_asset", {"asset_path": asset_path})
    return json.dumps(result, indent=2)


@mcp.tool()
def duplicate_asset(source_path: str, dest_path: str) -> str:
    """Duplicate an asset to a new path.

    Args:
        source_path: Source asset path.
        dest_path: Destination asset path.
    """
    result = _send_command("duplicate_asset", {"source_path": source_path, "dest_path": dest_path})
    return json.dumps(result, indent=2)


@mcp.tool()
def does_asset_exist(asset_path: str) -> str:
    """Check if an asset exists at the given path.

    Args:
        asset_path: Asset path to check.
    """
    result = _send_command("does_asset_exist", {"asset_path": asset_path})
    return json.dumps(result, indent=2)


@mcp.tool()
def save_asset(asset_path: str) -> str:
    """Save a modified asset.

    Args:
        asset_path: Asset path to save.
    """
    result = _send_command("save_asset", {"asset_path": asset_path})
    return json.dumps(result, indent=2)


@mcp.tool()
def search_assets(class_name: str = "", directory: str = "/Game/", recursive: bool = True) -> str:
    """Search for assets using the Asset Registry.

    Args:
        class_name: Filter by class name (e.g. 'Material', 'Texture2D').
        directory: Directory to search in.
        recursive: Include subdirectories.
    """
    result = _send_command("search_assets", {"class_name": class_name, "directory": directory, "recursive": recursive})
    return json.dumps(result, indent=2)


# -- Project tools -----------------------------------------------------------


@mcp.tool()
def get_project_info() -> str:
    """Get the UEFN project name and content root path.

    Use the returned content_root as the base path for asset operations
    (e.g. list_assets, search_assets, create assets via execute_python).
    In UEFN the content root is '/{ProjectName}/', NOT '/Game/'.
    """
    result = _send_command("get_project_info")
    return json.dumps(result, indent=2)


# -- Level tools -------------------------------------------------------------


@mcp.tool()
def save_current_level() -> str:
    """Save the current level."""
    result = _send_command("save_current_level")
    return json.dumps(result, indent=2)


@mcp.tool()
def get_level_info() -> str:
    """Get info about the current level (name, actor count)."""
    result = _send_command("get_level_info")
    return json.dumps(result, indent=2)


# -- Viewport tools ----------------------------------------------------------


@mcp.tool()
def get_viewport_camera() -> str:
    """Get the current viewport camera position and rotation."""
    result = _send_command("get_viewport_camera")
    return json.dumps(result, indent=2)


@mcp.tool()
def set_viewport_camera(
    location: Optional[list[float]] = None,
    rotation: Optional[list[float]] = None,
) -> str:
    """Move the viewport camera to a position.

    Args:
        location: [x, y, z] world coordinates.
        rotation: [pitch, yaw, roll] in degrees.
    """
    params: dict[str, Any] = {}
    if location is not None:
        params["location"] = location
    if rotation is not None:
        params["rotation"] = rotation
    result = _send_command("set_viewport_camera", params)
    return json.dumps(result, indent=2)


# ---------------------------------------------------------------------------
# Extended editor control (uefn-mcp-server-extended fork)
#
# These close the biggest gaps against the Unity MCP server. Every underlying
# API was signature-verified in a live UEFN editor - see MCP_UPGRADE.md.
# ---------------------------------------------------------------------------


# play_mode / PIE is deliberately NOT exposed as a tool.
#
# IMPLEMENTATION_PLAN.md section 2, ruling 9: UEFN's play model is
# Play-in-Client via SessionToolset, and PIE entry triggers the world change
# that kills the in-process listener - the bridge dies mid-call. The API is
# available (LevelEditorSubsystem.editor_request_begin_play), which is exactly
# why it is tempting; availability is not a reason to ship it.
#
# The listener still carries a play_mode handler for deliberate manual use via
# execute_python, but no agent gets a one-call path to killing the bridge.


@mcp.tool()
def pilot_actor(action: str = "status", actor_path: str = "") -> str:
    """Attach the viewport camera to an actor, or detach it.

    Args:
        action: "pilot", "eject", or "status".
        actor_path: Full path, label, or name of the actor to pilot.
                    Required when action is "pilot".
    """
    params: dict[str, Any] = {"action": action}
    if actor_path:
        params["actor_path"] = actor_path
    result = _send_command("pilot_actor", params)
    return json.dumps(result, indent=2)


@mcp.tool()
def take_screenshot(
    filename: str = "",
    res_x: int = 1920,
    res_y: int = 1080,
    force_game_view: bool = False,
    delay: float = 0.0,
    wait_seconds: float = 20.0,
) -> str:
    """Capture a high-resolution screenshot of the UEFN viewport.

    Use this to SEE the editor rather than infer its state from properties.
    The PNG lands in the editor's Screenshots folder (under AppData, not in
    the island's Content/ folder, so it is never bundled at publish). The
    returned "path" can be opened with the Read tool.

    The capture takes several editor frames; this tool waits for the file to
    land before returning, so "exists": true means it is really on disk.

    Args:
        filename: Output name. Defaults to a timestamped mcp_*.png.
        res_x: Width in pixels.
        res_y: Height in pixels.
        force_game_view: Hide editor-only gizmos and icons in the capture.
        delay: Seconds to wait before capturing.
        wait_seconds: How long to wait for the file to appear.
    """
    result = _send_command(
        "take_screenshot",
        {
            "filename": filename,
            "res_x": res_x,
            "res_y": res_y,
            "force_game_view": force_game_view,
            "delay": delay,
        },
    )

    # The capture needs several editor ticks. Poll here rather than blocking
    # the editor's main thread, so the tool returns a file that actually exists.
    name = result.get("filename", filename)
    deadline = time.time() + max(5.0, wait_seconds)
    status = {}
    while time.time() < deadline:
        time.sleep(0.4)
        try:
            status = _send_command("screenshot_status", {"filename": name})
        except Exception:
            continue
        if status.get("exists"):
            break

    result.update(
        {
            "pending": not status.get("exists", False),
            "exists": status.get("exists", False),
            "size_bytes": status.get("size_bytes", 0),
        }
    )
    if not status.get("exists", False):
        result["note"] = (
            "capture did not land within %.0fs. The UEFN window may be idle - "
            "click it to give the editor focus, then retry." % wait_seconds
        )
    else:
        result["note"] = "saved - open it with the Read tool"
    return json.dumps(result, indent=2)


@mcp.tool()
def console_command(command: str, use_game_world: bool = True) -> str:
    """Run an Unreal console command inside UEFN.

    Examples: "stat fps", "stat unit", "r.ScreenPercentage 50", "showflag.Collision 1".

    Console commands produce no return value - read their output with
    get_editor_log afterwards.

    Args:
        command: The console command line.
        use_game_world: Target the play-in-editor world when one exists.
                        Set false to always target the editor world.
    """
    result = _send_command(
        "console_command", {"command": command, "use_game_world": use_game_world}
    )
    return json.dumps(result, indent=2)


@mcp.tool()
def validate_assets(
    asset_paths: Optional[list[str]] = None,
    directory: str = "",
    recursive: bool = True,
    usecase: str = "MANUAL",
) -> str:
    """Run Fortnite's own asset validators - the scripted pre-publish check.

    This is the tool that answers "is this island safe to publish?" without
    clicking through the editor. It reports, per asset, whether Epic's
    validators consider it VALID, INVALID, or NOT_VALIDATED, plus every
    validator error and warning.

    Give either asset_paths or directory, not both.

    Args:
        asset_paths: Explicit list of asset object paths to validate.
        directory: Content path to scan instead, e.g. "/Game/".
        recursive: Recurse into subfolders when scanning a directory.
        usecase: One of COMMANDLET, MANUAL, NONE, PRE_SUBMIT, SAVE, SCRIPT.
                 PRE_SUBMIT is the strictest and the closest to publishing.
    """
    params: dict[str, Any] = {"recursive": recursive, "usecase": usecase}
    if asset_paths:
        params["asset_paths"] = asset_paths
    if directory:
        params["directory"] = directory
    result = _send_command("validate_assets", params, timeout=120.0)
    return json.dumps(result, indent=2)


@mcp.tool()
def list_devices(class_filter: str = "", kind: str = "") -> str:
    """List every configurable Creative actor placed in the level.

    Devices are the gameplay logic of an island - barriers, item granters,
    timers, score managers, player spawners. This finds them all and reports
    how many options each exposes, plus a by_class summary.

    Static props are excluded: every placed actor in UEFN answers the options
    API, but a prop's only option is its label, so anything with a single
    option is filtered out.

    Args:
        class_filter: Case-insensitive substring of the class,
                      e.g. "Barrier" or "ItemGranter".
        kind: "device" for first-class Device_*/VerseDevice actors,
              "configurable" for other option-bearing actors such as player
              spawners. Empty returns both.
    """
    result = _send_command(
        "list_devices", {"class_filter": class_filter, "kind": kind}
    )
    return json.dumps(result, indent=2)


@mcp.tool()
def get_device_options(actor_path: str) -> str:
    """Read every configurable option on a Creative device, with its value.

    This exposes the device's Details-panel settings - the things a creator
    would normally click through in the UEFN UI.

    Two limits, both measured rather than assumed:
      - Options are READ-ONLY here. No proven write path exists yet, so no
        write tool is offered rather than one that silently does nothing.
      - This API does not surface Verse @editable values; a VerseDevice
        returns only its three base Creative options. They ARE readable by a
        different route (DeviceToolset.GetDeviceProperties), just not here.

    Args:
        actor_path: Full path, label, or name of the device actor.
    """
    result = _send_command("get_device_options", {"actor_path": actor_path})
    return json.dumps(result, indent=2)


# ---------------------------------------------------------------------------
# read_log / read_crashes - off disk, in THIS process
#
# IMPLEMENTATION_PLAN.md section 4: log reading belongs here, not in the
# listener. Three reasons, all of which bit us on 2026-09-04:
#   1. Zero game-thread cost - it never touches the editor tick.
#   2. It works when the editor is busy, hung, or the listener is dead. That
#      is exactly when you most want the log.
#   3. The listener's get_editor_log served content 37 minutes stale while the
#      file on disk was current to the second, and ignored its filter_str.
#      The old handler is left alone deliberately; use this instead.
# ---------------------------------------------------------------------------

_LOG_DIR = os.path.join(
    os.environ.get("LOCALAPPDATA", ""), "UnrealEditorFortnite", "Saved", "Logs"
)
_LOG_FILES = {
    "editor": "UnrealEditorFortnite.log",
    "lore": "Lore.log",
}
_CRASH_DIR = os.path.join(
    os.environ.get("LOCALAPPDATA", ""), "UnrealEditorFortnite", "Saved", "Crashes"
)


def _resolve_log_path(log: str) -> str:
    """Map a friendly log name (or an explicit path) to a file on disk."""
    if log in _LOG_FILES:
        return os.path.join(_LOG_DIR, _LOG_FILES[log])
    if os.path.isabs(log):
        return log
    return os.path.join(_LOG_DIR, log)


def _line_level(line: str) -> str:
    """Classify a UE log line. UE writes 'LogFoo: Error: msg'."""
    low = line.lower()
    if ": error:" in low or "fatal" in low:
        return "error"
    if ": warning:" in low:
        return "warning"
    return "display"


@mcp.tool()
def read_log(
    lines: int = 100,
    filter: str = "",
    level: str = "all",
    since: str = "",
    cursor: int = 0,
    log: str = "editor",
) -> str:
    """Read the UEFN editor log from disk.

    Prefer this over get_editor_log: it reads the live file directly, so it is
    never stale, costs the editor nothing, and still works when the editor is
    hung or the in-editor listener is dead.

    Args:
        lines: Return at most this many of the most recent matching lines.
        filter: Case-insensitive substring; only matching lines are returned.
        level: "all", "error", "warning", or "error+warning".
        since: Return only lines at or after this timestamp prefix, e.g.
               "2026.09.04-07.30". Matches UE's [YYYY.MM.DD-HH.MM.SS:mmm] stamp.
        cursor: Byte offset from a previous call's next_cursor. Reads only what
                has been appended since then - use it to poll for new output.
        log: "editor" (UnrealEditorFortnite.log), "lore" (Lore.log), a bare
             filename in the Logs folder, or an absolute path.

    Returns lines plus next_cursor, so a follow-up call can read only what is new.
    """
    path = _resolve_log_path(log)
    if not os.path.isfile(path):
        available = []
        if os.path.isdir(_LOG_DIR):
            available = sorted(f for f in os.listdir(_LOG_DIR) if f.endswith(".log"))
        return json.dumps(
            {"error": "log not found: %s" % path, "available": available}, indent=2
        )

    size = os.path.getsize(path)
    start = max(0, int(cursor))
    if start > size:
        start = 0  # file rotated out from under us

    # Without a cursor, read only the tail rather than the whole file.
    TAIL_BYTES = 2_000_000
    if cursor <= 0 and size > TAIL_BYTES:
        start = size - TAIL_BYTES

    with open(path, "rb") as fh:
        fh.seek(start)
        raw = fh.read()

    text = raw.decode("utf-8", errors="replace")
    all_lines = text.splitlines()
    # A partial first line is likely when we seeked into the middle of one.
    if start > 0 and all_lines:
        all_lines = all_lines[1:]

    want = (level or "all").lower()
    needle = (filter or "").lower()

    matched = []
    for ln in all_lines:
        if needle and needle not in ln.lower():
            continue
        if want != "all":
            lv = _line_level(ln)
            if want == "error+warning":
                if lv not in ("error", "warning"):
                    continue
            elif lv != want:
                continue
        if since:
            stamp = ln[1:24] if ln.startswith("[") else ""
            if stamp and stamp < since:
                continue
        matched.append(ln)

    total = len(matched)
    if lines > 0:
        matched = matched[-lines:]

    return json.dumps(
        {
            "file": path,
            "file_size": size,
            "next_cursor": size,
            "matched": total,
            "returned": len(matched),
            "level": want,
            "filter": filter,
            "lines": matched,
        },
        indent=2,
    )


@mcp.tool()
def read_crashes(limit: int = 3, context_lines: int = 40) -> str:
    """List recent UEFN crash reports and show each one's call stack.

    Reads Saved/Crashes off disk, so it works after the editor has died -
    which is the only time it matters. Use it to find out why the last
    session ended.

    Args:
        limit: How many of the most recent crashes to report.
        context_lines: Lines of each crash log to include.
    """
    if not os.path.isdir(_CRASH_DIR):
        return json.dumps({"crashes": [], "note": "no crash folder: %s" % _CRASH_DIR}, indent=2)

    entries = []
    for name in os.listdir(_CRASH_DIR):
        full = os.path.join(_CRASH_DIR, name)
        if os.path.isdir(full):
            entries.append((os.path.getmtime(full), name, full))
    entries.sort(reverse=True)

    out = []
    for mtime, name, full in entries[: max(1, limit)]:
        rec = {
            "crash": name,
            "when": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(mtime)),
            "files": sorted(os.listdir(full))[:12],
        }
        log_path = None
        for f in os.listdir(full):
            if f.lower().endswith(".log"):
                log_path = os.path.join(full, f)
                break
        if log_path:
            try:
                with open(log_path, "rb") as fh:
                    tail = fh.read()[-200_000:]
                rec["log_tail"] = tail.decode("utf-8", errors="replace").splitlines()[
                    -max(1, context_lines):
                ]
            except Exception as e:
                rec["log_error"] = str(e)
        out.append(rec)

    return json.dumps({"crash_dir": _CRASH_DIR, "count": len(entries), "crashes": out}, indent=2)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    # Allow --port override (skips auto-discovery, uses fixed port)
    for i, arg in enumerate(sys.argv[1:], 1):
        if arg == "--port" and i < len(sys.argv) - 1:
            _discovered_port = int(sys.argv[i + 1])

    mcp.run()
