from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

from .browser import open_browser_url
from .config import DB_PATH, DEFAULT_MLX_MODEL_DIR, RUNTIME_LOG_PATH, RuntimeSettings
from .logging import RuntimeLog
from .runtime import EdenRuntime
from .storage.graph_store import GraphStore
from .tui.app import run_tui


def build_runtime(args) -> EdenRuntime:
    store = GraphStore(DB_PATH)
    launch_profile = store.read_config("runtime_launch_profile") or {}
    appearance = store.read_config("tui_appearance") or {}
    backend = getattr(args, "backend", None) or launch_profile.get("backend") or "mlx"
    explicit_model_path = getattr(args, "model_path", None) or launch_profile.get("model_path")
    model_path = explicit_model_path or (str(DEFAULT_MLX_MODEL_DIR) if backend == "mlx" else None)
    settings = RuntimeSettings(
        model_backend=backend,
        model_path=model_path,
        ui_look=str(appearance.get("look") or "amber_dark"),
        observatory_host=getattr(args, "host", "127.0.0.1"),
        observatory_port=getattr(args, "port", 8741),
    )
    runtime_log = RuntimeLog(RUNTIME_LOG_PATH)
    return EdenRuntime(store=store, settings=settings, runtime_log=runtime_log)


def cmd_app(args) -> int:
    runtime = build_runtime(args)
    run_tui(runtime)
    return 0


def cmd_demo(args) -> int:
    runtime = build_runtime(args)
    experiment = runtime.initialize_experiment(args.mode)
    session = runtime.start_session(experiment["id"], title="Demo session")
    outcome = runtime.chat(session_id=session["id"], user_text=args.prompt)
    feedback = None
    if args.feedback:
        feedback = runtime.apply_feedback(
            session_id=session["id"],
            turn_id=outcome.turn["id"],
            verdict=args.feedback,
            explanation=args.feedback_explanation or f"demo {args.feedback}",
            corrected_text=args.corrected_text or "",
        )
    exports = runtime.export_observability(experiment_id=experiment["id"], session_id=session["id"])
    print(
        json.dumps(
            {
                "experiment_id": experiment["id"],
                "session_id": session["id"],
                "turn_id": outcome.turn["id"],
                "feedback": feedback,
                "exports": exports,
                "graph_counts": outcome.graph_counts,
            },
            indent=2,
        )
    )
    return 0


def cmd_ingest(args) -> int:
    runtime = build_runtime(args)
    result = runtime.ingest_document(experiment_id=args.experiment_id, path=args.path)
    print(json.dumps(result, indent=2))
    return 0


def cmd_export(args) -> int:
    runtime = build_runtime(args)
    result = runtime.export_observability(experiment_id=args.experiment_id, session_id=args.session_id)
    print(json.dumps(result, indent=2))
    return 0


def cmd_observatory(args) -> int:
    runtime = build_runtime(args)
    status = runtime.start_observatory(host=args.host, port=args.port, reuse_existing=args.reuse_existing)
    print(json.dumps(status, indent=2))
    if args.open:
        latest = runtime.store.get_latest_experiment()
        target_url = status["url"]
        if latest is not None:
            runtime.export_observability(experiment_id=latest["id"], session_id=None)
            target_url = f"{status['url']}{latest['id']}/observatory_index.html"
        launch = open_browser_url(target_url)
        if not launch.ok:
            print(
                json.dumps(
                    {
                        "warning": "browser_launch_failed",
                        "target_url": target_url,
                        "detail": launch.detail,
                    },
                    indent=2,
                ),
                file=sys.stderr,
            )
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        runtime.stop_observatory()
    return 0


def main(argv: list[str] | None = None) -> int:
    argv = list(argv) if argv is not None else sys.argv[1:]
    if not argv or argv[0].startswith("-"):
        argv = ["app", *argv]
    parser = argparse.ArgumentParser(prog="eden", description="EDEN local-first memetic runtime.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    app_parser = subparsers.add_parser("app", help="Launch the Textual TUI.")
    app_parser.add_argument("--backend", default=None, choices=["mock", "mlx"])
    app_parser.add_argument("--model-path", default=None, help=argparse.SUPPRESS)
    app_parser.set_defaults(func=cmd_app)

    demo_parser = subparsers.add_parser("demo", help="Run a one-turn demo and export observability artifacts.")
    demo_parser.add_argument("--backend", default=None, choices=["mock", "mlx"])
    demo_parser.add_argument("--model-path", default=None, help=argparse.SUPPRESS)
    demo_parser.add_argument("--mode", default="blank", choices=["blank", "seeded"])
    demo_parser.add_argument("--prompt", default="Explain how ADAM persists identity through the graph.")
    demo_parser.add_argument("--feedback", default="accept", choices=["accept", "edit", "reject", "skip"])
    demo_parser.add_argument("--feedback-explanation", default="demo feedback explanation")
    demo_parser.add_argument("--corrected-text", default="")
    demo_parser.set_defaults(func=cmd_demo)

    ingest_parser = subparsers.add_parser("ingest", help="Ingest a document into an existing experiment.")
    ingest_parser.add_argument("--backend", default=None, choices=["mock", "mlx"])
    ingest_parser.add_argument("--model-path", default=None, help=argparse.SUPPRESS)
    ingest_parser.add_argument("experiment_id")
    ingest_parser.add_argument("path")
    ingest_parser.set_defaults(func=cmd_ingest)

    export_parser = subparsers.add_parser("export", help="Export graph and basin artifacts for an experiment.")
    export_parser.add_argument("--backend", default=None, choices=["mock", "mlx"])
    export_parser.add_argument("--model-path", default=None, help=argparse.SUPPRESS)
    export_parser.add_argument("experiment_id")
    export_parser.add_argument("--session-id", default=None)
    export_parser.set_defaults(func=cmd_export)

    observatory_parser = subparsers.add_parser("observatory", help="Serve the exports directory over HTTP.")
    observatory_parser.add_argument("--backend", default=None, choices=["mock", "mlx"])
    observatory_parser.add_argument("--model-path", default=None, help=argparse.SUPPRESS)
    observatory_parser.add_argument("--host", default="127.0.0.1")
    observatory_parser.add_argument("--port", type=int, default=8741)
    observatory_parser.add_argument("--open", dest="open", action=argparse.BooleanOptionalAction, default=False)
    observatory_parser.add_argument("--reuse-existing", dest="reuse_existing", action=argparse.BooleanOptionalAction, default=True)
    observatory_parser.set_defaults(func=cmd_observatory)

    args = parser.parse_args(argv)
    return args.func(args)
