"""
CLI Command Line Arguments
"""
from argparse import ArgumentParser

from eris_cli.scripts import (
    banking,
    members,
    accounting,
)

def register_command(argp, flag, cmd):
    """Add a command to the parser"""
    argp.add_argument(
        flag,
        dest="command",
        action="store_const",
        const=cmd,
        help=cmd.__doc__)


parser = ArgumentParser(
    description="eris membership tool")

# Options
parser.add_argument("--filename")
parser.add_argument("--iban-hash")
parser.add_argument("--id")
parser.add_argument("--name")
parser.add_argument("--email")
parser.add_argument("--amount")
parser.add_argument("--split", nargs="*")
parser.add_argument("--encoding")
parser.add_argument("--comment")
parser.add_argument("--interval")
parser.add_argument("--date")
parser.add_argument("--force", default=False, action="store_true")


# Commands
register_command(
    parser, "--list-members", members.list_members)
register_command(
    parser, "--import-members", members.import_members)
register_command(
    parser, "--calculate-accounts", accounting.calculate_member_accounts)
register_command(
    parser, "--import-bank-csv", banking.import_bank_csv)
register_command(
    parser, "--list-bank-rules", banking.list_rules)
register_command(
    parser, "--assign-member-iban", banking.assign_member_iban)
register_command(
    parser, "--assign-split-iban", banking.assign_split_iban)
register_command(
    parser, "--import-payment-intervals", members.import_payment_intervals)
register_command(
    parser, "--list-transactions", banking.list_transactions)
register_command(
    parser, "--undo-transaction", banking.undo_transaction)
register_command(
    parser, "--set-fee", members.set_member_fee)
register_command(
    parser, "--set-interval", members.set_interval)
register_command(
    parser, "--adjust-account", accounting.adjust_member_account)
register_command(
    parser, "--update-name", members.update_name)
register_command(
    parser, "--end-membership", members.end_membership)
register_command(
    parser, "--add-member", members.add_member)


def print_help():
    """Print help text"""
    parser.print_help()


def parse_args():
    """Parse commandline arguments"""
    return parser.parse_args()
