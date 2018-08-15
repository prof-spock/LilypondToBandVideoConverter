# LilypondToBandVideoConverter

## Introduction

The LilypondToBandVideoConverter is a system of several
python scripts that orchestrate existing command line tools
to convert a music piece written in the lilypond notation to

- a *PDF score* of the whole piece,

- several *PDF voice extracts*,

- a *MIDI file with all voices* (with some preprocessing
  applied for humanization),

- *audio mix files* with several subsets of voices (specified
  by configuration), and

- *video files* for several output devices visualizing the
  score notation pages and having the mixes as mutually
  selectable audio tracks as backing tracks.

For processing a piece one must have

- a *lilypond fragment file* with the score information
  containing specific lilypond identifiers, and

- a *configuration file* giving details like the voices
  occuring in the piece, their associated midi instrument,
  target audio volume, list of mutable voices for the audio
  tracks etc.

Based on those files the python scripts -- together with some
open-source command-line software like ffmpeg or fluidsynth -- produce
all the target files either incrementally or altogether.

## Installation and Requirements

All the scripts are written in python and can be installed as a python
package.  The package requires either Python&nbsp;2.7 or
Python&nbsp;3.3 or later.

Additionally the following software has to be available:

- *[lilypond][]*: for generating the score pdf, voice
   extract pdfs, the raw midi file and the score images used
   in the video files,

- *[ffmpeg][]*: for video generation and video
   postprocessing,

- *[fluidsynth][]*: for generation of voice audio files from
   a midi file,

- *[sox][]*: for instrument-specific postprocessing of audio
   files for the target mix files as well as the mixdown,
   and

Optionally the following software is also used:

- *[qaac][]*: the AAC-encoder for the final audio mix file
   compression.

- *[mp4box][]*: the MP4 container packaging software

The location of all those commands as well as a few other
settings has to be defined in a global configuration file
for the LilypondToBandVideoConverter.

Installation is done from the PyPi repository via

    pip install lilypondToBVC

## Further Information

The detailed manual is available [here].

[ffmpeg]: http://ffmpeg.org/
[fluidsynth]: http://www.fluidsynth.org/
[here]: lilypondToBandVideoConverter.pdf
[lilypond]: http://lilypond.org/
[lilypondFileSyntax]: http://tensi.eu/thomas
[mp4box]: https://gpac.wp.imt.fr/mp4box/mp4box-documentation/
[qaac]: https://sites.google.com/site/qaacpage/
[sox]: http://sox.sourceforge.net/
