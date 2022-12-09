"""
Import data files, like a legacy members export
"""

from csv import reader as csv_reader
from csv import DictReader

def read_members_csv(file):
    """Read CSV members list"""
    reader = DictReader(file)# csv_reader(file, delimiter=",")
    return list(reader)


