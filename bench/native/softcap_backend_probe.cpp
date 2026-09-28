// Exercise real GGML allocation, CUDA graph fusion and launch at the int32 boundary.
#include "ggml.h"
#include "ggml-alloc.h"
#include "ggml-backend.h"
#include "ggml-cuda.h"
#include <algorithm>
#include <cmath>
#include <cstdio>
#include <cstdlib>
#include <vector>
int main(int argc, char ** argv) {
    const int64_t rows = argc > 1 ? std::atoll(argv[1]) : 8192;
    if (rows < 1 || rows > 11264) return 2;
    ggml_backend_t backend = ggml_backend_cuda_init(0);
    if (!backend) return 3;
    ggml_init_params params = { 1024*1024, nullptr, true };
    ggml_context * ctx = ggml_init(params);
    ggml_tensor * input = ggml_new_tensor_2d(ctx, GGML_TYPE_F32, 262144, rows);
    ggml_set_input(input);
    auto output = ggml_scale(ctx, ggml_tanh(ctx, ggml_scale(ctx, input, 1.0f/30.0f)), 30.0f);
    ggml_set_output(output);
    auto graph = ggml_new_graph(ctx);
    ggml_build_forward_expand(graph, output);
    auto allocator = ggml_gallocr_new(ggml_backend_get_default_buffer_type(backend));
    if (!ggml_gallocr_alloc_graph(allocator, graph)) return 4;
    std::printf("{\"event\":\"allocated\",\"rows\":%lld,\"elements\":%lld,\"buffer_bytes\":%zu}\n",
        (long long)rows, (long long)ggml_nelements(input), ggml_gallocr_get_buffer_size(allocator,0));
    std::fflush(stdout);
    std::vector<float> zeros(1024*1024, 0);
    for (size_t offset=0; offset<ggml_nbytes(input); offset+=zeros.size()*sizeof(float))
        ggml_backend_tensor_set(input, zeros.data(), offset, std::min(zeros.size()*sizeof(float),ggml_nbytes(input)-offset));
    const size_t indices[] = {0, (size_t)ggml_nelements(input)/2, (size_t)ggml_nelements(input)-1};
    const float values[] = {-45.0f, 3.0f, 60.0f};
    for(int i=0;i<3;++i) ggml_backend_tensor_set(input,&values[i],indices[i]*sizeof(float),sizeof(float));
    auto status=ggml_backend_graph_compute(backend,graph);
    ggml_backend_synchronize(backend);
    if(status != GGML_STATUS_SUCCESS) return 5;
    // CUDA fast-math tanh is approximate; use explicit absolute + relative tolerance.
    std::printf("{\"event\":\"tolerance\",\"absolute\":0.00001,\"relative\":0.00001}\n");
    bool pass=true;
    for(int i=0;i<3;++i) {
        float actual=0; ggml_backend_tensor_get(output,&actual,indices[i]*sizeof(float),sizeof(float));
        const float expected=30.0f*std::tanh(values[i]/30.0f);
        if(!std::isfinite(actual) || std::fabs(actual-expected) > 1e-5f + 1e-5f*std::fabs(expected)) pass=false;
        std::printf("{\"event\":\"sentinel\",\"index\":%zu,\"actual\":%.8g,\"expected\":%.8g}\n",indices[i],actual,expected);
    }
    std::printf("{\"event\":\"result\",\"pass\":%s}\n",pass?"true":"false");
    ggml_gallocr_free(allocator);ggml_free(ctx);ggml_backend_free(backend);
    return pass?0:6;
}
