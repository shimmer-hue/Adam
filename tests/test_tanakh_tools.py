from __future__ import annotations

import json
from pathlib import Path


def test_tanakh_substrate_manifest_index_and_passage(runtime) -> None:
    manifest = runtime.tanakh_service.sync_substrate()
    index = runtime.tanakh_service.get_index()
    passage = runtime.tanakh_get_passage(ref="Ezek 1:1-3", mode="keep_cantillation")

    assert manifest["text_version"] == "UXLC 2.4"
    assert manifest["build"] == "27.5"
    assert manifest["archive_sha256"]
    assert manifest["fetch_timestamp"]
    assert index["book_lookup"]["Ezekiel"]["chapters"][0]["verse_count"] == 5
    assert passage["canonical_ref"] == "Ezek 1:1-3"
    assert passage["book_filename"] == "Ezekiel"
    assert passage["verse_count"] == 3
    assert passage["processed_text"] == passage["canonical_text"]
    assert passage["provenance"]["dataset"]["archive_sha256"] == manifest["archive_sha256"]


def test_tanakh_analyzer_and_scene_hashes_are_deterministic(runtime) -> None:
    passage = runtime.tanakh_get_passage(ref="Ezek 1:1-3", mode="keep_cantillation")
    gematria_one = runtime.tanakh_gematria(
        input_text=passage["canonical_text"],
        scheme="mispar_hechrechi",
        preprocess="strip_pointing",
    )
    gematria_two = runtime.tanakh_gematria(
        input_text=passage["canonical_text"],
        scheme="mispar_hechrechi",
        preprocess="strip_pointing",
    )
    scene_params = {
        "preprocess": "strip_pointing",
        "letter_angle": 0.19,
        "word_radius": 0.31,
        "verse_height": 1.2,
        "theme": "amber",
        "oscillation_amplitude": 0.24,
        "seed": 7,
    }
    scene_one = runtime.tanakh_compile_merkavah_scene(ref="Ezek 1:1-3", params=scene_params)
    scene_two = runtime.tanakh_compile_merkavah_scene(ref="Ezek 1:1-3", params=scene_params)

    assert gematria_one["total"] > 0
    assert gematria_one["output_hash"] == gematria_two["output_hash"]
    assert scene_one["scene_hash"] == scene_two["scene_hash"]
    assert scene_one["scene_id"] == scene_two["scene_id"]
    assert scene_one["nodes"] == scene_two["nodes"]
    assert scene_one["edges"] == scene_two["edges"]
    assert scene_one["link_map"] == scene_two["link_map"]


def test_tanakh_surface_export_writes_expected_artifacts(runtime, tmp_path: Path) -> None:
    out_dir = tmp_path / "tanakh_exports"
    paths, payload = runtime.tanakh_service.export_surface_bundle(
        experiment_id="exp-tanakh",
        session_id="sess-tanakh",
        out_dir=out_dir,
        ref="Ezek 1:1-5",
        params={
            "preprocess": "keep_cantillation",
            "gematria_scheme": "mispar_gadol",
            "notarikon_mode": "first_letter",
            "temurah_mapping": "atbash",
            "scene": {
                "theme": "sea",
                "seed": 13,
                "letter_angle": 0.18,
                "word_radius": 0.27,
                "verse_height": 0.95,
                "oscillation_amplitude": 0.15,
            },
        },
    )

    expected_keys = {
        "tanakh_surface_json",
        "tanakh_manifest",
        "tanakh_index",
        "tanakh_passage",
        "tanakh_scene",
        "tanakh_measurements",
        "tanakh_render_validation",
        "tanakh_render_validation_html",
    }
    assert expected_keys.issubset(paths)
    for key in expected_keys:
        assert Path(paths[key]).exists(), key

    surface_payload = json.loads(Path(paths["tanakh_surface_json"]).read_text(encoding="utf-8"))
    assert surface_payload["bundle_hash"] == payload["bundle_hash"]
    assert surface_payload["bundle"]["scene"]["scene_hash"] == payload["bundle"]["scene"]["scene_hash"]
    assert surface_payload["bundle"]["validation"]["comparison_status"] == "manual_review_required"
    assert surface_payload["bundle"]["analyses"]["gematria"]["scheme"] == "mispar_gadol"
