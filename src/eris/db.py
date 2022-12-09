"""
Database
"""
from datetime import date
from decimal import Decimal
import json

import sqlite3

DEFAULT_FEE = 20.0
DEFAULT_INTERVAL = 1

def connect(filename):
    """Open Sqlite Database"""
    return sqlite3.connect(filename)


def dict_row(row, cur):
    """Create a dict from a fetched row with a cursor"""
    if not row:
        return None
    return dict(zip((f[0] for f in cur.description), row))


def decode_date(date_str):
    """Parse date format: YYYY-MM-DD"""
    year, month, day = date_str.split("-")
    return date(int(year), int(month), int(day))


def encode_date(date_repr):
    """Encode a date"""
    if isinstance(date_repr, date):
        return date_repr.strftime("%Y-%m-%d")

    return date_repr


def encode_decimal(value):
    """Encode a decimal value"""
    return str(value)


def encode_json(value):
    """Encode json value"""
    if not value:
        return value
    return json.dumps(value)


def decode_member(member):
    """Decode string values from member"""
    if not member:
        return None

    member["membership_start"] = decode_date(member["membership_start"])
    if member["membership_end"]:
        member["membership_end"] = decode_date(member["membership_end"])
    member["last_payment"] = decode_date(member["last_payment"])
    member["fee"] = Decimal(member["fee"])
    member["account"] = Decimal(member["account"])

    return member


def decode_transaction(transaction):
    """Decode transaction"""
    transaction["date"] = decode_date(transaction["date"])
    transaction["amount"] = Decimal(transaction["amount"])

    return transaction


def decode_bank_import_rule(rule):
    """Decode a bank import rule"""
    if not rule:
        return rule

    if rule.get("params"):
        rule["params"] = json.loads(rule["params"])

    return rule


def get_members(conn):
    """Get all members from the database"""
    qry = """
         SELECT * FROM members
          ORDER BY name ASC
    """
    cur = conn.cursor()
    cur.execute(qry)
    res = cur.fetchall()

    return [decode_member(dict_row(row, cur)) for row in res]


def get_member(conn, member_id):
    """Get a members by id from the database"""
    qry = """
        SELECT *
          FROM members
         WHERE id = ?
    """
    cur = conn.cursor()
    cur.execute(qry, [member_id])
    res = cur.fetchone()

    return decode_member(dict_row(res, cur))


def get_members_by_name(conn, name):
    """Get all members matching a name"""
    qry = """
        SELECT *
          FROM members
         WHERE name LIKE ?
    """
    params = (
        "%{}%".format(name),
    )
    cur = conn.cursor()
    cur.execute(qry, params)
    res = cur.fetchall()

    return [decode_member(dict_row(row, cur)) for row in res]


def get_member_by_name(conn, name):
    """Get a member from the database"""
    qry = """
        SELECT *
          FROM members
         WHERE name LIKE ?
    """
    cur = conn.cursor()
    cur.execute(qry, [name])
    res = cur.fetchone()

    return decode_member(dict_row(res, cur))


def add_member(conn, member):
    """Add a member"""
    fee = member.get("fee")
    if not fee:
        fee = DEFAULT_FEE
    interval = member.get("interval")
    if not interval:
        interval = DEFAULT_INTERVAL
    start = member.get("membership_start", date.today())
    end   = member.get("membership_end")
    account = member.get("account", -fee) # Initial fee
    notes = member.get("notes", "")

    qry = """
        INSERT INTO members (
          name,
          email,
          notes,
          interval,
          fee,
          account,
          membership_start,
          membership_end,
          last_payment
        ) VALUES ( ?, ?, ?, ?, ?, ?, ?, ?, ? )
        RETURNING id
    """
    params = (
        member["name"],
        member["email"],
        notes,
        interval,
        fee,
        account,
        encode_date(start),
        encode_date(end),
        encode_date(start),
    )

    cur = conn.cursor()
    cur.execute(qry, params)
    res = cur.fetchone()
    conn.commit()

    return get_member(conn, res[0])


def end_membership(conn, member_id, end=None):
    """Update the note of a member"""
    if not end:
        end = date.today()

    qry = """
        UPDATE members SET membership_end = ? WHERE id = ?
    """
    cur = conn.cursor()
    cur.execute(qry, (end, member_id))
    conn.commit()

    return get_member(conn, member_id)


def set_name(conn, member_id, name):
    """Update the note of a member"""
    qry = """
        UPDATE members SET name = ? WHERE id = ?
    """
    cur = conn.cursor()
    cur.execute(qry, (name, member_id))
    conn.commit()

    return get_member(conn, member_id)


def set_notes(conn, member_id, notes):
    """Update the note of a member"""
    qry = """
        UPDATE members SET notes = ? WHERE id = ?
    """
    cur = conn.cursor()
    cur.execute(qry, (notes, member_id))
    conn.commit()

    return get_member(conn, member_id)


def set_interval(conn, member_id, interval):
    """Update the payment interval of a member"""
    qry = """
        UPDATE members SET interval = ? WHERE id = ?
    """
    cur = conn.cursor()
    cur.execute(qry, (interval, member_id))
    conn.commit()

    return get_member(conn, member_id)


def set_fee(conn, member_id, fee):
    """Update the membership fee"""
    qry = """
        UPDATE members SET fee = ? WHERE id = ?
    """
    cur = conn.cursor()
    cur.execute(qry, (fee, member_id))
    conn.commit()

    return get_member(conn, member_id)


def add_payment(conn, transaction):
    """Add payment to member"""
    member = get_member(conn, transaction["member_id"])
    if transaction["date"] < member["last_payment"]:
        print("WARNING: last_payment for member is more recent.")
        payment_date = member["last_payment"]

    qry = """
        UPDATE members
           SET account = account + ?,
               last_payment = ?
         WHERE id = ?
    """
    params = (
        encode_decimal(transaction["amount"]),
        encode_date(transaction["date"]),
        transaction["member_id"],
    )
    cur = conn.cursor()
    cur.execute(qry, params)
    conn.commit()

    return get_member(conn, transaction["member_id"])


def set_account(conn, member_id, value):
    """Set account value for member"""
    qry = """
        UPDATE members SET account = ? WHERE id = ?
    """
    params = (
        encode_decimal(value),
        member_id,
    )
    cur = conn.cursor()
    cur.execute(qry, params)
    conn.commit()

    return get_member(conn, member_id)


def get_transactions(conn, member_id=None, since=None):
    """Get transactions"""
    filters = " 1 "
    params = []
    if member_id:
        filters += "AND member_id = ? "
        params.append(member_id)
    if since:
        filters += "AND date(date) >= date(?) "
        params.append(since)

    qry = """
        SELECT * FROM transactions WHERE
    """ + filters

    cur = conn.cursor()
    cur.execute(qry, params)
    res = cur.fetchall()

    return [decode_transaction(dict_row(row, cur)) for row in res]


def get_transaction(conn, tx_id):
    """Get a transaction by id"""
    qry = """
        SELECT * FROM transactions WHERE id = ?
    """
    cur = conn.cursor()
    cur.execute(qry, (tx_id,))
    res = cur.fetchone()

    return decode_transaction(dict_row(res, cur))


def add_transaction(conn, transaction):
    """Add a transaction"""
    today = date.today()
    tx_date = transaction.get("date", today)

    qry = """
        INSERT INTO transactions (
          member_id,
          date,
          account_name,
          amount,
          description
        ) VALUES ( ?, ?, ?, ?, ? )
        RETURNING id
    """
    params = (
        transaction["member_id"],
        encode_date(tx_date),
        transaction.get("account_name", ""),
        encode_decimal(transaction.get("amount", "0.00")),
        transaction.get("description", ""),
    )
    cur = conn.cursor()
    cur.execute(qry, params)
    res = cur.fetchone()
    conn.commit()

    return get_transaction(conn, res[0])


def get_accounts_calculated_at(conn):
    """Get the date of the last account calculation"""
    qry  = """
        SELECT accounts_calculated_at
          FROM state
    """
    cur = conn.cursor()
    cur.execute(qry)
    res = cur.fetchone()

    return decode_date(res[0])


def set_accounts_calculated_at(conn, calculated_at):
    """Set the date of the account calculation"""
    qry = """
        UPDATE state
           SET accounts_calculated_at = ?
    """
    params = (
        encode_date(calculated_at),
    )
    cur = conn.cursor()
    cur.execute(qry, params)
    conn.commit()

    return get_accounts_calculated_at(conn)


def get_bank_import_rules(conn):
    """Get all bank import rules"""
    qry = """SELECT * FROM bank_import_rules"""
    cur = conn.cursor()
    cur.execute(qry)
    res = cur.fetchall()

    return [dict_row(r, cur) for r in res]


def get_bank_import_rule(conn, iban_hash):
    """Get a bank import rule for an iban hash"""
    qry = """
        SELECT * FROM bank_import_rules
         WHERE iban_hash = ?
    """
    params = (
        iban_hash,
    )
    cur = conn.cursor()
    cur.execute(qry, params)
    res = cur.fetchone()

    return decode_bank_import_rule(dict_row(res, cur))


def add_bank_import_rule(conn, rule):
    """Insert a bank import rule"""
    qry = """
        INSERT INTO bank_import_rules (
            iban_hash,
            member_id,
            handler,
            params
        ) VALUES ( ?, ?, ?, ? )
    """
    params = (
        rule["iban_hash"],
        rule["member_id"],
        rule["handler"],
        encode_json(rule.get("params")),
    )

    cur = conn.cursor()
    cur.execute(qry, params)
    conn.commit()

    return get_bank_import_rule(conn, rule["iban_hash"])
