"""
ERIS Bank CSV Import
"""

from datetime import date
from decimal import Decimal

from eris import db
from eris.banking import import_transactions


def print_not_imported(transaction):
    """Show a not imported transaction"""
    print("{}: {} EUR".format(transaction["account_name"],
                              transaction["amount"]))
    print("\tIBAN: {iban}\t{iban_hash}".format(**transaction))
    print("\t{description}".format(**transaction))
    print("")


def import_bank_csv(members_db, args):
    """Import a deutsche bank CSV"""
    if not args.filename:
        print("please provide the CSV with transactions using --filename")
        return

    if args.force:
        if input("proceed? (y/n) ") != "y":
            print("abort")
            return

    not_imported = import_transactions(
        members_db,
        args.filename,
        encoding=args.encoding,
        force=args.force,
    )

    if not_imported:
        print("Could not import the following transactions.")
        print("Consider creating import rules for:")
        for transaction in not_imported:
            print_not_imported(transaction)


def print_rule(members_db, rule):
    """Print a bank import rule"""
    member = db.get_member(members_db, rule["member_id"])
    print("{:<30} ({})\t{}:\t{}".format(
        member["name"], member["id"], rule["iban_hash"], rule["handler"]))


def list_rules(members_db, _args):
    """List all bank import rules"""
    rules = db.get_bank_import_rules(members_db)
    for rule in rules:
        print_rule(members_db, rule)


def print_transaction(members_db, tx):
    """Print a tx"""
    member = db.get_member(members_db, tx["member_id"])
                                        
    print("{}\t{}\t{:<20}\t{:<40}\t{}\t{}".format(
        tx["id"], tx["date"],
        member["name"],
        tx["account_name"],
        tx["amount"],
        tx["description"]))


def list_transactions(members_db, args):
    """List transactions"""
    member = None
    if args.name:
        qry = '%' + args.name + '%'
        member = db.get_member_by_name(members_db, qry)
        if not member:
            print("member not found: {}".format(args.name))
            return
    else:
        if args.id:
            member = db.get_member(members_db, args.id)
            if not member:
                print("member not found: {}".format(args.name))
                return

    member_id = None
    if member:
        member_id = member["id"]
    
    transactions = db.get_transactions(members_db, member_id=member_id)
    for tx in transactions:
        print_transaction(members_db, tx)


def undo_transaction(members_db, args):
    """Subtract the amount from the member account and undo transaction"""
    if not args.id:
        print("--id <transaction_id> is required")
        return
    tx = db.get_transaction(members_db, args.id)
    if not tx:
        print("transaction not found")
        return

    member = db.get_member(members_db, tx["member_id"])
    next_amount = member["account"] - tx["amount"]
    print("Member: {} ({})".format(member["name"], member["id"]))
    print("Transaction: {}\t {} \t{} EUR, {}".format(
        tx["id"], tx["date"], tx["amount"], tx["description"]))
    print("Current member account: {} EUR, next: {} EUR".format(member["account"],
                                                        next_amount))
    print("")
    if input("proceed? (y/n) ") != "y":
        print("not undoing transaction")
        return

    # Set account and create undo transaction
    undo_tx = {
        "member_id": member["id"],
        "date": date.today(),
        "amount": -tx["amount"],
        "account_name": tx["account_name"],
        "description": "[UNDO] " + tx["description"],
    }

    db.set_account(members_db, member["id"], next_amount)
    db.add_transaction(members_db, undo_tx)

    print("ok")


def assign_member_iban(members_db, args):
    """Use this member ID for the matching IBAN hash"""
    if not args.iban_hash:
        print("--iban-hash required")
        return
    if not args.id:
        print("--id required")
        return
    rule = {
        "iban_hash": args.iban_hash,
        "member_id": args.id,
        "handler": "use_member_id",
    }
    rule = db.add_bank_import_rule(members_db, rule)
    print_rule(members_db, rule)


def assign_split_iban(members_db, args):
    """Split the amount to multiple members"""
    if not args.iban_hash:
        print("--iban-hash required")
        return
    if not args.split:
        print("--split user1_id=20.0 user2_id=8.5 ... is required")
        return

    assignments = [s.split("=") for s in args.split]

    rule_member_id = None
    total = Decimal(0)
    for member_id, amount in assignments:
        member = db.get_member(members_db, member_id)
        if not member:
            print("member not found with ID: {}".format(member_id))
            return

        print(" - assinging {} EUR to {} ({})".format(
            amount, member["name"], member["id"]))

        rule_member_id = member_id
        total += Decimal(amount)

    print("Total amount: {} EUR".format(total))

    rule = {
        "iban_hash": args.iban_hash,
        "member_id": rule_member_id,
        "handler": "split_accounts",
        "params": list(assignments),
    }
    rule = db.add_bank_import_rule(members_db, rule)
    print_rule(members_db, rule)
