import json, sys, collections
d = json.load(open(sys.argv[1]))
print(f"network lookups (non-local): {len(d['lookups'])}")
for (t, h), n in collections.Counter(map(tuple, d["lookups"])).most_common():
    print(f"   {n:3d}  {h:28s} {t}")
print(f"file writes into the project or outside temp dirs: {len(d['writes'])}")
for (t, p), n in collections.Counter(map(tuple, d["writes"])).most_common():
    print(f"   {n:3d}  {p}   <- {t}")
