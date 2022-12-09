"""
ERIS Bank Import: Currently supported are CSV
exports of Deutsche Bank.
"""

import csv
import hashlib
from datetime import date
from decimal import Decimal

from eris import db

F_DATE = 0
F_ACCOUNT_NAME = 3
F_DESCRIPTION = 4
F_IBAN = 5
F_BIC = 6
F_AMOUNT = 16


def hash_iban(name, iban):
    """Hash the iban"""
    return hashlib.pbkdf2_hmac(
        'sha256', bytes(name, 'iso-8859-1'), bytes(iban, 'iso-8859-1'), 1000,
    ).hex()[:12]


class UnknownMemberError(ValueError):
    """Member could not be resolved"""


def decode_date(value):
    """Parse a date: format dd.mm.yyyy"""
    parts = value.split(".")
    if len(parts) != 3:
        raise ValueError("not a date:", value)
    return date(int(parts[2]), int(parts[1]), int(parts[0]))


def decode_amount(value):
    """Decode the amount"""
    value = value.replace(".", "").replace(",", ".")
    return Decimal(value)


def decode_transaction(row):
    """Decode a bank transaction row"""
    return {
        "date": decode_date(row[F_DATE]),
        "account_name": row[F_ACCOUNT_NAME],
        "description": row[F_DESCRIPTION],
        "iban": row[F_IBAN],
        "iban_hash": hash_iban(row[F_ACCOUNT_NAME], row[F_IBAN]),
        "bic": row[F_BIC],
        "amount": decode_amount(row[F_AMOUNT]),
    }


def read_transactions(filename, encoding=None):
    """Read bank .csv"""
    if not encoding:
        encoding="iso-8859-1" # default

    transactions = []
    with open(filename, encoding=encoding) as file:
        reader = csv.reader(file, delimiter=";")
        for row in reader:
            try:
                decode_date(row[0])
            except:
                continue
            if len(row) < F_AMOUNT:
                continue
            if not row[F_AMOUNT]:
                continue # We can skip outbound TX

            transactions.append(decode_transaction(row))

    return transactions


def validate_transaction(members_db, transaction):
    """Check if the transaction should be added"""
    member = db.get_member(members_db, transaction["member_id"])
    if transaction["date"] <= member["last_payment"]:
        return ("Date {} is before last payment: {} " +
            "for member: {} ({})").format(
                transaction["date"],
                member["last_payment"],
                member["name"],
                member["id"])

    return None


def add_payment(members_db, transaction):
    """Log transaction and add payment to account"""
    member = db.get_member(members_db, transaction["member_id"])

    db.add_payment(members_db, transaction)
    db.add_transaction(members_db, transaction)

    print("Added payment from {} ({}): {}, {} ({})".format(
        member["name"],
        transaction["account_name"],
        transaction["amount"],
        transaction["date"],
        transaction["description"]))


def import_handler_rule_member_id(members_db, transaction, rule, force=False):
    """Create a transaction. Use member ID from rule."""
    member = db.get_member(members_db, rule["member_id"])
    if not member:
        raise UnknownMemberError(transaction)

    transaction["member_id"] = member["id"]
    error = validate_transaction(members_db, transaction)
    if error and not force:
        print(error)
        return

    add_payment(members_db, transaction)


def import_handler_split_accounts(members_db, transaction, rule, force=False):
    """Split the transaction"""
    fallback_id = rule["member_id"]
    rest = transaction["amount"]
    total = Decimal(0)
    # Check rule
    for member_id, amount in rule["params"]:
        member = db.get_member(members_db, rule["member_id"])
        if not member:
            raise UnknownMemberError(transaction)

        print("Split assigning {} EUR of {} EUR to {} ({})".format(
            amount,
            transaction["amount"],
            member["name"],
            member["id"]))

        total += Decimal(amount)

    if total > transaction["amount"]:
        raise ValueError(
            "total of split amount {} EUR is > incoming amount {} EUR".format(
                total,
                transaction["amount"]))

    # Apply
    for member_id, amount in rule["params"]:
        transaction["member_id"] = member_id
        transaction["amount"] = Decimal(amount)

        # Check if we should add
        error = validate_transaction(members_db, transaction)
        if error and not force:
            print(error)
            return

        add_payment(members_db, transaction)
        rest -= Decimal(amount)

    if rest > 0:
        member = db.get_member(members_db, fallback_id)
        print("Adding split overflow of {} EUR to: {} ({})".format(
            rest,
            member["name"],
            member["id"]))

        transaction["amount"] = rest
        transaction["member_id"] = fallback_id

        add_payment(members_db, transaction)


def import_handler_account_name(members_db, transaction, _rule, force=False):
    """Create transaction. Member name should match the account name"""
    member = db.get_member_by_name(members_db, transaction["account_name"])
    if not member:
        raise UnknownMemberError(transaction)
    transaction["member_id"] = member["id"]

    error = validate_transaction(members_db, transaction)
    if error and not force:
        print(error)
        return

    add_payment(members_db, transaction)


IMPORT_HANDLERS = {
    "use_member_id": import_handler_rule_member_id,
    "split_accounts": import_handler_split_accounts,
}


def import_transaction(members_db, transaction, force=False):
    """Import a transaction"""
    handler = import_handler_account_name

    # Check if we have a override rule
    rule = db.get_bank_import_rule(members_db, transaction["iban_hash"])
    if rule:
        handler = IMPORT_HANDLERS[rule["handler"]]

    handler(members_db, transaction, rule, force=force)


def import_transactions(members_db, filename, encoding=None, force=False):
    """Import transactions from bank CSV"""
    transactions = read_transactions(filename, encoding=encoding)
    not_imported = []
    for transaction in transactions:
        try:
            import_transaction(members_db, transaction, force=force)
        except UnknownMemberError as e:
            not_imported.append(transaction)

    return not_imported
