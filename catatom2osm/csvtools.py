"""CSV related help functions."""
import csv
import io
import os

from catatom2osm.config import delimiter, encoding
from catatom2osm.exceptions import CatIOError


def dict2csv(csv_path, a_dict, sort=None):
    """
    Write a dictionary to a csv file.

    Optinally sorted by key (sort=0) or value (sort=1)
    """
    with io.open(csv_path, "w", encoding=encoding) as csv_file:
        dictitems = list(a_dict.items())
        if sort in [0, 1]:
            dictitems.sort(key=lambda x: x[sort])
        for (k, v) in dictitems:
            row = delimiter.join(v) if isinstance(v, (list, tuple, set)) else v
            csv_file.write("%s%s%s%s" % (k, delimiter, row, "\n"))


def csv2dict(csv_path, a_dict=None, exists=False, single=True):
    """Read a dictionary from a csv file."""
    a_dict = {} if a_dict is None else a_dict
    msg = _("Failed to load CSV file '%s'") % os.path.basename(csv_path)
    if os.path.exists(csv_path):
        with open(csv_path) as csv_file:
            csv_reader = csv.reader(csv_file, delimiter=str(delimiter))
            for row in csv_reader:
                if len(row) < 2:
                    raise CatIOError(msg)
                a_dict[row[0]] = row[1] if single else row[1:]
    elif exists:
        raise CatIOError(msg)
    return a_dict


def filter(csv_path, *args, query=lambda row, args: True, stop=False):
    """
    Return csv rows filtered using query.

    Args:
        args: aditional arguments for query function
        query (func): function with args row and wargs that returns
                      a boolean deciding if each row will be included or not
        stop (bool): Stop at first match or get all
    """
    output = []
    with open(csv_path) as csv_file:
        csv_reader = csv.reader(csv_file, delimiter=str(delimiter))
        for row in csv_reader:
            if query(row, args):
                if stop:
                    return row
                output.append(row)
    return output


def search(csv_path, *args, query=lambda row, args: True):
    """
    Return first matched row in csv.

    Args:
        args: aditional arguments for query function
        query (func): function with args row and wargs that returns
                      a boolean deciding if each row will be included or not
    """
    return filter(csv_path, *args, query=query, stop=True)


def get_key(csv_path, key):
    """Get a row given first column value."""

    def query(row, args):
        return row[0] == args[0]

    return search(csv_path, key, query=query)


def startswith(csv_path, key):
    """Get rows which first column starts with key."""

    def query(row, args):
        return row[0].startswith(args[0])

    return filter(csv_path, key, query=query)
