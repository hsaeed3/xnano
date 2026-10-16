# xnano-audio

Synthesize, play and capture sound in Python without audio files or extra dependencies.

## Install

```bash
pip install xnano-audio
```

Or install it as an extra of the top-level `xnano` package, which exposes it as `xnano.audio` and adds `canvas.audio`, `canvas.play` and `canvas.bpm`:

```bash
pip install "xnano[audio]"
```

On Linux, playing on an audio device requires ALSA. Synthesis and rendering work without a device everywhere.

## Example

```python
from xnano_audio import render_note, TerminalAudioEffect

# Synthesize a bell with reverb, no device needed
ding = render_note('bell', 'C6', effects=[TerminalAudioEffect.reverb()])
assert ding.peak <= 0.98

# Build a melody on a beat timeline
from xnano_audio import TerminalMelody, TerminalTempoMap

melody = (
    TerminalMelody(tempo_map=TerminalTempoMap(100))
    .appended_note('C4')
    .appended_chord(['E4', 'G4'], duration_beats=2)
    .appended_rest(1)
)
sound = melody.render('piano')
```

## What it provides

- **Synthesis**: 20+ built-in instruments (piano, organ, guitar, synth, kick, snare, bells, etc.) rendered deterministically to raw samples
- **Effects**: reverb, delay, distortion, filters, tremolo and bit-crushing, composable and reusable
- **Melodies**: notes arranged on a beat timeline with tempo maps and time signatures
- **Playback**: play sounds and instruments on the default output device with sample-accurate timing
- **Capture**: read the level of the default input device (microphone)
- **No audio files**: every sound is computed on the fly

## Links

- **Repository**: https://github.com/hsaeed3/xnano
- **Documentation**: https://xnano.hammad.app
- **API reference**: https://xnano.hammad.app/api-reference/
- **License**: MIT
