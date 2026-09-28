#!/usr/bin/env python3
"""Incrementally build the pinned benchmark runner and real CUDA backend probe."""
import argparse
import hashlib
import json
import shlex
import subprocess
import sys
from pathlib import Path
HERE = Path(__file__).resolve().parent
p = argparse.ArgumentParser(description=__doc__)
p.add_argument('checkout', type=Path)
args = p.parse_args()
root = args.checkout.resolve()
subprocess.run([sys.executable, str(HERE/'prepare.py'), str(root)], check=True)
subprocess.run([sys.executable, str(HERE.parents[1]/'tests/native/test_softcap_boundary.py'), str(root/'ggml/src/ggml-cuda/softcap.cu')], check=True)
subprocess.run(['cmake', '--build', str(root/'build'), '--target', 'llama-diffusion-cli', '-j8'], check=True)
directory = root/'build/examples/diffusion'
command = shlex.split((directory/'CMakeFiles/llama-diffusion-cli.dir/link.txt').read_text())
command[command.index('CMakeFiles/llama-diffusion-cli.dir/diffusion-cli.cpp.o')] = str(HERE/'softcap_backend_probe.cpp')
probe = root/'build/bin/softcap-backend-probe'
command[command.index('-o')+1] = str(probe)
command += ['-I'+str(root/'ggml/include'), '-std=c++17']
subprocess.run(command, cwd=directory, check=True)
manifest_path = root/'benchmark-v2-build.json'
manifest = json.loads(manifest_path.read_text())
manifest['binaries'] = {str(path): hashlib.sha256(path.read_bytes()).hexdigest()
                       for path in (root/'build/bin/llama-diffusion-cli', probe)}
manifest['cmake_cache_sha256'] = hashlib.sha256((root/'build/CMakeCache.txt').read_bytes()).hexdigest()
manifest['probe_source_sha256'] = hashlib.sha256((HERE/'softcap_backend_probe.cpp').read_bytes()).hexdigest()
manifest_path.write_text(json.dumps(manifest, indent=2))
