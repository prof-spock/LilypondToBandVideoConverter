# -*- coding: utf-8-unix -*-
# lilypondFileGenerator -- generates a lilypond main file for several
#                          parameters by inclusion of a structured lilypond
#                          file with tracks
#
#   includeFileName:              name of include file with music
#   phase:                        tells whether a voice extract, a full score
#                                 a video or a midi should be produced
#   title:                        song full title (only required for score and
#                                 voice output)
#   year:                         year of arrangement (only required for score
#                                 and voice output)
#   voice:                        voice name (for generating an extract file)
#   voices:                       slash separated list of voice names in
#                                 arrangement (for midi, score or video,
#                                 optional)
#   voiceNameToChordsMap:         map from voice name to chord target
#   voiceNameToLyricsMap:         map from voice name to lyrics target
#                                 and count of lyrics lines
#   orientation:                  information for video whether it should be
#                                 in landscape (h) or portrait (v) format 
#   deviceId:                     information for video whether it should be
#                                 for iPad (i), lumia (l) or internet (n)
#                                 target device
#
# It is assumed that the include file has the following names defined:
#    voices:        "bass", "myDrums" (as "drums" is a reserved identifier),
#                   "guitar", "keyboardTop", "keyboardBottom", "vocals"
#                   (unless the voices parameter is set)
#    chord list:    "chordsXXX" where XXX is the capitalised
#                   voice name (chords are defined for voice names in
#                   voiceNameToChordsMap)
#    tempo list:    "tempoTrack" (only necessary when phase = "midi")
#    lyrics lines:  they are labelled "vocLyricsA", "vocLyricsB", ...
#                   or "bgVocLyricsA", "bgVocLyricsB", ...
#-----------------------

###########
# IMPORTS #
###########

import argparse
import re
import sys

from ltbvc_businesstypes import canonicalVoiceName
from simplelogging import Logging
from ttbase import iif, iif2, iif3
from utf8file import UTF8File

#-------------------------
# configuration constants
#-------------------------

songMeasureToTempoMap = None

# lilypond articulation: use articulate.ly
# tabulature tag: name of tabulature tag (data is removed from standard
#                 guitar staff)

tabulatureTag = "tabulature"
lilypondArticulationIsUsed = False

#-------------------------
# mappings for instruments
#-------------------------

# default assignment of voice names to midi instrument names
voiceNameToMidiNameMap = { "bass"           : "electric bass (pick)",
                           "bgVocals"       : "synth voice",
                           "drums"          : "power kit",
                           "guitar"         : "overdriven guitar",
                           "keyboard"       : "rock organ",
                           "keyboardSimple" : "rock organ",
                           "organ"          : "rock organ",
                           "percussion"     : "power kit",
                           "vocals"         : "synth voice" }

#--------------------
#--------------------

class _LilypondIncludeFile:
    """represents the lilypond file to be included"""

    @classmethod
    def definedMacroNameSet (cls, includeFileName):
        """returns set of all defined macros in include file with
           <includeFileName>; does a very simple analysis and assumes
           that a definition line consists of the name and an equals
           sign"""

        Logging.trace(">>: %s", includeFileName)

        result = set()
        includeFile = open(includeFileName, "r")
        lineList = includeFile.readlines()
        definitionRegExp = re.compile(r" *([a-zA-Z]+) *=")

        for line in lineList:
            matchResult = definitionRegExp.match(line)

            if matchResult:
                macroName = matchResult.group(1)
                result.update([ macroName ])

        Logging.trace("<<: %s", result)
        return result

#--------------------
#--------------------

class LilypondFile:
    """represents the lilypond file to be generated"""

    _ProcessingState_beforeInclusion = 0
    _ProcessingState_afterInclusion  = 1

    #--------------------
    # LOCAL FEATURES
    #--------------------

    def _addLyrics (self, voiceName):
        """adds all lyrics lines to current <voice>"""

        Logging.trace(">>: '%s'", voiceName)

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
            self._printLine("    \\new Lyrics \\lyricsto"
                            + " \"" + label + "\""
                            + " { \\" + lyricsMacroName + " }")

        Logging.trace("<<")

    #--------------------

    def _addLyricsVoiceIntro (self, voiceName, indentationPrefix):
        """adds a named voice definition line for a voice with lyrics
           (which can later be referenced by a lyrics line)"""

        Logging.trace(">>: voiceName = '%s'", voiceName)

        voiceLabelCount = len(self._voiceToLabelMap) + 1
        currentVoiceLabel = "song" + "ABCDEFGHIJKLMNOPQR"[voiceLabelCount - 1]
        self._voiceToLabelMap[voiceName] = currentVoiceLabel
        self._print(indentationPrefix + "\\new Voice = "
                    + "\"" + currentVoiceLabel + "\" ")

        Logging.trace("<<: label = %s", currentVoiceLabel)

    #--------------------

    def _canonicalVoiceName (self, voiceName):
        """returns name of voice to be used within lilypond"""

        Logging.trace(">>: '%s'", voiceName)

        result = iif2(voiceName == "keyboardSimple", "keyboard",
                      voiceName == "drums", "myDrums", voiceName)

        Logging.trace("<<: '%s'", result)
        return result

    #--------------------

    def _classifyVoice (self, voiceName):
        """returns <isLyricsVoice> and <isFullKeyboardVoice>
           depending on <voiceName>"""

        Logging.trace(">>: '%s'", voiceName)

        isFullKeyboardVoice = (voiceName == "keyboard")
        isLyricsVoice       = (self._lyricsCount(voiceName) > 0)

        Logging.trace("<<: isLyricsVoice = %d, isFullKeyboardVoice = %d",
                      isLyricsVoice, isFullKeyboardVoice)
        return isLyricsVoice, isFullKeyboardVoice

    #--------------------

    def _ensureMacroAvailability (self, macroName, alternativeMacroNameList):
        """checks whether <macroName> is available in include file; if
           not, several alternatives are tried in
           <alternativeMacroNameList>"""

        Logging.trace(">>: macro = %s, alternativesList = %s",
                      macroName, alternativeMacroNameList)
        isFound = (macroName in self._includeFileMacroNameSet)
        hasAncestor = False

        if not isFound:
            for otherMacroName in iter(alternativeMacroNameList):
                if otherMacroName in self._includeFileMacroNameSet:
                    st = "%s = { \\%s }" % (macroName, otherMacroName)
                    self._printLine(st, False)
                    hasAncestor = True
                    break

        Logging.trace("<<: isFound = %s, hasAncestor = %s",
                      isFound, hasAncestor)
            
    #--------------------

    def _getPVEntry (self, map, phase, voiceName, defaultValue):
        """Returns entry of two-level <map> at <phase> and <voiceName>;
           if there is no such entry, <defaultValue> is returned"""

        embeddedMap = map.get(phase, {})
        result = embeddedMap.get(voiceName, defaultValue)
        Logging.trace("--: voiceName = %s, phase = %s, result = %s,"
                      + " map = %s, embeddedMap = %s",
                      voiceName, phase, result, map, embeddedMap)
        return result

    #--------------------

    def _lilypondVoiceName (self, voiceName):
        """returns name of voice to be used within lilypond"""

        Logging.trace(">>: '%s'", voiceName)

        result = iif2(voiceName == "drums", "myDrums",
                      voiceName.endswith("Simple"), voiceName[:-6], voiceName)

        Logging.trace("<<: '%s'", result)
        return result

    #--------------------

    def _lyricsCount (self, voiceName):
        """returns lyrics count for <voiceName> if any"""

        Logging.trace(">>: '%s'", voiceName)

        result = 0
        target = self._phase

        if voiceName in self._voiceNameToLyricsMap:
            entry = self._voiceNameToLyricsMap[voiceName]
            result = entry.get(target, 0)
        
        Logging.trace("<<: %d", result)
        return result
        
    #--------------------

    def _makeVoiceText (self, voiceName):
        """generates the lilypond commands for single <voice>;
           <self._phase> tells whether this voice is part of a single
           voice, a video or a full score"""

        Logging.trace(">>: '%s'", voiceName)

        isLyricsVoice, isFullKeyboardVoice = self._classifyVoice(voiceName)
        isPartOfFullScore = (self._phase != "extract")
        clefString = self._getPVEntry(self._phaseAndVoiceNameToClefMap,
                                      self._phase, voiceName, "G")
        st = iif(clefString == "", "", "\\clef \"%s\"" % clefString)
        lilypondVoiceName = self._lilypondVoiceName(voiceName)
        voiceMacroName = lilypondVoiceName + self._phase.capitalize()
        alternativeMacroNameList = [ lilypondVoiceName ]
        self._ensureMacroAvailability(voiceMacroName,
                                      alternativeMacroNameList)

        st = (st
              + "\\keyAndTime "
              + iif(isPartOfFullScore, "",
                    "\\initialTempo \\compressFullBarRests ")
              + "\\" + voiceMacroName)

        Logging.trace("<<: '%s'", st)
        return st

    #--------------------

    def _print (self, st, isBuffered=True):
        """writes <st> to current lilypond file <self>; if
           <isBuffered> is set, the line is not directly written, but
           buffered"""

        cls = self.__class__
        template = iif(isBuffered, "--: /%d/ =>'%s'", "--: /%d/ <='%s'")
        effectiveProcessingState = \
          iif(self._processingState != cls._ProcessingState_afterInclusion
              or isBuffered, self._processingState,
              cls._ProcessingState_beforeInclusion)

        Logging.trace(template, effectiveProcessingState, st.strip("\n"))
        self._processedTextBuffer[effectiveProcessingState].append(st)

    #--------------------

    def _printLine (self, st, isBuffered=True):
        """writes <st> to current lilypond file <self> terminated by a
           newline; if <isBuffered> is set, the line is not
           directly written, but buffered"""

        self._print(st + "\n", isBuffered)

    #--------------------

    def _writeFullScore (self):
        """writes a complete score for all voices to <self>"""

        Logging.trace(">>: %s", self)

        self._printLine("\\score {")
        self._printLine("  <<")

        for voiceName in self._voiceNameList:
            self._writeVoice(voiceName)

        self._printLine("  >>")
        self._printLine("  \\layout {}")
        self._printLine("}")

        Logging.trace("<<")

    #--------------------

    def _writeHeader (self):
        """writes the header of a lilypond file also including the
           music-file to <self>"""

        Logging.trace(">>: %s", self)

        cls = self.__class__

        # provide phase name as a lilypond macro
        self._printLine("ltbvcProcessingPhase = \"%s\"" % self._phase)

        if self._isVideoScore:
            # provide video device name as a lilypond macro
            self._printLine("ltbvcVideoDeviceName = \"%s\""
                            % self._videoDeviceName)

        # print initial tempo for all target files
        initialTempo = songMeasureToTempoMap[1][0]
        self._printLine("initialTempo = { \\tempo 4 = %d }" % initialTempo)

        if not self._targetIsPdf:
            self._writeNonPdfHeader()
            self._printLine("")
            
        if not self._targetIsPdf and self._lilypondArticulationIsUsed:
            # add reference to articulation file
            self._printLine("\\include \"articulate.ly\"")
            self._printLine("")

        if self._targetIsPdf:
            self._writePdfLayoutHeader()
            self._printLine("")

        # include the specific note stuff
        self._printLine("% include note stuff")
        self._printLine("\\include \"" + self._includeFileName + "\"")
        self._printLine("")

        self._processingState = cls._ProcessingState_afterInclusion

        if self._isVideoScore:
            self._writeVideoSettings()
            self._printLine("")

        Logging.trace("<<")

    #--------------------

    def _writeKeyboardVoice (self, indentation, isPartOfFullScore,
                             staffInstrumentSettingA, staffInstrumentSettingB):
        """writes voice data for keyboard voice with <voiceStaff> and
           information whether this is part of a score by
           <isPartOfFullScore>"""

        Logging.trace(">>: file = %s, isPartOfFullScore = %d,"
                      + " staffInstrSettingA = '%s',"
                      + " staffInstrSettingB = '%s'",
                      self, isPartOfFullScore,
                      staffInstrumentSettingA, staffInstrumentSettingB)

        self._printLine("    \\new PianoStaff <<")

        if isPartOfFullScore and not self._isVideoScore:
            self._printLine(indentation + staffInstrumentSettingA)
            self._printLine(indentation + staffInstrumentSettingB)

        self._printLine(indentation + "\\new Staff {")
        self._printLine(indentation + "  "
                        + self._makeVoiceText("keyboardTop"))
        self._printLine(indentation + "}")
        self._printLine(indentation + "\\new Staff {")
        self._printLine(indentation + "  "
                        + self._makeVoiceText("keyboardBottom"))
        self._printLine(indentation + "}")
        self._printLine("    >>")

        Logging.trace("<<")

    #--------------------

    def _writeNonPdfHeader (self):
        """writes the header of a lilypond file based on <self> targetting for
           a MIDI file or a video"""

        Logging.trace(">>: %s", self)

        # print count-in definition
        self._printLine("countIn = { R1*2\\mf }")
        self._printLine("drumsCountIn = \\drummode"
                        + " { ss2\\mf ss | ss4 ss ss ss | }")
       
        # print tempo track
        self._printLine("tempoTrack = {")
        measureList = songMeasureToTempoMap.keys()
        measureList.sort()
        previousMeasure = 0
        indentation = "    "

        for measure in measureList:
            if measure == 1:
                st = indentation + "\\initialTempo"
            else:
                tempo = songMeasureToTempoMap[measure][0]
                skipCount = measure - previousMeasure
                st = ("%s\\skip 1*%d\n%s%%%d\n%s\\tempo 4 =%d"
                      % (indentation, skipCount,
                         indentation, measure,
                         indentation, tempo))

            previousMeasure = measure
            self._printLine(st)
                
        self._printLine("}")

        Logging.trace("<<")

    #--------------------

    def _writeMidiScore (self):
        """sets up a complete score for MIDI output for all voices"""

        Logging.trace(">>: %s", self)

        self._printLine("\\score {")
        self._printLine("  <<")
        self._printLine("    { \\initialTempo \\countIn \\tempoTrack }")

        prefix = ("\\unfoldRepeats"
                  + iif(self._lilypondArticulationIsUsed, " \\articulate", ""))

        # we add an empty count in for the normal tracks and a drum count
        # in to the drum track
        normalPrefix = prefix + " { \\keyAndTime \\countIn "
        drumsPrefix  = prefix + " { \\keyAndTime \\drumsCountIn "

        # also a suffix of 2 measures is used for having a trailing reverb
        drumsSuffix = " R1 \\drummode { ss64\\ppppp }"
        otherSuffix = " R1 { c64\\ppppp }"

        indentation = "      "

        for voiceName in self._voiceNameList:
            isLyricsVoice, isFullKeyboardVoice = self._classifyVoice(voiceName)
            lilypondVoiceName = self._lilypondVoiceName(voiceName)
            voiceStaff = self._getPVEntry(self._phaseAndVoiceNameToStaffMap,
                                          self._phase, voiceName, "Staff")
            isDrumVoice = (voiceStaff == "DrumStaff")
            voiceInstrument = voiceNameToMidiNameMap.get(voiceName, "clav")
            self._printLine("    \\new " + voiceStaff + " ="
                            + " \"" + voiceName + "\""
                            + " \\with { midiInstrument ="
                            " \"" + voiceInstrument + "\" } { ")

            if isDrumVoice:
                  self._printLine(indentation + drumsPrefix
                                  + "\\" + lilypondVoiceName
                                  + drumsSuffix + " }")
            elif isLyricsVoice:
                self._addLyricsVoiceIntro(voiceName, indentation)
                self._printLine(" { " + normalPrefix
                                + "\\" + lilypondVoiceName
                                + otherSuffix + " } }")
            elif not isFullKeyboardVoice:
                self._printLine(indentation + normalPrefix
                                + "\\" + lilypondVoiceName
                                + otherSuffix + " }")
            else:
                # a complex keyboard staff
                self._printLine(indentation + "<<")
                self._printLine(indentation + "  \\new Staff { "
                                + normalPrefix + "\\keyboardTop"
                                + otherSuffix + " } }")
                self._printLine(indentation + "  \\new Staff { "
                                + normalPrefix + "\\keyboardBottom"
                                + otherSuffix + " } }")
                self._printLine(indentation + ">>")

            self._printLine("    }")

            if isLyricsVoice:
                self._addLyrics(voiceName)

        self._printLine("  >>")
        self._printLine("  \\midi {}")
        self._printLine("}")

        Logging.trace("<<")

    #--------------------

    def _writeNonKeyboardVoice (self, indentation, voiceName,
                                voiceStaff, isLyricsVoice,
                                isPartOfFullScore,
                                staffInstrumentSettingA,
                                staffInstrumentSettingB):
        """writes voice data for keyboard voice with <voiceStaff> and
           information whether this is part of a score by
           <isPartOfFullScore>"""

        Logging.trace(">>: file = %s, voiceName = '%s', voiceStaff = '%s',"
                      + " isLyricsVoice = %d, isPartOfFullScore = %d,"
                      + " staffInstrSettingA = '%s',"
                      + " staffInstrSettingB = '%s'",
                      self, voiceName, voiceStaff, isLyricsVoice,
                      isPartOfFullScore,
                      staffInstrumentSettingA, staffInstrumentSettingB)

        isDrumVoice = (voiceStaff == "DrumStaff")
        
        if isDrumVoice:
            self._printLine("    \\new " + voiceStaff + " {")
        else:
            self._printLine("    \\new " + voiceStaff + " \\with { ")
            self._printLine("      \\consists \"Instrument_name_engraver\"")
            self._printLine("    }{")

        if isPartOfFullScore and not self._isVideoScore:
            self._printLine(indentation + staffInstrumentSettingA)
            self._printLine(indentation + staffInstrumentSettingB)

        if not isDrumVoice:
            if isLyricsVoice:
                self._addLyricsVoiceIntro(voiceName, indentation)
            else:
                self._print(indentation + "\\new Voice")

            self._printLine(" \\with {")
            self._printLine(indentation
                            + "  \\consists \"Pitch_squash_engraver\" }{")

        self._printLine(indentation + "  " + self._makeVoiceText(voiceName))

        if not isDrumVoice:
            self._printLine(indentation + "}")

        self._printLine("    }")

        if isLyricsVoice:
            self._addLyrics(voiceName)

        Logging.trace("<<")

    #--------------------

    def _writePdfLayoutHeader (self):
        """writes all layout settings for a PDF output to <self>"""

        Logging.trace(">>: %s", self)

        self._printLine("%===================")
        self._printLine("%= GLOBAL SETTINGS =")
        self._printLine("%===================")
        self._printLine("")
        self._printLine("\\header {")
        self._printLine("    title = \"" + self._title + "\"")
        st = ("    composer = \"%s\"" % self._composerText)
        self._printLine(st)
        self._printLine("    tagline = ##f")
        self._printLine("}")
        self._printLine("")

        Logging.trace("<<")

    #--------------------

    def _writeVideoSettings (self):
        """puts out the paper, resolution and system size definitions
           for the video file to be generated"""

        Logging.trace(">>")

        self._printLine("% -- use high resolution and scale it down later")
        self._printLine("#(ly:set-option 'resolution %d)"
                        % self._videoEffectiveResolution)
        self._printLine("")
        self._printLine("#(set-global-staff-size %d)" % self._videoSystemSize)
        self._printLine("\paper {")

        self._printLine("    % -- remove all markup --")
        lilypondParameterList = \
            ("print-page-number", "print-first-page-number",
             "evenFooterMarkup", "oddFooterMarkup",
             "evenHeaderMarkup", "oddHeaderMarkup", "bookTitleMarkup",
             "scoreTitleMarkup", "ragged-last-bottom")

        for parameter in lilypondParameterList:
            self._printLine("    %s=##f" % parameter)

        self._printLine("    % define the page sizes")
        margin = "%6.3f" % self._videoTopBottomMargin
        self._printLine("    top-margin    = %s" % margin)
        self._printLine("    bottom-margin = %s" % margin)
        self._printLine("    paper-width   = %6.2f" % self._videoPaperWidth)
        self._printLine("    paper-height  = %6.2f" % self._videoPaperHeight)
        self._printLine("    line-width    = %6.2f" % self._videoLineWidth)
        self._printLine("}")
        
        Logging.trace("<<")

    #--------------------

    def _writeVoice (self, voiceName):
        """puts out the score for <voiceName> either as a standalone
           score or a part of a larger score"""

        Logging.trace(">>: '%s'", voiceName)

        isPartOfFullScore = (self._phase != "extract")
        indentation = "      "

        if not isPartOfFullScore:
            # make heading and score frame
            self._printLine("\\header { subtitle = \"("
                            + canonicalVoiceName(voiceName) + ")\" }")
            self._printLine("")
            self._printLine("\\score {")
            self._printLine("  <<")

        isLyricsVoice, isFullKeyboardVoice = self._classifyVoice(voiceName)
        voiceStaff = self._getPVEntry(self._phaseAndVoiceNameToStaffMap,
                                      self._phase, voiceName, "Staff")
        voiceStaffInstrument = \
            self._voiceNameToScoreNameMap.get(voiceName, voiceName)
        staffInstrumentSetting = " = #\"" + voiceStaffInstrument + "\""
        staffInstrumentSettingA = ("\\set " + voiceStaff + ".instrumentName"
                                   + staffInstrumentSetting)
        staffInstrumentSettingB = ("\\set " + voiceStaff
                                   + ".shortInstrumentName"
                                   + staffInstrumentSetting)

        target = self._phase

        if voiceName in self._voiceNameToChordsMap:
           if target in self._voiceNameToChordsMap[voiceName]:
            chordsName = "chords" + (voiceName[0].upper() + voiceName[1:])
            chordsMacroName = chordsName + target.capitalize()
            alternativeMacroNameList = [ chordsName,
                                         "chords" + target.capitalize(),
                                         "allChords" ]
            self._ensureMacroAvailability(chordsMacroName,
                                          alternativeMacroNameList)
            self._printLine("    \\new ChordNames {"
                            + iif(isPartOfFullScore, "",
                                  " \\compressFullBarRests")
                            + " \\" + chordsMacroName + " }")

        if isFullKeyboardVoice:
            self._writeKeyboardVoice(indentation, isPartOfFullScore,
                                     staffInstrumentSettingA,
                                     staffInstrumentSettingB)
        else:
            self._writeNonKeyboardVoice(indentation, voiceName, voiceStaff,
                                        isLyricsVoice, isPartOfFullScore,
                                        staffInstrumentSettingA,
                                        staffInstrumentSettingB)

        if not isPartOfFullScore:
            # make score footing
            self._printLine("  >>")
            self._printLine("  \\layout {}")
            self._printLine("}")

        Logging.trace("<<")

    #--------------------
    # EXPORTED FEATURES
    #--------------------

    @classmethod
    def initialize (cls, measureToTempoMap):
        """Sets module-specific configuration variables"""

        global songMeasureToTempoMap

        Logging.trace(">>: measureToTempoMap = %s", measureToTempoMap)
        songMeasureToTempoMap = measureToTempoMap
        
        Logging.trace("<<")

    #--------------------

    def __init__ (self, fileName):
        """initializes lilypond file"""

        Logging.trace(">>: '%s'", fileName)
        
        cls = self.__class__

        self._file                        = UTF8File.open(fileName, "w")
        self._processedTextBuffer         = [ [], [] ]
        self._processingState             = cls._ProcessingState_beforeInclusion
        self._phase                       = ""
        self._includeFileName             = ""
        self._includeFileMacroNameSet     = set()
        self._title                       = ""
        self._voiceNameList               = []
        self._composerText                = ""
        self._voiceNameToChordsMap        = {}
        self._voiceNameToLyricsMap        = {}
        
        self._lilypondArticulationIsUsed  = lilypondArticulationIsUsed
        self._voiceToLabelMap             = {}

        # video parameters (set to arbitrary values)
        self._videoEffectiveResolution    = 100
        self._videoTopBottomMargin        = 5
        self._videoSystemSize             = 25
        self._videoPaperWidth             = 10
        self._videoPaperHeight            = 10
        self._videoLineWidth              = 8

        # derived data
        self._targetIsPdf                 = False
        self._isVideoScore                = False

        Logging.trace("<<: %s", self)

    #--------------------

    def __str__ (self):
        st = (("LilypondFile(phase = '%s', title = '%s', composerText = '%s',"
               + " includeFileName = '%s', voiceNameList = %s,"
               + " voiceNameToChordsMap = %s, voiceNameToLyricsMap = %s,"
               + " videoEffectiveResolution = %s, videoSystemSize = %s, "
               + " videoTopBottomMargin = %s, videoPaperWidth = %s,"
               + " videoPaperHeight = %s, videoLineWidth = %s)")
              % (self._phase, self._title, self._composerText,
                 self._includeFileName, self._voiceNameList,
                 self._voiceNameToChordsMap, self._voiceNameToLyricsMap,
                 self._videoEffectiveResolution, self._videoSystemSize,
                 self._videoTopBottomMargin, self._videoPaperWidth,
                 self._videoPaperHeight, self._videoLineWidth))

        return st

    #--------------------

    def close (self):
        """finalizes lilypond file"""

        Logging.trace(">>: %s", self)
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

    def generate (self, includeFileName, phase,
                  voiceNameList, title, composerText,
                  voiceNameToChordsMap, voiceNameToLyricsMap,
                  voiceNameToScoreNameMap, phaseAndVoiceNameToClefMap,
                  phaseAndVoiceNameToStaffMap):
        """Sets parameters for generation and starts generation based
           on phase."""

        Logging.trace(">>: includeFileName = '%s', phase = '%s',"
                      + " voiceNameList = '%s', title = '%s',"
                      + " composerText = '%s',"
                      + " voiceNameToChordsMap = %s,"
                      + " voiceNameToLyricsMap = %s,"
                      + " voiceNameToScoreNameMap = %s,"
                      + " phaseAndVoiceNameToClefMap = %s,"
                      + " phaseAndVoiceNameToStaffMap = %s",
                      includeFileName, phase, voiceNameList,
                      title, composerText, voiceNameToChordsMap,
                      voiceNameToLyricsMap, voiceNameToScoreNameMap,
                      phaseAndVoiceNameToClefMap,
                      phaseAndVoiceNameToStaffMap)

        self._phase                       = phase
        self._includeFileName             = includeFileName
        self._title                       = title
        self._composerText                = composerText
        self._voiceNameList               = voiceNameList
        self._voiceNameToChordsMap        = voiceNameToChordsMap
        self._voiceNameToLyricsMap        = voiceNameToLyricsMap
        self._voiceNameToScoreNameMap     = voiceNameToScoreNameMap
        self._phaseAndVoiceNameToClefMap  = phaseAndVoiceNameToClefMap
        self._phaseAndVoiceNameToStaffMap = phaseAndVoiceNameToStaffMap

        self._voiceToLabelMap             = {}
        self._isFirstChordedSystem        = True
        
        # derived data
        self._targetIsPdf                 = (phase in ["extract", "score"])
        self._isVideoScore                = (phase == "video")

        self._includeFileMacroNameSet = \
            _LilypondIncludeFile.definedMacroNameSet(includeFileName)

        Logging.trace("--: %s", self)

        self._writeHeader()

        if phase == "extract":
            voiceName = self._voiceNameList[0]
            self._writeVoice(voiceName)
        elif phase == "midi":
            self._writeMidiScore()
        else:
            self._writeFullScore()

        self.close()

        Logging.trace("<<")

    #--------------------

    def setVideoParameters (self, deviceName, effectiveResolution, systemSize,
                            topBottomMargin, paperWidth, paperHeight,
                            lineWidth):
        """Sets all parameters needed for subsequent video generation"""
        
        Logging.trace(">>: deviceName = %s, effectiveResolution = %d,"
                      + " systemSize = %d,"
                      + " topBottomMargin = %4.2f, paperWidth = %5.2f,"
                      + " paperHeight = %5.2f, lineWidth = %5.2f",
                      deviceName, effectiveResolution, systemSize,
                      topBottomMargin, paperWidth, paperHeight, lineWidth)

        self._videoDeviceName          = deviceName
        self._videoEffectiveResolution = effectiveResolution
        self._videoSystemSize          = systemSize
        self._videoTopBottomMargin     = topBottomMargin
        self._videoPaperWidth          = paperWidth
        self._videoPaperHeight         = paperHeight
        self._videoLineWidth           = lineWidth

        Logging.trace("<<")
