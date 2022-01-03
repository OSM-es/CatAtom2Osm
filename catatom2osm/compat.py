"""Accessory methods for compatibility between different systems"""
from builtins import str, bytes
import codecs
import gettext
import locale
import six
import sys

# See http://lxml.de/tutorial.html for the source of the includes
etreemsg = ""
try:
    from lxml import etree
    etreemsg = "Running with lxml.etree"
except ImportError: # pragma: no cover
    try:
        import xml.etree.ElementTree as etree
        etreemsg = "Running with ElementTree"
    except ImportError:
        try:
            import cElementTree as etree
            etreemsg = "Running with cElementTree"
        except ImportError:
            try:
                import elementtree.ElementTree as etree
                etreemsg = "Running with ElementTree"
            except ImportError:
                etreemsg = "Failed to import ElementTree from any known place"
                raise ImportError(etreemsg)

def set_es_time():
    try:
        language, encoding = locale.getdefaultlocale()
        encoding = encoding or 'UTF-8'
        locale.setlocale(locale.LC_TIME, ('es', encoding))
    except locale.Error:
        locale.setlocale(locale.LC_TIME, 'esp')

def get_stderr():
    """Return wrapped version of stderr encoded to terminal code page"""
    if six.PY2:
        return codecs.getwriter(sys.stdout.encoding or 'UTF-8')(sys.stderr)
    return sys.stderr


class Terminal(object):

    def __init__(self, encoding):
        self.encoding = encoding

    def encode(self, msg):
        """Encode strings to W$ terminal with Python2"""
        return str(msg) if sys.stdout.encoding == 'utf-8' else \
            bytes(msg, self.encoding).decode(sys.stdout.encoding or 'UTF-8')

    def decode(self, msg):
        """Decode strings from W$ terminal with Python2"""
        return str(msg) if sys.stdout.encoding == 'utf-8' else \
            bytes(msg, sys.stdout.encoding).decode(self.encoding or 'UTF-8')

