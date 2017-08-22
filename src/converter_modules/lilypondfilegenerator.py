# -*- coding: utf-8-unix -*-
# lilypondFileGenerator -- generates a lilypond main file for several
#                          parameters by inclusion of a structured lilypond
#                          file with tracks
#
#   includeFileName:              name of include file with music
#   mode:                         tells whether a voice extract, a full score
#                                 a video or a midi should be produced
#   title:                        song full title (only required for score and
#                                 voice output)
#   year:                         year of arrangement (only required for score
#                                 and voice output)
#   voice:                        voice name (for generating an extract file)
#   voices:                       slash separated list of voice names in
#                                 arrangement (for midi, score or video,
#                                 optional)
#   lyricsCountVocals:            number of lyrics lines for lead vocals in
#                                 arrangement
#   lyricsCountBgVocals:          number of lyrics lines for background vocals
#                                 in arrangement
#   useSpecialLayoutForExtracts:  flag to tell whether a standalone music
#                                 expression should be used for the voice
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
#    chord list:    "allChordsXXX" where XXX is the capitalised
#                   voice name (chords are only added for voices that do
#                   neither match "vocals" nor "drums")
#    tempo list:    "tempoTrack" (only necessary when mode = "MIDI")
#    lyrics lines:  they are labelled "vocLyricsA", "vocLyricsB", ...
#                   or "bgVocLyricsA", "bgVocLyricsB", ...
#-----------------------

###########
# IMPORTS #
###########

import argparse
from simplelogging import Logging
import sys
from ttbase import iif, iif2
from utf8file import UTF8File

#-------------------------
# configuration constants
#-------------------------

songMeasureToTempoMap        = None

# lilypond articulation: use articulate.ly
# tabulature tag: name of tabulature tag (data is removed from standard
#                 guitar staff)

tabulatureTag = "tabulature"
lilypondArticulationIsUsed = False

#-------------------------
# mappings for instruments
#-------------------------

# special staff definitions for instruments, default is "Staff"
instrumentToStaffMap = { "drums"      : "DrumStaff",
                         "keyboard"   : "PianoStaff",
                         "percussion" : "DrumStaff" }

# special clef definitions for instruments, default is "G"
instrumentToClefMap = { "bass"           : "bass_8",
                        "drums"          : "",
                        "guitar"         : "G_8",
                        "keyboardBottom" : "bass",
                        "percussion"     : "" }

instrumentToMidiNameMap = { "bass"           : "electric bass (pick)",
                            "bgVocals"       : "synth voice",
                            "drums"          : "power kit",
                            "guitar"         : "overdriven guitar",
                            "keyboard"       : "rock organ",
                            "keyboardSimple" : "rock organ",
                            "organ"          : "rock organ",
                            "percussion"     : "power kit",
                            "vocals"         : "synth voice" }

instrumentToShortNameMap = { "bass"           : "bs",
                             "bgVocals"       : "bvc",
                             "drums"          : "dr",
                             "guitar"         : "gtr",
                             "keyboard"       : "kb",
                             "keyboardSimple" : "kb",
                             "organ"          : "org",
                             "percussion"     : "prc",
                             "strings"        : "str",
                             "synthesizer"    : "syn",
                             "vocals"         : "voc" }

#--------------------
#--------------------

class LilypondFile:
    """represents the lilypond file to be generated"""

    #--------------------
    # LOCAL FEATURES
    #--------------------

    def _addVocalsIntro (self, voiceName, indentationPrefix):
        """adds a named voice definition line for a vocals voice
           (which can later be referenced by a lyrics line)"""

        Logging.trace(">>: voiceName = '%s'", voiceName)

        voiceLabelCount = len(self._voiceToLabelMap) + 1
        currentVoiceLabel = "song" + "ABCDEF"[voiceLabelCount - 1]
        self._voiceToLabelMap[voiceName] = currentVoiceLabel
        self._print(indentationPrefix + "\\new Voice = "
                    + "\"" + currentVoiceLabel + "\" ")

        Logging.trace("<<")

    #--------------------

    def _addVocalLyrics (self, voiceName):
        """adds all lyrics lines to current <voice> (assuming it is a
           '*[Vv]ocals' voice"""

        Logging.trace(">>: '%s'", voiceName)

        isLeadVocals = (voiceName == "vocals")
        lyricsNamePrefix = "\\" + iif(isLeadVocals, "voc", "bgVoc") + "Lyrics"
        lyricsCount = iif(isLeadVocals,
                          self._lyricsCountVocals, self._lyricsCountBgVocals)
        lyricsCount = iif(self._isVideoScore, 1, lyricsCount)

        if lyricsCount == "" or lyricsCount > 6:
            Logging.trace("--: bad lyrics count: %d", lyricsCount)
            lyricsCount = 0

        for voiceIndex in range(1, lyricsCount + 1):
            if self._targetIsPdf or voiceIndex == 1:
                if not self._targetIsPdf:
                    # output goes to midi or video file
                    lyricsName = (lyricsNamePrefix
                                  + iif(self._isVideoScore, "Video", "Midi"))
                else:
                    lyricsName = (lyricsNamePrefix
                                  + "ABCDEF"[voiceIndex - 1]
                                  + iif(self._useSpecialLayoutForExtracts,
                                        "Standalone", ""))

                label = self._voiceToLabelMap[voiceName]

                self._printLine("    \\new Lyrics \\lyricsto"
                                + " \"" + label + "\""
                                + " { " + lyricsName + " }")

        Logging.trace("<<")

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
        """returns <isDrumVoice>, <isGuitar> <isVocalsVoice> and
           <isFullKeyboardVoice> depending on <voiceName>"""

        Logging.trace(">>: '%s'", voiceName)

        isDrumVoice         = (voiceName in ["drums", "percussion"])
        isGuitar            = (voiceName == "guitar")
        isFullKeyboardVoice = (voiceName == "keyboard")
        isVocalsVoice       = ("ocals" in voiceName)

        Logging.trace("<<: isDrumVoice = %d, isGuitar = %d,"
                      + " isVocalsVoice = %d, isFullKeyboardVoice = %d",
                      isDrumVoice, isGuitar, isVocalsVoice,
                      isFullKeyboardVoice)
        return isDrumVoice, isGuitar, isVocalsVoice, isFullKeyboardVoice

    #--------------------

    def _makeVoiceText (self, voiceName):
        """generates the lilypond commands for single <voice>;
           <self._mode> tells whether this voice is part of a single
           voice, a video or a full score"""

        Logging.trace(">>: '%s'", voiceName)

        isDrumVoice, isGuitar, isVocalsVoice, isFullKeyboardVoice = \
            self._classifyVoice(voiceName)
        isPartOfFullScore = (self._mode != "voice")

        if isDrumVoice:
            st = ""
        else:
            st = ("\\clef \""
                  + instrumentToClefMap.get(voiceName, "G")
                  + "\" ")

        canonicalVoiceName = \
            (self._canonicalVoiceName(voiceName)
             + iif3(self._isVideoScore, "Video",
                    self._mode == "voice", "Standalone",
                    self._mode == "midi", "Midi", ""))

        st = (st
              + "\\keyAndTime "
              + iif(isPartOfFullScore, "",
                    "\\initialTempo \\compressFullBarRests ")
              + iif(isGuitar, "\\removeWithTag #'" + tabulatureTag + " ", "")
              + "\\" + canonicalVoiceName)

        Logging.trace("<<: '%s'", st)
        return st

    #--------------------

    def _print (self, st):
        """writes <st> to current lilypond file <self>"""

        Logging.trace("--: '%s'", st)
        self._file.write(st)

    #--------------------

    def _printLine (self, st):
        """writes <st> to current lilypond file <self> terminated by a
           newline"""

        Logging.trace("--: '%s'", st)
        self._file.write(st + "\n")

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
            isDrumVoice, isGuitar, isVocalsVoice, isFullKeyboardVoice = \
                self._classifyVoice(voiceName)
            canonicalVoiceName = self._canonicalVoiceName(voiceName)
            voiceStaff = instrumentToStaffMap.get(voiceName, "Staff")
            voiceInstrument = instrumentToMidiNameMap.get(voiceName, "clav")
            self._printLine("    \\new " + voiceStaff + " ="
                            + " \"" + voiceName + "\""
                            + " \\with { midiInstrument ="
                            " \"" + voiceInstrument + "\" } { ")

            if isDrumVoice:
                  self._printLine(indentation + drumsPrefix
                                  + "\\" + canonicalVoiceName
                                  + drumsSuffix + " }")
            elif isVocalsVoice:
                self._addVocalsIntro(voiceName, indentation)
                self._printLine(" { " + normalPrefix
                                + "\\" + canonicalVoiceName
                                + otherSuffix + " } }")
            elif not isFullKeyboardVoice:
                self._printLine(indentation + normalPrefix
                                + "\\" + canonicalVoiceName
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

            if isVocalsVoice:
                self._addVocalLyrics(voiceName)

        self._printLine("  >>")
        self._printLine("  \\midi {}")
        self._printLine("}")

        Logging.trace("<<")

    #--------------------

    def _writeNonKeyboardVoice (self, indentation, voiceName,
                                voiceStaff, isDrumVoice,
                                isVocalsVoice, isPartOfFullScore,
                                staffInstrumentSettingA,
                                staffInstrumentSettingB):
        """writes voice data for keyboard voice with <voiceStaff> and
           information whether this is part of a score by
           <isPartOfFullScore>"""

        Logging.trace(">>: file = %s, voiceName = '%s', voiceStaff = '%s',"
                      + " isDrumVoice = %d, isVocalsVoice = %d,"
                      + " isPartOfFullScore = %d,"
                      + " staffInstrSettingA = '%s',"
                      + " staffInstrSettingB = '%s'",
                      self, voiceName, voiceStaff,
                      isDrumVoice, isVocalsVoice, isPartOfFullScore,
                      staffInstrumentSettingA, staffInstrumentSettingB)
        
        if not isDrumVoice:
            self._printLine("    \\new " + voiceStaff + " {")
        else:
            self._printLine("    \\new " + voiceStaff + " \\with { ")
            self._printLine("      \\consists \"Instrument_name_engraver\"")
            self._printLine("    }{")

        if isPartOfFullScore and not self._isVideoScore:
            self._printLine(indentation + staffInstrumentSettingA)
            self._printLine(indentation + staffInstrumentSettingB)

        if not isDrumVoice:
            if isVocalsVoice:
                self._addVocalsIntro(voiceName, indentation)
            else:
                self._print(indentation + "\\new Voice")

            self._printLine(" \\with {")
            self._printLine(indentation
                            + "  \\consists \"Pitch_squash_engraver\" }{")

        self._printLine(indentation + "  " + self._makeVoiceText(voiceName))

        if not isDrumVoice:
            self._printLine(indentation + "}")

        self._printLine("    }")

        if isVocalsVoice:
            self._addVocalLyrics(voiceName)

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

        canonicalVoiceName = iif(voiceName == "keyboardSimple",
                                 "keyboard", voiceName)
        isPartOfFullScore = (self._mode != "voice")
        indentation = "      "

        if not isPartOfFullScore:
            # make heading and score frame
            self._printLine("\\header { subtitle = \"("
                            + canonicalVoiceName + ")\" }")
            self._printLine("")
            self._printLine("\\score {")
            self._printLine("  <<")

        isDrumVoice, isGuitar, isVocalsVoice, isFullKeyboardVoice = \
            self._classifyVoice(voiceName)
        voiceStaff = instrumentToStaffMap.get(voiceName, "Staff")
        voiceStaffInstrument = \
            instrumentToShortNameMap.get(voiceName, voiceName)
        staffInstrumentSetting = " = #\"" + voiceStaffInstrument + "\""
        staffInstrumentSettingA = ("\\set " + voiceStaff + ".instrumentName"
                                   + staffInstrumentSetting)
        staffInstrumentSettingB = ("\\set " + voiceStaff
                                   + ".shortInstrumentName"
                                   + staffInstrumentSetting)

        if (not isDrumVoice
            and (isPartOfFullScore and self._isFirstChordedSystem
                 or (not isPartOfFullScore and not isVocalsVoice))):
            chordsName = (canonicalVoiceName[0].upper()
                          + canonicalVoiceName[1:])
            chordsName = iif2(self._isVideoScore, "allChordsVideo",
                              isPartOfFullScore, "allChords",
                              "allChords" + chordsName)
            self._printLine("    \\new ChordNames {"
                            + iif(isPartOfFullScore, "",
                                  " \\compressFullBarRests")
                            + " \\" + chordsName + " }")

            # when in a full score only the first melodic instrument has
            # chord symbols
            self._isFirstChordedSystem = False


        if isFullKeyboardVoice:
            self._writeKeyboardVoice(indentation, isPartOfFullScore,
                                     staffInstrumentSettingA,
                                     staffInstrumentSettingB)
        else:
            self._writeNonKeyboardVoice(indentation, voiceName, voiceStaff,
                                        isDrumVoice, isVocalsVoice,
                                        isPartOfFullScore,
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

        self._file                        = UTF8File.open(fileName, "w")
        self._mode                        = ""
        self._includeFileName             = ""
        self._title                       = ""
        self._voiceNameList               = []
        self._composerText                = ""
        self._lyricsCountVocals           = 0
        self._lyricsCountBgVocals         = 0
        
        self._lilypondArticulationIsUsed  = lilypondArticulationIsUsed
        self._voiceToLabelMap             = {}
        self._isFirstChordedSystem        = True

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
        st = (("LilypondFile(mode = '%s', title = '%s', composerText = '%s',"
               + " lyricsCountVoc = %d, lyricsCountBgVoc = %d,"
               + " voiceNameList = %s,"
               + " videoEffectiveResolution = %s, videoSystemSize = %s, "
               + " videoTopBottomMargin = %s, videoPaperWidth = %s,"
               + " videoPaperHeight = %s, videoLineWidth = %s)")
              % (self._mode, self._title, self._composerText,
                 self._lyricsCountVocals, self._lyricsCountBgVocals,
                 self._voiceNameList,
                 self._videoEffectiveResolution, self._videoSystemSize,
                 self._videoTopBottomMargin, self._videoPaperWidth,
                 self._videoPaperHeight, self._videoLineWidth))

        return st

    #--------------------

    def close (self):
        """finalizes lilypond file"""

        Logging.trace(">>: %s", self)
        self._file.close()
        Logging.trace("<<")

    #--------------------

    def generate (self, includeFileName, mode,
                  voiceNameList, title, composerText,
                  lyricsCountVocals, lyricsCountBgVocals):
        """Sets parameters for generation and starts generation based
           on mode."""

        Logging.trace(">>: includeFileName = '%s', mode = '%s',"
                      + " voiceNameList = '%s', title = '%s',"
                      + " composerText = '%s',"
                      + " lyricsCountVoc = %d, lyricsCountBgVoc = %d",
                      includeFileName, mode, voiceNameList,
                      title, composerText, lyricsCountVocals,
                      lyricsCountBgVocals)

        self._mode                        = mode
        self._includeFileName             = includeFileName
        self._title                       = title
        self._composerText                = composerText
        self._voiceNameList               = voiceNameList
        self._lyricsCountVocals           = lyricsCountVocals
        self._lyricsCountBgVocals         = lyricsCountBgVocals

        self._voiceToLabelMap             = {}
        self._isFirstChordedSystem        = True
        
        # derived data
        self._targetIsPdf                 = (mode in ["voice", "score"])
        self._isVideoScore                = (mode == "video")

        Logging.trace("--: %s", self)

        self._writeHeader()

        if mode == "voice":
            voiceName = self._voiceNameList[0]
            self._writeVoice(voiceName)
        elif mode == "midi":
            self._writeMidiScore()
        else:
            self._writeFullScore()

        self.close()

        Logging.trace("<<")

    #--------------------

    def setVideoParameters (self, effectiveResolution, systemSize,
                            topBottomMargin, paperWidth, paperHeight,
                            lineWidth):
        """Sets all parameters needed for subsequent video generation"""
        
        Logging.trace(">>: effectiveResolution = %d, systemSize = %d,"
                      + " topBottomMargin = %4.2f, paperWidth = %5.2f,"
                      + " paperHeight = %5.2f, lineWidth = %5.2f",
                      effectiveResolution, systemSize, topBottomMargin,
                      paperWidth, paperHeight, lineWidth)

        self._videoEffectiveResolution = effectiveResolution
        self._videoSystemSize          = systemSize
        self._videoTopBottomMargin     = topBottomMargin
        self._videoPaperWidth          = paperWidth
        self._videoPaperHeight         = paperHeight
        self._videoLineWidth           = lineWidth

        Logging.trace("<<")
