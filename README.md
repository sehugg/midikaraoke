MIDI Karaoke for OS X
=====================

Many MIDI files have built-in lyrics.
You can make them sing using OS X speech services!

Installation:

Type "make" to build the phoneme helper (you need Xcode Command-Line Tools
installed)

Usage:

    ./singit3.py <midi file> <flags>

This will parse the MIDI file, look for vocal tracks using keyword matching,
convert to phonemes, and output to speaker.

If the keyword match doesn't work (there's no track named "Melody" or
similar) then you can use the -m flag to explicity pass the melody track.

To output to AIFF files, pass the -o flag; they'll be created in the current
directory.
Then you can import the MIDI into
Garageband or whatever and drag the AIFF file(s) into a new track.

There are other flags, pass the -h flag to see help.

Enjoy!




