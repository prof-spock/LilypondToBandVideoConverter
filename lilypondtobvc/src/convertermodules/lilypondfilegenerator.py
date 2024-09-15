# lilypondFileGenerator -- generates a lilypond main file for several
#                          parameters by inclusion of a structured lilypond
#                          file with tracks
#
# author: Dr. Thomas Tensi, 2006 - 2017

#====================
# IMPORTS
#====================

import re

from basemodules.simplelogging import Logging
from basemodules.simpletypes import Boolean, Integer, Map, Natural, \
                                    Object, Real, String, StringList, \
                                    StringMap, StringSet
from basemodules.ttbase import iif, iif2
from basemodules.utf8file import UTF8File

from .ltbvc_businesstypes import humanReadableVoiceName

#-------------------------
# configuration constants
#-------------------------

# lilypond articulation: use articulate.ly
lilypondArticulationIsUsed = False

indentationPerLevel = (" " * 4)

#-------------------------
# mappings for instruments
#-------------------------

# default assignment of voice names to midi instrument names
_lilypondInstrumentNameList = [
    "acoustic grand", "bright acoustic", "electric grand", "honky-tonk",
    "electric piano 1", "electric piano 2", "harpsichord", "clav",
    "celesta", "glockenspiel", "music box", "vibraphone",
    "marimba", "xylophone", "tubular bells", "dulcimer",
    "drawbar organ", "percussive organ", "rock organ", "church organ",
    "reed organ", "accordion", "harmonica", "concertina",
    "acoustic guitar (nylon)", "acoustic guitar (steel)",
        "electric guitar (jazz)", "electric guitar (clean)",
    "electric guitar (muted)", "overdriven guitar", "distorted guitar",
        "guitar harmonics",
    "acoustic bass", "electric bass (finger)", "electric bass (pick)",
        "fretless bass",
    "slap bass 1", "slap bass 2", "synth bass 1", "synth bass 2",
    "violin", "viola", "cello", "contrabass",
    "tremolo strings", "pizzicato strings", "orchestral harp", "timpani",
    "string ensemble 1", "string ensemble 2", "synthstrings 1",
        "synthstrings 2",
    "choir aahs", "voice oohs", "synth voice", "orchestra hit",
    "trumpet", "trombone", "tuba", "muted trumpet",
    "french horn", "brass section", "synthbrass 1", "synthbrass 2",
    "soprano sax", "alto sax", "tenor sax", "baritone sax",
    "oboe", "english horn", "bassoon", "clarinet",
    "piccolo", "flute", "recorder", "pan flute",
    "blown bottle", "shakuhachi", "whistle", "ocarina",
    "lead 1 (square)", "lead 2 (sawtooth)", "lead 3 (calliope)",
        "lead 4 (chiff)",
    "lead 5 (charang)", "lead 6 (voice)", "lead 7 (fifths)",
        "lead 8 (bass+lead)",
    "pad 1 (new age)", "pad 2 (warm)", "pad 3 (polysynth)", "pad 4 (choir)",
    "pad 5 (bowed)", "pad 6 (metallic)", "pad 7 (halo)", "pad 8 (sweep)",
    "fx 1 (rain)", "fx 2 (soundtrack)", "fx 3 (crystal)", "fx 4 (atmosphere)",
    "fx 5 (brightness)", "fx 6 (goblins)", "fx 7 (echoes)", "fx 8 (sci-fi)",
    "sitar", "banjo", "shamisen", "koto",
    "kalimba", "bagpipe", "fiddle", "shanai",
    "tinkle bell", "agogo", "steel drums", "woodblock",
    "taiko drum", "melodic tom", "synth drum", "reverse cymbal",
    "guitar fret noise", "breath noise", "seashore", "bird tweet",
    "telephone ring", "helicopter", "applause", "gunshot"
]

#--------------------

_lilypondDrumNameList = [
    "standard kit", "standard kit", "standard kit", "standard kit",
    "standard kit", "standard kit", "standard kit", "standard kit",
    "room kit", "room kit", "room kit", "room kit",
    "room kit", "room kit", "room kit", "room kit",
    "power kit", "power kit", "power kit", "power kit",
    "power kit", "power kit", "power kit", "power kit",
    "electronic kit", "tr-808 kit", "tr-808 kit", "tr-808 kit",
    "tr-808 kit", "tr-808 kit", "tr-808 kit", "tr-808 kit",
    "jazz kit", "jazz kit", "jazz kit", "jazz kit",
    "jazz kit", "jazz kit", "jazz kit", "jazz kit",
    "brush kit", "brush kit", "brush kit", "brush kit",
    "brush kit", "brush kit", "brush kit", "brush kit",
    "orchestra kit", "orchestra kit", "orchestra kit", "orchestra kit",
    "orchestra kit", "orchestra kit", "orchestra kit", "orchestra kit",
    "sfx kit", "sfx kit", "sfx kit", "sfx kit",
    "sfx kit", "sfx kit", "sfx kit", "sfx kit",
    "sfx kit", "sfx kit", "sfx kit", "sfx kit",
    "sfx kit", "sfx kit", "sfx kit", "sfx kit",
    "sfx kit", "sfx kit", "sfx kit", "sfx kit",
    "sfx kit", "sfx kit", "sfx kit", "sfx kit",
    "sfx kit", "sfx kit", "sfx kit", "sfx kit",
    "sfx kit", "sfx kit", "sfx kit", "sfx kit",
    "sfx kit", "sfx kit", "sfx kit", "sfx kit",
    "sfx kit", "sfx kit", "sfx kit", "sfx kit",
    "sfx kit", "sfx kit", "sfx kit", "sfx kit",
    "sfx kit", "sfx kit", "sfx kit", "sfx kit",
    "sfx kit", "sfx kit", "sfx kit", "sfx kit",
    "sfx kit", "sfx kit", "sfx kit", "sfx kit",
    "sfx kit", "sfx kit", "sfx kit", "sfx kit",
    "sfx kit", "sfx kit", "sfx kit", "sfx kit",
    "sfx kit", "sfx kit", "sfx kit", "mt-32 kit"
]

#--------------------
#--------------------

class _LilypondIncludeFile:
    """Represents the lilypond file to be included"""

    @classmethod
    def definedMacroNameSet (cls,
                             includeFileName : String) -> StringSet:
        """returns set of all defined macros in include file with
           <includeFileName>; does a very simple analysis and assumes
           that a definition line consists of the name and an equals
           sign"""

        Logging.trace(">>: %r", includeFileName)

        result = set()

        includeFile = UTF8File(includeFileName, "rt")
        lineList = includeFile.readlines()
        includeFile.close()

        definitionRegExp = re.compile(r" *([a-zA-Z]+) *=")

        for line in lineList:
            matchResult = definitionRegExp.match(line)

            if matchResult:
                macroName = matchResult.group(1)
                result.update([ macroName ])

        Logging.trace("<<: %r", result)
        return result

#--------------------
#--------------------

class LilypondFile:
    """Represents the lilypond file to be generated"""

    _ProcessingState_beforeInclusion = 0
    _ProcessingState_afterInclusion  = 1
    _indentationLevel = 0

    #--------------------
    # LOCAL FEATURES
    #--------------------

    def _addLyrics (self,
                    voiceName : String):
        """Adds all lyrics lines to current <voice>"""

        Logging.trace(">>: %s", voiceName)

        target = self._phase
        lyricsMacroNamePrefix = "%sLyrics%s" % (voiceName, target.capitalize())
        lyricsCount = self._lyricsCount(voiceName)
        suffixList = "ABCDEFGHIJK"

        if lyricsCount == 0 or lyricsCount > len(suffixList):
            Logging.trace("--: bad lyrics count: %d", lyricsCount)
            lyricsCount = 0

        for voiceIndex in range(1, lyricsCount + 1):
            suffix = suffixList[voiceIndex - 1]
            lyricsMacroName = lyricsMacroNamePrefix + suffix
            alternativeMacroNameList = [ lyricsMacroNamePrefix,
                                         voiceName + "Lyrics" + suffix ]

            if voiceIndex == 1:
                alternativeMacroNameList.append(voiceName + "Lyrics")

            self._ensureMacroAvailability(lyricsMacroName,
                                          alternativeMacroNameList)
            label = self._voiceToLabelMap[voiceName]
            Logging.trace("--: lyricsto %s -> %s", label, lyricsMacroName)
            st = ("\\new Lyrics \\lyricsto"
                  + " \"" + label + "\""
                  + " { \\" + lyricsMacroName + " }")
            self._printLine(0, st)

        Logging.trace("<<")

    #--------------------

    def _addLyricsVoiceIntro (self,
                              voiceName : String):
        """Adds a named voice definition line for a voice with lyrics
           (which can later be referenced by a lyrics line)"""

        Logging.trace(">>: voiceName = %s", voiceName)

        voiceLabelCount = len(self._voiceToLabelMap) + 1
        currentVoiceLabel = "song" + "ABCDEFGHIJKLMNOPQR"[voiceLabelCount - 1]
        self._voiceToLabelMap[voiceName] = currentVoiceLabel
        self._print(0, "\\new Voice = " + "\"" + currentVoiceLabel + "\" ")

        Logging.trace("<<: label = %s", currentVoiceLabel)

    #--------------------

    def _ensureMacroAvailability (self,
                                  macroName : String,
                                  alternativeMacroNameList : StringList):
        """Checks whether <macroName> is available in include file; if
           not, several alternatives are tried in
           <alternativeMacroNameList>"""

        Logging.trace(">>: macro = %r, alternativesList = %r",
                      macroName, alternativeMacroNameList)
        isFound = (macroName in self._includeFileMacroNameSet)
        ancestor = None

        if not isFound:
            for otherMacroName in iter(alternativeMacroNameList):
                if otherMacroName in self._includeFileMacroNameSet:
                    st = "%s = { \\%s }" % (macroName, otherMacroName)
                    self._printLine(0, st, False)
                    ancestor = otherMacroName
                    break

        Logging.trace("<<: isFound = %r, ancestor = %r",
                      isFound, ancestor)

    #--------------------

    @classmethod
    def _getPVEntry (cls,
                     currentMap : StringMap,
                     phase : String,
                     voiceName : String,
                     defaultValue : Object) -> Object:
        """Returns entry of two-level <currentMap> at <phase> and <voiceName>;
           if there is no such entry, <defaultValue> is returned"""

        embeddedMap = currentMap.get(phase, {})
        result = embeddedMap.get(voiceName, defaultValue)
        Logging.trace("--: voiceName = %s, phase = %s, result = %r,"
                      + " map = %r, embeddedMap = %r",
                      voiceName, phase, result, currentMap, embeddedMap)
        return result

    #--------------------

    @classmethod
    def _lilypondDurationCode (cls,
                               durationInQuarters : Real) -> StringList:
        """Returns a list of lilypond duration strings from a real
           number of quarters in <durationInQuarters>; e.g. 4.0
           quarters would be encoded as [ '1' ] (a single whole note)"""

        Logging.trace(">>: %s", durationInQuarters)

        epsilon = 0.01
        duration = durationInQuarters / 4.0
        referenceDurationList = ( 1.5, 1.0 )
        lilypondNoteNumber = 1
        result = []

        while duration > 0 and lilypondNoteNumber <= 64:
            for i in range(2):
                referenceDuration = \
                    referenceDurationList[i] / lilypondNoteNumber

                while duration >= referenceDuration:
                    result.append("%d%s"
                                  % (lilypondNoteNumber,
                                     iif(i == 0, ".", "")))
                    duration -= referenceDuration
                
            lilypondNoteNumber *= 2

        Logging.trace("<<: %s", result)
        return result

    #--------------------

    @classmethod
    def _lilypondVoiceName (cls,
                            voiceName : String,
                            drumsNameIsExpanded : Boolean = False):
        """Returns name of voice to be used within lilypond; if
           <drumsNameIsExpanded> is set, then a plain "drums" name is
           replaced by "myDrums" """

        Logging.trace(">>: voiceName= %s, drumsNameIsExpanded = %r",
                      voiceName, drumsNameIsExpanded)

        result = iif(voiceName == "drums" and drumsNameIsExpanded,
                     "myDrums", voiceName)
        result = result.replace("Simple", "").replace("Extended", "")

        Logging.trace("<<: %s", result)
        return result

    #--------------------

    def _lyricsCount (self,
                      voiceName : String) -> Natural:
        """Returns lyrics count for <voiceName> if any"""

        Logging.trace(">>: %s", voiceName)

        result = 0
        target = self._phase

        if voiceName in self._voiceNameToLyricsMap:
            entry = self._voiceNameToLyricsMap[voiceName]
            result = entry.get(target, 0)

        Logging.trace("<<: %d", result)
        return result

    #--------------------

    def _makeVoiceText (self,
                        voiceName : String,
                        voiceStaff : String) -> String:
        """Generates the string with lilypond commands for single
           <voice> with <voiceStaff>"""

        Logging.trace(">>: name = %s, staff = %r", voiceName, voiceStaff)

        cls = self.__class__
        isDrumVoice       = (voiceStaff == "DrumStaff")
        isTabulatureVoice = (voiceStaff == "TabStaff")
        drumsNameIsExpanded = (self._phase == "score")
        lilypondVoiceName = cls._lilypondVoiceName(voiceName,
                                                   drumsNameIsExpanded)
        voiceMacroName = lilypondVoiceName + self._phase.capitalize()
        plainLilypondVoiceName = cls._lilypondVoiceName(voiceName, True)
        alternativeMacroNameList = [ plainLilypondVoiceName ]
        self._ensureMacroAvailability(voiceMacroName,
                                      alternativeMacroNameList)

        voiceText = (iif(not self._isExtractScore, "",
                         "\\initialTempo \\compressEmptyMeasures ")
                     + "\\" + voiceMacroName)

        if self._isVideoScore:
            voiceText = "\\unfoldRepeats { \\keyAndTime %s }" % voiceText
        elif not self._isMidiScore:
            voiceText = "\\keyAndTime " + voiceText
        else:
            # for MIDI we add an empty count in for the normal tracks
            # and a drum count in to the drum track; also a suffix of
            # two measures is used for having a trailing reverb
            prefix = "\\unfoldRepeats { \\keyAndTime "
            suffix = "\\ppppp }}"

            if isDrumVoice:
                drumsPrefix  = prefix + "\\drumsCountIn "
                drumsSuffix = " s1 \\drummode { ss64" + suffix
                voiceText = drumsPrefix + voiceText + drumsSuffix
            else:
                normalPrefix = prefix + "\\countIn "
                normalSuffix = " s1 { c64" + suffix
                voiceText = normalPrefix + voiceText + normalSuffix

        clefString = cls._getPVEntry(self._phaseAndVoiceNameToClefMap,
                                     self._phase, voiceName, "G")
        clefString = iif(isTabulatureVoice, "", clefString)

        voiceText = (iif(clefString == "", "", "\\clef \"%s\"" % clefString)
                     + voiceText)

        Logging.trace("<<: %r", voiceText)
        return voiceText

    #--------------------

    def _print (self,
                relativeIndentationLevel : Integer,
                st : String,
                isBuffered : Boolean = True):
        """Writes <st> to current lilypond file <self>; if
           <isBuffered> is set, the line is not directly written, but
           buffered"""

        cls = self.__class__

        if relativeIndentationLevel < 0:
            cls._indentationLevel += relativeIndentationLevel

        if isBuffered:
            indentation = indentationPerLevel * cls._indentationLevel
            effectiveProcessingState = self._processingState
            template = "--: /%d/ =>%r"
        else:
            indentation = ""
            effectiveProcessingState = cls._ProcessingState_beforeInclusion
            template = "--: /%d/ <=%r"

        Logging.trace(template, effectiveProcessingState, st.strip("\n"))
        st = indentation + st
        self._processedTextBuffer[effectiveProcessingState].append(st)

        if relativeIndentationLevel > 0:
            cls._indentationLevel += relativeIndentationLevel

    #--------------------

    def _printEmptyLine (self):
        """Prints an empty line"""

        self._processedTextBuffer[self._processingState].append("\n")

    #--------------------

    def _printLine (self,
                    relativeIndentationLevel : Integer,
                    st : String,
                    isBuffered : Boolean = True):
        """Writes <st> to current lilypond file <self> terminated by a
           newline; if <isBuffered> is set, the line is not
           directly written, but buffered"""

        self._print(relativeIndentationLevel, st + "\n", isBuffered)

    #--------------------

    def _resetPrintIndentation (self):
        """Resets indentation for printing to 0"""

        cls = self.__class__
        cls._indentationLevel = 0

    #--------------------

    @classmethod
    def _tempoString (cls,
                      tempo : Real) -> String:
        """Returns tempo string for given <tempo> in bpm where tempo may be
           a float"""

        noteValue = 4
        tempoValue = tempo
        isDone = False

        while True:
            if noteValue >= 32 or tempoValue - int(tempoValue) < 0.001:
                break
            else:
                noteValue *= 2
                tempoValue *= 2
        
        result = "\\tempo %d=%d" % (noteValue, tempoValue)
        return result

    #--------------------

    def _writeChords (self,
                      voiceName : String):
        """Writes chords for voice with <voiceName> (if applicable)"""

        Logging.trace(">>: %s", voiceName)

        cls = self.__class__
        target = self._phase

        if voiceName in self._voiceNameToChordsMap:
            if target in self._voiceNameToChordsMap[voiceName]:
                lilypondVoiceName = cls._lilypondVoiceName(voiceName)
                lilypondVoiceName = (lilypondVoiceName[0].upper()
                                     + lilypondVoiceName[1:])
                chordsName = "chords" + lilypondVoiceName
                chordsMacroName = chordsName + target.capitalize()
                alternativeMacroNameList = [ chordsName,
                                             "chords" + target.capitalize(),
                                             "allChords" ]
                self._ensureMacroAvailability(chordsMacroName,
                                              alternativeMacroNameList)
                st = ("\\new ChordNames {"
                      + iif(self._isExtractScore,
                            " \\compressEmptyMeasures", "")
                      + " \\" + chordsMacroName + " }")

                self._printLine(0, st)

        Logging.trace("<<")

    #--------------------

    def _writeHeader (self):
        """Writes the header of a lilypond file also including the
           music-file to <self>"""

        Logging.trace(">>: lilypondFile = %r", self)

        cls = self.__class__

        self._printLine(0, "\\version \"%s\"" % self._lilypondVersion)

        # provide phase name as a lilypond macro
        self._printLine(0, "ltbvcProcessingPhase = \"%s\"" % self._phase)

        if self._isVideoScore:
            # provide video device name as a lilypond macro
            self._printLine(0, "ltbvcVideoDeviceName = \"%s\""
                            % self._videoDeviceName)

        # print initial tempo for all target files
        initialTempo = self._songMeasureToTempoMap[1][0]
        self._printLine(0,
                        ("initialTempo = { %s }"
                         % cls._tempoString(initialTempo)))

        if not self._targetIsPdf:
            self._writeNonPdfHeader()
            self._printEmptyLine()

        if not self._targetIsPdf and self._lilypondArticulationIsUsed:
            # add reference to articulation file
            self._printLine(0, "\\include \"articulate.ly\"")
            self._printEmptyLine()

        if self._targetIsPdf:
            self._writePdfLayoutHeader()
            self._printEmptyLine()

        # include the specific note stuff
        self._printLine(0, "% include note stuff")
        self._printLine(0, "\\include \"" + self._includeFileName + "\"")
        self._printEmptyLine()

        self._processingState = cls._ProcessingState_afterInclusion

        if self._isVideoScore:
            self._writeVideoSettings()
            self._printEmptyLine()

        Logging.trace("<<")

    #--------------------

    def _writeNonPdfHeader (self):
        """Writes the header of a lilypond file based on <self>
           targetting for a MIDI file or a video"""

        Logging.trace(">>: %r", self)

        cls = self.__class__
        
        # print default count-in definition (two measures, four beats)
        self._printLine(0, "countIn = { R1*2\\mf }")
        self._printLine(0, ("drumsCountIn = \\drummode"
                            + " { ss2\\mf ss | ss4 ss ss ss | }"))

        # print tempo track
        self._printLine(+1, "tempoTrack = {")
        measureList = list(self._songMeasureToTempoMap.keys())
        measureList.sort()
        previousMeasure = 0

        for measure in measureList:
            if measure == 1:
                self._printLine(0, "\\initialTempo")
            else:
                measureData = self._songMeasureToTempoMap[measure]
                tempo              = measureData[0]
                quartersPerMeasure = measureData[1]
                skipCount = measure - previousMeasure
                durationStringList = \
                    cls._lilypondDurationCode(quartersPerMeasure)

                for durationString in durationStringList:
                    self._printLine(0, ("\\skip %s*%d"
                                        % (durationString, skipCount)))

                self._printLine(0, "%%%d\n" % measure)
                self._printLine(0, cls._tempoString(tempo))

            previousMeasure = measure

        self._printLine(-1, "}")

        Logging.trace("<<")

    #--------------------

    def _writePdfLayoutHeader (self):
        """Writes all layout settings for a PDF output to <self>"""

        Logging.trace(">>: %r", self)

        self._printLine(0, "%===================")
        self._printLine(0, "%= GLOBAL SETTINGS =")
        self._printLine(0, "%===================")
        self._printEmptyLine()
        self._printLine(+1, "\\header {")
        self._printLine(0, "title = \"" + self._title + "\"")
        self._printLine(0, "composer = \"%s\"" % self._composerText)
        self._printLine(0, "tagline = ##f")
        self._printLine(-1, "}")
        self._printEmptyLine()

        Logging.trace("<<")

    #--------------------

    def _writeSingleVoiceStaff (self,
                                voiceName : String,
                                extension : String,
                                voiceStaff : String,
                                isSimpleStaff : Boolean):
        """Writes voice data for voice with <voiceName> and <extension> with
           <voiceStaff>; <isSimpleStaff> tells whether this is the
           only staff for the instrument"""

        Logging.trace(">>: file = %r, voiceName = %s, extension = %s,"
                      + " voiceStaff = %s, isSimpleStaff = %r",
                      self, voiceName, extension, voiceStaff, isSimpleStaff)

        isLyricsVoice     = (self._lyricsCount(voiceName) > 0)
        isDrumVoice       = (voiceStaff == "DrumStaff")
        isTabulatureVoice = (voiceStaff == "TabStaff")

        effectiveVoiceName = voiceName + extension

        introText = ("\\new " + voiceStaff
                     + iif(not self._isMidiScore, "",
                           " = %s" % effectiveVoiceName))

        if not self._isMidiScore:
            midiInstrumentPart = ""
        else:
            # get the instrument
            midiInstrumentNumber = \
                self._midiVoiceNameToInstrumentMap.get(voiceName, 0)

            if isDrumVoice:
                voiceInstrument = \
                    _lilypondDrumNameList[midiInstrumentNumber]
            else:
                voiceInstrument = \
                    _lilypondInstrumentNameList[midiInstrumentNumber]

            midiInstrumentPart = (" midiInstrument = \"%s\""
                                  % voiceInstrument)

        withPart = (iif(isDrumVoice, "",
                        "\\consists \"Instrument_name_engraver\"")
                    + midiInstrumentPart)
        withPart = withPart.strip()
        withPart = iif(withPart == "", "", " \\with { " + withPart + " }")

        self._printLine(+1, introText + withPart + " {")

        if isSimpleStaff and not (self._isExtractScore or self._isVideoScore):
            self._writeVoiceStaffInstrumentSettings(voiceName, voiceStaff)

        voiceText = self._makeVoiceText(effectiveVoiceName, voiceStaff)

        if isDrumVoice or isTabulatureVoice:
            self._printLine(0, voiceText)
        else:
            if isLyricsVoice:
                self._addLyricsVoiceIntro(effectiveVoiceName)
            else:
                self._print(0, "\\new Voice")

            self._printLine(+1, " \\with {")
            self._printLine(0, "\\consists \"Pitch_squash_engraver\" }{")
            self._printLine(0, voiceText)
            self._printLine(-1, "}")

        self._printLine(-1, "}")

        if isLyricsVoice:
            self._addLyrics(effectiveVoiceName)

        Logging.trace("<<")

    #--------------------

    def _writeScore (self):
        """Puts out score depending on <self._phase>"""

        Logging.trace(">>: %r", self)

        voiceName = self._voiceNameList[0]
        relevantVoiceNameList = iif(self._isExtractScore, [ voiceName ],
                                    self._voiceNameList)
        self._printEmptyLine()

        if self._isExtractScore:
            # make heading
            self._printLine(0, "\\header { subtitle = \"("
                            + humanReadableVoiceName(voiceName) + ")\" }")
            self._printEmptyLine()

        self._printLine(+1,  "\\score {")
        self._printLine(+1, "<<")

        if self._isMidiScore:
            self._printLine(0, "{ \\initialTempo \\countIn \\tempoTrack }")

        for voiceName in relevantVoiceNameList:
            self._writeVoice(voiceName)

        self._printLine(-1, ">>")

        # make score footing
        if self._isMidiScore:
            self._printLine(0, "\\midi {")
            # move dynamic performer to staff context for correct
            # output of embedded voices
            template = "\\context { \\%s \\%s \"Dynamic_performer\" }"
            self._printLine(+1, template % ("Staff", "consists"))
            self._printLine(0,  template % ("Voice", "remove  "))
            self._printLine(-1, "}")
        elif not self._isVideoScore:
            self._printLine(0, "\\layout {}")
        else:
            # HACK: for video score mark bar numbers and bar lines
            # with special colors for later data scraping in
            # postscript file
            self._printLine(+1, "\\layout {")
            st = "\\override Score.BarNumber.break-visibility = ##(#f #f #t)"
            self._printLine(0, st)
            st = "\\override %s.color = #(rgb-color %s)"
            self._printLine(0,  st % ("Score.BarNumber", ".001 .002 .003"))
            self._printLine(0,  st % ("Staff.BarLine",   ".003 .002 .001"))
            self._printLine(-1, "}")

        self._printLine(-1, "}")

        Logging.trace("<<")

    #--------------------

    def _writeVideoSettings (self):
        """Puts out the paper, resolution and system size definitions
           for the video file to be generated"""

        Logging.trace(">>")

        self._printLine(0, "% -- define the resolution in pixels per inch")
        self._printLine(0, "#(ly:set-option 'resolution %d)"
                        % self._videoResolution)
        self._printEmptyLine()
        self._printLine(0,
                        "#(set-global-staff-size %d)" % self._videoSystemSize)
        self._printLine(+1, "\\paper {")
        self._printLine(0, "% -- remove all markup --")

        lilypondParameterList = \
            ("print-page-number", "print-first-page-number",
             "evenFooterMarkup", "oddFooterMarkup",
             "evenHeaderMarkup", "oddHeaderMarkup", "bookTitleMarkup",
             "scoreTitleMarkup", "ragged-last-bottom")

        for parameter in lilypondParameterList:
            self._printLine(0, "%s=##f" % parameter)

        self._printLine(0, "% define the page sizes")
        margin = "%6.3f" % self._videoTopBottomMargin
        self._printLine(0, "top-margin    = %s" % margin)
        self._printLine(0, "bottom-margin = %s" % margin)
        self._printLine(0, "paper-width   = %6.2f" % self._videoPaperWidth)
        self._printLine(0, "paper-height  = %6.2f" % self._videoPaperHeight)
        self._printLine(0, "line-width    = %6.2f" % self._videoLineWidth)
        self._printLine(-1, "}")

        # HACK: add a stencil function for colouring the bar numbers
        # in a special (almost black) colour such that later scraping
        # of postscipt file reveals the bar numbers
        self._printEmptyLine()
        self._printLine(+1, "#(define (markGrobInvisibly grob)")
        self._printLine(+1, "(ly:stencil-in-color")
        self._printLine(0,  "(ly:text-interface::print grob) .001 .002 .003")
        self._printLine(-1, ")")
        self._printLine(-1, ")")

        Logging.trace("<<")

    #--------------------

    def _writeVoice (self,
                     voiceName : String):
        """Puts out the score part for <voiceName>"""

        Logging.trace(">>: %s", voiceName)

        cls = self.__class__
        voiceStaffList = cls._getPVEntry(self._phaseAndVoiceNameToStaffListMap,
                                         self._phase, voiceName, [ "Staff" ])
        voiceStaffCount = len(voiceStaffList)

        if not self._isMidiScore:
            self._writeChords(voiceName)

        extensionList = iif2(voiceStaffCount == 1, [ "" ],
                             voiceStaffCount == 2, [ "Top", "Bottom" ],
                             [ "Top", "Middle", "Bottom" ])

        if voiceStaffCount > 1:
            voiceStaff = "GrandStaff"
            self._printLine(+1, "\\new %s <<" % voiceStaff)
            self._writeVoiceStaffInstrumentSettings(voiceName, voiceStaff)

        for i, voiceStaff in enumerate(voiceStaffList):
            extension = extensionList[i]
            self._writeSingleVoiceStaff(voiceName, extension, voiceStaff,
                                        voiceStaffCount == 1)

        if voiceStaffCount > 1:
            self._printLine(-1, ">>")

        Logging.trace("<<")

    #--------------------

    def _writeVoiceStaffInstrumentSettings (self,
                                            voiceName : String,
                                            voiceStaff : String):
        """Writes the instrument name setting commands for given
           <voiceName> with staff <voiceStaff>"""

        Logging.trace(">>: name = %s, staff = %s", voiceName, voiceStaff)

        if not self._isExtractScore:
            voiceStaffInstrument = \
                self._voiceNameToScoreNameMap.get(voiceName, voiceName)
            staffInstrumentSetting = " = #\"" + voiceStaffInstrument + "\""
            prefix = "\\set " + voiceStaff + "."
            suffix = "nstrumentName" + staffInstrumentSetting
            staffInstrumentSettingA = prefix + "i" + suffix
            staffInstrumentSettingB = prefix + "shortI" + suffix

            self._printLine(0, staffInstrumentSettingA)
            self._printLine(0, staffInstrumentSettingB)

        Logging.trace("<<")

    #--------------------
    # EXPORTED FEATURES
    #--------------------

    def __init__ (self,
                  fileName : String):
        """Initializes lilypond file named <fileName>"""

        Logging.trace(">>: %r", fileName)

        cls = self.__class__

        self._composerText                = ""
        self._file                        = UTF8File(fileName, "wt")
        self._includeFileMacroNameSet     = set()
        self._includeFileName             = ""
        self._isFirstChordedSystem        = False
        self._lilypondArticulationIsUsed  = lilypondArticulationIsUsed
        self._lilypondVersion             = "???"
        self._phase                       = ""
        self._phaseAndVoiceNameToClefMap  = {}
        self._phaseAndVoiceNameToStaffListMap = {}
        self._processedTextBuffer         = [ [], [] ]
        self._processingState             = cls._ProcessingState_beforeInclusion
        self._songMeasureToTempoMap       = {}
        self._title                       = ""
        self._voiceNameList               = []
        self._voiceNameToChordsMap        = {}
        self._voiceNameToLyricsMap        = {}
        self._voiceNameToScoreNameMap     = {}
        self._voiceToLabelMap             = {}

        # video parameters (set to arbitrary values)
        self._videoDeviceName      = ""
        self._videoResolution      = 100
        self._videoTopBottomMargin = 5
        self._videoSystemSize      = 25
        self._videoPaperWidth      = 10
        self._videoPaperHeight     = 10
        self._videoLineWidth       = 8

        # derived data
        self._targetIsPdf                 = False
        self._isExtractScore              = False
        self._isMidiScore                 = False
        self._isVideoScore                = False

        Logging.trace("<<: %r", self)

    #--------------------

    def __repr__ (self) -> String:
        st = (("LilypondFile(phase = %r, title = %r, composerText = %r,"
               + " includeFileName = %r, lilypondVersion = %s,"
               + " voiceNameList = %r, voiceNameToChordsMap = %r,"
               + " voiceNameToLyricsMap = %r, songMeasureToTempoMap = %r,"
               + " videoResolution = %r, videoSystemSize = %r,"
               + " videoTopBottomMargin = %r, videoPaperWidth = %r,"
               + " videoPaperHeight = %r, videoLineWidth = %r)")
              % (self._phase, self._title, self._composerText,
                 self._includeFileName, self._lilypondVersion,
                 self._voiceNameList, self._voiceNameToChordsMap,
                 self._voiceNameToLyricsMap, self._songMeasureToTempoMap,
                 self._videoResolution, self._videoSystemSize,
                 self._videoTopBottomMargin, self._videoPaperWidth,
                 self._videoPaperHeight, self._videoLineWidth))

        return st

    #--------------------

    def close (self):
        """finalizes lilypond file"""

        Logging.trace(">>: %r", self)
        cls = self.__class__

        # write all buffers
        stateList = [cls._ProcessingState_beforeInclusion,
                     cls._ProcessingState_afterInclusion]
        for processingState in stateList:
            for line in self._processedTextBuffer[processingState]:
                self._file.write(line)

        self._file.close()
        Logging.trace("<<")

    #--------------------

    def generate (self,
                  includeFileName : String,
                  lilypondVersion : String,
                  phase : String,
                  voiceNameList : StringList,
                  title : String,
                  composerText : String,
                  voiceNameToChordsMap : StringMap,
                  voiceNameToLyricsMap : StringMap,
                  voiceNameToScoreNameMap : StringMap,
                  measureToTempoMap : Map,
                  phaseAndVoiceNameToClefMap : StringMap,
                  phaseAndVoiceNameToStaffListMap : StringMap):
        """Sets parameters for generation and starts generation based
           on phase."""

        Logging.trace(">>: includeFileName = %r, lilypondVersion = %s,"
                      + " phase = %s, voiceNameList = %r,"
                      + " title = %r, composerText = %r,"
                      + " voiceNameToChordsMap = %r,"
                      + " voiceNameToLyricsMap = %r,"
                      + " voiceNameToScoreNameMap = %r,"
                      + " measureToTempoMap = %r,"
                      + " phaseAndVoiceNameToClefMap = %r,"
                      + " phaseAndVoiceNameToStaffListMap = %r",
                      includeFileName, lilypondVersion, phase,
                      voiceNameList, title, composerText,
                      voiceNameToChordsMap, voiceNameToLyricsMap,
                      voiceNameToScoreNameMap, measureToTempoMap,
                      phaseAndVoiceNameToClefMap,
                      phaseAndVoiceNameToStaffListMap)

        self._includeFileName                 = includeFileName
        self._lilypondVersion                 = lilypondVersion
        self._phase                           = phase
        self._title                           = title
        self._composerText                    = composerText
        self._voiceNameList                   = voiceNameList
        self._voiceNameToChordsMap            = voiceNameToChordsMap
        self._voiceNameToLyricsMap            = voiceNameToLyricsMap
        self._voiceNameToScoreNameMap         = voiceNameToScoreNameMap
        self._phaseAndVoiceNameToClefMap      = phaseAndVoiceNameToClefMap
        self._phaseAndVoiceNameToStaffListMap = \
            phaseAndVoiceNameToStaffListMap

        self._songMeasureToTempoMap           = measureToTempoMap

        self._voiceToLabelMap                 = {}
        self._isFirstChordedSystem            = True

        # derived data
        self._targetIsPdf    = (phase in ["extract", "score"])
        self._isExtractScore = (phase == "extract")
        self._isMidiScore    = (phase == "midi")
        self._isVideoScore   = (phase == "video")

        self._includeFileMacroNameSet = \
            _LilypondIncludeFile.definedMacroNameSet(includeFileName)

        Logging.trace("--: %r", self)

        self._resetPrintIndentation()
        self._writeHeader()
        self._writeScore()
        self.close()

        Logging.trace("<<")

    #--------------------

    def setMidiParameters (self,
                           voiceNameToMidiInstrumentMap : StringMap,
                           voiceNameToMidiVolumeMap : StringMap,
                           voiceNameToMidiPanMap : StringMap):
        """Sets all parameters needed for subsequent midi file generation"""

        Logging.trace(">>: voiceNameToMidiInstrumentMap = %r,"
                      + " voiceNameToMidiVolumeMap = %r,"
                      + " voiceNameToMidiPanMap = %r",
                      voiceNameToMidiInstrumentMap,
                      voiceNameToMidiVolumeMap,
                      voiceNameToMidiPanMap)

        self._midiVoiceNameToInstrumentMap = voiceNameToMidiInstrumentMap
        self._midiVoiceNameToVolumeMap     = voiceNameToMidiVolumeMap
        self._midiVoiceNameToPanMap        = voiceNameToMidiPanMap

        Logging.trace("<<")

    #--------------------

    def setVideoParameters (self,
                            deviceName : String,
                            videoResolution : Natural,
                            systemSize : Natural,
                            topBottomMargin : Real,
                            paperWidth : Real,
                            paperHeight : Real,
                            lineWidth : Real):
        """Sets all parameters needed for subsequent video generation"""

        Logging.trace(">>: deviceName = %r, scalingFactor = %d,"
                      + " systemSize = %d,"
                      + " topBottomMargin = %4.2f, paperWidth = %5.2f,"
                      + " paperHeight = %5.2f, lineWidth = %5.2f",
                      deviceName, videoResolution, systemSize,
                      topBottomMargin, paperWidth, paperHeight, lineWidth)

        self._videoDeviceName      = deviceName
        self._videoResolution      = videoResolution
        self._videoSystemSize      = systemSize
        self._videoTopBottomMargin = topBottomMargin
        self._videoPaperWidth      = paperWidth
        self._videoPaperHeight     = paperHeight
        self._videoLineWidth       = lineWidth

        Logging.trace("<<")
