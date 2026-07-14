from pathlib import Path


SCRIPT = Path(__file__).parents[1] / "scripts" / "install-macos.sh"


def test_macos_installer_bootstraps_only_an_isolated_caelus_runtime():
    script = SCRIPT.read_text()

    assert '"$BIN_DIR/caelus" runtime init' in script
    assert 'HERMES_HOME="$CAELUS_HOME/runtime" hermes setup < /dev/tty' in script
    assert "hermes setup\n" not in script.replace(
        'HERMES_HOME="$CAELUS_HOME/runtime" hermes setup < /dev/tty\n', ""
    )


def test_macos_installer_can_bootstrap_a_versioned_release_when_piped_from_the_web():
    script = SCRIPT.read_text()

    assert 'CAELUS_VERSION="${CAELUS_VERSION:-v0.1.6}"' in script
    assert "archive/refs/tags/$CAELUS_VERSION.tar.gz" in script
    assert "tar -xz" in script
    assert "CAELUS_SOURCE_DIR" in script
    assert '${BASH_SOURCE[0]:-$0}' in script
    assert 'Downloading Caelus Terminal ${CAELUS_VERSION}' in script
    assert "cleanup()" in script
    assert "  return 0" in script


def test_macos_installer_bootstraps_python_and_offers_interactive_gate_and_provider_setup():
    script = SCRIPT.read_text()

    assert "ensure_python" in script
    assert "brew install python@3.11" in script
    assert "Homebrew is required to install Python automatically" in script
    assert '"$BIN_DIR/caelus" gate set < /dev/tty' in script
    assert 'HERMES_HOME="$CAELUS_HOME/runtime" hermes setup < /dev/tty' in script


UNINSTALL_SCRIPT = Path(__file__).parents[1] / "scripts" / "uninstall-macos.sh"


def test_macos_uninstaller_removes_only_caelus_owned_paths_and_launcher():
    script = UNINSTALL_SCRIPT.read_text()

    assert 'CAELUS_HOME="${CAELUS_HOME:-$HOME/.caelus}"' in script
    assert 'BIN_DIR="${CAELUS_BIN_DIR:-$HOME/.local/bin}"' in script
    assert 'rm -rf "$CAELUS_HOME"' in script
    assert 'rm -f "$LAUNCHER"' in script
    assert "hermes uninstall" not in script
