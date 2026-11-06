# PoC dubbing: per-line TTS (piper), fit each line into its slot (start → next line start) with atempo ≤1.35, place at original start,
# mix over background stem (demucs no_vocals if present, else nothing), burn nothing; write SRT matching the dubbed lines.
import json, subprocess, sys, wave, os
F="/home/agent/tools/ffmpeg/ffmpeg"; PY="/home/agent/tools/piper-venv/bin/python"; V="/home/agent/tools/piper-voices/"
src, script, bg, out = sys.argv[1:5]; LANG=(sys.argv[5] if len(sys.argv)>5 else "es")
# voices per language: speaker label -> (model, speaker id). Extend when a job needs more speakers.
VOICES={"es":{"A":("es_ES-sharvard-medium.onnx",1),"B":("es_ES-davefx-medium.onnx",0),"C":("es_ES-sharvard-medium.onnx",0)},
        "de":{"A":("de_DE-thorsten-medium.onnx",0),"B":("de_DE-kerstin-low.onnx",0)},
        "fr":{"A":("fr_FR-siwis-medium.onnx",0),"B":("fr_FR-upmc-medium.onnx",1),"C":("fr_FR-upmc-medium.onnx",0)},
        "it":{"A":("it_IT-paola-medium.onnx",0),"B":("it_IT-riccardo-x_low.onnx",0)}, "pt":{"A":("pt_BR-faber-medium.onnx",0),"B":("pt_BR-cadu-medium.onnx",0)}}
L=json.load(open(script)); voices=VOICES[LANG]
os.makedirs("tts",exist_ok=True); parts=[]; report=[]
def dur(p):
    with wave.open(p) as w: return w.getnframes()/w.getframerate()
for i,l in enumerate(L):
    # TODO: for >1 speaker in de/fr/it/pt download a 2nd voice (distinct voices required)
    model,spk=voices.get(l["spk"], voices["A"]); raw=f"tts/{i}.wav"
    subprocess.run([PY,"-m","piper","-m",V+model,"-s",str(spk),"-f",raw],input=l[LANG].encode(),check=True,capture_output=True)
    slot=(L[i+1]["start"] if i+1<len(L) else l["end"]+1.0)-l["start"]-0.05; d=dur(raw); tempo=max(1.0,d/slot)
    fit=f"tts/{i}_fit.wav"
    subprocess.run([F,"-v","error","-y","-i",raw,"-af",f"atempo={min(tempo,1.35):.3f}","-ar","24000","-ac","1",fit],check=True)
    nd=dur(fit); l["dub_start"]=l["start"]; l["dub_end"]=round(l["start"]+nd,2)
    report.append({"line":i,"tts_s":round(d,2),"slot_s":round(slot,2),"tempo":round(min(tempo,1.35),2),"overrun_s":round(max(0,nd-slot),2),"note":l.get("note","")})
    parts.append((fit,l["start"]))
inputs=[]; filt=[]
for k,(p,t) in enumerate(parts): inputs+=["-i",p]; filt.append(f"[{k+1}:a]adelay={int(t*1000)}:all=1[d{k}]")
n=len(parts); mix="".join(f"[d{k}]" for k in range(n))
cmd=[F,"-v","error","-y","-i",src]+inputs
if bg!="-": cmd+=["-i",bg]; filt.append(f"[{n+1}:a]volume=1.0[bg]"); mix+="[bg]"; n+=1
filt.append(f"{mix}amix=inputs={n}:normalize=0:duration=longest[a]")
subprocess.run(cmd+["-filter_complex",";".join(filt),"-map","0:v","-map","[a]","-c:v","copy","-c:a","aac","-shortest",out],check=True)
def ts(x): h=int(x//3600); m=int(x%3600//60); s=x%60; return f"{h:02}:{m:02}:{s:06.3f}".replace(".",",")
with open(out.rsplit(".",1)[0]+f".{LANG}.srt","w") as f:
    for i,l in enumerate(L): f.write(f"{i+1}\n{ts(l['dub_start'])} --> {ts(l['dub_end'])}\n{l[LANG]}\n\n")
json.dump(report,open(out.rsplit(".",1)[0]+".report.json","w"),indent=1); print(json.dumps(report))
