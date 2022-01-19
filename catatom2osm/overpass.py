"""Minimum Overpass API interface"""
import re

from catatom2osm import download

api_servers = [
    "http://overpass-api.de/api/interpreter?",
    "http://overpass.osm.rambler.ru/cgi/interpreter?"
]


class Query(object):
    """Class for a query to Overpass"""

    def __init__(self, search_area, output='xml', down=True, meta=True):
        """
        Args:
            search_area (str): See set_search_area
            output (str): xml (default) / json
            down (bool): True (default) to include recurse down elements
            meta (bool): True (default) to include metadata
        """
        self.output = output
        self.down = '(._;>>;);' if down else ''
        self.meta = 'out meta;' if meta else 'out;'
        self.area_id = ''
        self.bbox = ''
        self.set_search_area(search_area)
        self.statements = []
        self.url = ''

    def set_search_area(self, search_area):
        """Set the area to search in. It could be either the osm id of a named
           area or a bounding box (bottom, left, top, right) clause."""
        if re.match(r'^\d{1,8}$', search_area):
            self.area_id = search_area
        elif re.match(r'^(-?\d{1,3}(\.\d+)?,\s*){3}-?\d{1,3}(\.\d+)?$', search_area):
            self.bbox = search_area
        else:
            msg = "Argument expected to be an area id or a bbox clause: %s"
            raise TypeError(msg % search_area)

    def add(self, *args):
        """Adds a statement to the query. Use QL query statements without bbox
           or area clauses. Example: node["name"="Berlin"]"""
        rsc = lambda s: s[:-1] if s[-1] == ';' else s
        for arg in args:
            if isinstance(arg, basestring):
                self.statements += rsc(arg).split(';')
            else:
                self.statements += [rsc(s) for s in arg]
        return self
    
    def get_url(self, n=0):
        """Returns url for the query"""
        if len(self.statements) > 0:
            search_area = ''
            query = ''
            if self.area_id:
                query = 'area(36{id:>08})->.searchArea;'.format(id=self.area_id)
                search_area = '(area.searchArea)'
            search_area += f'({self.bbox});' if self.bbox else ';'
            query += search_area.join(self.statements) + search_area
            self.url = '{u}data=[out:{o}][timeout:250];({q});{d}{m}'.format(
                u=api_servers[n], q=query, o=self.output, d=self.down, m=self.meta
            )
        return self.url

    def download(self, filename, log=False):
        """Downloads query result to filename"""
        for i in range(len(api_servers)):
            try:
                if log: log.debug(self.get_url(i))
                download.wget(self.get_url(i), filename)
                return
            except IOError as e:
                pass
        raise IOError("Can't read from any Overpass server'")
    
    def read(self):
        """Returns query result"""
        response = download.get_response(self.get_url())
        return response.text.encode(response.apparent_encoding)

