\version "2.18.2"
\include "english.ly"

keyAndTime = { \key e \major  \time 4/4 }

%====================
% CHORDS
%====================

chordsIntro = \chordmode { b1*2 | }
chordsOutro = \chordmode { e1*2 | b2 a2 | e1 }
chordsVerse = \chordmode { e1*4 | a1*2 e1*2 | b1 a1 e1*2 }

allChords = {
    \chordsIntro  \repeat unfold 2 { \chordsVerse }
    \chordsOutro
}

chordsExtract = { \chordsIntro  \chordsVerse  \chordsOutro }
chordsScore   = { \chordsExtract }

%====================
% VOCALS
%====================

vocTransition = \relative c' { r4 b'8 as a g e d | }

vocVersePrefix = \relative c' {
    e2 r | r8 e e d e d b a |
    b2 r | r4 e8 d e g a g | a8 g4. r2 | r4 a8 g a e e d |
    e2 r | r1 | b'4. a2 g8 | a4. g4 d8 d e~ | e2 r |
}

vocIntro = { r1 \vocTransition }

vocVerse = { \vocVersePrefix \vocTransition }

vocals = { \vocIntro \vocVerse \vocVersePrefix R1*5 }

vocalsExtract = {
    \vocIntro
    \repeat volta 2 { \vocVersePrefix }
    \alternative {
	{ \vocTransition }{ R1 }
    }
    R1*4
}

vocalsScore = { \vocalsExtract }

%--------------------
% lyrics
%--------------------

vocalsLyricsBPrefix = \lyricmode {
    \set stanza = #"2. " Don't you know I'll go for
}

vocalsLyricsBSuffix = \lyricmode {
    good, be- cause you've ne- ver un- der- stood,
    that I'm bound to leave this quar- ter,
    walk a- long to no- ones home:
    go down to no- where in the end.
}

vocalsLyricsA = \lyricmode {
    \set stanza = #"1. "
    Fee- ling lone- ly now I'm gone,
    it seems so hard I'll stay a- lone,
    but that way I have to go now,
    down the road to no- where town:
    go down to no- where in the end.
    \vocalsLyricsBPrefix
}

vocalsLyricsB = \lyricmode {
    _ _ _ _ _ _ \vocalsLyricsBSuffix
}

vocalsLyrics = { \vocalsLyricsA \vocalsLyricsBSuffix }

%====================
% BASS
%====================

bsTonPhrase  = \relative c, { \repeat unfold 7 { e8  } fs8 }

bsSubDPhrase = \relative c, { \repeat unfold 7 { a'8 } gs8 }

bsDomPhrase  = \relative c, { \repeat unfold 7 { b'8 } cs8 }

bsDoubleTonPhrase = { \repeat percent 2 { \bsTonPhrase } }

bsOutroPhrase = \relative c, { b8 b b b gs a b a | e1 | }

bsIntro = { \repeat percent 2 { \bsDomPhrase } }

bsOutro = { \bsDoubleTonPhrase  \bsOutroPhrase }

bsVersePrefix = {
    \repeat percent 4 { \bsTonPhrase }
    \bsSubDPhrase \bsSubDPhrase \bsDoubleTonPhrase
    \bsDomPhrase \bsSubDPhrase \bsTonPhrase
}

bsVerse = { \bsVersePrefix \bsTonPhrase }

bass = { \bsIntro  \bsVerse \bsVerse  \bsOutro }

bassExtract = {
    \bsIntro
    \repeat volta 2 { \bsVersePrefix }
    \alternative {
	{\bsTonPhrase} {\bsTonPhrase}
    }
    \bsOutro
}

bassScore = { \bassExtract }

%====================
% BASS
%====================

gtrTonPhrase  = \relative c { e,8 b' fs' b, b' fs b, fs }

gtrSubDPhrase = \relative c { a8 e' b' e, e' b e, b }

gtrDomPhrase  = \relative c { b8 fs' cs' fs, fs' cs fs, cs }

gtrDoubleTonPhrase = { \repeat percent 2 { \gtrTonPhrase } }

gtrOutroPhrase = \relative c { b4 fs' a, e | <e b'>1 | }

gtrIntro = { \repeat percent 2 { \gtrDomPhrase } }

gtrOutro = { \gtrDoubleTonPhrase | \gtrOutroPhrase }

gtrVersePrefix = {
    \repeat percent 4 { \gtrTonPhrase }
    \gtrSubDPhrase  \gtrSubDPhrase  \gtrDoubleTonPhrase
    \gtrDomPhrase  \gtrSubDPhrase  \gtrTonPhrase
}

gtrVerse = { \gtrVersePrefix \gtrTonPhrase }

guitar = { \gtrIntro  \gtrVerse  \gtrVerse  \gtrOutro }

guitarExtract = {
    \gtrIntro
    \repeat volta 2 { \gtrVersePrefix }
    \alternative {
	{\gtrTonPhrase} {\gtrTonPhrase}
    }
    \gtrOutro
}

guitarScore = { \guitarExtract }

%====================
% DRUMS
%====================

drmPhrase = \drummode { <bd hhc>8 hhc <sn hhc> hhc }

drmOstinato = { \repeat unfold 2 { \drmPhrase } }

drmFill = \drummode { \drmPhrase tomh8 tommh toml tomfl }

drmIntro = { \drmOstinato  \drmFill }

drmOutro = \drummode { \repeat percent 6 { \drmPhrase } | <sn cymc>1 | }

drmVersePrefix = {
    \repeat percent 3 { \drmOstinato }  \drmFill
    \repeat percent 2 { \drmOstinato  \drmFill }
    \repeat percent 3 { \drmOstinato }
}

drmVerse = { \drmVersePrefix \drmFill }

myDrums = { \drmIntro  \drmVerse \drmVerse  \drmOutro }

myDrumsExtract = {
    \drmIntro
    \repeat volta 2 {\drmVersePrefix}
    \alternative {
	{\drmFill} {\drmFill}
    }
    \drmOutro
}

myDrumsScore = { \myDrumsExtract }
