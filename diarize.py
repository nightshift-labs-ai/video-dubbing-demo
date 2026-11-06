# Speaker labels for whisper segments: resemblyzer d-vectors per segment → agglomerative clustering (cosine, distance threshold).
# usage: demucs-venv/bin/python diarize.py <vocals_or_src.wav> <segments.json> [threshold=0.35] → prints segments with "spk": A/B/C...
import json, sys, numpy as np
from resemblyzer import VoiceEncoder, preprocess_wav
from sklearn.cluster import AgglomerativeClustering
import soundfile as sf
wav_path, seg_path = sys.argv[1], sys.argv[2]; thr = float(sys.argv[3]) if len(sys.argv) > 3 else 0.35
audio, sr = sf.read(wav_path); audio = audio.mean(1) if audio.ndim > 1 else audio
S = json.load(open(seg_path)); enc = VoiceEncoder("cpu"); E = []; ok = []
for i, s in enumerate(S):
    a = audio[int(s["start"] * sr):int(s["end"] * sr)]
    w = preprocess_wav(a.astype(np.float32), source_sr=sr)
    if len(w) < 16000 * 0.6: ok.append(False); E.append(None); continue   # too short → inherit neighbour label
    E.append(enc.embed_utterance(w)); ok.append(True)
X = np.array([e for e in E if e is not None])
lab = AgglomerativeClustering(n_clusters=None, distance_threshold=thr, metric="cosine", linkage="average").fit_predict(X) if len(X) > 1 else [0] * len(X)
# singleton clusters from short lines (<1.5 s) are unreliable → move them to the nearest other cluster centroid
lab = np.array(lab); idx = [i for i, k in enumerate(ok) if k]
for c in set(lab.tolist()):
    m = np.where(lab == c)[0]
    if len(m) == 1 and len(set(lab.tolist())) > 1:
        seg = S[idx[m[0]]]
        if seg["end"] - seg["start"] < 1.5:
            cents = {d: X[lab == d].mean(0) for d in set(lab.tolist()) if d != c}
            lab[m[0]] = max(cents, key=lambda d: float(np.dot(X[m[0]], cents[d]) / np.linalg.norm(cents[d])))
# clusters made only of short lines (median < 1.5 s) are usually fragments of a real speaker → merge into the nearest big cluster
for c in sorted(set(lab.tolist()), key=lambda d: int((lab == d).sum())):   # smallest first; never merge below 2 speakers
    m = np.where(lab == c)[0]; others = [d for d in set(lab.tolist()) if d != c]
    if len(others) < 2 and len(set(lab.tolist())) <= 2: break
    if not others: break
    durs = [S[idx[k]]["end"] - S[idx[k]]["start"] for k in m]
    if np.median(durs) < 1.5:
        cent = X[m].mean(0); cents = {d: X[lab == d].mean(0) for d in others}
        lab[m] = max(cents, key=lambda d: float(np.dot(cent, cents[d]) / (np.linalg.norm(cents[d]) * np.linalg.norm(cent))))
lab = lab.tolist()
# relabel by first appearance → A, B, C
order = {}; it = iter(lab); L = []
for k in ok: L.append(next(it) if k else None)
for i in range(len(L)):
    if L[i] is None: L[i] = L[i - 1] if i and L[i - 1] is not None else next((x for x in L[i:] if x is not None), 0)
for i, s in enumerate(S):
    order.setdefault(L[i], "ABCDEFGH"[len(order)]); s["spk"] = order[L[i]]
print(json.dumps(S, indent=1, ensure_ascii=False))
