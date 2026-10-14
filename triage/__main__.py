"""Command line entry point: ``python -m triage``."""

from __future__ import annotations

import argparse
import sys
from datetime import date
from pathlib import Path

from .ai import AIConfigError, provider_chain
from .config import DEFAULT_INPUT_PATH, DEFAULT_OUTPUT_DIR, ConfigError, load_dotenv
from .loader import LoaderError
from .pipeline import run, write_outputs


def parse_as_of(value: str | None) -> date | None:
    if value is None:
        return None
    if value.strip().lower() == "today":
        return date.today()
    try:
        return date.fromisoformat(value.strip())
    except ValueError as exc:
        raise argparse.ArgumentTypeError("--as-of must be YYYY-MM-DD or 'today'") from exc


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m triage",
        description="Validate, categorise, acknowledge and flag service requests from a CSV file.",
    )
    parser.add_argument("--input", "-i", default=str(DEFAULT_INPUT_PATH), help="CSV file to read (default: data/requests.csv)")
    parser.add_argument("--output", "-o", default=str(DEFAULT_OUTPUT_DIR), help="folder for the output files (default: output/)")
    parser.add_argument(
        "--as-of",
        type=parse_as_of,
        default=None,
        help="date for 'future date' and 'overdue' checks: YYYY-MM-DD or 'today' (default: latest submission date in the file)",
    )
    parser.add_argument("--ai", action="store_true", help="refine acknowledgements with the AI provider configured in .env (off by default)")
    parser.add_argument("--rules", default=None, help="alternative rules.json")
    parser.add_argument("--ack", default=None, help="alternative acknowledgements.json")
    parser.add_argument("--quiet", "-q", action="store_true", help="only print the output file paths")
    return parser


def print_report(result, paths, quiet: bool) -> None:
    if not quiet:
        s = result.summary
        print(f"Read {s['total']} requests from {result.input_name} (as of {result.as_of.isoformat()}, {result.as_of_source})")
        print(f"  valid: {s['valid']}   incomplete/invalid: {s['invalid']}")
        print(f"  needs human review: {s['needs_human_review']}   auto-acknowledged: {s['auto_acknowledged']}")
        print("  by category: " + ", ".join(f"{k} {v}" for k, v in s["by_category"].items()))
        if result.ai_enabled:
            print(f"  AI drafting: on ({result.ai_provider}) -> " + ", ".join(f"{k} {v}" for k, v in s["acknowledgement_sources"].items()))
        else:
            print("  AI drafting: off (templates only)")
        queue = [r for r in result.results if r.needs_human_review]
        if queue:
            print("  review queue:")
            for r in queue:
                codes = ", ".join(f.code for f in r.review_flags if f.severity != "info")
                print(f"    - {r.request.display_id:<10} {r.request.priority or '-':<7} {r.category.category:<24} {codes}")
        print("Outputs:")
    for label, path in paths.items():
        print(f"  {label:<17} {path}")


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    ai_settings = None
    if args.ai:
        load_dotenv()
        try:
            ai_settings = provider_chain()
        except AIConfigError as exc:
            print(f"AI configuration error: {exc}", file=sys.stderr)
            return 2
        if ai_settings is None:
            print("--ai requested but TRIAGE_AI_PROVIDER is not set; continuing with templates only.", file=sys.stderr)

    try:
        result = run(args.input, as_of=args.as_of, ai_settings=ai_settings, rules_path=args.rules, ack_path=args.ack)
        paths = write_outputs(result, Path(args.output))
    except (LoaderError, ConfigError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 2

    print_report(result, paths, args.quiet)
    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
