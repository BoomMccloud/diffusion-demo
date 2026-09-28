#pragma once
// Benchmark protocol v2. SIGUSR1 requests cancellation; only the main thread logs.
#include <algorithm>
#include <chrono>
#include <csignal>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <cstdint>
#include <string>
#include <vector>
namespace benchmark_trace {
inline volatile std::sig_atomic_t cancelled = 0;
inline FILE * stream = nullptr;
inline int turn = 0, block = -1;
inline bool stopped = false;
inline const char * reason = "block_budget";
inline double now() {
    return std::chrono::duration<double>(std::chrono::steady_clock::now().time_since_epoch()).count();
}
inline bool enabled() { return std::getenv("DIFFUSION_EVENT_PATH") != nullptr; }
inline bool diagnostic() {
    auto mode = std::getenv("DIFFUSION_TRACE_MODE");
    return mode && !std::strcmp(mode, "diagnostic");
}
inline void event(const char * name, const std::string & fields = "") {
    if (!enabled()) return;
    if (!stream) stream = std::fopen(std::getenv("DIFFUSION_EVENT_PATH"), "a");
    if (!stream) { std::perror("benchmark trace"); std::exit(74); }
    std::fprintf(stream, "{\"version\":2,\"event\":\"%s\",\"monotonic_seconds\":%.9f,\"turn\":%d,\"block\":%d%s}\n",
                 name, now(), turn, block, fields.c_str());
    std::fflush(stream);
}
inline void init() {
    if (!enabled()) return;
    std::signal(SIGUSR1, [](int) { cancelled = 1; });
}
inline void begin() {
    ++turn; block = -1; stopped = false; reason = "block_budget";
    // Do not clear a signal received while a request was being dispatched.
    event("begin", ",\"repetition_policy\":\"off\"");
}
inline void stop() {
    if (stopped) return;
    event("stop", std::string(",\"reason\":\"") + (cancelled ? "cancelled" : reason) + "\"");
    stopped = true; cancelled = 0;
}
inline int prefill_chunk(int ubatch) {
    if (!enabled()) return ubatch;
    auto value = std::getenv("DIFFUSION_PREFILL_CHUNK");
    const int requested = value ? std::atoi(value) : 2048;
    return requested > 0 && requested < ubatch ? requested : ubatch;
}
// Incremental prefill: the prompt-KV store persists across blocks, so only tokens past the longest
// already-stored common prefix are re-encoded. DIFFUSION_INCREMENTAL_PREFILL=0 restores full re-prefill.
inline bool incremental_prefill() {
    auto value = std::getenv("DIFFUSION_INCREMENTAL_PREFILL");
    return !(value && !std::strcmp(value, "0"));
}
inline std::vector<int32_t> & prefilled() { static std::vector<int32_t> tokens; return tokens; }
inline int32_t prefill_reuse(const int32_t * tokens, int32_t n) {
    auto & cached = prefilled();
    if (!incremental_prefill()) { cached.clear(); return 0; }
    const int32_t limit = std::min<int32_t>((int32_t) cached.size(), n - 1);  // always encode >= 1 token
    int32_t k = 0;
    while (k < limit && cached[k] == tokens[k]) ++k;
    cached.resize(k);  // store positions >= k are about to be overwritten
    return k;
}
inline void prefill_done(const int32_t * tokens, int32_t end) {
    if (incremental_prefill()) prefilled().assign(tokens, tokens + end);
}
}
