"""OSM XML format serializer."""
import logging

from lxml import etree

from catatom2osm import config, osm

log = logging.getLogger(config.app_name)


def add_tags(item, elem):
    for key, value in elem.tags.items():
        etree.SubElement(item, "tag", dict(k=key, v=str(value)))


def serialize(outfile, data):
    """Output XML for an OSM data set."""
    root = etree.Element("osm", data.attrs)
    if data.note is not None:
        etree.SubElement(root, "note").text = data.note
    if data.meta is not None:
        etree.SubElement(root, "meta", data.meta)
    if data.tags:
        cs = etree.SubElement(root, "changeset")
        add_tags(cs, data)
    for node in data.nodes:
        e = etree.SubElement(root, "node", node.attrs)
        add_tags(e, node)
    for way in data.ways:
        e = etree.SubElement(root, "way", way.attrs)
        add_tags(e, way)
    for rel in data.relations:
        e = etree.SubElement(root, "relation", rel.attrs)
        for m in rel.members:
            etree.SubElement(e, "member", m.attrs)
        add_tags(e, rel)
    options = dict(pretty_print=True, xml_declaration=True, encoding="utf-8")
    output = etree.tostring(root, **options)
    outfile.write(output.decode())


def deserialize(infile, data=None):
    """Generate a OSM data set from OSM XML or append to existing data."""
    if data is None:
        data = osm.Osm()
    context = etree.iterparse(infile, events=("end",))
    childs = []
    tags = {}
    for event, elem in context:
        if elem.tag == "osm":
            data.upload = elem.get("upload")
            data.version = elem.get("version")
            data.generator = elem.get("generator")
        elif elem.tag == "changeset":
            data.tags = tags
            tags = {}
        elif elem.tag == "note":
            data.note = str(elem.text)
        elif elem.tag == "meta":
            data.meta = dict(elem.attrib)
        elif elem.tag == "node":
            lon = float(elem.get("lon"))
            lat = float(elem.get("lat"))
            n = data.Node(lon, lat, tags=tags, attrs=dict(elem.attrib))
            tags = {}
        elif elem.tag == "way":
            w = data.Way(tags=tags, attrs=dict(elem.attrib))
            w.nodes = childs
            childs = []
            tags = {}
        elif elem.tag == "nd":
            childs.append(elem.get("ref"))
        elif elem.tag == "relation":
            r = data.Relation(tags=tags, attrs=dict(elem.attrib))
            r.members = childs
            childs = []
            tags = {}
        elif elem.tag == "member":
            childs.append(
                {
                    "ref": elem.get("ref"),
                    "type": elem.get("type"),
                    "role": elem.get("role"),
                }
            )
        elif elem.tag == "tag":
            tags[elem.get("k")] = elem.get("v")
        elem.clear()
        if hasattr(elem, "xpath"):
            for ancestor in elem.xpath("ancestor-or-self::*"):
                while ancestor.getprevious() is not None:
                    del ancestor.getparent()[0]
    del context
    for way in data.ways:
        missing = []
        for i, ref in enumerate(way.nodes):
            if isinstance(ref, str):
                if "n{}".format(ref) in data.index:
                    n = data.get(ref)
                    way.nodes[i] = n
                    data.parents[n].add(way)
                else:
                    missing.append(i)
        if len(missing) > 0:
            for i in sorted(missing, reverse=True):
                way.nodes.pop(i)
            if way.version is not None:
                way.version = str(int(way.version) + 1)
    for rel in data.relations:
        missing = []
        for i, m in enumerate(rel.members):
            if isinstance(m, dict):
                if m["type"][0].lower() + str(m["ref"]) in data.index:
                    el = data.get(m["ref"], m["type"])
                    rel.members[i] = osm.Relation.Member(el, m["role"])
                    data.parents[el].add(rel)
                else:
                    missing.append(i)
        if len(missing) > 0:
            for i in sorted(missing, reverse=True):
                rel.members.pop(i)
            if rel.version is not None:
                rel.version = str(int(rel.version) + 1)
    return data
