import io
import json
import os
import re

from lxml import etree
from osm2geojson import json2shapes
from shapely.geometry import shape

from catatom2osm import config, csvtools, download, hgwnames, osmxml, overpass
from catatom2osm.exceptions import CatValueError


def list_code(code):
    if code == "99":
        list_provincial_offices()
    else:
        code = f"{code:>02}"
        if len(code) > 2:
            list_districts(code)
        else:
            list_municipalities(code)


def list_provincial_offices():
    title = _("Territorial office")
    print(title)
    print("=" * len(title))
    for code, prov in config.prov_codes.items():
        print(f"{code} {prov}")


def get_districts(code):
    id, name = get_municipality(code)
    query = overpass.Query(id)
    query.add('wr["boundary"="administrative"]["admin_level"="9"]')
    query.add('wr["boundary"="administrative"]["admin_level"="10"]')
    result = query.read()
    with io.BytesIO(result) as fo:
        data = osmxml.deserialize(fo)
    district = {}
    subarea = []
    ward = []
    for e in data.elements:
        if e.tags.get("boundary", "") == "administrative":
            if e.type == "relation":
                if e.tags.get("admin_level", "") == "9":
                    id = e.id
                    district[id] = {"boundary": e, "subarea": []}
                    for m in e.members:
                        if m.role == "subarea":
                            district[id]["subarea"].append(m.element)
                            subarea.append(m.element.id)
                            if m.element in ward:
                                ward.remove(m.element)
                elif e.tags.get("admin_level", "") == "10" and e.id not in subarea:
                    ward.append(e)
            elif e.type == "way" and e.is_closed():
                if e.tags.get("admin_level", "") == "9":
                    district[e.id] = {"boundary": e}
                elif e.tags.get("admin_level", "") == "10":
                    ward.append(e)
    by_name_dist = lambda d: d["boundary"].tags.get("name", "")
    by_name_ward = lambda w: w.tags.get("name", "")
    districts = []
    for d in sorted(district.values(), key=by_name_dist):
        e = d["boundary"]
        districts.append((False, str(e.id), _("District"), e.tags.get("name", "")))
        subarea = d.get("subarea", [])
        for m in sorted(subarea, key=by_name_ward):
            districts.append((True, str(m.id), _("Ward"), m.tags.get("name", "")))
    for w in sorted(ward, key=by_name_ward):
        districts.append((False, str(w.id), _("Ward"), w.tags.get("name", "")))
    return districts


def list_districts(code):
    districts = get_districts(code)
    for row in districts:
        tab = "  " if row[0] else ""
        print(tab + " ".join(row[1:]))


def get_municipality(mun_code):
    fn = os.path.join(config.app_path, "municipalities.csv")
    result = csvtools.get_key(fn, mun_code)
    if result:
        __, id, name = result
        return (id, name)
    return (None, None)


def search_municipality(cat_path, mun_code, name, bounding_box):
    fn = os.path.join(cat_path, mun_code + ".geojson")
    mun = None
    if os.path.exists(fn):
        with open(fn) as fo:
            geojson = json.load(fo)
        mun = shape(geojson["features"][0]["geometry"])
        bounding_box = "{1},{0},{3},{2}".format(*mun.buffer(0.01).bounds)
    query = overpass.Query(bounding_box, "json", mun is not None, False)
    query.add('rel["admin_level"="8"]')
    try:
        data = json.loads(query.read())
        shapes = json2shapes(data)
        if mun:
            max_area = 0
            mname = ""
            id = 0
            matching = None
            for s in shapes:
                if (
                    "tags" in s["properties"]
                    and s["properties"]["tags"].get("admin_level") == "8"
                    and "boundary" in s["properties"]["tags"]
                ):
                    if s["shape"].intersects(mun):
                        area = s["shape"].intersection(mun).area / s["shape"].area
                        if area > max_area:
                            max_area = area
                            mname = s["properties"]["tags"].get("name")
                            id = str(s["properties"]["id"])
            if mname and max_area > 0.9:
                return (id, mname)
        getter = lambda e: e.get("tags", {}).get("name", "")
        elements = [
            e
            for e in data["elements"]
            if (
                e.get("tags", {}).get("admin_level") == "8"
                and "boundary" in e.get("tags", {})
                and "name" in e.get("tags", {})
            )
        ]
        matching = hgwnames.dsmatch(name, elements, getter)
    except ConnectionError:
        pass
    if matching:
        id = str(matching["id"])
        name = matching["tags"]["name"]
        return (id, name)
    return (None, None)


def get_municipalities(prov_code):
    url = config.prov_url["BU"].format(code=prov_code)
    response = download.get_response(url)
    root = etree.fromstring(response.content)
    ns = {"atom": "http://www.w3.org/2005/Atom"}
    municipios = []
    for entry in root.findall("atom:entry", namespaces=ns):
        row = entry.find("atom:title", ns).text.replace("buildings", "")
        row = row.replace("Territorial office", "")
        municipios.append(row.strip().split("-"))
    return municipios


def list_municipalities(prov_code):
    municipalities = get_municipalities(prov_code)
    if prov_code not in config.prov_codes.keys():
        msg = _("Province code '%s' is not valid") % prov_code
        raise CatValueError(msg)
    office = config.prov_codes[prov_code]
    title = _("Territorial office %s - %s") % (prov_code, office)
    print(title)
    print("=" * len(title))
    for mun_code, mun_name in municipalities:
        print(f"{mun_code} {mun_name}")


def get_boundary(cat_path, boundary_search_area, id_or_name):
    query = overpass.Query(boundary_search_area)
    if re.search(r"^[0-9]+$", id_or_name):
        query.add(f"wr({id_or_name})")
    else:
        query.add(f'wr["boundary"="administrative"]["name"="{id_or_name}"]')
    result = query.read()
    with io.BytesIO(result) as fo:
        data = osmxml.deserialize(fo)
    fn = id_or_name
    for e in data.elements:
        if e.type == "relation" or (e.type == "way" and e.is_closed()):
            if e.tags.get("boundary", "") == "administrative":
                fn = e.tags.get("name", fn)
                break
    fn = os.path.join(cat_path, fn.replace(" ", "_") + ".osm")
    with open(fn, "wb") as fo:
        fo.write(result)
    fn += "|layername=multipolygons"
    return fn
