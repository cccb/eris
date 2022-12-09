"""
CLI entry point
"""
from eris import db
from eris_cli.cli import parse_args, print_help

def __main__():
    """CLI main entry point"""
    members_db = db.connect("members.sqlite3")
    args = parse_args()
    command = args.command
    if not command:
        print_help()
        return

    command(members_db, args)
