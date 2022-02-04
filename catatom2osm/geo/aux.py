is_inside = lambda f1, f2: (
        f2.geometry().contains(f1.geometry())
        or f2.geometry().overlaps(f1.geometry())
)

def is_inside_area(f1, f2):
    g1 = f1.geometry()
    g2 = f2.geometry()
    inter = g2.intersection(g1)
    return inter.area() / g1.area() >= 0.5

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
