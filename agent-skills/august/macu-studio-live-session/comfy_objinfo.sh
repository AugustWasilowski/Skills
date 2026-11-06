#!/usr/bin/env bash
# Ground-truth: what model files do leo's ComfyUI WAN loaders actually offer?
q() {
  local node="$1" field="${2:-model}"
  echo "=== $node ($field) ==="
  curl -s "http://127.0.0.1:8188/object_info/$node" \
   | python3 -c "import sys,json
try:
  d=json.load(sys.stdin)[\"$node\"]['input']
  v=(d.get('required',{}).get(\"$field\") or d.get('optional',{}).get(\"$field\"))
  print(v[0] if v else 'NONE')
except Exception as e:
  print('ERR', e)"
}
q WanVideoModelLoader model
q WanVideoLoraSelect lora
q CLIPVisionLoader clip_name
q WanVideoVAELoader model_name
q WanVideoTextEncodeCached t5
