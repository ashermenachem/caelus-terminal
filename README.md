# Caelus Terminal

A macOS-first terminal chat UI powered by the Hermes Agent runtime.

## Current prototype

The first build is isolated from the active Hermes installation. It renders the matrix-style terminal dashboard and includes a small client for Hermes's documented local API server.

```bash
cd /Users/ashermenachem/Developer/caelus-terminal
./.venv/bin/python -m caelus_terminal --demo
```

Expand collapsed tool activity:

```bash
./.venv/bin/python -m caelus_terminal --demo --expanded-tools
```

## Optional runtime connection

When a separately configured local Hermes API server is running, send one message without touching the active default Hermes home:

```bash
./.venv/bin/python -m caelus_terminal \
  --endpoint http://127.0.0.1:8642/v1 \
  --api-key YOUR_LOCAL_KEY \
  --agent nova \
  --chat "Hello"
```

## Privacy and attribution

- No personal Caelus memory, credentials, sessions, or workflows are included.
- Runtime testing uses an isolated `HERMES_HOME`, never the active `~/.hermes` directory.
- Caelus Terminal is powered by Hermes Agent; full licensing notices will be included before distribution.
