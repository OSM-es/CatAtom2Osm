"""
CSV related help functions
"""
import csv
import io
import six
from catatom2osm.config import eol, encoding, delimiter


def dict2csv(csv_path, a_dict, sort=None):
    """
    Writes a dictionary to a csv file, optinally sorted by key (sort=0) or 
    value (sort=1)
    """
    with io.open(csv_path, 'w', encoding=encoding) as csv_file:
        dictitems = list(a_dict.items())
        if sort in [0, 1]:
            dictitems.sort(key=lambda x:x[sort])
        for (k, v) in dictitems:
            csv_file.write("%s%s%s%s" % (k, delimiter, v, '\n'))

def csv2dict(csv_path, a_dict, encoding=encoding):
    """Read a dictionary from a csv file"""
    with open(csv_path) as csv_file:
        csv_reader = csv.reader(csv_file, delimiter=str(delimiter))
        for row in csv_reader:
            if len(row) < 2:
                raise IOError(_("Failed to load CSV file '%s'") % csv_file.name)
            elif six.PY2:
                a_dict[row[0].decode(encoding)] = row[1].decode(encoding)
            else:
                a_dict[row[0]] = row[1]
    return a_dict
