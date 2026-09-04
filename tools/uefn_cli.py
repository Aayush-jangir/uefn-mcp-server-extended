"""Talk to the UEFN listener directly over HTTP, bypassing the MCP client.

WHY THIS EXISTS
---------------
Edits to `uefn_listener.py` take effect by re-running the listener inside the
editor. Edits to `mcp_server.py` do NOT - they need the MCP *client* process
restarted, which throws away the session's context. This script speaks the same
wire protocol `mcp_server.py` uses, so new listener commands can be exercised
end-to-end without restarting anything.

USAGE
    python tools/uefn_cli.py ping
    python tools/uefn_cli.py list_devices '{"kind":"device"}'
    python tools/uefn_cli.py get_device_options '{"actor_path":"TrophyBarrier_W"}'

Ports 8775-8780 = the extended fork. The original server is on 8765-8770; the
split is deliberate, so do not point this at the original by "tidying" it.
"""

import json
import sys
import urllib.request

DEFAULT_PORT = 8775
MAX_PORT = 8780


def find_port(default_port: int = DEFAULT_PORT, max_port: int = MAX_PORT) -> int:
    for port in range(default_port, max_port + 1):
        try:
            with urllib.request.urlopen("http://127.0.0.1:%d" % port, timeout=1.0) as r:
                if json.loads(r.read().decode()).get("status") == "ok":
                    return port
        except Exception:
            pass
    raise SystemExit(
        "No listener on %d-%d. Start it in UEFN: Tools > Execute Python Script > "
        "uefn_listener.py" % (default_port, max_port)
    )


def call(command: str, params: dict = None, timeout: float = 60.0) -> dict:
    port = find_port()
    payload = json.dumps({"command": command, "params": params or {}}).encode()
    req = urllib.request.Request(
        "http://127.0.0.1:%d" % port,
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=timeout) as r:
        body = json.loads(r.read().decode())
    if not body.get("success", False):
        raise SystemExit(
            "FAILED: %s\n%s" % (body.get("error"), body.get("traceback", ""))
        )
    return body.get("result", {})


if __name__ == "__main__":
    if len(sys.argv) < 2:
        raise SystemExit(__doc__)
    cmd = sys.argv[1]
    prm = json.loads(sys.argv[2]) if len(sys.argv) > 2 else {}
    print(json.dumps(call(cmd, prm), indent=2))
