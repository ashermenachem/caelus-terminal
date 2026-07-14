#!/usr/bin/env bash
# Build a distributable wheel and exercise it plus the macOS installer in isolated paths.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PYTHON="${PYTHON:-python3}"
DIST_DIR="${DIST_DIR:-$ROOT/dist}"
SMOKE_ROOT="$(mktemp -d)"
trap 'rm -rf "$SMOKE_ROOT"' EXIT

command -v "$PYTHON" >/dev/null || { echo "Python is required." >&2; exit 1; }
"$PYTHON" -m pytest --version >/dev/null || {
  echo "pytest is required for release verification." >&2
  exit 1
}

cd "$ROOT"
"$PYTHON" -m pytest tests -q
rm -rf "$DIST_DIR"
mkdir -p "$DIST_DIR"
"$PYTHON" -m pip wheel --no-deps --no-build-isolation "$ROOT" --wheel-dir "$DIST_DIR"

WHEEL=("$DIST_DIR"/caelus_agent-*.whl)
[[ -f "${WHEEL[0]}" ]] || { echo "Wheel was not produced." >&2; exit 1; }

"$PYTHON" - "${WHEEL[0]}" <<'PY'
import sys
import zipfile

with zipfile.ZipFile(sys.argv[1]) as wheel:
    names = set(wheel.namelist())
    required = {
        "caelus_terminal/access_gate.py",
        "caelus_terminal/templates.py",
    }
    if not required <= names or not any(name.endswith("/licenses/LICENSE") for name in names) or not any(
        name.endswith("/licenses/NOTICE") for name in names
    ):
        raise SystemExit("Wheel is missing Caelus modules or required notices")
PY

"$PYTHON" -m venv "$SMOKE_ROOT/wheel-venv"
"$SMOKE_ROOT/wheel-venv/bin/python" -m pip install --no-deps "${WHEEL[0]}" >/dev/null
HOME="$SMOKE_ROOT/wheel-home" "$SMOKE_ROOT/wheel-venv/bin/caelus" --demo >/dev/null

mkdir -p "$SMOKE_ROOT/fake-bin"
printf '#!/usr/bin/env bash\nexit 0\n' > "$SMOKE_ROOT/fake-bin/hermes"
chmod +x "$SMOKE_ROOT/fake-bin/hermes"
HOME="$SMOKE_ROOT/installer-user-home" \
SHELL="/bin/zsh" \
CAELUS_HOME="$SMOKE_ROOT/installer-home" \
CAELUS_BIN_DIR="$SMOKE_ROOT/installer-bin" \
CAELUS_SKIP_SETUP=1 \
PYTHON="$PYTHON" \
PATH="$SMOKE_ROOT/fake-bin:$PATH" \
bash "$ROOT/scripts/install-macos.sh" >/dev/null
grep -Fqx "export PATH=\"$SMOKE_ROOT/installer-bin:\$PATH\"" "$SMOKE_ROOT/installer-user-home/.zprofile"
test "$(HOME="$SMOKE_ROOT/installer-user-home" SHELL=/bin/zsh /bin/zsh -lc 'command -v caelus')" = "$SMOKE_ROOT/installer-bin/caelus"
grep -Fqx '# CAELUS_LAUNCHER=1' "$SMOKE_ROOT/installer-bin/caelus"
"$SMOKE_ROOT/installer-bin/caelus" --demo >/dev/null
test -f "$SMOKE_ROOT/installer-home/runtime/.env"
test ! -e "$SMOKE_ROOT/installer-home/runtime/auth.json"
HOME="$SMOKE_ROOT/installer-user-home" \
CAELUS_HOME="$SMOKE_ROOT/installer-home" \
CAELUS_BIN_DIR="$SMOKE_ROOT/installer-bin" \
bash "$ROOT/scripts/uninstall-macos.sh" >/dev/null
test ! -e "$SMOKE_ROOT/installer-home"
test ! -e "$SMOKE_ROOT/installer-bin/caelus"

echo "Release verification passed: $DIST_DIR"
