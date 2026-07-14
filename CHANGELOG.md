# Changelog

All notable changes to Caelus Agent are documented here.

## 0.1.11 — 2026-07-14

### Fixed
- Rebuilt the terminal chat as a stable redrawn conversation view with distinct user/agent messages, wrapping, visible working state, and a dedicated message composer.
- New Caelus runtimes now receive a generic product identity that introduces the agent as Caelus while accurately crediting Hermes Agent as the runtime.
- An existing default Hermes identity is migrated to Caelus without touching runtime sessions, provider configuration, or other user state.

## 0.1.10 — 2026-07-14

### Fixed
- The macOS installer now writes a home-bound `caelus` launcher and adds its bin directory to the user’s login-shell PATH.
- The launcher's private `CAELUS_HOME` now consistently scopes the runtime, access gate, and plain `caelus` startup path.
- The installer now prints the exact one-line PATH refresh command needed in the current Terminal after a piped install.

## 0.1.9 — 2026-07-14

### Added
- Concrete Caelus Replay recording and deterministic replay through the local Cua Driver trajectory recorder.

### Safety
- Recorded trajectories are local-only, use Cua Driver action capture, replay at a visible pace, and stop on their first error.

## 0.1.8 — 2026-07-14

### Added
- Caelus Replay v0: guided, hostname-restricted read-only workflow recipes with previews, guarded Hermes runs, and private run receipts.

### Safety
- Replay v0 rejects credential-like recipe content and instructs the runtime not to submit, message, purchase, delete, publish, change settings, or handle secrets.

## 0.1.7 — 2026-07-14

### Changed
- Renamed the product from Caelus Terminal to Caelus Agent across product copy, package metadata, installer messaging, notices, and licensing.
- Replaced the package/about description with “A local-first agent command center powered by Hermes Agent.”

## 0.1.6 — 2026-07-14

### Fixed
- Clarified that proprietary releases may be downloaded and run as official, unmodified software while source reuse, redistribution, and derivative products remain prohibited.

## 0.1.5 — 2026-07-14

### Changed
- Future Caelus Agent releases are proprietary and all rights are reserved. Earlier MIT-licensed releases retain their original license grants.

## 0.1.4 — 2026-07-14

### Added
- Versioned one-line uninstaller that removes the entire Caelus-owned local workspace and launcher without touching shared system dependencies.

## 0.1.3 — 2026-07-14

### Added
- Installer dependency preflight: reuses supported Python, or installs Homebrew and Python 3.11 when necessary.
- Guided first-run prompts for the local access gate, isolated provider setup, and starting Caelus.

## 0.1.2 — 2026-07-14

### Fixed
- Made the piped web installer safe to run from standard input and ensured temporary-source cleanup never changes a successful install into a failed shell exit.

## 0.1.1 — 2026-07-14

### Added
- Public, versioned macOS bootstrap installer and a one-line quick-install command.
- Product-first README with the Caelus visual mark, feature map, simple onboarding, command reference, and technical reference.
- Plain `caelus` launch support using only the private connection details in its isolated runtime.

### Fixed
- Explicit package discovery so README image assets cannot be mistaken for a Python package during wheel builds.

## 0.1.0 — 2026-07-14

### Added
- Isolated local Hermes runtime launcher with loopback API configuration and health/status controls.
- Persistent Hermes sessions, structured run-event streaming, tool activity display, and run cancellation.
- Safe allowlisted agent-template export/import with checksum validation and extraction protections.
- A disclosed, three-attempt local access gate that stores only a salted verifier.
- MIT licensing, Hermes runtime attribution, a wheel build, isolated installer validation, and GitHub Actions release verification.

### Security and privacy
- Caelus runtime setup, templates, release artifacts, and installer tests exclude personal Hermes profiles, credentials, sessions, memory, logs, and browser state by construction.
- The local access gate is documented as a deterrent, not server-side authentication.
