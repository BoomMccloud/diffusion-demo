# Clover llama.cpp build, following the official GGUF model card steps
# (https://huggingface.co/Diffuspace/Clover-35B-A3B-Preview-GGUF) on DGX Spark (GB10, arm64).
FROM nvidia/cuda:13.0.1-devel-ubuntu24.04

RUN apt-get update && apt-get install -y --no-install-recommends \
        git cmake build-essential ca-certificates python3 python3-pip python3-venv \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /opt
# Step 1 of the model card: clone and check out the PR head.
RUN git clone https://github.com/ggml-org/llama.cpp.git \
    && cd llama.cpp \
    && git fetch origin pull/31306/head \
    && git checkout --detach FETCH_HEAD \
    && git rev-parse HEAD > /opt/llama.cpp.sha

# Step 2 of the model card: the CUDA build. The only addition is the CUDA
# architecture, because `docker build` has no GPU to detect (GB10 is SM 121).
# The stub libcuda lets the linker resolve driver symbols at build time.
WORKDIR /opt/llama.cpp
RUN ln -s /usr/local/cuda/lib64/stubs/libcuda.so /usr/local/cuda/lib64/stubs/libcuda.so.1 \
    && LD_LIBRARY_PATH=/usr/local/cuda/lib64/stubs cmake -S . -B build-clover \
        -DGGML_CUDA=ON \
        -DCMAKE_CUDA_ARCHITECTURES=121 \
        -DLLAMA_CURL=OFF \
        -DLLAMA_BUILD_TESTS=OFF \
        -DLLAMA_BUILD_SERVER=ON \
        -DCMAKE_BUILD_TYPE=Release \
    && LD_LIBRARY_PATH=/usr/local/cuda/lib64/stubs cmake --build build-clover --config Release \
        --target llama-speculative-simple -j"$(nproc)" \
    && rm /usr/local/cuda/lib64/stubs/libcuda.so.1

# Plain AR tools and llama-server from the same build tree. The server target
# needs -DLLAMA_BUILD_SERVER=ON above, the one change from the model card flags. The model card's draft-self mode is
# not in this commit, and llama-speculative-simple refuses to run without one.
RUN ln -s /usr/local/cuda/lib64/stubs/libcuda.so /usr/local/cuda/lib64/stubs/libcuda.so.1 \
    && LD_LIBRARY_PATH=/usr/local/cuda/lib64/stubs cmake --build build-clover --config Release \
        --target llama-completion llama-bench llama-server -j"$(nproc)" \
    && rm /usr/local/cuda/lib64/stubs/libcuda.so.1

# gguf-py from the same checkout, for dumping GGUF metadata.
RUN python3 -m venv /opt/venv && /opt/venv/bin/pip install --no-cache-dir ./gguf-py
ENV PATH=/opt/llama.cpp/build-clover/bin:/opt/venv/bin:$PATH
WORKDIR /work
