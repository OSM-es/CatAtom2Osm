get_geometry = lambda f: f.geometry() if hasattr(f, 'geometry') else f

def is_inside(f1, f2):
    g1 = get_geometry(f1)
    g2 = get_geometry(f2)
    return g2.contains(g1) or g2.overlaps(g1)

def is_inside_area(f1, f2):
    g1 = get_geometry(f1)
    g2 = get_geometry(f2)
    if g2.contains(g1):
        return True
    elif g2.overlaps(g1):
        inter = g2.intersection(g1)
        return inter.area() / g1.area() >= 0.5
    return False

get_attributes = lambda feat: \
    dict([(i, feat[i]) for i in range(len(feat.fields().toList()))])

def merge_groups(adjs):
    """Merge all sets in adjs with common members."""
    groups = []
    while adjs:
        group = set(adjs.pop())
        lastlen = -1
        while len(group) > lastlen:
            lastlen = len(group)
            for adj in adjs[:]:
                for p in adj:
                    if p in group:
                        group |= set(adj)
                        adjs.remove(adj)
                        break
        groups.append(group)
    return groups
