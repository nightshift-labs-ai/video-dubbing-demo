#!/usr/bin/env bash
# One-command dubbing job, two phases (translation in between is done by the agent, line by line).
#   phase 1: bash dubjob.sh prep <video> <jobdir>            → <jobdir>/segments.json (with spk labels), stems, script_template.json
#   (agent fills "<lang>" text per line in <jobdir>/script_<lang>.json; keep names/terms; add "note" for hard lines)
#   phase 2: bash dubjob.sh dub <jobdir> <lang>              → <jobdir>/out/dubbed_<lang>.mp4 + .srt + report.json
set -euo pipefail
H=$(cd "$(dirname "$0")" && pwd); FF=/home/agent/tools/ffmpeg; PV=/home/agent/tools/piper-venv/bin/python; DV=/home/agent/tools/demucs-venv/bin/python
export PATH=$FF:$PATH
case "$1" in
prep)
  V="$2"; J="$3"; mkdir -p "$J"; cp "$V" "$J/src.mp4"; cd "$J"
  D=$(ffprobe -v error -show_entries format=duration -of csv=p=0 src.mp4); echo "duration ${D}s"
  ffmpeg -v error -y -i src.mp4 -ac 2 -ar 44100 src.wav
  ffmpeg -v error -y -i src.mp4 -ac 1 -ar 16000 -f s16le src16.raw
  $PV -I -c "
from faster_whisper import WhisperModel
import json, numpy as np
a=np.frombuffer(open('src16.raw','rb').read(),np.int16).astype(np.float32)/32768
m=WhisperModel('base.en',device='cpu',compute_type='int8',download_root='/home/agent/tools/whisper-models')
segs,_=m.transcribe(a,vad_filter=True)
json.dump([{'start':round(s.start,2),'end':round(s.end,2),'text':s.text.strip()} for s in segs],open('asr.json','w'),indent=1)"
  $DV -m demucs --two-stems=vocals -n htdemucs -o sep src.wav >/dev/null 2>&1
  $DV "$H/diarize.py" sep/htdemucs/src/vocals.wav asr.json 0.35 2>/dev/null | sed -n '/^\[/,$p' > segments.json
  python3 -c "
import json; S=json.load(open('segments.json'))
json.dump([{'start':s['start'],'end':s['end'],'spk':s['spk'],'en':s['text'],'XX':''} for s in S],open('script_template.json','w'),indent=1,ensure_ascii=False)
print(len(S),'lines; speakers',sorted(set(s['spk'] for s in S)))"
  echo "NEXT: copy script_template.json → script_<lang>.json, rename key XX → <lang>, translate; then: bash $0 dub $J <lang>";;
dub)
  J="$2"; L="$3"; cd "$J"; mkdir -p out
  python3 -c "
import json,sys; S=json.load(open('script_$L.json')); bad=[i for i,s in enumerate(S) if not s.get('$L','').strip()]
sys.exit('untranslated lines: '+str(bad)) if bad else print(len(S),'lines ok')"
  python3 "$H/dub.py" src.mp4 "script_$L.json" sep/htdemucs/src/no_vocals.wav "out/dubbed_$L.mp4" "$L" > /dev/null
  python3 -c "
import json; R=json.load(open('out/dubbed_$L.report.json'))
print('lines',len(R),'stretched',sum(r['tempo']>1 for r in R),'max overrun s',max(r['overrun_s'] for r in R))
for r in R:
  if r['overrun_s']>0.3: print('  REWRITE SHORTER line',r['line'],'overrun',r['overrun_s'])"
  ls -la out;;
*) echo "usage: dubjob.sh prep <video> <jobdir> | dub <jobdir> <lang>"; exit 1;;
esac
