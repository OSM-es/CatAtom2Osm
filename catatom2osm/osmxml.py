"""OSM XML format serializer"""
import logging
from lxml import etree

from catatom2osm import config, osm
log = logging.getLogger(config.app_name)


def write_elem(outfile, e):
    try:
        outfile.write(etree.tostring(e, pretty_print=True).decode())
    except TypeError: # pragma: no cover
        outfile.write(etree.tostring(e).decode())

def serialize(outfile, data):
    """Output XML for an OSM data set"""
    outfile.write("<?xml version='1.0' encoding='UTF-8'?>\n")
    attrs = ''.join([" {}='{}'".format(k, v) for (k,v) in data.attrs.items()])
    outfile.write("<osm{}>\n".format(attrs))
    if data.note is not None:
        e = etree.Element('note')
        e.text = data.note
        write_elem(outfile, e)
    if data.meta is not None:
        e = etree.Element('meta')
        for (k, v) in data.meta.items():
            e.set(k, v)
        write_elem(outfile, e)
    if data.tags:
        e = etree.Element('changeset')
        for (key, value) in data.tags.items():
            e.append(etree.Element('tag', dict(k=key, v=str(value))))
        write_elem(outfile, e)
    for node in data.nodes:
        e = etree.Element('node', node.attrs)
        for key, value in node.tags.items():
            e.append(etree.Element('tag', dict(k=key, v=str(value))))
        write_elem(outfile, e)
    for way in data.ways:
        e = etree.Element('way', way.attrs)
        for node in way.nodes:
            e.append(etree.Element('nd', dict(ref=str(node.id))))
        for key, value in way.tags.items():
            e.append(etree.Element('tag', dict(k=key, v=str(value))))
        write_elem(outfile, e)
    for rel in data.relations:
        e = etree.Element('relation', rel.attrs)
        for m in rel.members:
            e.append(etree.Element('member', m.attrs))
        for key, value in rel.tags.items():
            e.append(etree.Element('tag', dict(k=key, v=str(value))))
        write_elem(outfile, e)
    outfile.write("</osm>\n")
        
def deserialize(infile, data=None):
    """Generates or append to an OSM data set from OSM XML"""
    if data is None:
        data = osm.Osm()
    context = etree.iterparse(infile, events=('end',))
    childs = []
    tags = {}
    for event, elem in context:
        if elem.tag == 'osm':
            data.upload = elem.get('upload')
            data.version = elem.get('version')
            data.generator = elem.get('generator')
        elif elem.tag == 'changeset':
            data.tags = tags
            tags = {}
        elif elem.tag == 'note':
            data.note = str(elem.text)
        elif elem.tag == 'meta':
            data.meta = dict(elem.attrib)
        elif elem.tag == 'node':
            lon = float(elem.get('lon'))
            lat = float(elem.get('lat'))
            n = data.Node(lon, lat, tags=tags, attrs=dict(elem.attrib))
            tags = {}
        elif elem.tag == 'way':
            w = data.Way(tags=tags, attrs=dict(elem.attrib))
            w.nodes = childs
            childs = []
            tags = {}
        elif elem.tag == 'nd':
            childs.append(elem.get('ref'))
        elif elem.tag == 'relation':
            r = data.Relation(tags=tags, attrs=dict(elem.attrib))
            r.members = childs
            childs = []
            tags = {}
        elif elem.tag == 'member':
            childs.append({
                'ref': elem.get('ref'),
                'type': elem.get('type'),
                'role': elem.get('role')
            })
        elif elem.tag == 'tag':
            tags[elem.get('k')] = elem.get('v')
        elem.clear()
        if hasattr(elem, 'xpath'):
            for ancestor in elem.xpath('ancestor-or-self::*'):
                while ancestor.getprevious() is not None:
                    del ancestor.getparent()[0]
    del context
    for way in data.ways:
        missing = []
        for i, ref in enumerate(way.nodes):
            if isinstance(ref, str):
                if 'n{}'.format(ref) in data.index:
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
                if m['type'][0].lower() + str(m['ref']) in data.index:
                    el = data.get(m['ref'], m['type'])
                    rel.members[i] = osm.Relation.Member(el, m['role'])
                    data.parents[el].add(rel)
                else:
                    missing.append(i)
        if len(missing) > 0:
            for i in sorted(missing, reverse=True):
                rel.members.pop(i)
            if rel.version is not None:
                rel.version = str(int(rel.version) + 1)
    return data

