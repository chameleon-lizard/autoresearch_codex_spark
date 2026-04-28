from __future__ import annotations

import json
import sys

from .runner import LoopRunner, build_arg_parser, parse_artifact_input


def main(argv=None):
    parser = build_arg_parser()
    args = parser.parse_args(argv)
    runner = LoopRunner()

    if args.command == "run":
        runner.run(max_iters=args.max_iters, limit=args.limit)
        return 0

    if args.command == "report":
        path = runner.report()
        print(path)
        return 0

    if args.command == "reset":
        runner.reset()
        print("Run state reset. Cache preserved at:", runner.paths.cache_dir)
        return 0

    if args.command == "score":
        artifact = parse_artifact_input(args.artifact)
        metrics = runner.score_artifact(artifact, limit=args.limit)
        print(json.dumps(metrics, indent=2, sort_keys=True))
        return 0

    return 1


if __name__ == "__main__":
    raise SystemExit(main())
