BUFFER_SIZE = 512
SIMPLIFY_BUILDING_PARTS = False

from catatom2osm.geo.aux import get_attributes
from catatom2osm.geo.debug import DebugWriter
from catatom2osm.geo.geometry import Geometry
from catatom2osm.geo.layer.address import AddressLayer
from catatom2osm.geo.layer.base import BaseLayer
from catatom2osm.geo.layer.cons import ConsLayer
from catatom2osm.geo.layer.highway import HighwayLayer
from catatom2osm.geo.layer.parcel import ParcelLayer
from catatom2osm.geo.layer.polygon import PolygonLayer
from catatom2osm.geo.layer.zoning import ZoningLayer
from catatom2osm.geo.point import Point
