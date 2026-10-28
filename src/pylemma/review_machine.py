"""Record or clear an operator-reviewed public trace link for a machine replay."""

import argparse
from pathlib import Path
from uuid import UUID

from pylemma.machine_store import MachineStore


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database", type=Path, required=True)
    parser.add_argument("--replay", type=UUID, required=True)
    parser.add_argument("--url")
    parser.add_argument(
        "--reviewed",
        action="store_true",
        help="Confirm review of every span and attribute before linking.",
    )
    args = parser.parse_args()
    if args.url and not args.reviewed:
        parser.error("Review the complete public trace and supply --reviewed.")
    if not args.database.is_file():
        parser.error("The database does not exist.")
    MachineStore(args.database).review(args.replay, args.url)


if __name__ == "__main__":
    main()
