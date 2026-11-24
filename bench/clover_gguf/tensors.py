import sys, re, collections
from gguf import GGUFReader
names = {}
for p in sys.argv[1:]:
    names[p] = {re.sub(r"blk\.\d+\.", "blk.N.", t.name) for t in GGUFReader(p).tensors}
    c = collections.Counter(re.sub(r"blk\.\d+\.", "blk.N.", t.name) for t in GGUFReader(p).tensors)
    names[p] = c
a, b = sys.argv[1:]
for k in sorted(set(names[a]) | set(names[b])):
    if names[a][k] != names[b][k]:
        print(f"{k}: official={names[a][k]} bartowski={names[b][k]}")
