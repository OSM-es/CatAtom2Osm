is_inside = lambda f1, f2: (
        f2.geometry().contains(f1.geometry())
        or f2.geometry().overlaps(f1.geometry())
)

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
                if len({p for p in adj if p in group}) > 0:
                    group |= set(adj)
                    adjs.remove(adj)
        groups.append(group)
    return groups
