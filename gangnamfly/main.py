import argparse
import json
import resource
import sys
import time
from pathlib import Path

from .config import EPISODES


def main():
    parser = argparse.ArgumentParser(description="GangnamFly local connectome/body experiment")
    parser.add_argument("--seed", type=int, default=64)
    parser.add_argument(
        "--episodes-dir",
        type=Path,
        default=EPISODES,
        help="Recording/checkpoint directory; choose a new directory for an incompatible protocol",
    )
    parser.add_argument(
        "--record-spikes", action="store_true", help="Optionally log all 166700 spike counts per brain step"
    )
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--seconds", type=float, default=4.0)
    parser.add_argument("--headless", action="store_true", help="Run one measured episode without web server")
    parser.add_argument("--train", action="store_true", help="Enable plasticity in headless episode")
    parser.add_argument(
        "--compare", action="store_true", help="Baseline, plastic training, frozen evaluation with same seed"
    )
    parser.add_argument("--idle", action="store_true", help="Wait for browser command before first episode")
    args = parser.parse_args()
    if args.seed < 0:
        parser.error("seed must be nonnegative")
    if not 0 < args.seconds <= 120 or not 1024 <= args.port <= 65535:
        parser.error("seconds must be >0 and <=120; port must be 1024..65535")
    if args.headless or args.compare:
        from .experiment import Experiment

        e = Experiment(root=args.episodes_dir, record_spikes=args.record_spikes)
        if args.train or args.compare:
            from .captured_target import load_target
            from .microcurriculum import MicroObjective

            e.objective = MicroObjective(load_target(e.environment), e.environment, 0)
        results = []
        try:
            for mode in (
                ["observe", "train", "observe"] if args.compare else ["train" if args.train else "observe"]
            ):
                e.begin(mode, duration=args.seconds, seed=args.seed)
                start = time.perf_counter()
                while not e.step():
                    pass
                results.append(
                    {
                        **e.finish(),
                        "wall_seconds": time.perf_counter() - start,
                        "realtime_factor": e.snapshot()["realtime_factor"],
                    }
                )
                print(json.dumps(results[-1]), flush=True)
        finally:
            e.finish("interrupted")
        report = {
            "episodes": results,
            "peak_rss_bytes": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
            * (1 if sys.platform == "darwin" else 1024),
            "interpretation": "Changed weights do not establish learned dancing. Compare frozen evaluations; single-seed pilot only.",
        }
        if args.compare:
            report["frozen_score_delta"] = results[-1]["score"] - results[0]["score"]
        (args.episodes_dir / "latest-report.json").write_text(json.dumps(report, indent=2) + "\n")
        print(json.dumps(report, indent=2))
        return
    from .runtime import Runtime
    from .server import LocalServer, handler

    runtime = Runtime(
        root=args.episodes_dir,
        duration=args.seconds,
        auto=not args.idle,
        seed=args.seed,
        record_spikes=args.record_spikes,
    )
    try:
        with LocalServer(("127.0.0.1", args.port), handler(runtime, args.port)) as server:
            print(f"GangnamFly: http://127.0.0.1:{args.port} (Ctrl+C stops and saves)", flush=True)
            server.serve_forever(poll_interval=0.2)
    except KeyboardInterrupt:
        pass
    finally:
        runtime.close()


if __name__ == "__main__":
    main()
