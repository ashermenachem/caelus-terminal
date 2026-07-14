# Changelog

All notable changes to Caelus Terminal are documented here.

## 0.1.6 — 2026-07-14

### Fixed
- Clarified that proprietary releases may be downloaded and run as official, unmodified software while source reuse, redistribution, and derivative products remain prohibited.

## 0.1.5 — 2026-07-14

### Changed
- Future Caelus Terminal releases are proprietary and all rights are reserved. Earlier MIT-licensed releases retain their original license grants.

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
