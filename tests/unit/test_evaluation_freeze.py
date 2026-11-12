import importlib.util
import json
import shutil
from types import SimpleNamespace

import pytest

from llm_eval import evaluation_freeze as freeze


@pytest.fixture
def checkout(tmp_path):
    paths = (*freeze.FROZEN_TEXT_FILES, *freeze.EVIDENCE_FILES, "config.toml", "evaluation-freeze.json")
    for relative in paths:
        target = tmp_path / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(freeze.ROOT / relative, target)
    return tmp_path


def change_json(path, edit):
    data = json.loads(path.read_text(encoding="utf-8-sig"))
    edit(data)
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def test_recorded_protocol_and_real_pinned_environment_pass_without_writes(checkout):
    before = {path: path.read_bytes() for path in checkout.rglob("*") if path.is_file()}
    report = freeze.check_evaluation_freeze(checkout)
    assert report["protocol_matches"]
    assert report["installed_environment_checked"]
    assert not report["ollama_runtime_checked"]
    assert not report["final_dataset_frozen"]
    assert report["freeze_sha256"] == freeze.json_sha256(checkout / "evaluation-freeze.json")
    assert before == {path: path.read_bytes() for path in checkout.rglob("*") if path.is_file()}


def test_future_dataset_selector_is_allowed_without_claiming_dataset_validation(checkout):
    config = checkout / "final-config.toml"
    config.write_text((checkout / "config.toml").read_text().replace('dataset = "data/pilot.json"', 'dataset = "data/final-not-created.json"'))
    assert not freeze.check_evaluation_freeze(checkout, config_path="final-config.toml", check_environment=False)["final_dataset_frozen"]


@pytest.mark.parametrize("before,after,field", [
    ('groundedness = 0.8', 'groundedness = 0.6', 'thresholds'),
    ('num_ctx = 4096', 'num_ctx = 8192', 'judge'),
    ('seed = 42', 'seed = 43', 'answer'),
    ('num_gpu = 0', 'num_gpu = false', 'answer'),
    ('prompt_version = "context-qa-v1"', 'prompt_version = "context-qa-v2"', 'prompt_version'),
])
def test_configuration_drift_fails_including_boolean_zero(checkout, before, after, field):
    path = checkout / "config.toml"
    path.write_text(path.read_text().replace(before, after, 1))
    with pytest.raises(ValueError, match=f"Configuration differs: {field}"):
        freeze.check_evaluation_freeze(checkout, check_environment=False)


def test_missing_dataset_or_extra_setting_is_not_silently_exempt(checkout):
    path = checkout / "config.toml"
    text = path.read_text().replace('dataset = "data/pilot.json"', 'undocumented_option = true')
    path.write_text(text)
    with pytest.raises(ValueError, match="dataset path"):
        freeze.check_evaluation_freeze(checkout, check_environment=False)
    path.write_text(text.replace('undocumented_option = true', 'dataset = "data/pilot.json"\nundocumented_option = true'))
    with pytest.raises(ValueError, match="undocumented_option"):
        freeze.check_evaluation_freeze(checkout, check_environment=False)


@pytest.mark.parametrize("relative", freeze.FROZEN_TEXT_FILES[:3])
def test_scoring_prompt_or_adapter_change_invalidates_the_record(checkout, relative):
    path = checkout / relative
    path.write_text(path.read_text() + "\n# changed after the recorded baseline\n")
    with pytest.raises(ValueError, match="Frozen file changed"):
        freeze.check_evaluation_freeze(checkout, check_environment=False)


def test_windows_checkout_line_endings_and_json_layout_do_not_invalidate_protocol(checkout):
    for relative in freeze.FROZEN_TEXT_FILES:
        path = checkout / relative
        path.write_bytes(path.read_text(encoding="utf-8-sig").replace("\n", "\r\n").encode("utf-8-sig"))
    for relative in freeze.EVIDENCE_FILES:
        path = checkout / relative
        path.write_text(json.dumps(json.loads(path.read_text(encoding="utf-8-sig")), sort_keys=True, indent=4), encoding="utf-8-sig")
    assert freeze.check_evaluation_freeze(checkout, check_environment=False)["protocol_matches"]


def test_editing_a_human_reason_changes_evidence_even_when_verdicts_are_preserved(checkout):
    path = checkout / "results/examples/consistency-human-review.json"
    change_json(path, lambda data: data["reviews"][0]["decisions"]["correctness"].update(reason="A later explanation."))
    with pytest.raises(ValueError, match="consistency-human-review.json"):
        freeze.check_evaluation_freeze(checkout, check_environment=False)


def test_manifest_cannot_omit_a_required_file(checkout):
    path = checkout / "evaluation-freeze.json"
    change_json(path, lambda data: data["text_sha256"].pop("src/llm_eval/metrics.py"))
    with pytest.raises(ValueError, match="coverage changed"):
        freeze.check_evaluation_freeze(checkout, check_environment=False)


def test_recorded_model_digests_must_agree_with_original_runs(checkout):
    path = checkout / "evaluation-freeze.json"
    change_json(path, lambda data: data["recorded_ollama"]["model_digests"].update({"qwen3:4b": "different"}))
    with pytest.raises(ValueError, match="Model digest record differs"):
        freeze.check_evaluation_freeze(checkout, check_environment=False)


@pytest.mark.parametrize("installed", ["different-version", None])
def test_wrong_or_missing_installed_package_fails(checkout, monkeypatch, installed):
    original = freeze.version

    def version(name):
        if name == "deepeval":
            if installed is None:
                raise freeze.PackageNotFoundError(name)
            return installed
        return original(name)

    monkeypatch.setattr(freeze, "version", version)
    with pytest.raises(ValueError, match="Installed dependency differs: deepeval"):
        freeze.check_evaluation_freeze(checkout)


def test_dependency_snapshot_cannot_silently_add_a_different_pin(checkout):
    path = checkout / "requirements-lock.txt"
    path.write_text(path.read_text().replace("deepeval==4.3.3", "deepeval==0.0.0"))
    with pytest.raises(ValueError, match="Frozen package versions differ"):
        freeze.check_evaluation_freeze(checkout, check_environment=False)


def test_another_python_minor_version_fails(checkout, monkeypatch):
    monkeypatch.setattr(freeze, "sys", SimpleNamespace(version_info=SimpleNamespace(major=3, minor=13)))
    with pytest.raises(ValueError, match="Python 3.12 is required"):
        freeze.check_evaluation_freeze(checkout)


def test_cli_reports_drift_and_missing_inputs_with_nonzero_status(checkout, monkeypatch, capsys):
    path = freeze.ROOT / "scripts/check_evaluation_freeze.py"
    spec = importlib.util.spec_from_file_location("freeze_command", path)
    command = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(command)
    monkeypatch.setattr(command, "check_evaluation_freeze", lambda **kwargs: freeze.check_evaluation_freeze(checkout, **kwargs))
    assert command.main([]) == 0
    assert '"ollama_runtime_checked": false' in capsys.readouterr().out
    (checkout / "src/llm_eval/metrics.py").write_text("changed")
    assert command.main([]) == 2
    assert "metrics.py" in capsys.readouterr().out
    assert command.main(["--config", "missing.toml"]) == 2
    assert "Freeze check failed" in capsys.readouterr().out
