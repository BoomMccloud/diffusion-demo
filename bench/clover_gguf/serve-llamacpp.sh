#!/bin/sh
# Start llama-server for one GGUF model folder on port 8080, in a throwaway container.
# Usage: serve-llamacpp.sh <model-folder-name> <gguf-file> [parallel-slots]
# Same settings as the Clover model card run: bf16 KV cache, flash attention, full offload.
# Optional environment:
#   MMPROJ=<file in the model folder>       vision projector, loaded with --mmproj
#   DRAFT_DIR=<folder> DRAFT=<gguf> SPEC=<type>  draft model for speculative decoding,
#                                           with SPEC_N=<max draft tokens> (default 15)
#   ALIAS=<name>                            served model name (default: the folder name)
#   KEEP=1                                  keep the container after it exits, for crash logs
set -e
name=$1; file=$2; np=${3:-32}
alias=${ALIAS:-$name}
extra=""
mounts="-v $HOME/clover/models/$name:/model:ro"
[ -n "$MMPROJ" ] && extra="$extra --mmproj /model/$MMPROJ"
if [ -n "$DRAFT" ]; then
  mounts="$mounts -v $HOME/clover/models/$DRAFT_DIR:/draft:ro"
  extra="$extra -md /draft/$DRAFT -ngld 99 --spec-type ${SPEC:-draft-simple} --spec-draft-n-max ${SPEC_N:-15}"
fi
docker rm -f srv-llamacpp >/dev/null 2>&1 || true
rm_flag="--rm"; [ -n "$KEEP" ] && rm_flag=""
docker run -d $rm_flag --name srv-llamacpp --gpus all --network host $mounts \
  clover-llamacpp:pr31306 \
  llama-server -m "/model/$file" --alias "$alias" \
    --host 127.0.0.1 --port 8080 \
    -ngl 99 -fa on -ctk bf16 -ctv bf16 \
    -c $((np * 4096)) -np "$np" --kv-unified \
    -t 8 -tb 8 --jinja --no-webui $extra
