"""
This module provides account calculation methods
"""

from datetime import date
from decimal import Decimal

from eris import db
from eris.logging import log


def num_months(start, end):
    """Calculate the number of months between two dates"""
    years = end.year - start.year
    return years * 12 + (end.month - start.month)


def calculate_member_account(member, last_calculation):
    """
    Calculate next member account value.
    """
    today = date.today()
    account = member["account"]

    # This is only relevant for the initial calculation
    last_update = last_calculation
    last_payment = member["last_payment"]
    if last_payment > last_calculation:
        last_update = last_payment

    # Calculate amount
    months = num_months(last_update, today)
    fee = months * member["fee"]
    next_amount = account - fee

    # Create transaction
    transaction = {
        "account_name": member["name"],
        "member_id": member["id"],
        "description": f"membership fee ({months} month)",
        "amount": -fee,
    }

    return next_amount, transaction


def run_account_calculations(members_db):
    """Calculate account for all members."""
    today = date.today()
    last_calculation = db.get_accounts_calculated_at(members_db)
    months = num_months(last_calculation, today)
    if months < 1:
        log("member account calculation is up to date")
        return
    log("calculating member accounts")

    members = db.get_members(members_db)
    for member in members:
        if member["membership_end"]:
            print("Skipping inactive member: {}".format(member["name"]))
            continue

        old_amount = member["account"]
        next_amount, transaction = calculate_member_account(member, last_calculation)
        log("{} - Old: {} New: {}", member["name"], old_amount, next_amount)

        # Update member account and log transaction
        transaction["date"] = today
        db.set_account(members_db, member["id"], next_amount)
        db.add_transaction(members_db, transaction)

    db.set_accounts_calculated_at(members_db, today)


def adjust_member_account(members_db, member_id, amount, comment):
    """Set member account value"""
    member = db.get_member(members_db, member_id)
    if not member:
        print("member not found")
        return

    current = member["account"]
    amount = Decimal(amount)
    diff = amount - member["account"]

    # Create transaction
    transaction = {
        "account_name": member["name"],
        "member_id": member["id"],
        "description": f"manual account adjustment, from {current} EUR: {comment}",
        "amount": diff,
        "date": date.today(),
    }

    print(transaction)

    if input("proceed? (y/n)") != "y":
        print("abort")
        return

    db.set_account(members_db, member["id"], amount)
    db.add_transaction(members_db, transaction)

    print("ok")


