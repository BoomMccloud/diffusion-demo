# Copy a GGUF, adding clover_moe.expert_shared_count = 1. Usage: add_key.py <in> <out>
import sys
from gguf import GGUFReader, GGUFWriter, GGUFValueType
src, dst = sys.argv[1:]
r = GGUFReader(src)
arch = r.fields["general.architecture"].contents()
w = GGUFWriter(dst, arch=arch, endianess=r.endianess)
for name, f in r.fields.items():
    if name.startswith("GGUF.") or name == "general.architecture":
        continue
    vt = f.types[0]
    sub = f.types[-1] if vt == GGUFValueType.ARRAY else None
    w.add_key_value(name, f.contents(), vt, sub_type=sub)
w.add_uint32(f"{arch}.expert_shared_count", 1)
for t in r.tensors:
    w.add_tensor_info(t.name, t.data.shape, t.data.dtype, t.data.nbytes, t.tensor_type)
w.write_header_to_file(); w.write_kv_data_to_file(); w.write_ti_data_to_file()
for t in r.tensors:
    w.write_tensor_data(t.data)
w.close()
