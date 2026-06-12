"""ZEUS-DB command-line interface."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from zeusdb.engine import AnalyzeOptions, ForensicEngine
from zeusdb.output.case_export import export_case
from zeusdb.output.json_export import export_json
from zeusdb.output.tsv_export import export_tsv


def build_parser() -> argparse.ArgumentParser:
    """Build CLI argument parser."""
    parser = argparse.ArgumentParser(
        prog="zeusdb",
        description="ZEUS-DB unified SQLite forensic analysis engine",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    analyze = sub.add_parser("analyze", help="Analyze a SQLite database")
    analyze.add_argument("database", help="Path to SQLite database file")
    analyze.add_argument("--wal", help="Explicit WAL file path")
    analyze.add_argument("--journal", help="Explicit rollback journal path")
    analyze.add_argument("--json", dest="json_out", help="Write JSON output to path")
    analyze.add_argument("--tsv", dest="tsv_out", help="Write TSV output to path")
    analyze.add_argument("--case", dest="case_out", help="Write CASE JSON to path")
    analyze.add_argument("--carve", action="store_true", help="Enable deleted record recovery")
    analyze.add_argument(
        "--no-freelist",
        action="store_true",
        help="Disable freelist page carving",
    )
    analyze.add_argument(
        "--no-boyer-moore",
        action="store_true",
        help="Disable Boyer-Moore page carving",
    )
    analyze.add_argument(
        "--salvage",
        action="store_true",
        help="Enable corrupt DB raw page salvage",
    )
    analyze.add_argument(
        "--tables",
        help="Comma-separated table names to analyze",
    )
    analyze.add_argument(
        "--relaxed",
        action="store_true",
        help="Disable strict sqlite format checking",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    """CLI entry point."""
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command != "analyze":
        parser.error(f"Unknown command: {args.command}")

    tables = args.tables.split(",") if args.tables else None
    options = AnalyzeOptions(
        carve=args.carve,
        carve_freelist=not args.no_freelist,
        boyer_moore=not args.no_boyer_moore,
        salvage=args.salvage,
        tables=tables,
        strict_format_checking=not args.relaxed,
        wal_path=args.wal,
        journal_path=args.journal,
    )

    engine = ForensicEngine()
    result = engine.analyze(Path(args.database), options)

    if args.json_out:
        export_json(result, args.json_out)
    if args.tsv_out:
        export_tsv(result, args.tsv_out)
    if args.case_out:
        export_case(result, args.case_out)

    summary = result.to_dict()["summary"]
    print(
        f"ZEUS-DB: {summary['total_records']} records "
        f"(live={summary['live_records']}, deleted={summary['deleted_records']})"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
