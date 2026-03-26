from __future__ import annotations

import argparse
import json
from pathlib import Path

from eden.config import EXPORT_DIR, TANAKH_CACHE_DIR
from eden.tanakh import DEFAULT_TANAKH_REF, TanakhService


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate Tanakh render-validation artifacts.")
    parser.add_argument("--out-dir", default=str(EXPORT_DIR / "tanakh_validation"), help="Artifact output directory.")
    parser.add_argument("--ref", default=DEFAULT_TANAKH_REF, help="Reference to materialize into the Tanakh surface bundle.")
    args = parser.parse_args()
    out_dir = Path(args.out_dir).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    service = TanakhService(cache_root=TANAKH_CACHE_DIR)
    _, payload = service.export_surface_bundle(
        experiment_id="tanakh_validation",
        session_id=None,
        out_dir=out_dir,
        ref=args.ref,
        params=None,
    )
    print(json.dumps(
        {
            "surface": str(out_dir / "tanakh_surface.json"),
            "validation_json": str(out_dir / "tanakh_render_validation.json"),
            "validation_html": str(out_dir / "tanakh_render_validation.html"),
            "bundle_hash": payload["bundle_hash"],
            "ref": payload["current_ref"],
        },
        ensure_ascii=False,
        indent=2,
    ))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
