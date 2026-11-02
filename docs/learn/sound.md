---
title: Sound
icon: lucide/music
---

# Sound

A canvas has a **speaker** and a **microphone**. The speaker plays notes,
chords, melodies and audio files. The microphone measures how loud the sound
around the computer is. xnano makes the sound of notes, chords and melodies
while they play. Thus, a program can play music without sound files.

To use sound, you need the `audio` extra. See
[Installation](installation.md#optional-extras). On a computer without a sound
device, `terminal.speaker.is_available` is `False`. If a program plays a sound
on such a computer, xnano raises an error. If your program must run on all
computers, check `is_available` before you play a sound. The first example does
this check. The other examples do not, so that they stay short.

## Notes and melodies

`speaker.play()` takes a note name, for example `'C4'`. It also takes **melody
text**, which is a list of notes with spaces between them:

- `:2` after a note holds the note for two beats.
- `rest` is a silence.
- `+` between notes plays them together as a chord.

```python
import xnano

with xnano.open(height=1) as terminal:
    terminal.screen.write('♪ playing · q quit')
    if terminal.speaker.is_available:
        terminal.speaker.play('C4 E4 G4:2 rest C4+E4+G4:2', instrument='piano')
    terminal.run(stop_on='q')
```

`play()` returns immediately. The sound plays while the program continues.

A [`Note`][xnano.Note] keeps a note as a value. It holds the pitch, the number of
beats and the instrument that plays the note. To make a chord, give a tuple of
pitches.

```python
import xnano

tap = xnano.Note('C5', beats=0.25, instrument='marimba')
chord = xnano.Note(('C4', 'E4', 'G4'), beats=2, instrument='electric_piano')
```

The `instrument` argument takes one of these names:

- **Instruments**: `piano`, `electric_piano`, `organ`, `bell`, `marimba`,
  `guitar`, `electric_guitar`, `pluck`, `bass`, `synth`, `pad` and `strings`
- **Waves**: `sine`, `square`, `saw` and `triangle`
- **Drums**: `kick`, `snare`, `hihat`, `open_hat`, `clap`, `tom` and `cowbell`

## Play notes from keys

A note is a value, so a key hook can play a note on each key press. In this
example, the number keys play a scale, and the space key plays a chord:

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

xnano measures beats at the tempo of the canvas. The default tempo is 120 beats
per minute. To change it, give `bpm=` to `xnano.open()`. A hook with `on='beat'`
runs on the beat, and its `every=` value is a number of beats. Thus, a metronome
needs only a few lines:

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

The speaker takes effects, as a placement does. When you add an effect to
`speaker.fx`, the effect changes all the sound that the speaker plays after that.
The effects are `reverb`, `delay`, `distortion`, `tremolo`, `bit_crush`,
`low_pass` and `high_pass`.

```python
import xnano

with xnano.open(height=1) as terminal:
    terminal.screen.write('a bell in a large room · q quit')
    terminal.speaker.fx.reverb(room=0.9, mix=0.5)
    terminal.speaker.play('C5 G5 E5:2', instrument='bell')
    terminal.run(stop_on='q')
```

## Audio files

`xnano.load_audio()` reads WAV, MP3, FLAC, Ogg Vorbis and MP4 files. The speaker
plays the result in the same way as a note.

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

`terminal.microphone.level` is the loudness of the input, from `0.0` to `1.0`.
It is an expression, as the clock is. Thus, it can set a size directly. This
meter becomes longer when you speak:

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

xnano opens the input device the first time that a program reads the level. If
there is no microphone, or if the program has no permission to record, the level
stays at `0`.

## Sound in tests

A canvas from `xnano.new()` has no sound device. Instead, the canvas records the
sound that it plays, on its own clock. `speaker.render()` returns the recording
as [`Audio`][xnano.Audio]. Thus, a test can examine the sound that a program
played, and no sound comes out of the speakers.

```python
import xnano

with xnano.new(width=10, height=1) as canvas:
    canvas.speaker.play('C4 E4 G4', instrument='piano')
    canvas.clock.step(delta_seconds=2.0)
    recording = canvas.speaker.render()
    print(recording)
```

The [`xnano.audio`][xnano.audio] reference gives more information:

- melodies that you make in code
- the volume of each sound, and its position between the left and right speakers
- the history of the microphone level
