#!/usr/bin/env bash
# Installs Caelus Agent without modifying an existing Hermes profile.
set -euo pipefail

if [[ "$(uname -s)" != "Darwin" ]]; then
  echo "Caelus Agent supports macOS only." >&2
  exit 1
fi

CAELUS_VERSION="${CAELUS_VERSION:-v0.1.11}"
REPOSITORY_URL="https://github.com/ashermenachem/caelus-agent"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")" && pwd)"
SOURCE_DIR="${CAELUS_SOURCE_DIR:-$(cd "$SCRIPT_DIR/.." && pwd)}"
DOWNLOADED_SOURCE=""
CAELUS_HOME="${CAELUS_HOME:-$HOME/.caelus}"
VENV="$CAELUS_HOME/venv"
BIN_DIR="${CAELUS_BIN_DIR:-$HOME/.local/bin}"
PYTHON="${PYTHON:-python3}"

cleanup() {
  [[ -z "$DOWNLOADED_SOURCE" ]] || rm -rf "$DOWNLOADED_SOURCE"
  return 0
}
trap cleanup EXIT

python_is_supported() {
  "$1" -c 'import sys; raise SystemExit(sys.version_info < (3, 9))' >/dev/null 2>&1
}

activate_homebrew() {
  if [[ -x /opt/homebrew/bin/brew ]]; then
    eval "$(/opt/homebrew/bin/brew shellenv)"
  elif [[ -x /usr/local/bin/brew ]]; then
    eval "$(/usr/local/bin/brew shellenv)"
  fi
}

install_homebrew() {
  echo "Python is missing or too old. Installing Homebrew so Caelus can install Python…"
  echo "macOS may ask for your administrator password; Caelus never receives or stores it."
  /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
  activate_homebrew
  command -v brew >/dev/null || {
    echo "Homebrew is required to install Python automatically, but it was not available after installation." >&2
    exit 1
  }
}

ensure_python() {
  if command -v "$PYTHON" >/dev/null 2>&1 && python_is_supported "$PYTHON"; then
    return 0
  fi
  if ! command -v brew >/dev/null 2>&1; then
    install_homebrew
  fi
  echo "Installing Python 3.11…"
  brew install python@3.11
  for candidate in python3.11 python3; do
    if command -v "$candidate" >/dev/null 2>&1 && python_is_supported "$candidate"; then
      PYTHON="$(command -v "$candidate")"
      return 0
    fi
  done
  echo "A supported Python installation could not be found after setup." >&2
  exit 1
}

ask_yes_no() {
  local prompt="$1"
  local response
  [[ -r /dev/tty ]] || return 1
  printf "%s [Y/n] " "$prompt" > /dev/tty
  read -r response < /dev/tty
  [[ -z "$response" || "$response" =~ ^[Yy]([Ee][Ss])?$ ]]
}

ensure_bin_dir_on_path() {
  local profile entry
  case "$(basename "${SHELL:-zsh}")" in
    zsh) profile="$HOME/.zprofile" ;;
    bash) profile="$HOME/.bash_profile" ;;
    *) profile="$HOME/.profile" ;;
  esac
  entry="export PATH=\"$BIN_DIR:\$PATH\""
  touch "$profile"
  if ! grep -Fqx "$entry" "$profile"; then
    printf '\n# Added by Caelus Agent\n%s\n' "$entry" >> "$profile"
    echo "Caelus added $BIN_DIR to your shell PATH."
  fi
  export PATH="$BIN_DIR:$PATH"
}

if [[ ! -f "$SOURCE_DIR/pyproject.toml" ]]; then
  command -v curl >/dev/null || { echo "curl is required for web installation." >&2; exit 1; }
  command -v tar >/dev/null || { echo "tar is required for web installation." >&2; exit 1; }
  DOWNLOADED_SOURCE="$(mktemp -d)"
  SOURCE_DIR="$DOWNLOADED_SOURCE/source"
  mkdir -p "$SOURCE_DIR"
  echo "Downloading Caelus Agent ${CAELUS_VERSION}…"
  curl -fsSL "$REPOSITORY_URL/archive/refs/tags/$CAELUS_VERSION.tar.gz" \
    | tar -xz -C "$SOURCE_DIR" --strip-components=1
fi

ensure_python
mkdir -p "$CAELUS_HOME" "$BIN_DIR"
"$PYTHON" -m venv "$VENV"
"$VENV/bin/python" -m pip install --upgrade pip >/dev/null
"$VENV/bin/python" -m pip install --force-reinstall --no-deps "$SOURCE_DIR" >/dev/null
cat > "$BIN_DIR/caelus" <<LAUNCHER
#!/usr/bin/env bash
# CAELUS_LAUNCHER=1
export CAELUS_HOME="$CAELUS_HOME"
exec "$VENV/bin/caelus" "\$@"
LAUNCHER
chmod 700 "$BIN_DIR/caelus"
ensure_bin_dir_on_path

# This creates only a dedicated local runtime and loopback API key. It never
# clones another local profile or starts provider authentication in that profile.
"$BIN_DIR/caelus" runtime init --runtime-home "$CAELUS_HOME/runtime"

echo "Caelus Agent installed: $BIN_DIR/caelus"
if ! command -v hermes >/dev/null 2>&1; then
  echo "Installing the local agent runtime…"
  curl -fsSL https://hermes-agent.nousresearch.com/install.sh | bash
  export PATH="$HOME/.local/bin:$PATH"
fi

if ! command -v hermes >/dev/null 2>&1; then
  echo "The runtime installer finished but its command is not on PATH yet. Reopen Terminal, then run Caelus again." >&2
  exit 1
fi

if [[ "${CAELUS_SKIP_SETUP:-0}" == "1" ]]; then
  echo "Skipping interactive setup (CAELUS_SKIP_SETUP=1)."
  exit 0
fi

if ask_yes_no "Set a local Caelus access password now?"; then
  "$BIN_DIR/caelus" gate set < /dev/tty
fi

if ask_yes_no "Connect your AI provider now?"; then
  HERMES_HOME="$CAELUS_HOME/runtime" hermes setup < /dev/tty
fi

if ask_yes_no "Start Caelus now?"; then
  "$BIN_DIR/caelus" runtime start
  echo "Ready. Run: caelus"
  echo "For this same Terminal, run: export PATH=\"$BIN_DIR:\$PATH\""
else
  echo "For this same Terminal, run: export PATH=\"$BIN_DIR:\$PATH\""
  echo "Then run: caelus runtime start && caelus"
fi
