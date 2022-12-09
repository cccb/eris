"""
ERIS Accounting Scripts
"""
from eris import accounting

def calculate_member_accounts(members_db, _args):
    """Run member account calculations"""
    accounting.run_account_calculations(members_db)

def adjust_member_account(members_db, args):
    """Set member account value"""
    if not args.id:
        print("--id <member id> is required")
        return

    if not args.amount:
        print("--amount 23.44 is required")
        return

    comment = ""
    if args.comment:
        comment = args.comment

    accounting.adjust_member_account(
        members_db, args.id, args.amount, comment)
