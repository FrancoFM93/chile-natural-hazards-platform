"""Run with python -m source_profiler; all analysis also works on local fixtures."""

import argparse
from datetime import datetime, timezone
from pathlib import Path
import sys

from .profiling import profile, render_report
from .query import Query, parse_datetime
from .sources import capture, decode_features, write_json


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--provider", choices=("both", "usgs", "emsc"), default="both")
    parser.add_argument("--start", required=True, help="ISO date/datetime; timezone omitted means UTC")
    parser.add_argument("--end", required=True, help="inclusive ISO boundary; date-only means UTC midnight")
    parser.add_argument("--bbox", nargs=4, type=float, required=True, metavar=("MIN_LON", "MIN_LAT", "MAX_LON", "MAX_LAT"))
    parser.add_argument("--min-magnitude", type=float, required=True)
    parser.add_argument("--usgs-fixture", type=Path)
    parser.add_argument("--emsc-fixture", type=Path)
    parser.add_argument("--output", type=Path, help="new directory; existing directories are never overwritten")
    args = parser.parse_args(argv)
    providers = ("usgs", "emsc") if args.provider == "both" else (args.provider,)
    fixtures = {"usgs": args.usgs_fixture, "emsc": args.emsc_fixture}
    if any(fixtures.values()):
        if any(fixtures[name] is None for name in providers):
            parser.error("offline mode requires a fixture for every selected provider")
        if any(path is not None and name not in providers for name, path in fixtures.items()):
            parser.error("a fixture was supplied for an unselected provider")
    try:
        min_lon, min_lat, max_lon, max_lat = args.bbox
        query = Query(
            parse_datetime(args.start, assume_utc=True), parse_datetime(args.end, assume_utc=True),
            min_lat, max_lat, min_lon, max_lon, args.min_magnitude,
        )
    except ValueError as exc:
        parser.error(str(exc))

    output = args.output or Path("artifacts") / datetime.now(timezone.utc).strftime("profile-%Y%m%dT%H%M%S%fZ")
    try:
        output.mkdir(parents=True, exist_ok=False)
        summaries = {}
        for provider in providers:
            body, metadata = capture(provider, query, output, fixtures[provider])
            try:
                if "error" in metadata:
                    raise ValueError(metadata["error"])
                features = decode_features(body, no_content=metadata.get("status_code") == 204)
                records, summary = profile(provider, features, query)
                write_json(output / f"{provider}.normalized.json", records)
            except ValueError as exc:
                summary = {"status": "failed", "error": str(exc)}
            summary["capture"] = metadata
            summaries[provider] = summary
        write_json(output / "profile.json", {"query": query.as_dict(), "providers": summaries})
        (output / "report.md").write_text(render_report(query, summaries), encoding="utf-8")
    except OSError as exc:
        print(f"Cannot write profiler output: {exc}", file=sys.stderr)
        return 1

    print(f"Report: {output / 'report.md'}")
    for provider, summary in summaries.items():
        if summary["status"] == "failed":
            print(f"{provider}: FAILED: {summary['error']}", file=sys.stderr)
        else:
            print(f"{provider}: {summary['event_count']} records, {summary['records_with_errors']} rows with errors")
    return int(any(summary["status"] == "failed" for summary in summaries.values()))


if __name__ == "__main__":
    sys.exit(main())
