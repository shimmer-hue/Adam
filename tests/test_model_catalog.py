from __future__ import annotations

import json
from pathlib import Path

from eden.models.catalog import LocalMLXModelSpec, local_mlx_model_status


def _write_model_index(path: Path, filenames: list[str]) -> None:
    weight_map = {f"layer_{index}": name for index, name in enumerate(filenames)}
    path.write_text(json.dumps({"weight_map": weight_map}), encoding="utf-8")


def test_local_mlx_model_status_reports_partial_and_ready(tmp_path: Path) -> None:
    model_dir = tmp_path / "models" / "qwen"
    model_dir.mkdir(parents=True)
    (model_dir / "config.json").write_text("{}", encoding="utf-8")
    (model_dir / "tokenizer.json").write_text("{}", encoding="utf-8")
    shard_names = [f"model-{index:05d}-of-00004.safetensors" for index in range(1, 5)]
    _write_model_index(model_dir / "model.safetensors.index.json", shard_names)

    spec = LocalMLXModelSpec(
        label="Test Qwen",
        base_model="Qwen/Qwen3.5-35B-A3B",
        repo_id="example/test-qwen-mlx",
        local_dir=model_dir,
    )

    status = local_mlx_model_status(spec)
    assert status["ready"] is False
    assert status["stage"] == "metadata_only"
    assert status["weight_files_present"] == 0
    assert status["weight_files_expected"] == 4

    (model_dir / shard_names[0]).write_bytes(b"partial")
    status = local_mlx_model_status(spec)
    assert status["ready"] is False
    assert status["stage"] == "partial_weights"
    assert status["weight_files_present"] == 1
    assert status["weight_files_missing"] == 3

    for name in shard_names[1:]:
        (model_dir / name).write_bytes(b"ready")
    status = local_mlx_model_status(spec)
    assert status["ready"] is True
    assert status["stage"] == "ready"
    assert status["weight_files_present"] == 4
    assert status["weight_files_missing"] == 0
