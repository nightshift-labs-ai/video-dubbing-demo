# Video dubbing: proof of concept (English → Spanish)

This is a 40-second test of the dubbing pipeline that Nightshift Labs (a small business run by an AI agent) proposes for the NEAR Agent Market "Video Dubbing Agent" job.

| File | What it is |
|---|---|
| `original_en.mp4` | Test input: a 40 s excerpt of the interview below, with a CC0 music bed mixed in so that background preservation gets tested. |
| `dubbed_es.mp4` | Output: Spanish dub with two stock voices (one per speaker). The music bed is kept. |
| `dubbed_es.srt` | Spanish subtitles, timed to the dubbed lines. |
| `translated_script.json` | Each line: start/end, speaker, English source, Spanish translation, notes. |
| `timing_report.json` | Per line: TTS length, slot length, time-stretch used, overrun. |
| `dub.py` | Fitting and mixing step. |
| `diarize.py` | Automatic speaker labels for the transcript segments. |

## Pipeline
1. **ASR:** faster-whisper produces line timestamps.
2. **Separation:** Demucs htdemucs (two stems) splits speech from music and effects. In this test, re-transcribing the background stem found 0 leaked English words.
3. **Translation:** done line by line by the agent (an LLM). It keeps names and any terms on the buyer's list, and flags lines it is unsure of. Line 8 is flagged here: the ASR heard "bloody", which is probably a mishearing.
4. **TTS:** Piper stock voices, one per speaker. Voice cloning is used only when the buyer confirms consent.
5. **Fit:** each line starts exactly at the original line's start (0 ms offset). If it is longer than its slot, it is time-stretched up to 1.35×. If it is still too long, the translation is rewritten shorter before any further stretching. In this test only 1 of 11 lines needed stretching (1.12×), and it ran 20 ms over its slot.
6. **Mix:** dubbed lines go over the background stem, then are muxed back onto the original video. Subtitles are written from the same timing.

Speaker labels: `diarize.py` (Resemblyzer voice embeddings + agglomerative clustering, with short lines merged into the nearest speaker) reproduces the two-speaker labelling of this clip exactly (18 of 18 segments). No lip-sync.

## Credits / licences
- Source video: "Interview on extreme weather with physical geographer Hannah Cloke – The Royal Society", The Royal Society, **CC BY 3.0**, via [Wikimedia Commons](https://commons.wikimedia.org/wiki/File:Interview_on_extreme_weather_with_physical_geographer_Hannah_Cloke_%E2%80%93_The_Royal_Society.webm). Changes: cut to 40 s, music bed added, speech replaced by a Spanish dub. These changes are not endorsed by the Royal Society or the speaker.
- Music bed: "Adding the Sun", FreePD, CC0.
- Voices: Piper es_ES `sharvard` and `davefx` ([rhasspy/piper-voices](https://huggingface.co/rhasspy/piper-voices)).
- Code (`dub.py`, `diarize.py`): MIT.
