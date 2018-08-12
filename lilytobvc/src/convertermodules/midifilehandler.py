# -*- coding: utf-8-unix -*-
# midiFileHandler -- converts midi file into a text representation
#                    and writes a midi file from text representation
#
# author: Dr. Thomas Tensi, 2017

#====================
# IMPORTS
#====================

import math

from basemodules.operatingsystem import OperatingSystem
from basemodules.simpleassertion import Assertion
from basemodules.simplelogging import Logging
from basemodules.ttbase import iif, intListToHex, stringToIntList
from basemodules.utf8file import UTF8File 

#====================

class MidiFileHandler:
    """This module provides two functions:
       - to read a midi file returning a text representation and
       - to write a midi file from a text representation."""

    #--------------------
    # LOCAL FEATURES
    #--------------------

    _Kind_string  = "S"
    _Kind_integer = "I"

    _fileHead  = "MThd"
    _trackHead = "MTrk"
    _trackEndMarker  = "TrkEnd"

    _byteToEventKindMap = { x: "Off" for x in range(0x80, 0x90) }
    _byteToEventKindMap.update({ x: "On" for x in range(0x90, 0xA0) })
    _byteToEventKindMap.update({ x: "PolyPress" for x in range(0xA0, 0xB0) })
    _byteToEventKindMap.update({ x: "Par" for x in range(0xB0, 0xC0) })
    _byteToEventKindMap.update({ x: "PrCh" for x in range(0xC0, 0xD0) })
    _byteToEventKindMap.update({ x: "ChanPress" for x in range(0xD0, 0xE0) })
    _byteToEventKindMap.update({ x: "PitchWhl" for x in range(0xE0, 0xF0) })
    _byteToEventKindMap.update({ 0xF0: "SysEx", 0xF7: "SysExEnd",
                                 0xFF: "Meta" })

    _byteToMetaEventKindMap = { 0x00: "SeqNum", 0x01: "Text",
                                0x02: "Copyright", 0x03: "TrkName",
                                0x04: "InstrName", 0x05: "Lyric",
                                0x06: "Marker", 0x07: "CuePt",
                                0x20: "ChanPrfx", 0x2F: "TrkEnd",
                                0x51: "Tempo", 0x54: "SMPTEOffset",
                                0x58: "TimeSig", 0x59: "KeySig",
                                0x7F: "SeqMeta" }

    _eventKindToByteMap = { "Off": 0x80, "On": 0x90, "PolyPress": 0xA0,
                            "Par": 0xB0, "PrCh": 0xC0, "ChanPress": 0xD0,
                            "PitchWhl": 0xE0, "SysEx": 0xF0, "SysExEnd": 0xF7,
                            "Meta": 0xFF }

    _eventKindToLengthMap = { "Off": 2, "On": 2, "PolyPress": 2,
                              "Par": 2, "PrCh": 1, "ChanPress": 1,
                              "PitchWhl": 2, "SysEx": "V", "SysExEnd": "V",
                              "Meta": "R" }

    _keyList = "CbGbDbAbEbBbF C G D A E B F# C# G# D# A#"

    _metaEventKindToByteMap = dict(map(reversed,
                                       _byteToMetaEventKindMap.items()))

    _metaEventKindToLengthMap = { "SeqNum": 2, "Text": "V", "Copyright": "V",
                                  "TrkName": "V", "InstrName": "V",
                                  "Lyric": "V", "Marker": "V",  "CuePt": "V",
                                  "ChanPrfx": 1, "TrkEnd": 0, "Tempo": 3,
                                  "SMPTEOffset": 5, "TimeSig": 4,
                                  "KeySig": 2, "SeqMeta": "V" }

    #--------------------
    #--------------------

    def _appendToByteList (self, list):
        """Appends integer list <list> to internal byte list and
           traces operation"""

        Logging.trace("--: %d -> %s",
                      len(self._byteList), intListToHex(list))
        self._byteList.extend(list)

    #--------------------

    def _appendToLineList (self, st):
        """Appends <st> to <self._lineList>"""

        Logging.trace("--: %d -> %s", self._position, st)
        self._lineList.append(st)

    #--------------------

    def _checkByteListWriteOperation (self, midiFileName):
        """Checks consistency of write operation of a byte list to be
           read from file with <midiFileName>"""

        Logging.trace(">>: %s", midiFileName)

        self.readFile(midiFileName)
        byteList = self._byteList
        testFileName = midiFileName + "-tst"
        self.writeFile(testFileName, lineList)
        otherByteList = self._byteList

        for i in range(min(len(byteList), len(otherByteList))):
            if byteList[i] != otherByteList[i]:
                Logging.trace("--: byte list difference at %d: %d <-> %d",
                              i, byteList[i], otherByteList[i])

        Logging.trace("<<")
        
    #--------------------

    def _convertByteListToLineList (self):
        """Converts midi stream <self._byteList> into text
           representation in <self._lineList>"""

        Logging.trace(">>")

        self._position = 0
        self._lineList = []
        
        trackCount = self._readMidiHeader()

        for i in range(trackCount):
            self._readMidiTrack()

        Logging.trace("<<")

    #--------------------

    def _convertLineListToByteList (self):
        """Converts line list representation of midi stream in
           <self._lineList> into midi stream <self._byteList>"""

        Logging.trace(">>")

        self._position = 0
        self._byteList = []
        trackCount = self._writeMidiHeader()

        for i in range(trackCount):
            self._writeMidiTrack()

        Logging.trace("<<")

    #--------------------

    def _getLine (self):
        """Returns line in <self._lineList> at <self._position> and
           advances position"""

        result = self._lineList[self._position]
        self._position += 1
        return result

    #--------------------

    def _metaEventKind (self, eventByte):
        """Calculates kind of meta event by given <eventByte>"""

        cls = self.__class__
        result = cls._byteToMetaEventKindMap.get(eventByte, None)
        return result

    #--------------------

    def _midiEventKind (self, eventByte):
        """Calculates kind of event by given <eventByte>"""

        cls = self.__class__
        result = cls._byteToEventKindMap.get(eventByte, None)
        return result

    #--------------------

    def _peekLine (self):
        """Returns line in <self._lineList> at <self._position>, but
           leaves position as is"""

        return self._lineList[self._position]

    #--------------------

    def _readIntBytes (self, count, isSigned=False):
        """Reads <count> bytes from <self._byteList> at
           <self._position> and returns them as an integer"""

        newPosition = self._position + count
        partList = self._byteList[self._position:newPosition]
        self._position = newPosition

        result = 0
        maxValue = 0

        for i in partList:
            maxValue = maxValue * 256 + 255
            result = result * 256 + i

        if isSigned:
            referenceValue = (maxValue + 1) / 2
            result = iif(result < referenceValue, result,
                         result - maxValue - 1)

        return result

    #--------------------

    def _readMetaEvent (self):
        """Reads meta event in midi stream <self._byteList> at
           <self._position> and returns representation without time
           indication"""

        Logging.trace(">>: %d", self._position)
        cls = self.__class__

        readIntProc = self._readIntBytes
        metaEventByte = readIntProc(1)
        metaEventKind = self._metaEventKind(metaEventByte)

        Assertion.check(metaEventKind is not None,
                        "bad MIDI format: expected meta event byte %d"
                        % metaEventByte)
        
        eventLength = cls._metaEventKindToLengthMap[metaEventKind]
        st = ""

        if eventLength == "V":
            # some text event or a sequencer specific meta event
            eventLength = self._readVariableBytes()

            if metaEventKind != "SeqMeta":
                st = "\"%s\"" % self._readStringBytes(eventLength)
            else:
                for i in range(eventLength):
                    st += iif(i > 0, " ", "") + ("%d" % readIntProc(1))
        else:
            eventLengthInFile = readIntProc(1)
            Assertion.check(eventLength == eventLengthInFile,
                            ("bad MIDI format: expected event length %d,"
                             + " found %d") % (eventLength, eventLengthInFile))

            if metaEventKind == "ChanPrfx":
                st = "%d" % (readIntProc(1) + 1)
            elif metaEventKind in ["SeqNum", "Tempo"]:
                st = "%d" % readIntProc(eventLength)
            elif metaEventKind == "SMPTEOffset":
                st = ("hr=%d mn=%d se=%d fr=%d ff=%d"
                       % (readIntProc(1), readIntProc(1), readIntProc(1),
                          readIntProc(1), readIntProc(1)))
            elif metaEventKind == "TimeSig":
                numerator                  = readIntProc(1)
                denominator                = 2 ** readIntProc(1)
                clocksPerClick             = readIntProc(1)
                thirtysecondsPerMidiClocks = readIntProc(1)
                st = "%d/%d %d %d" % (numerator, denominator, clocksPerClick,
                                      thirtysecondsPerMidiClocks)
            elif metaEventKind == "KeySig":
                accidentalCount = readIntProc(1, isSigned=True)
                isMinor = (readIntProc(1) == 1)
                i = (accidentalCount + 7)
                i = iif(isMinor, i + 3, i) * 2
                key = cls._keyList[i:i+2].strip()
                key += iif(isMinor, "m", "")
                st = key
                Logging.trace("--: accidentalCount = %d, i = %d",
                              accidentalCount, i)

        eventKind = "Meta " + metaEventKind

        Logging.trace("<<: kind = '%s', st = '%s'", eventKind, st)
        return eventKind, st
        
    #--------------------

    def _readMidiEvent (self):
        """Reads event in midi stream <self._byteList> at
           <self._position> and updates <self._lineList> accordingly"""

        Logging.trace(">>: %d", self._position)

        cls = self.__class__
        deltaTime = self._readVariableBytes()
        self._currentTime += int(deltaTime)

        eventByte = self._readIntBytes(1)
        eventKind = self._midiEventKind(eventByte)

        Assertion.check(eventKind is not None,
                        "bad MIDI format: expected event byte")

        eventLength = cls._eventKindToLengthMap[eventKind]

        if eventLength == "R":
            # meta event
            eventKind, st = self._readMetaEvent()
        elif eventLength == "V":
            # sysex event
            eventLength = self._readVariableBytes()
            st = ""

            for i in range(eventLength):
                value = self._readIntBytes(1)
                st = st + iif(i > 0, " ", "") + "%d" % value
        else:
            # channel message
            channel = eventByte % 16 + 1
            valueA  = self._readIntBytes(1)
            st = "ch=%d" % channel

            if eventLength == 2:
                valueB = self._readIntBytes(1)

            if eventByte < 0xB0:
                st += " n=%d v=%d" % (valueA, valueB)
            elif eventByte < 0xC0:
                st += " c=%d v=%d" % (valueA, valueB)
            elif eventByte < 0xD0:
                st += " p=%d" % valueA
            elif eventByte < 0xE0:
                st += " v=%d" % valueA
            else:
                st += " v=%d" % (valueA + valueB * 128)

        st = iif(st == "", st, " " + st)
        currentLine = "%d %s%s" % (self._currentTime, eventKind, st)
        self._appendToLineList(currentLine)
        isTrackEnd = (eventKind == "Meta TrkEnd")

        Logging.trace("<<")
        return isTrackEnd

    #--------------------

    def _readMidiHeader (self):
        """Converts header in midi stream <self._byteList> at
           <self._position> and appends text representation to
           <self._lineList>"""

        Logging.trace(">>: %d", self._position)

        cls = self.__class__

        header       = self._readStringBytes(4)
        length       = self._readIntBytes(4)
        fileFormat   = self._readIntBytes(2)
        trackCount   = self._readIntBytes(2)
        timeDivision = self._readIntBytes(2)

        Assertion.check(header == cls._fileHead, "midi header chunk expected")
        Assertion.check(length == 6, "midi header must have length 6")
        Assertion.check(fileFormat <= 2, "midi format must be 0, 1, or 2")

        st = ("%s %d %d %d"
              % ("MFile", fileFormat, trackCount, timeDivision))
        self._appendToLineList(st)
        
        Logging.trace("<<: %d", self._position)
        return trackCount

    #--------------------

    def _readMidiTrack (self):
        """Converts track in midi stream <self._byteList> at
           <self._position> and appends text representation of all
           events to <self._lineList>"""

        Logging.trace(">>: %d", self._position)

        cls = self.__class__

        header = self._readStringBytes(4)
        length = self._readIntBytes(4)

        Assertion.check(header == cls._trackHead,
                        "track header chunk expected")

        self._appendToLineList(cls._trackHead)
        self._currentTime = 0
        isTrackEnd = False

        while not isTrackEnd:
            isTrackEnd = self._readMidiEvent()
        
        self._appendToLineList(cls._trackEndMarker)
        
        Logging.trace("<<")

    #--------------------

    def _readStringBytes (self, count):
        """Reads <count> bytes from <self._byteList> at
           <self._position> and returns them as a string"""

        newPosition = self._position + count
        partList = self._byteList[self._position:newPosition]
        self._position = newPosition

        result = ""

        for ch in partList:
            result = result + chr(ch)

        Logging.trace("--: %s", result)
        return result
    
    #--------------------

    def _readVariableBytes (self):
        """Reads bytes from <self._byteList> at <self._position> and
           returns them as an integer until top bit is not set"""

        isDone = False
        result = 0

        while not isDone:
            part = self._byteList[self._position]
            self._position += 1
            isDone = (part < 128)
            part = part & 127
            result = result * 128 + part

        Logging.trace("--: %d", result)
        return result
    
    #--------------------

    def _tokenize (self, st):
        """Splits <st> at blanks, but keeps strings together and
           returns part list"""

        partList = []
        inString = False
        part = ""

        for ch in st:
            if ch != " " and ch != "\"":
                part += ch
            elif ch == "\"":
                part += ch
                inString = not inString
            elif inString:
                part += ch
            elif part > "":
                partList.append(part)
                part = ""
                inString = False

        if part > "":
            partList.append(part)

        return partList

    #--------------------

    def _writeIntBytes (self, value, count, isSigned=False):
        """Writes integer <value> as <count> bytes and appends to
           <self._byteList>"""

        if isSigned and value < 0:
            maxValue = 256 ** count
            value = int(maxValue - value)

        partList = []

        for i in range(count):
            partList = [ value % 256 ] + partList
            value //= 256

        self._appendToByteList(partList)

    #--------------------

    def _writeListBytes (self, list):
        """Writes elements from <list> as integer values and appends
           them to <self._byteList>"""

        for value in list:
            self._writeIntBytes(int(value), 1)

    #--------------------

    def _writeMetaEvent (self, argumentList):
        """Converts meta event with argument given by <argumentList>
           to midi stream and appends to <self._byteList>"""

        currentLine = self._peekLine()
        Logging.trace(">>: %d - %s", self._position, currentLine)

        cls = self.__class__

        metaEventKind = argumentList[0]
        metaEventByte = cls._metaEventKindToByteMap.get(metaEventKind, None)
        Assertion.check(metaEventByte is not None,
                        "bad text line: expected meta event kind '%s'"
                        % metaEventKind)
        self._writeIntBytes(metaEventByte, 1)
        argumentList = argumentList[1:]

        eventLength = cls._metaEventKindToLengthMap[metaEventKind]

        Logging.trace("--: kind=%s, length=%s", metaEventKind, eventLength)

        if eventLength == "V":
            # some text event or a sequencer specific meta event
            if metaEventKind == "SeqMeta":
                self._writeVariableBytes(len(argumentList))
                self._writeListBytes(argumentList)
            else:
                st = argumentList[0][1:-1]
                Logging.trace("--: st='%s'", st)
                self._writeVariableBytes(len(st))
                self._writeStringBytes(st)
        else:
            self._writeIntBytes(eventLength, 1)

            if metaEventKind == "ChanPrfx":
                self._writeIntBytes(int(argumentList[0]) - 1, 1)
            elif metaEventKind in ["SeqNum", "Tempo"]:
                self._writeIntBytes(int(argumentList[0]), eventLength)
            elif metaEventKind == "SMPTEOffset":
                argumentList = map(lambda x: int(x[3:]), argumentList)
                for i in range(len(argumentList)):
                    self._writeIntBytes(argumentList[i], 1)
            elif metaEventKind == "TimeSig":
                numerator, denominator = argumentList[0].split("/")
                numerator = int(numerator)
                denominator = int(denominator)
                denominator = [0, 0, 1, 1, 2, 2, 2, 2, 3][denominator]
                self._writeIntBytes(numerator, 1)
                self._writeIntBytes(denominator, 1)
                self._writeIntBytes(int(argumentList[1]), 1)
                self._writeIntBytes(int(argumentList[2]), 1)
            elif metaEventKind == "KeySig":
                key = argumentList[0]
                isMinor = key.endswith("m")
                key = (iif(isMinor, key[:-1], key) + " ")[0:2]
                accidentalCount = cls._keyList.index(key) // 2
                accidentalCount = iif(isMinor, accidentalCount - 3,
                                      accidentalCount) - 7
                self._writeIntBytes(accidentalCount, 1, isSigned=True)
                self._writeIntBytes(iif(isMinor, 1, 0), 1)

        isTrackEnd = (metaEventKind == "TrkEnd")
        Logging.trace("<<: isTrackEnd = %s", isTrackEnd)
        return isTrackEnd

    #--------------------

    def _writeMidiHeader (self):
        """Converts head line in <self._lineList> at <self._position>
           to midi stream and appends to <self._byteList>"""

        currentLine = self._peekLine()
        Logging.trace(">>: %d - %s", self._position, currentLine)

        cls = self.__class__
        currentLine = self._getLine()
        partList = currentLine.split(" ")
        Assertion.check(len(partList) == 4, "bad MIDI header format")

        headerLength = 6
        fileFormat   = int(partList[1])
        trackCount   = int(partList[2])
        timeDivision = int(partList[3])

        self._writeStringBytes(cls._fileHead)
        self._writeIntBytes(headerLength, 4)
        self._writeIntBytes(fileFormat, 2)
        self._writeIntBytes(trackCount, 2)
        self._writeIntBytes(timeDivision, 2)

        Logging.trace("<<")
        return trackCount

    #--------------------

    def _writeMidiEvent (self):
        """Converts current midi event in <self._lineList> at
           <self._position> to midi stream and appends to
           <self._byteList>"""

        Logging.trace(">>: %d - %s", self._position, self._peekLine())

        cls = self.__class__
        currentLine = self._peekLine()
        partList = self._tokenize(currentLine)

        absoluteTime = int(partList[0])
        eventKind    = partList[1]
        Logging.trace("--: t=%d, ev='%s'", absoluteTime, eventKind)

        Assertion.check(absoluteTime >= self._currentTime,
                        "absolute time in file must be ascending")
        Assertion.check(eventKind in cls._eventKindToByteMap,
                        "event kind unknown: '%s'" % eventKind)

        self._writeVariableBytes(absoluteTime - self._currentTime)
        self._currentTime = absoluteTime

        eventByte   = cls._eventKindToByteMap[eventKind]
        eventLength = cls._eventKindToLengthMap[eventKind]

        if eventLength in ["R", "V"]:
            argumentList = partList[2:]
        else:
            channel = int(partList[2][3:]) - 1
            eventByte = eventByte | (channel & 15)
            argumentList = partList[3:]

        self._writeIntBytes(eventByte, 1)
        isTrackEnd = False

        if eventLength == "R":
            # meta event
            isTrackEnd = self._writeMetaEvent(argumentList)
        else:
            if eventLength == "V":
                # sysex start or sysex end
                self._writeVariableBytes(len(argumentList))
            else:
                # channel message => convert all arguments to int strings
                argumentList = map(lambda x: x.split("=")[1], argumentList)

            self._writeListBytes(argumentList)

        self._position += 1
        Logging.trace("<<: isTrackEnd = %s", isTrackEnd)
        return isTrackEnd

    #--------------------

    def _writeMidiTrack (self):
        """Converts track in <self._lineList> starting at
           <self._position> to midi stream and appends to
           <self._byteList>"""

        Logging.trace(">>: %d", self._position)

        cls = self.__class__

        header = self._getLine()
        Assertion.check(header == cls._trackHead,
                        "track header chunk expected")
        self._writeStringBytes(header)

        # keep current position for later length insertion
        chunkLengthPosition = len(self._byteList)

        # process all event lines
        self._currentTime = 0
        isDone = False

        while not isDone:
            isDone = self._writeMidiEvent()

        # skip over "TrkEnd" line
        trkEndLine = self._getLine()
        Assertion.check(trkEndLine == cls._trackEndMarker,
                        "track end of chunk expected")

        # insert length indication
        Logging.trace("--: breaking up at %d", chunkLengthPosition)
        trackData      = self._byteList[chunkLengthPosition:]
        self._byteList = self._byteList[:chunkLengthPosition]
        self._writeIntBytes(len(trackData), 4)
        self._byteList += trackData
        
        Logging.trace("<<")

    #--------------------

    def _writeStringBytes (self, st):
        """Writes integer <value> as <count> bytes and appends to
           <self._byteList>"""

        self._appendToByteList(stringToIntList(st))

    #--------------------

    def _writeVariableBytes (self, value):
        """Writes integer <value> as bytes and appends to
           <self._byteList> using a variable number of bytes"""

        Logging.trace(">>: %08X", value)

        isDone = False
        partList = []

        while not isDone:
            partialValue = value % 128 + 128
            value = value // 128
            isDone = (value == 0)
            partList = [ partialValue ] + partList

        partList[len(partList) - 1] -= 128

        self._appendToByteList(partList)
        Logging.trace("<<")

    #--------------------
    # EXPORTED FEATURES
    #--------------------

    def __init__ (self):
        """Initializes file handler object"""

        self._position    = None
        self._byteList    = None
        self._lineList    = None
        self._currentTime = None
        
    #--------------------

    def readFile (self, fileName):
        """Reads a midi file and returns a text representation as a
           line list."""

        Logging.trace(">>: %s", fileName)

        midiFile = UTF8File(fileName, "rb")
        self._byteList = bytearray(midiFile.read())
        midiFile.close()

        self._convertByteListToLineList()

        Logging.trace("<<")
        return self._lineList

    #--------------------

    def writeFile (self, fileName, lineList):
        """Writes a midi file from text representation <lineList>"""

        Logging.trace(">>: %s", fileName)

        self._lineList = lineList

        for currentLine in lineList:
            Logging.trace("--: %s", currentLine)
            
        self._convertLineListToByteList()

        midiFile = UTF8File(fileName, "wb")
        midiFile.write(bytearray(self._byteList))
        midiFile.close()

        Logging.trace("<<")
