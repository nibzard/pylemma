"""Record or remove an operator-reviewed public trace reference."""

import argparse
import sqlite3
from pathlib import Path
from uuid import UUID

from pylemma.records.sqlite import MatchStore


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database", type=Path, required=True)
    commands = parser.add_subparsers(dest="command", required=True)
    record = commands.add_parser("record-link")
    record.add_argument("match_id", type=UUID)
    record.add_argument("url")
    record.add_argument("--reviewed", action="store_true", required=True)
    remove = commands.add_parser("remove-link")
    remove.add_argument("match_id", type=UUID)
    args = parser.parse_args(argv)
    try:
        MatchStore(args.database).set_public_trace_url(
            args.match_id, args.url if args.command == "record-link" else None
        )
    except (ValueError, KeyError, sqlite3.Error):
        parser.error(
            "Cannot update the link. Check the database, match, and reviewed URL."
        )
    print("Stored trace reference updated.")


if __name__ == "__main__":
    main()
