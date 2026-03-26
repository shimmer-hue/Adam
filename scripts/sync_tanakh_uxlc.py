from __future__ import annotations

import argparse
import json

from eden.config import TANAKH_CACHE_DIR
from eden.tanakh import TanakhService


def main() -> int:
    parser = argparse.ArgumentParser(description="Fetch, verify, and index the Tanach.us UXLC substrate.")
    parser.add_argument("--force", action="store_true", help="Redownload and rebuild the substrate cache.")
    args = parser.parse_args()
    service = TanakhService(cache_root=TANAKH_CACHE_DIR)
    manifest = service.sync_substrate(force_refresh=args.force)
    print(json.dumps(manifest, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
