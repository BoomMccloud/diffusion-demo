"""Exercise actual source host launch arithmetic without allocating a huge tensor."""
from pathlib import Path
import subprocess,sys,tempfile
source=Path(sys.argv[1]).read_text();source=source[source.index('static __global__'):source.index('// fused GGML_OP_SCALE')]
pre=r'''
#include <cstdint>
#include <cmath>
#include <cstdio>
#define __global__
#define CUDA_SOFTCAP_BLOCK_SIZE 256
struct D { unsigned int x=0; } blockDim,blockIdx,threadIdx;
void ggml_cuda_pdl_lc(){} void ggml_cuda_pdl_sync(){}
using cudaStream_t=int;
struct ggml_cuda_kernel_launch_params { int64_t blocks; ggml_cuda_kernel_launch_params(int64_t b,int,int,int):blocks(b){} };
int64_t observed_k,observed_blocks;
template<typename F,typename K> void ggml_cuda_kernel_launch(F,const ggml_cuda_kernel_launch_params &p,const float*,float*,float,float,K k){ observed_k=k; observed_blocks=p.blocks; }
'''
post=r'''
int main(){
 for(int64_t positions:{8191LL,8192LL,8239LL,11264LL}){
  int64_t expected=positions*262144;
  softcap_f32_cuda(nullptr,nullptr,1.0f,30.0f,expected,0);
  bool ok=observed_k==expected && observed_blocks==(expected+255)/256;
  printf("positions=%lld expected=%lld actual=%lld blocks=%lld %s\n",(long long)positions,(long long)expected,(long long)observed_k,(long long)observed_blocks,ok?"PASS":"FAIL");
  if(!ok)return 1;
 }
}
'''
with tempfile.TemporaryDirectory() as d:
 p=Path(d)/'probe.cpp';p.write_text('#include <initializer_list>\n'+pre+source+post)
 subprocess.run(['c++','-std=c++17','-O0',str(p),'-o',d+'/probe'],check=True)
 raise SystemExit(subprocess.call([d+'/probe']))
