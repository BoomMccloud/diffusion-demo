"""Compile the incremental-prefill bookkeeping in benchmark_trace.h and check block reuse."""
from pathlib import Path
import subprocess
import tempfile
header = Path(__file__).resolve().parents[2] / "bench" / "native"
source = '''#include "benchmark_trace.h"
#include <cassert>
#include <cstdlib>
using benchmark_trace::prefill_reuse;
using benchmark_trace::prefill_done;
int main() {
    const int32_t block0[] = {2, 10, 11, 12};
    const int32_t block1[] = {2, 10, 11, 12, 20, 21};
    const int32_t other[]  = {2, 10, 99, 12, 20};
    // First block: nothing stored yet.
    assert(prefill_reuse(block0, 4) == 0);
    prefill_done(block0, 2);                   // a chunk boundary
    prefill_done(block0, 4);
    // Next block extends the committed prefix: only the new tokens are encoded.
    assert(prefill_reuse(block1, 6) == 4);
    prefill_done(block1, 6);
    // Identical input still re-encodes the last token.
    assert(prefill_reuse(block1, 6) == 5);
    prefill_done(block1, 6);
    // A divergent prompt reuses only the shared head.
    assert(prefill_reuse(other, 5) == 2);
    // A failed chunk leaves nothing stored past the divergence point.
    assert(prefill_reuse(block1, 6) == 2);
    // Disabled: always a full prefill, and no stale state survives.
    setenv("DIFFUSION_INCREMENTAL_PREFILL", "0", 1);
    prefill_done(block1, 6);
    assert(prefill_reuse(block1, 6) == 0);
    unsetenv("DIFFUSION_INCREMENTAL_PREFILL");
    assert(prefill_reuse(block1, 6) == 0);
}
'''
with tempfile.TemporaryDirectory() as folder:
    cpp = Path(folder) / 'test.cpp'
    cpp.write_text(source)
    binary = str(Path(folder) / 'test')
    subprocess.run(['c++', '-std=c++17', '-I' + str(header), str(cpp), '-o', binary], check=True)
    raise SystemExit(subprocess.call([binary]))
