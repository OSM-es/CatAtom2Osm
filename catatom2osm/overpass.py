"""Minimum Overpass API interface."""
import re

from catatom2osm import config, download
from catatom2osm.exceptions import CatIOError


class Query(object):
    """Class for a query to Overpass."""

    def __init__(self, search_area, output="xml", down=True, meta=True):
        """
        Construct a query.

        Args:
            search_area (str): See set_search_area
            output (str): xml (default) / json
            down (bool): True (default) to include recurse down elements
            meta (bool): True (default) to include metadata
        """
        self.output = output
        self.down = "(._;>>;);" if down else ""
        self.meta = "out meta;" if meta else "out;"
        self.area_id = ""
        self.bbox = ""
        self.set_search_area(search_area)
        self.statements = []
        self.url = ""

    def set_search_area(self, search_area):
        """
        Set the area to search in.

        It could be either the osm id of a named area or a bounding box
        (bottom, left, top, right) clause.
        """
        if re.match(r"^\d{1,8}$", search_area):
            self.area_id = search_area
        elif re.match(r"^(-?\d{1,3}(\.\d+)?,\s*){3}-?\d{1,3}(\.\d+)?$", search_area):
            self.bbox = search_area
        else:
            msg = "Argument expected to be an area id or a bbox clause: %s"
            raise TypeError(msg % search_area)

    def add(self, *args):
        """
        Add a statement to the query.

        Use QL query statements without bbox or area clauses.

        Example: node["name"="Berlin"]
        """

        def rsc(st):
            return st[:-1] if st[-1] == ";" else st

        for arg in args:
            if isinstance(arg, str):
                self.statements += rsc(arg).split(";")
            else:
                self.statements += [rsc(s) for s in arg]
        return self

    def get_url(self, server=config.osm3s_servers[0]):
        """Return the url for the query."""
        if len(self.statements) > 0:
            search_area = ""
            query = ""
            if self.area_id:
                query = "area(36{id:>08})->.searchArea;".format(id=self.area_id)
                search_area = "(area.searchArea)"
            search_area += f"({self.bbox});" if self.bbox else ";"
            query += search_area.join(self.statements) + search_area
            self.url = "{u}data=[out:{o}][timeout:250];({q});{d}{m}".format(
                u=server, q=query, o=self.output, d=self.down, m=self.meta
            )
        return self.url

    def download(self, filename, log=False):
        """Download query results to filename."""
        for server in config.osm3s_servers:
            try:
                url = self.get_url(server)
                if log:
                    log.debug(self.url)
                download.wget(url, filename)
                return
            except IOError:
                pass
        raise CatIOError("Can't read from any Overpass server'")

    def read(self):
        """Return query results."""
        response = download.get_response(self.get_url())
        return response.text.encode('utf-8')
