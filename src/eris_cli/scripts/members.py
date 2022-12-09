"""
Eris CLI
"""

import json
from datetime import date

from eris import db
from eris.readers import read_members_csv

def list_members(members_db, args):
    """
    List all members
    """
    today = date.today()
    if args.name:
        members = db.get_members_by_name(members_db, args.name)
    else:
        members = db.get_members(members_db)
    print("{:>4}\t{:<24}\t{:<30}\t{:<24}\t{:>12}\t{}\t{}\t{}\t{}".format(
        "ID", "Name", "Email", "Notes", "Account", "Last Payment", "Interval", "Fee", "Inacive"))
    print("{:-<180}".format("-"))
    for member in members:
        member_until = member["membership_end"]
        inactive = False
        if member_until and member_until < today:
            inactive = True

        member["inactive"] = ""
        if inactive:
            member["inactive"] = "X"
        print("{id:>4}\t{name:<24}\t{email:<30}\t{notes:<24}\t{account:>12.2f}\t{last_payment}\t{interval:>12}\t{fee:>}\t{inactive:>}".format(**member))


def import_members(members_db, args):
    """
    Import members from JSON
    """
    if not args.filename:
        print("please provide the json dump using --filename")
        return

    members = []
    with open(args.filename) as file:
        members = json.load(file)

    for member in members:
        import_member(members_db, member)


def import_member(members_db, member):
    """Import a single member"""
    if db.get_member_by_name(members_db, member["name"]):
        print("Skipping {name} {email}, already present".format(**member))
        return

    if not member.get("email"):
        member["email"] = "vorstand@berlin.ccc.de"
        member["notes"] += "  E-Mail unbekannt"

    row = db.add_member(members_db, member)
    print("Imported {id}: {name} {email}".format(**row))


INTERVALS = {
    "d": 1, # 'dauerauftrag'
    "m": 1,
    "q": 4,
    "j": 12,
    "b": 1, # I have no idea.
}


def get_payment_interval(intervals, name):
    """Get payment interval from legacy members db"""
    # Get member
    member = None
    for m in intervals:
        if m["name"] == name:
            member = m

    if not member:
        return (1, False)

    return (INTERVALS[member["zahlungsart"]], True)


def import_payment_intervals(members_db, args):
    """
    Import payment intervals
    """
    # The byro members database was corrupt there, I guess.

    if not args.filename:
        print("please provide the json dump using --filename")
        return

    with open(args.filename) as file:
        intervals = read_members_csv(file)

    members = db.get_members(members_db)

    for m in members:
        (interval, found) = get_payment_interval(intervals, m["name"])
        if not found:
            continue
        
        # Update member
        db.set_interval(members_db, m["id"], interval)


def set_interval(members_db, args):
    """Set payment interval"""
    if not args.id:
        print("--id <member id> is required")
        return

    if not args.interval:
        print("--interval <months> is required")
        return

    member = db.get_member(members_db, args.id)
    if not member:
        print("member not found")
        return

    # Update member
    db.set_interval(members_db, member["id"], int(args.interval))


def set_member_fee(members_db, args):
    """Set membership fee"""
    if not args.id:
        print("--id <member id> is required")
        return

    if not args.amount:
        print("--amount 23.44 is required")
        return

    member = db.get_member(members_db, args.id)
    if not member:
        print("member not found")
        return

    db.set_fee(members_db, member["id"], args.amount)


def update_name(members_db, args):
    """Change a name"""
    if not args.id:
        print("--id <member id> is required")
        return

    if not args.name:
        print("--name <new name> is required")
        return

    db.set_name(members_db, args.id, args.name)
    

def end_membership(members_db, args):
    """End a membership"""
    if not args.id:
        print("--id <member id> is required")
        return

    if not args.date:
        print("--date <YYYY-MM-DD> required")
        return

    db.end_membership(members_db, args.id, end=args.date)
    

def add_member(members_db, args):
    """Add a member to the database"""
    if not args.name:
        print("--name is required")
        return

    if not args.email:
        print("--email is required")
        return
    
    if not args.date:
        print("--date membership start is required")
        return

    member = {
        "name": args.name,
        "email": args.email,
        "membership_start": args.date,
    }

    if args.amount:
        member["fee"] = args.amount

    if args.comment:
        member["notes"] = args.comment

    print(member)

    if input("proceed? (y/n) ") != "y":
        print("abort")
        return

    member = db.add_member(members_db, member)
    print(member)

    


