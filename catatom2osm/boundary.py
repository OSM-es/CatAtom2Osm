import io
import os
import re

from catatom2osm import config, csvtools, osmxml, overpass
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


def list_municipalities(code):
    fn = os.path.join(config.app_path, "municipalities.csv")
    if code not in config.prov_codes.keys():
        msg = _("Province code '%s' is not valid") % code
        raise CatValueError(msg)
    office = config.prov_codes[code]
    title = _("Territorial office %s - %s") % (code, office)
    print(title)
    print("=" * len(title))
    for mun in csvtools.startswith(fn, code):
        print(f"{mun[0]} {mun[2]}")


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
    print(districts)
    return districts


def list_districts(code):
    districts = get_districts(code)
    for row in districts:
        tab = "  " if row[0] else ""
        print(tab + " ".join(row[1:]))


def get_municipality(code):
    fn = os.path.join(config.app_path, "municipalities.csv")
    result = csvtools.get_key(fn, code)
    if not result:
        msg = _("Municipality code '%s' don't exists") % code
        raise CatValueError(msg)
    __, id, name = result
    return (id, name)


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
