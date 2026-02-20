import argparse


def build_arg_parser(description: str) -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=description)
    parser.add_argument(
        "--dry-run",
        action="store_true",
        default=True,
        help="Run without making changes (default: enabled)",
    )
    parser.add_argument(
        "--apply-comments",
        action="store_true",
        default=False,
        help="Actually post comments to Jira issues",
    )
    parser.add_argument(
        "--apply-transitions",
        action="store_true",
        default=False,
        help="Actually transition Jira issues",
    )
    parser.add_argument(
        "--max-writes",
        type=int,
        default=None,
        metavar="N",
        help="Limit the number of write operations (comments + transitions)",
    )
    return parser


def resolve_dry_run(args: argparse.Namespace) -> bool:
    if args.apply_comments or args.apply_transitions:
        return False
    return True
