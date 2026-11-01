---
title: Sound
icon: lucide/music
---

# Sound

A canvas has a **speaker** that plays notes, chords, melodies and audio files,
and a **microphone** that hears how loud the room is. Everything is synthesized
as it plays, so a program makes music without a single sound file.

Sound needs the `audio` extra from
[Installation](installation.md#optional-extras). On a computer with no sound
device, `terminal.speaker.is_available` is `False` and playing raises an error
that says so. A program that must run everywhere checks `is_available` first, as
the first example below does; the others leave the check out to stay short.

## Notes and melodies

`speaker.play()` takes a note name such as `'C4'`, or **melody text**: notes
separated by spaces, where `:2` holds a note for two beats, `rest` is a silence
and `+` joins notes into a chord.

```python
import xnano

with xnano.open(height=1) as terminal:
    terminal.screen.write('♪ playing · q quit')
    if terminal.speaker.is_available:
        terminal.speaker.play('C4 E4 G4:2 rest C4+E4+G4:2', instrument='piano')
    terminal.run(stop_on='q')
```

`play()` returns at once, and the sound plays while the program goes on.

A [`Note`][xnano.Note] is the same thing as a value you keep: its pitch, how
many beats it lasts, and the instrument that plays it. A tuple of pitches is a
chord.

```python
import xnano

tap = xnano.Note('C5', beats=0.25, instrument='marimba')
chord = xnano.Note(('C4', 'E4', 'G4'), beats=2, instrument='electric_piano')
```

The instruments are `piano`, `electric_piano`, `organ`, `bell`, `marimba`,
`guitar`, `electric_guitar`, `pluck`, `bass`, `synth`, `pad` and `strings`; the
plain waves `sine`, `square`, `saw` and `triangle`; and the drums `kick`,
`snare`, `hihat`, `open_hat`, `clap`, `tom` and `cowbell`.

## Playing from keys

Notes are plain values, so a key hook can play one on every press. Here the
number keys play a scale, and space plays a chord:

```python
import xnano

scale = ['C4', 'D4', 'E4', 'G4', 'A4']
chord = xnano.Note(('C4', 'E4', 'G4'), beats=2, instrument='electric_piano')

with xnano.open(height=2) as terminal:
    terminal.screen.write('1-5 play a note · space a chord · q quit', dim=True)
    playing = terminal.screen.write('', foreground='cyan')

    @terminal.hook(on='key', keys=['1', '2', '3', '4', '5', 'space'])
    def play(context: xnano.Context):
        key = context.keyboard.key
        if key == 'space':
            context.speaker.play(chord)
            playing.text = '♪ C4 E4 G4'
        else:
            pitch = scale[int(key) - 1]
            context.speaker.play(xnano.Note(pitch, beats=0.5))
            playing.text = f'♪ {pitch}'

    terminal.run(stop_on='q')
```

## Tempo and beats

Beats are measured at the canvas's tempo: 120 beats per minute, unless you give
`bpm=` to `xnano.open()`. A hook with `on='beat'` runs on the beat, with
`every=` counted in beats, which makes a metronome a few lines long:

```python
import xnano

with xnano.open(height=1, bpm=90) as terminal:
    count = terminal.screen.write('')
    tick = xnano.Note('C6', beats=0.1, instrument='cowbell')
    beat = 0

    @terminal.hook(on='beat', every=1)
    def click(context: xnano.Context):
        global beat
        beat += 1
        count.text = '● ' * (beat % 4 or 4)
        context.speaker.play(tick)

    terminal.run(stop_on='q')
```

## Sound effects

Sound takes effects the way a placement does. `speaker.fx` adds one to
everything the speaker plays after it: `reverb`, `delay`, `distortion`,
`tremolo`, `bit_crush`, `low_pass` and `high_pass`.

```python
import xnano

with xnano.open(height=1) as terminal:
    terminal.screen.write('a bell in a large room · q quit')
    terminal.speaker.fx.reverb(room=0.9, mix=0.5)
    terminal.speaker.play('C5 G5 E5:2', instrument='bell')
    terminal.run(stop_on='q')
```

## Audio files

`xnano.load_audio()` reads WAV, MP3, FLAC, Ogg Vorbis and MP4 files, and the
speaker plays the result like a note.

```python
import xnano

chime = xnano.load_audio('chime.wav')

with xnano.open(height=1) as terminal:
    terminal.screen.write('space chime · q quit')

    @terminal.hook(on='key', keys='space')
    def ring(context: xnano.Context):
        context.speaker.play(chime)

    terminal.run(stop_on='q')
```

## The microphone

`terminal.microphone.level` is how loud the input is, from `0.0` to `1.0`. It's
an expression, like the clock, so it can drive a size directly. This meter grows
with your voice:

```python
import xnano

with xnano.open(height=2) as terminal:
    terminal.screen.write('speak into your microphone · q quit', dim=True)
    level = terminal.microphone.level
    terminal.screen.write('░' * 40, y=1, dim=True)
    terminal.screen.write(
        '█' * 40, x=0, y=1, width=level * 40 + 1, foreground='green', layer=1
    )
    terminal.run(stop_on='q')
```

The input device opens the first time the level is read. Without a microphone,
or without permission to record, the level stays at `0`.

## Sound in tests

A canvas from `xnano.new()` has no sound device: what it plays is recorded
instead, at the canvas's own time. `speaker.render()` hands it back as
[`Audio`][xnano.Audio], so a test can check what a program played without making
a sound.

```python
import xnano

with xnano.new(width=10, height=1) as canvas:
    canvas.speaker.play('C4 E4 G4', instrument='piano')
    canvas.clock.step(delta_seconds=2.0)
    recording = canvas.speaker.render()
    print(recording)
```

The [`xnano.audio`][xnano.audio] reference has the rest: melodies built in code,
how loud and where in the stereo field each sound plays, and the microphone's
history.
