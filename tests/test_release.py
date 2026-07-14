from pathlib import Path


ROOT = Path(__file__).parents[1]


def test_release_metadata_and_notices_disclose_runtime_and_proprietary_caelus_terms():
    pyproject = (ROOT / "pyproject.toml").read_text()
    license_text = (ROOT / "LICENSE").read_text()
    notice = (ROOT / "NOTICE").read_text()

    assert 'readme = "README.md"' in pyproject
    assert 'license = {text = "Proprietary"}' in pyproject
    assert 'License :: Other/Proprietary License' in pyproject
    assert 'packages = ["caelus_terminal"]' in pyproject
    assert "All Rights Reserved" in license_text
    assert "No permission is granted" in license_text
    assert "Caelus Terminal" in notice
    assert "Hermes Agent" in notice
    assert "Nous Research" in notice


def test_macos_installer_honors_isolated_home_and_bin_directory():
    script = (ROOT / "scripts" / "install-macos.sh").read_text()

    assert 'BIN_DIR="${CAELUS_BIN_DIR:-$HOME/.local/bin}"' in script
    assert '"$BIN_DIR/caelus" runtime init --runtime-home "$CAELUS_HOME/runtime"' in script
    assert 'PYTHON="${PYTHON:-python3}"' in script


def test_release_check_builds_wheel_and_smoke_tests_isolated_install():
    script = (ROOT / "scripts" / "release-check.sh").read_text()

    assert "pip wheel --no-deps --no-build-isolation" in script
    assert "pytest tests -q" in script
    assert "CAELUS_SKIP_SETUP=1" in script


def test_release_workflow_and_changelog_exist_for_versioned_distribution():
    workflow = (ROOT / ".github" / "workflows" / "release-check.yml").read_text()
    changelog = (ROOT / "CHANGELOG.md").read_text()

    assert "macos-latest" in workflow
    assert "scripts/release-check.sh" in workflow
    assert "upload-artifact" in workflow
    assert "0.1.0" in changelog
