# UEFN + Claude Code — startup checklist

**Open UEFN → Tools ▸ Execute Python Script ▸ `uefn_listener.py` → open a Claude Code session → `/mcp` shows `uefn ✓`**

No terminal required. The only manual step is starting the listener inside UEFN.

---

## Every session

**1. Open UEFN** and load `TheScar`.

**2. Start the listener** — Tools ▸ Execute Python Script ▸ browse to:

```
G:\UEFN\uefn-mcp-server\uefn_listener.py
```

Wait for the popup: **Listener: Running**, port 8765.

**3. Open a NEW Claude Code session** (Claude Desktop app, or `claude` in a terminal — either
works). The `uefn` server is registered at **user scope**, so it loads in any project directory.

**4. Type `/mcp`** — `uefn` should show as connected with **28 tools**.

---

## Notes

- **Order doesn't matter.** The MCP server starts and advertises all 28 tools even if the listener
  isn't running yet. Only the individual tool call fails, with a clear message, and it retries on the
  next call — so if you forget step 2, just start the listener and try again. **No need to restart
  Claude Code.**
- **The listener does not survive a UEFN restart.** Close UEFN, and step 2 must be repeated.
- **An already-open Claude Code session won't pick up config changes.** MCP servers connect at
  session start. After editing MCP config, start a new session.

## Deliberate choice: no auto-start

The repo ships an `init_unreal.py` auto-start hook, but installing it means copying
`init_unreal.py` + `uefn_listener.py` into `TheScar\Content\Python\` — and anything under `Content/`
gets bundled when the island is published. We start the listener manually instead to keep the
shipped project clean. **Don't install the hook.**

---

## Troubleshooting

**Is the listener actually up?**

```bash
curl http://127.0.0.1:8765/status
```

Healthy response: `{"status": "ok", "version": "0.2.0", "port": 8765, ...}`

**`/mcp` shows an error?** Never trust the bare `-32000: Connection closed` — it hides the real
cause. The actual stderr is logged here:

```
%LOCALAPPDATA%\claude-cli-nodejs\Cache\<project-slug>\mcp-logs-uefn\*.jsonl
```

e.g. `C:\Users\aayus\AppData\Local\claude-cli-nodejs\Cache\G--UEFN-TheScar\mcp-logs-uefn\`

**Known past failure (fixed 2026-08-09):** this PC has three `python.exe` on PATH — Microsoft Store
3.13, msys2 3.12, and PyManager 3.14. Registering the server as bare `python` meant Claude Code
resolved a different interpreter than the terminal did, one without the `mcp` package, giving
`ModuleNotFoundError: No module named 'mcp'` behind the opaque `-32000`.

Fixed by giving the server its own venv and registering it by **absolute path**:

```bash
claude mcp add --scope user uefn -- G:/UEFN/uefn-mcp-server/.venv/Scripts/python.exe G:/UEFN/uefn-mcp-server/mcp_server.py
```

Never register a bare `python` command for an MCP server on this machine.

**Rebuilding the venv from scratch**, if it ever breaks:

```bash
"C:\Users\aayus\AppData\Local\Microsoft\WindowsApps\python.exe" -m venv "G:\UEFN\uefn-mcp-server\.venv"
```

```bash
"G:\UEFN\uefn-mcp-server\.venv\Scripts\python.exe" -m pip install "mcp<2.0.0"
```

`mcp` must be **below 2.0** — `mcp_server.py` imports `mcp.server.fastmcp.FastMCP`, which 2.x
removed. Currently pinned at 1.29.0.
