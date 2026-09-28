"""Compile the actual CLI trimming lambda with repeated values and an EOG sentinel."""
from pathlib import Path
import subprocess
import sys
import tempfile
source = Path(sys.argv[1]).read_text()
start = source.index('    auto trim_canvas =')
end = source.index('\n    };', start) + len('\n    };')
trim = source[start:end]
header = Path(__file__).resolve().parents[2] / "bench" / "native"
prefix = '''#include "benchmark_trace.h"
#include <cstddef>
#include <cassert>
using llama_token = int;
bool llama_vocab_is_eog(void *, int token) { return token == 99; }
int main() {
setenv("DIFFUSION_EVENT_PATH", "unused", 1);
void * vocab = nullptr;
'''
suffix = '''
const int repeated[] = {1,1,1,1,1,1,1,1,1};
assert(trim_canvas(repeated, 9) == 9);
const int stopped[] = {1,1,1,99,1,1,1,1,1};
assert(trim_canvas(stopped, 9) == 3);
}
'''
with tempfile.TemporaryDirectory() as folder:
    cpp = Path(folder)/'test.cpp'
    cpp.write_text(prefix + trim + suffix)
    binary = str(Path(folder)/'test')
    subprocess.run(['c++','-std=c++17','-I'+str(header),str(cpp),'-o',binary],check=True)
    raise SystemExit(subprocess.call([binary]))
