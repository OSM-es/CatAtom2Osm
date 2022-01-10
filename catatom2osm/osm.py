"""OpenStreetMap data model"""
from collections import defaultdict, Counter

# Number of significant decimal digits. 0 to cancel rounding. With a value 
# greater than 7, JOSM give duplicated points errors
COOR_DIGITS = 0


class Osm(object):
    """Class to implement a OSM data set."""

    def __init__(self, upload='never', generator=None):
        self.upload = upload
        self.version = '0.6'
        self.generator = generator
        self.counter = 0
        self.parents = defaultdict(set)
        self.elements = set()
        self.index = {} # elements by id
        self.tags = {}
        self.note = None
        self.meta = None
        self._attr_list = ('upload', 'version', 'generator')

    @property
    def nodes(self):
        """Returns list of nodes in elements"""
        return [e for e in self.elements if isinstance(e, Node)]

    @property
    def ways(self):
        """Returns list of ways in elements"""
        return [e for e in self.elements if isinstance(e, Way)]

    @property
    def relations(self):
        """Returns list of relations in elements"""
        return [e for e in self.elements if isinstance(e, Relation)]

    @property
    def attrs(self):
        """Returns dictionary of properties in self._attr_list"""
        attrs = {
            k: getattr(self, k, None) for k in self._attr_list
            if getattr(self, k, None) is not None
        }
        if self.upload in ['yes', 'upload']:
            attrs.pop('upload')
        return attrs

    def get(self, eid, etype='n'):
        """Returns element by its id"""
        eid = str(eid)
        if eid[0] not in 'nwr':
            eid = etype[0].lower() + eid
        return self.index[eid]

    def remove(self, el):
        """Remove el from element, from its parents and its orphand childs"""
        self.elements.discard(el)
        if el.fid in self.index:
            del self.index[el.fid]
        for parent in frozenset(self.parents[el]):
            parent.remove(el)
        for child in el.childs:
            if isinstance(child, Element):
                if self.parents[child] == set([el]):
                    self.remove(child)
                else:
                    try:
                        self.parents[child].remove(el)
                    except KeyError:
                        pass

    def replace(self, n1, n2):
        """Replaces n1 witn n2 in elements."""
        n1.container = None
        self.elements.discard(n1)
        del self.index[n1.fid]
        n2.container = self
        self.elements.add(n2)
        self.index[n2.fid] = n2
        self.parents[n2] = self.parents[n1]
        del self.parents[n1]

    def merge_duplicated(self):
        """Merge elements with the same geometry."""
        geomdupes = defaultdict(list)
        for el in self.elements:
            geomdupes[el.geometry()].append(el)
        for geom, dupes in list(geomdupes.items()):
            if len(dupes) > 1:
                i = 0   # first element in dupes with different tags or id
                while i < len(dupes) - 1 and dupes[i] == geom:
                    i += 1  # see __eq__ method of Element
                for el in dupes:
                    if el is not dupes[i] and el == dupes[i]: 
                        for parent in frozenset(self.parents[el]):
                            parent.container = self
                            parent.replace(el, dupes[i])
                        self.replace(el, dupes[i])
        for way in self.ways:
            way.clean_duplicated_nodes()

    def append(self, data, query=None):
        """
        Append data elements to this dataset avoiding duplicates.
        Optionally filter by query.

        Args:
            data (iterable, Osm or Element ): source data
            query (func): function to apply to each element and returns a
                boolean deciding if it will be included or not

        Example:
            >>> d1 = osm.Osm()
            >>> n1 = d1.Node(1, 1, tags={'tourism': 'viewpoint'})
            >>> n2 = d1.Node(2, 2, tags={'amenity': 'cafe'})
            >>> d2 = osm.Osm()
            >>> d2.append(d1)  # all
            >>> d3 = osm.Osm()
            >>> d3.append(d1, lambda e: 'amenity' in e.tags)  # only amenities
        """
        if isinstance(data, Element):
            if not query or query(data):
                data.copyto(self)
        else:
            if isinstance(data, Osm):
                data = data.elements
            for el in data:
                self.append(el, query)

    def __getattr__(self, name):
        """
        Helper to create elements.
        Example:
        >>> d = osm.Osm()
        >>> n = d.Node(1,1) # instead of
        >>> n = osm.Node(d, 1, 1)
        """
        if name in ['Node', 'Way', 'Relation', 'Polygon', 'MultiPolygon']:
            cls = globals()[name]
            return lambda *args, **kwargs: cls(self, *args, **kwargs)
        raise AttributeError


class Element(object):
    """Base class for Osm elements"""

    def __init__(self, container, tags={}, attrs={}):
        """Each element must belong to a container OSM dataset"""
        self.container = container
        self.action = 'modify'
        self.visible = 'true'
        self.tags = dict((k,v) for (k,v) in list(tags.items()))
        self.version = None
        self.timestamp = None
        self.changeset = None
        self.uid = None
        self.user = None
        self._attr_list = (
            'id', 'action', 'visible', 'version', 
            'timestamp', 'changeset', 'uid', 'user'
        )
        self.attrs = attrs
        if not hasattr(self, 'id'):
            container.counter -= 1
            self.id = container.counter
        container.elements.add(self)
        container.index[self.fid] = self

    def __eq__(self, other):
        """Used to determine if two elements could be merged."""
        if isinstance(other, self.__class__):
            a = dict(self.__dict__)
            b = dict(other.__dict__)
            a.pop('container', None)
            b.pop('container', None)
            if other.is_new() or self.is_new(): a['id'] = 0
            if other.is_new() or self.is_new(): b['id'] = 0
            if b['tags'] == {}: a['tags'] = {}
            if a['tags'] == {}: b['tags'] = {}
            return a == b
        elif self.is_new() and self.tags == {}:
            return self.geometry() == other
        return False

    def __ne__(self, other):
        return not self.__eq__(other)

    def __hash__(self):
        return id(self)

    def is_new(self):
        """Returns true if this element is new to OSM"""
        return self.id <= 0

    @property
    def type(self):
        """Returns class name as string"""
        return self.__class__.__name__.lower()

    @property
    def fid(self):
        """Returns id as unique string"""
        return self.type[0] + str(self.id)

    @property
    def attrs(self):
        """Returns the element attributes as a dictionary"""
        attrs = {
            k: getattr(self, k, None) for k in self._attr_list
            if getattr(self, k, None) is not None
        }
        if 'id' in attrs:
            attrs['id'] = str(attrs['id'])
        return attrs

    @attrs.setter
    def attrs(self, attrs):
        """Sets the element attributes from a dictionary"""
        for (k, v) in attrs.items():
            if k == 'id':
                v = int(v)
            if k in self._attr_list:
               setattr(self, k, v)


class Node(Element):
    """A node is a pair of coordinates"""

    def __init__(self, container, x, y=0, *args, **kwargs):
        """Use any of this:
        >>> d = osm.Osm()
        >>> n1 = d.Node(1,1)
        >>> p = (1,1)
        >>> n2 = d.Node(p)
        """
        super(Node, self).__init__(container, *args, **kwargs)
        (self.x, self.y) = (x[0], x[1]) \
            if hasattr(x, '__getitem__') else (x, y)
        if COOR_DIGITS:
            self.x = round(self.x, COOR_DIGITS)
            self.y = round(self.y, COOR_DIGITS)
        self._attr_list = self._attr_list + ('lon', 'lat')

    def __getitem__(self, key):
        """n[0], n[1] is equivalent to n.x, n.y"""
        if key not in (0,1):
            raise IndexError
        return self.x if key == 0 else self.y

    def geometry(self):
        """Returns pair of coordinates"""
        return (self.x, self.y)

    @property
    def childs(self):
        """Only for simetry with ways and relations"""
        return set()

    @property
    def lon(self):
        """Returns longitude as string"""
        return str(self.x)
    
    @lon.setter
    def lon(self, value):
        """Sets longitude from string"""
        self.x = float(value)

    @property
    def lat(self):
        """Returns latitude as string"""
        return str(self.y)
    
    @lat.setter
    def lat(self, value):
        """Sets latitude from string"""
        self.y = float(value)

    def copyto(self, container):
        """Copy self in another container"""
        if self.fid not in container.index.keys():
            container.Node(self.geometry(), tags=self.tags, attrs=self.attrs)

    def __str__(self):
        return str((self.x, self.y))


class Way(Element):
    """A way is a list of nodes"""

    def __init__(self, container, nodes=[], *args, **kwargs):
        """Use any of this:
        >>> d = osm.Osm()
        >>> n1 = d.Node(1,1)
        >>> n2 = d.Node(2,2)
        >>> w = d.Way([n1, n2])
        >>> w = d.Way([(1,1), (2,2)])
        """
        super(Way, self).__init__(container, *args, **kwargs)
        self.nodes = []
        for n in nodes:
            self.append(n)

    @property
    def childs(self):
        """Returns set of unique nodes"""
        return set(self.nodes)

    def is_closed(self):
        """Returns true if the way is closed"""
        return (len(self.nodes) > 2) and self.nodes[0] == self.nodes[-1]

    def is_open(self):
        """Returns true if the way is not closed"""
        return (len(self.nodes) > 1) and self.nodes[0] != self.nodes[-1]

    def shoelace(self):
        """Returns the area for a closed way or 0, + for CCW nodes, - for CW"""
        s = 0
        if self.is_closed():
            for i in range(len(self.nodes) - 1):
                n1 = self.nodes[i]
                n2 = self.nodes[i+1]
                s += (n1.x * n2.y - n2.x * n1.y)
        return s

    def append(self, n):
        """Append n to nodes"""
        if not isinstance(n, Node):
            n = Node(self.container, n)
        self.nodes.append(n)
        self.container.parents[n].add(self)

    def remove(self, n):
        """Remove n from nodes"""
        self.nodes = [o for o in self.nodes if o is not n]
        self.container.parents[n].remove(self)

    def replace(self, n1, n2):
        """Replaces first occurence of node n1 with n2"""
        self.nodes = [n2 if n is n1 else n for n in self.nodes]
        self.container.parents[n1].remove(self)
        self.container.parents[n2].add(self)

    def __eq__(self, other):
        """Used to determine if two elements could be merged."""
        if self.is_open():
            return super(Way, self).__eq__(other)
        elif isinstance(other, self.__class__):
            a = dict(self.__dict__)
            b = dict(other.__dict__)
            a.pop('container', None)
            b.pop('container', None)
            if other.is_new() or self.is_new(): a['id'] = 0
            if other.is_new() or self.is_new(): b['id'] = 0
            if b['tags'] == {}: a['tags'] = {}
            if a['tags'] == {}: b['tags'] = {}
            a['nodes'] = self.geometry()
            b['nodes'] = other.geometry()
            return a == b
        elif self.is_new() and self.tags == {}:
            if hasattr(other, 'index'):
                i = other.index(min(other))
                return self.geometry() == other[i:] + other[1:i+1]
        return False

    def __ne__(self, other):
        return not self.__eq__(other)

    def __hash__(self):
        return id(self)

    def geometry(self):
        """Returns tuple of coordinates"""
        g = tuple(n.geometry() for n in self.nodes)
        if self.is_closed():
            i = g.index(min(g))
            g = g[i:] + g[1:i+1]
            if self.shoelace() < 0:
                g = g[::-1]
        return g
    
    def clean_duplicated_nodes(self):
        """Removes consecutive duplicate nodes"""
        if self.nodes:
            merged = [self.nodes[0]]
            for i, n in enumerate(self.nodes[1:]):
                if n != self.nodes[i]:
                    merged.append(n)
            self.nodes = merged
    
    def search_node(self, x, y):
        """Returns osm node of way in the given position or None"""
        result = None
        for n in self.nodes:
            if n.x == x and n.y == y:
                result = n
                break
        return result

    def copyto(self, container):
        """Copy self in another container"""
        if self.fid not in container.index.keys():
            for n in self.nodes:
                n.copyto(container)
            container.Way(nodes=self.nodes, tags=self.tags, attrs=self.attrs)


class Relation(Element):
    """A relation is a collection of nodes, ways or relations with a role."""

    def __init__(self, container, members=[], *args, **kwargs):
        super(Relation, self).__init__(container, *args, **kwargs)
        self.members = []
        for m in members:
            self.append(m)

    @property
    def childs(self):
        """Returns set of unique members elements"""
        return set([m.element for m in self.members])

    def append(self, m, role=None):
        """Adds a member"""
        if not isinstance(m, Relation.Member):
            m = Relation.Member(m, role)
        self.members.append(m) 
        self.container.parents[m.element].add(self)

    def remove(self, e):
        """Remove e from members"""
        self.members = [m for m in self.members if m.element is not e]
        self.container.parents[e].remove(self)

    def replace(self, e1, e2):
        """Replaces first occurence of element e1 with e2"""
        self.members = [Relation.Member(e2, m.role) 
            if m.element == e1 else m for m in self.members]
        self.container.parents[e1].remove(self)
        self.container.parents[e2].add(self)

    def is_valid_multipolygon(self):
        """Returns true if this is valid as a multipolygon relation"""
        ends = []
        for m in self.members:
            if m.role not in ('outer', 'inner') or m.type != 'way':
                return False
            w = m.element
            if len(w.nodes) < 2:
                return False
            ends.append(w.nodes[0].geometry())
            ends.append(w.nodes[-1].geometry())
        is_conected = all([c == 2 for c in list(Counter(ends).values())])
        return is_conected

    def geometry(self):
        """Returns tuple of coordinates"""
        return tuple(m.element.geometry() for m in self.members)

    def outer_geometry(self):
        """If this is a valid multipolygon returns the outer rings
        with every open way conected as areas"""
        if not self.is_valid_multipolygon():
            return []
        outer = [m.element.geometry() for m in self.members if m.role == 'outer']
        i = 0
        while i < len(outer):
            w1 = outer[i]
            if len(w1) > 1 and w1[0] != w1[-1]:
                match = True
                while match:
                    match = False
                    for w2 in frozenset(outer[i+1:]):
                        w1 = outer[i]
                        if len(w2) > 1 and w2[0] != w2[-1]:
                            if w2[0] == w1[-1]:
                                outer[i] = w1 + w2[1:]
                                outer.remove(w2)
                                match = True
                            elif w2[-1] == w1[-1]:
                                outer[i] = w1 + w2[-2::-1]
                                outer.remove(w2)
                                match = True
            i += 1
        return outer

    def copyto(self, container):
        """Copy self in another container"""
        if self.fid not in container.index.keys():
            for m in self.members:
                m.element.copyto(container)
            tags = self.tags
            attrs = self.attrs
            container.Relation(members=self.members, tags=tags, attrs=attrs)

    class Member(object):
        """An element is member of a relation with a role."""
    
        def __init__(self, element, role=None):
            self.element = element
            self.role = role
        
        def __eq__(self, other):
            """Used to determine if two elements could be merged."""
            if isinstance(other, self.__class__):
                return self.__dict__ == other.__dict__
            else:
                return False

        def __ne__(self, other):
            return not self.__eq__(other)

        @property
        def type(self):
            if isinstance(self.element, Node):
                return 'node'
            elif isinstance(self.element, Way):
                return 'way'
            return 'relation'
        
        @property
        def ref(self):
            return self.element.id if hasattr(self.element, 'id') else None

        @property
        def attrs(self):
            attrs = dict(type=self.type, ref=str(self.ref))
            if self.role is not None:
                attrs['role'] = self.role
            return attrs


class Polygon(Relation):
    """Helper to create a multipolygon type relation with one outer ring and
       many inner rings."""
    
    def __init__(self, container, rings=[], *args, **kwargs):
        super(Polygon, self).__init__(container, *args, **kwargs)
        self.tags['type'] = 'multipolygon'
        role = 'outer'
        for ring in rings:
            if isinstance(ring, Way):
                self.append(ring, role)
            else:
                self.append(Way(container, ring), role)
            role = 'inner'


class MultiPolygon(Polygon):
    """Helper to create a multipolygon type relation with many outer ring and
       many inner rings."""

    def __init__(self, container, parts=[], *args, **kwargs):
        super(MultiPolygon, self).__init__(container, *args, **kwargs)
        for part in parts:
            role = 'outer'
            for ring in part:
                if isinstance(ring, Way):
                    self.append(ring, role)
                else:
                    self.append(Way(container, ring), role)
                role = 'inner'
