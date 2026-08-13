# MOSS voice samples

Place short clean reference voice samples here for MOSS-TTS-Nano voice cloning tests.

Requirements:
- 5-20 seconds
- wav or mp3
- one speaker
- no music
- no background noise
- no heavy reverb

Suggested names:
- moss_test_01.wav
- moss_test_02.wav
- moss_test_03.wav

The tester also reads samples from:

```text
G:/Projects/AI-YouTube/MOSS_TTS_Nano/assets/voice_samples/
```

Generated test audio is written to `<workspace>/outputs/tts_tests/moss_tts_test.wav`
(`src/tts_providers/moss_tts_provider.py`, via the path contract's `outputs_root` -
not a literal path). `outputs/` itself was retired 2026-08-13; this tester
recreates the directory on demand, and its output stays untracked.

Do not commit voice sample audio or generated wav/mp3 files.
