#include "llama.h"
#include "chat.h"
#include "common.h"
#include <iostream>
#include <string>
static void quiet(enum ggml_log_level, const char *, void *) {}
int main(int argc,char **argv) {
 if(argc!=2) return 2; llama_log_set(quiet,nullptr); llama_backend_init();
 auto params=llama_model_default_params(); params.vocab_only=true;
 auto *model=llama_model_load_from_file(argv[1],params); if(!model) return 3;
 auto *vocab=llama_model_get_vocab(model); auto templates=common_chat_templates_init(model, "");
 std::string line; while(std::getline(std::cin,line)) {
  bool prompt=line.rfind("p:",0)==0; if(prompt) line=line.substr(2); if(line.size()%2) return 4;
  std::string s; for(size_t i=0;i<line.size();i+=2) s.push_back(static_cast<char>(std::stoi(line.substr(i,2),nullptr,16)));
  if(prompt) { common_chat_msg msg; msg.role="user"; msg.content=s; common_chat_templates_inputs inputs; inputs.messages={msg}; inputs.add_generation_prompt=true; s=common_chat_templates_apply(templates.get(),inputs).prompt; }
  int n=llama_tokenize(vocab,s.data(),s.size(),nullptr,0,prompt,prompt); std::cout << (n<0?-n:n) << std::endl;
 }
 llama_model_free(model); llama_backend_free(); return 0;
}
