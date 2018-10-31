# -*- coding: utf-8-unix -*-
# midiTransformer -- processes midi file and provides several
#                    transformations on it (e.g. drum humanization,
#                    volume adaptation, etc.)
#
# author: Dr. Thomas Tensi, 2006 - 2016

#====================
# IMPORTS
#====================

from datetime import datetime
import random
import re

from basemodules.operatingsystem import OperatingSystem
from basemodules.simpleassertion import Assertion
from basemodules.simplelogging import Logging
from basemodules.stringutil import convertStringToMap
from basemodules.ttbase import adaptToRange, iif, iif2, isInRange, MyRandom
from basemodules.validitychecker import ValidityChecker

from .midifilehandler import MidiFileHandler

#====================

_infinity = 999999999
_humanizationStyleNameToTextMap = {}
_humanizedTrackNameSet = set()
_voiceNameToVariationFactorMap  = {}

#====================

class _LineBuffer:
    """This class is a utility for providing buffered output to a line
       list.  The line list is given upon construction of the buffer
       and the buffer may be manipulated, cleared or appended to the
       line list."""

    #--------------------

    def __init__ (self, associatedLineList):
        """Prepares <self> as a buffer for <associatedLineList>"""

        self._info = []
        self._isActive = False
        self._lineList = associatedLineList
        
    #--------------------

    def activate (self, isActive):
        """Activates or deactivates <self> depending on <isActive>."""

        self._isActive = isActive

    #--------------------

    def clear (self):
        """Resets <self> to an empty buffer."""

        self._info = []

    #--------------------

    def flush (self):
        """Appends all data from <self> to associated line list and
           sets <self> inactive."""

        self._lineList.extend(self._info)
        self.clear()
        self.activate(False)

    #--------------------

    def length (self):
        """Returns count of lines in <self>."""

        return len(self._info)
 
    #--------------------

    def lineList (self):
        """Returns list of lines in <self>."""

        return self._info
 
    #--------------------

    def pop (self):
        """Removes first element in buffer."""

        self._info.pop(0)

    #--------------------

    def prepend (self, currentLine):
        """Prepends <currentLine> to buffer as first line."""

        self._info.insert(0, currentLine)

    #--------------------

    def writeLine (self, currentLine):
        """Adds <currentLine> as last line in buffer (when active) or
           as last line in associated line list (when buffer is
           inactive)."""

        if self._isActive:
            self._info.append(currentLine)
        else:
            self._lineList.append(currentLine)


#====================
# MusicTime
#====================

class _MusicTime:
    """This module encapsulates the handling of positions within a
       measure as well as the conversion between MIDI time and musical
       time."""

    _quartersPerMeasure = None
    _separator = ":"
    _ticksPerQuarterNote = None

    semibreveDuration    = None
    quarterDuration      = None
    sixteenthDuration    = None
    thirtysecondDuration = None

    firstPosition = None
    
    #--------------------

    @classmethod
    def initialize (cls, ticksPerQuarterNote, quartersPerMeasure):
        """Sets values for <ticksPerQuarterNote> and
           <quartersPerMeasure>"""

        Logging.trace(">>: tpq = %d, qpm = %s",
                      ticksPerQuarterNote, quartersPerMeasure)
 
        cls._quartersPerMeasure   = quartersPerMeasure
        cls._ticksPerQuarterNote  = ticksPerQuarterNote

        cls.measureDuration      = _MusicTime("1:0:0:0", True)
        cls.semibreveDuration    = _MusicTime("0:4:0:0", True)
        cls.quarterDuration      = cls.semibreveDuration.multiply(0.25)
        cls.sixteenthDuration    = cls.quarterDuration.multiply(0.25)
        cls.thirtysecondDuration = cls.quarterDuration.multiply(0.125)

        cls.firstPosition = _MusicTime("1:1:1:1", False)

        Logging.trace("<<")
    
    #--------------------

    def __init__ (self, value, isDuration):
        """Creates a music time object, which is either a time or a
           duration"""

        self._isDuration = isDuration
        self._data       = value

    #--------------------

    def __str__ (self):
        """Returns the string representation of a music time object"""

        return ("MusicTime(%s/%s)"
                % (self._data, iif(self._isDuration, "du", "tm")))

    #--------------------

    def absolute (self):
        """Calculates absolute value of <self>"""

        result = _MusicTime(self._isDuration)

        if self._data.startswith("-"):
            result._data = self._data[1:]
        else:
            result._data = self._data

        return result

    #--------------------

    def add (self, duration):
        """Returns sum of <self> and <duration>"""

        Logging.trace(">>: time = %s, duration = %s", self, duration)

        Assertion.pre(not self._isDuration and duration._isDuration,
                      "bad parameters for add")

        cls = self.__class__

        midiTime       = self.toMidiTime()
        midiDuration   = duration.toMidiTime()
        midiResultTime = midiTime + midiDuration

        result = cls.fromMidiTime(midiResultTime, False)

        Logging.trace("<<: %s", result)
        return result

    #--------------------

    @classmethod
    def fromMidiTime (cls, midiTime, isDuration):
        """Splits up absolute midi time in <midiTime> into measure
           number, quarter number within measure, sixteenth number
           within quarter and remainder ticks; counting starts with 1
           for a time and with 0 for a duration; result is returned as
           a music time; also assumes that <quartersPerMeasure>
           contains the right number of quarters within a measure"""

        ##Logging.trace(">>: midiTime = %d, isDuration = %s",
        ##              midiTime, isDuration)

        isNegative = (midiTime < 0)
        remainingMidiTime = round(abs(midiTime))
        ticksPerQuarterNote = cls._ticksPerQuarterNote

        factorList = [ ticksPerQuarterNote * cls._quartersPerMeasure,
                       ticksPerQuarterNote, ticksPerQuarterNote // 4, 1 ]
        partList = []

        for factor in factorList:
            part = round(remainingMidiTime / factor)
            remainingMidiTime -= factor * part
            partList.append(part)
        
        measure, quarter, sixteenth, remainder = partList

        if not isDuration:
            measure   += 1
            quarter   += 1
            sixteenth += 1
            remainder += 1

        st = ("%s%s%s%s%s%s%s%s"
              % (iif(isNegative, "-", ""),
                 measure, cls._separator,
                 quarter, cls._separator,
                 sixteenth, cls._separator,
                 remainder))
        result = _MusicTime(st, isDuration)

        ##Logging.trace("<<: %s", str(result))
        return result

    #--------------------

    def isAt (self, reference, rasterSize):
        """Tells whether <self> is near <reference> for some measure where
           <reference> is given as float factor of a semibreve; must
           be within a symmetric interval of <rasterSize>; a
           wraparound at the measure boundary is accounted for"""

        Logging.trace(">>: %s, reference = %s, rasterSize = %s",
                      self, reference, rasterSize)
        Assertion.pre(not self._isDuration, "first parameter must be a time")

        cls = self.__class__

        tpqn = cls._ticksPerQuarterNote

        # find relative position in midi ticks
        measure, _ = self._data.split(cls._separator, 1)
        measure = int(measure)

        midiMeasureDuration = round(cls._quartersPerMeasure * tpqn)
        midiTime = (self.toMidiTime() - (measure - 1) * midiMeasureDuration)

        # check whether relative position is near <referenceTime>
        midiReferenceTime   = round(4 * tpqn * reference)
        midiHalfRasterSize  = round(4 * tpqn * rasterSize / 2.0)

        Logging.trace("--: midiTime = %d, midiReferenceTime = %d,"
                      + " midiHalfRaster = %d, midiMeasure = %d,"
                      + " qpm = %s, tpqn = %d",
                      midiTime, midiReferenceTime,
                      midiHalfRasterSize, midiMeasureDuration,
                      cls._quartersPerMeasure, tpqn)

        # check positive range
        midiOtherTime = midiReferenceTime + midiHalfRasterSize
        isNear = isInRange(midiTime, midiReferenceTime, midiOtherTime)
        Logging.trace("--: midiOtherTimeA = %d, isNear = %s",
                      midiOtherTime, isNear)

        if not isNear and midiOtherTime > midiMeasureDuration:
            # wraparound
            midiOtherTime -= midiMeasureDuration
            isNear = isInRange(midiTime, 0, midiOtherTime)
            Logging.trace("--: midiOtherTimeB = %d, isNear = %s",
                          midiOtherTime, isNear)
            
        # check negative range
        if not isNear:
            midiOtherTime = midiReferenceTime - midiHalfRasterSize
            isNear = isInRange(midiTime, midiOtherTime, midiReferenceTime)
            Logging.trace("--: midiOtherTimeC = %d, isNear = %s",
                          midiOtherTime, isNear)
            
            if not isNear and midiOtherTime < 0:
                # wraparound
                midiOtherTime += midiMeasureDuration
                isNear = isInRange(midiTime, midiOtherTime, midiMeasureDuration)
                Logging.trace("--: midiOtherTimeD = %d, isNear = %s",
                              midiOtherTime, isNear)
            
        result = isNear
        Logging.trace("<<: %s", result)
        return result

    #--------------------

    def measure (self):
        """Tells the measure of <self>"""

        Assertion.pre(not self._isDuration, "parameter must be a time")
        cls = self.__class__
        separatorPosition = self._data.find(cls._separator)
        result = int(self._data[:separatorPosition])
        return result

    #--------------------

    def normalize (self):
        """Calculates a standard representation of <self> and returns
           it"""

        Assertion.pre(not self._isDuration, "parameter must be a time")
        cls = self.__class__
        midiTime = self.toMidiTime()
        return cls.fromMidiTime(midiTime, False)

    #--------------------

    def multiply (self, factor):
        """Does a scalar multiplication of duration <self> by <factor>
           and returns scaled duration"""

        Logging.trace(">>: duration = %s, factor = %f", self, factor)
        Assertion.pre(self._isDuration, "parameter must be a duration")

        cls = self.__class__
        midiDuration = self.toMidiTime()
        result = cls.fromMidiTime(round(midiDuration * factor), True)

        Logging.trace("<<: %s", str(result))
        return result

    #--------------------

    def subtract (self, other):
        """Calculates difference of <self> and <other> and returns a
           duration"""

        Logging.trace(">>: %s, %s", self, other)

        cls = self.__class__
        midiTimeA = self.toMidiTime()
        midiTimeB = other.toMidiTime()
        midiDuration = midiTimeA - midiTimeB
        result = cls.fromMidiTime(midiDuration, True)

        Logging.trace("<<: %s", result)
        return result

    #--------------------

    def toMidiTime (self):
        """Converts <self> into midi time and returns value; assumes
           that <quartersPerMeasure> contains the right number of
           quarters within a measure; if <self._isDuration> is true,
           given time is a duration (starting at '0:0:0:0')"""

        ##Logging.trace(">>: %s", str(self))

        cls = self.__class__
        isNegative = self._data.startswith("-")
        timeString = iif(isNegative, self._data[1:], self._data)
        timePartList = timeString.split(cls._separator)

        if not self._isDuration:
            for i in range(len(timePartList)):
                # for a time: make all entries in part list zero-based
                # instead of one-based
                timePartList[i] = str(int(timePartList[i]) - 1)

        result = ((((int(timePartList[0]) * cls._quartersPerMeasure
                     + int(timePartList[1])) * 4
                    + int(timePartList[2])) * cls._ticksPerQuarterNote // 4)
                  + int(timePartList[3]))
        result = round(iif(isNegative, -result, result))

        ##Logging.trace("<<: %d", result)
        return result

#====================

class _HumanizationStyle:
    """This class encapsulates all services for midi track
       humanization. The style describes how many count-in measures
       are skipped, how the timing and the velocity may be changed
       depending on the position of a hit within a measure."""

    defaultStyleName = "humanizationStyleDefault"
    _defaultStyleAsString = \
        ("{ 0.00: 1.15/0, 0.25: 1/0.2, 0.50: 1.1/0.2, 0.75: 1/0.2,"
         + "  OTHER: 0.85/B0.25,"
         + "  RASTER: 0.03125, SLACK:0.1 }")
    _velocityAndTimingSeparator = "/"

    #--------------------
    # EXPORTED FEATURES
    #--------------------

    @classmethod
    def initialize (cls):
        """Fills mapping from style name to associated style
           string from configuration file"""

        Logging.trace(">>")

        scriptFilePath = OperatingSystem.scriptFilePath()
        scriptFileDirectoryPath = OperatingSystem.dirname(scriptFilePath)

        Logging.trace("<<")

    #--------------------

    def __init__ (self, styleName):
        """Finds style for given <styleName> and returns it as a
           structure; if name is unknown, returns None"""

        Logging.trace(">>: %s", styleName)

        cls = self.__class__
        humanizationStyleNameList = _humanizationStyleNameToTextMap.keys()

        if styleName in humanizationStyleNameList:
            styleAsString = _humanizationStyleNameToTextMap[styleName]
        else:
            Logging.trace("--: could not find style name %s", styleName)

            if cls.defaultStyleName in humanizationStyleNameList:
                styleAsString = \
                    _humanizationStyleNameToTextMap[cls.defaultStyleName]
            else:
                styleAsString = cls._defaultStyleAsString

        style = convertStringToMap(styleAsString)
        Logging.trace("--: style = %s", style)

        rasterSize = style.get("RASTER", "0.03125")
        ValidityChecker.isNumberString(rasterSize,
                                       "raster invalid in '%s'" % styleName,
                                       True)
        rasterSize = float(rasterSize)

        slackValue = style.get("SLACK")
        ValidityChecker.isNumberString(slackValue,
                                       "slack invalid in '%s'" % styleName,
                                       True)
        slackValue = float(slackValue)
        
        self._name                           = styleName
        self._rasterSize                     = rasterSize
        self._slack                          = slackValue
        self._positionToDirectionMap         = {}
        self._positionToTimeVariationMap     = {}
        self._positionToVelocityVariationMap = {}
        self._validPositions                 = []

        keyList = style.keys()
        separator = cls._velocityAndTimingSeparator

        # velocity and timing definition
        for positionKey in keyList:
            velocityAndTiming = style[positionKey]

            if positionKey in ["RASTER", "SLACK"]:
                continue
            elif positionKey != "OTHER":
                positionKey = float(positionKey)
                self._validPositions.append(positionKey)

            Logging.trace("--: position = %s, value = %s",
                          positionKey, velocityAndTiming)
            Assertion.check(separator in velocityAndTiming,
                            "bad value for %s in %s"
                            % (positionKey, styleName))
            velocity, timing = velocityAndTiming.split(separator)
            direction = timing[0]

            if direction not in "AB":
                direction = ""
            else:
                timing = timing[1:]

            velocity = float(velocity)
            timing   = float(timing)

            self._positionToVelocityVariationMap[positionKey] = velocity
            self._positionToDirectionMap[positionKey]         = direction
            self._positionToTimeVariationMap[positionKey]     = timing
            Logging.trace("--: %s -> %4.2f/%s%4.2f",
                          positionKey, velocity, direction, timing)

        Logging.trace("<<: %s", self)

    #--------------------

    def __str__ (self):
        """Returns the string representation of <self>"""

        st = ("_HumanizationStyle(%s,"
              + " RASTER = %s, SLACK = %s,"
              + " VELOCITY = %s, DIRECTIONS = %s, TIMING = %s)")
        result = st % (self._name,
                       self._rasterSize, self._slack,
                       self._positionToVelocityVariationMap,
                       self._positionToDirectionMap,
                       self._positionToTimeVariationMap)
        return result
    
    #--------------------

    def hasDirectionalShiftAt (self, eventPositionInMeasure):
        """Tells whether there is a directional timing shift at
           <eventPositionInMeasure> and returns it"""

        Logging.trace(">>: %s", eventPositionInMeasure)
        result = self._positionToDirectionMap[eventPositionInMeasure]
        Logging.trace("<<: %s", result)
        return result

    #--------------------

    @classmethod
    def instrumentVariationFactors (cls, instrumentName):
        """Returns the instrument specific variation factors
           for <instrumentName>"""

        Logging.trace(">>: %s", instrumentName)
        result = _voiceNameToVariationFactorMap.get(instrumentName,
                                                    [1.0,1.0])
        Logging.trace("<<: [%4.3f, %4.3f]", result[0], result[1])
        return result

    #--------------------

    def keys (self):
        """Returns all time positions"""

        return self._validPositions

    #--------------------

    def timingVariationFactor (self, eventPositionInMeasure):
        """Returns the associated timing variation factor (in percent)
           for the <eventPositionInMeasure>"""

        Logging.trace(">>: %s", eventPositionInMeasure)
        result = self._positionToTimeVariationMap.get(eventPositionInMeasure, 0)
        Logging.trace("<<: %s", result)
        return result

    #--------------------

    def raster (self):
        """Returns the raster of current style"""

        Logging.trace(">>")
        result = self._rasterSize
        Logging.trace("<<: %s", result)
        return result

    #--------------------

    def velocityFactor (self, eventPositionInMeasure):
        """Returns the associated velocity factor (in percent) for the
           <eventPositionInMeasure>"""

        Logging.trace(">>: %s", eventPositionInMeasure)
        result = self._positionToVelocityVariationMap \
                     .get(eventPositionInMeasure, 0)
        Logging.trace("<<: %s", result)
        return result

    #--------------------

    def velocitySlack (self):
        """Returns the associated slack (in percent)"""

        Logging.trace(">>")
        result = self._slack
        Logging.trace("<<: %s", result)
        return result

#====================

class _Humanizer:
    """This class encapsulates the service for humanization of one or
       more MIDI event lists based on a humanization style.  It
       uses an internal event list and processes each single
       note-on/note-off event as well as the timing of other events."""

    _quartersPerMeasure = None
    _countInMeasureCount = 0
    
    #--------------------

    class _HumanizerEvent:
        """This class defines a single event in the event list of the
           humanizer."""

        def __init__ (self):
            self.midiTime = None
            self.text     = None
            self.kind     = None
            self.channel  = None
            self.note     = None
            self.velocity = None
            self.partner  = None
    
        #--------------------

        def __str__ (self):
            st = ("_HumanizerEvent(midiTime = %s, text = '%s', kind = %s,"
                  + " channel = %s, note = %s, velocity = %s, partner = %s)")
            return (st % (self.midiTime, self.text, self.kind, self.channel,
                          self.note, self.velocity, self.partner))

    #--------------------
    # LOCAL FEATURES
    #--------------------

    def _adjustTiming (self, eventIndex, musicTime, eventPositionInMeasure,
                       instrumentTimingVariationFactor):
        """Adjusts timing of note event given at <eventIndex> with
           parameters <musicTime> and <noteKind>;
           <instrumentTimingVariationFactor> gives an instrument
           specific factor"""

        Logging.trace(">>: index = %d, time = %s, positionInMeasure = %s,"
                      + " instrumentTimingVariation = %4.3f",
                      eventIndex, musicTime, eventPositionInMeasure,
                      instrumentTimingVariationFactor)

        cls = self.__class__
        result = None
        timeAsString = str(musicTime)
        style = self._styleForTime(musicTime)
        effectiveMeasureIndex = musicTime.measure() - cls._countInMeasureCount

        if effectiveMeasureIndex <= 0:
            # leave as is, because those measures are count-ins
            result = musicTime
        elif timeAsString in self._timeToAdjustedTimeMap:
            # we already have seen this event time => reuse cached value
            result = self._timeToAdjustedTimeMap[timeAsString]
        else:
            direction = style.hasDirectionalShiftAt(eventPositionInMeasure)
            variationFactor = \
                style.timingVariationFactor(eventPositionInMeasure)
            variationDuration = \
                _MusicTime.thirtysecondDuration.multiply(variationFactor)

            # do a random variation with a square distribution
            randomFactor = cls._squaredrand() * 2 - 1

            # if ahead or behind, adapt the random factor
            randomFactor = iif2(direction == "A", -abs(randomFactor),
                                direction == "B",  abs(randomFactor),
                                randomFactor)

            # adjust by instrument
            randomFactor *= instrumentTimingVariationFactor
            variationDuration = variationDuration.multiply(randomFactor)
            result = musicTime.add(variationDuration)
            self._timeToAdjustedTimeMap[timeAsString] = result

        Logging.trace("<<: %s", str(result))
        return result

    #--------------------

    def _adjustVelocity (self, eventIndex, musicTime, velocity,
                         eventPositionInMeasure,
                         instrumentVelocityVariationFactor):
        """Adjusts velocity of note event given at <eventIndex> with
           parameters <musicTime> and <noteKind>;
           <instrumentTimingVariationFactor> gives an instrument
           specific factor"""

        Logging.trace(">>: index = %d, time = %s, velocity = %d,"
                      + " positionInMeasure = %s,"
                      + " instrumentVelocityVariation = %4.3f",
                      eventIndex, musicTime, velocity, eventPositionInMeasure,
                      instrumentVelocityVariationFactor)

        cls = self.__class__
        result = None
        style = self._styleForTime(musicTime)
        effectiveMeasureIndex = musicTime.measure() - cls._countInMeasureCount

        if effectiveMeasureIndex <= 0:
            # leave as is, because those measures are count-ins
            result = velocity
        else:
            factor = style.velocityFactor(eventPositionInMeasure)
            slack  = style.velocitySlack()

            # randomFactor shall be between -1 and 1
            randomFactor = cls._squaredrand() * 2 - 1
            # adjust by instrument
            randomFactor *= instrumentVelocityVariationFactor
            factor += randomFactor * slack
            velocity = int(velocity * factor)
            velocity = adaptToRange(velocity, 0, 127)
            result = velocity

        Logging.trace("<<: %d", result)
        return result

    #--------------------

    def _asLineList (self):
        """Converts internal event list containing MIDI events into a
           text line list"""

        Logging.trace(">>")

        result = []

        for event in self._eventList:
            midiTime = event.midiTime
            currentLine = iif(isInRange(midiTime, 0, _infinity - 1),
                              str(midiTime) + " ", "")

            if event.kind not in ["On", "Off"]:
                currentLine += event.text
            else:
                currentLine += ("On ch=%d n=%d v=%d"
                                % (event.channel, event.note, event.velocity))

            result.append(currentLine)
            Logging.trace("--: %s", currentLine)
        
        Logging.trace("<<")
        return result

    #--------------------

    def _convertToEventList (self, lineList):
        """Converts <lineList> containing MIDI events into the
           internal event list"""

        Logging.trace(">>")

        cls = self.__class__
        eventCount = len(lineList)
        noteToStartIndexMap = {}

        # split MIDI event lines into time and event text part
        # and process note on and note off events
        for i in range(eventCount):
            currentLine = lineList[i]

            if " " in currentLine:
                midiTime, st = currentLine.split(" ", 1)
                midiTime = int(midiTime)
                tokenList = st.split(" ")
                kind = tokenList[0]
            else:
                st = currentLine
                midiTime = iif(currentLine == "MTrk", -1, _infinity)
                kind = "special"

            channel      = None
            affectedNote = None
            velocity     = None
            partner      = None

            if kind in ["On", "Off"]:
                channel      = int((tokenList[1])[3:])
                affectedNote = int((tokenList[2])[2:])

                if kind == "On":
                    if tokenList[-1] == "v=0":
                        kind = "Off"
                    else:
                        # note on event
                        noteToStartIndexMap[affectedNote] = i
                        velocity = int((tokenList[3])[2:])
                        partner  = 0

                if kind == "Off":
                    velocity = 0

                    if affectedNote in noteToStartIndexMap:
                        j = noteToStartIndexMap[affectedNote]
                        partner = j
                        self._eventList[j].partner = i
                        del noteToStartIndexMap[affectedNote]

            event = cls._HumanizerEvent()

            event.midiTime = midiTime
            event.text     = st
            event.kind     = kind
            event.channel  = channel
            event.note     = affectedNote
            event.velocity = velocity
            event.partner  = partner
            Logging.trace("--: event = %s", str(event))
            self._eventList.append(event)

        Logging.trace("<<")
    
    #--------------------

    @classmethod
    def _findCanonicalTrackName (cls, trackName):
        """Returns track name without any suffixes appended for
           multiple MIDI tracks of the same instrument."""

        # TODO: something must be done here
        return trackName

    #--------------------

    def _findEventPositionInMeasure (self, musicTime):
        """Finds position of event within measure and returns it as
           a float value"""

        Logging.trace(">>: %s", musicTime)

        cls = self.__class__
        result = None
        style = self._styleForTime(musicTime)
        rasterSize = style.raster()

        # traverse all time positions
        for position in style.keys():
            if musicTime.isAt(position, rasterSize):
                result = position
                break

        result = iif(result is None, "OTHER", result)
        Logging.trace("<<: %s", result)
        return result
    
    #--------------------
    
    def _processEventList (self, trackName):
        """Traverses all events in the internal list and shapes note
           events"""

        Logging.trace(">>: %s", trackName)

        instrumentVelocityVariationFactor, \
        instrumentTimingVariationFactor = \
            _HumanizationStyle.instrumentVariationFactors(trackName)
        eventCount = len(self._eventList)
        noteToStartIndexMap = {}

        for i in reversed(range(eventCount)):
            event    = self._eventList[i]
            midiTime = event.midiTime

            if event.kind not in ["On", "Off"]:
                result = self._timeToAdjustedTimeMap.get(str(midiTime),
                                                         midiTime)
            elif event.kind == "On":
                partnerEvent  = self._eventList[event.partner]
                note          = event.note
                startMidiTime = event.midiTime
                endMidiTime   = partnerEvent.midiTime
                midiDuration  = endMidiTime - startMidiTime
                self._processSingleEvent(i, startMidiTime, note,
                                         event.velocity, midiDuration,
                                         instrumentVelocityVariationFactor,
                                         instrumentTimingVariationFactor)

                if note in noteToStartIndexMap:
                    # check whether there is an overlap to following
                    # note of same pitch
                    j                  = noteToStartIndexMap[note]
                    nextNoteEvent      = self._eventList[j]
                    otherStartMidiTime = nextNoteEvent.midiTime

                    if otherStartMidiTime <= endMidiTime:
                        # clip
                        partnerEvent.midiTime = otherStartMidiTime - 1
                        Logging.trace("--: corrected overlap of next"
                                      + " %d (%d) into %d (%d)",
                                      j, otherStartMidiTime, i, endMidiTime)

                noteToStartIndexMap[note] = i

        Logging.trace("<<")

    #--------------------

    def _processSingleEvent (self, eventIndex, midiTime, note, velocity,
                             midiDuration, instrumentVelocityVariation,
                             instrumentTimingVariation):
        """Humanizes note event given at <eventIndex> with parameters
           <midiTime>, <note>, <velocity> and <midiDuration>;
           <instrumentVelocityVariation> and
           <instrumentTimingVariation> give the instrument specific
           factors for the variation"""

        Logging.trace(">>: index = %d, midiTime = %s,"
                      + " note = %s, velocity = %s,"
                      + " midiDuration = %s, instrumentVelocityVariation = %s,"
                      + " instrumentTimingVariation = %s",
                      eventIndex, midiTime, note, velocity,
                      midiDuration, instrumentVelocityVariation,
                      instrumentTimingVariation)

        musicTime  = _MusicTime.fromMidiTime(midiTime, False)
        style = self._styleForTime(musicTime)
        eventPositionInMeasure = self._findEventPositionInMeasure(musicTime)

        velocity          = self._adjustVelocity(eventIndex, musicTime, velocity,
                                                 eventPositionInMeasure,
                                                 instrumentVelocityVariation)
        musicTime         = self._adjustTiming(eventIndex, musicTime,
                                               eventPositionInMeasure,
                                               instrumentTimingVariation)

        event = self._eventList[eventIndex]
        event.midiTime = musicTime.toMidiTime()
        event.velocity = velocity

        Logging.trace("<<: %s", event)

    #--------------------

    def _sortEventList (self):
        """Sorts events in <eventList> by time"""

        Logging.trace(">>")

        kindOrder = { "special":0, "Meta":1, "PrCh":2, "Par":3, "KeySig":4,
                      "TimeSig":5, "Tempo":6, "Off":7, "On":8 }
        trackEndMetaEventText = "Meta TrkEnd"
        keyExtractionProc = (lambda x:
                             iif(x.text == trackEndMetaEventText, _infinity,
                                 x.midiTime * 10 + kindOrder[x.kind]))
        self._eventList.sort(key=keyExtractionProc)

        Logging.trace("<<")

    #--------------------

    @classmethod
    def _squaredrand (cls):
        """Returns a random distribution around 0.5 with a root
           probability density around 0.5"""

        result = MyRandom.random()
        result = result * 2 - 1
        sign = iif(result < 0, -1, 1)
        result =  sign * result * result
        result = result / 2.0 + 0.5
        Logging.trace("--: %f", result)
        return result

    #--------------------

    def _styleForMeasure (self, measureIndex):
        """Returns style that is valid at given <measureIndex>"""

        if measureIndex in self._measureToHumanizationStyleMap:
            result = self._measureToHumanizationStyleMap[measureIndex]
        else:
            if measureIndex > 1:
                result = self._styleForMeasure(measureIndex - 1)
            else:
                styleName = _HumanizationStyle.defaultStyleName
                result    = _HumanizationStyle(styleName)

            self._measureToHumanizationStyleMap[measureIndex] = result

        return result

    #--------------------

    def _styleForTime (self, musicTime):
        """Returns style that is valid at given <musicTime>"""

        Logging.trace(">>: %s", musicTime)

        cls = self.__class__
        effectiveMeasureIndex = musicTime.measure() - cls._countInMeasureCount
        result = self._styleForMeasure(effectiveMeasureIndex)

        Logging.trace("<<: %s", result._name)
        return result

    #--------------------
    # EXPORTED FEATURES
    #--------------------

    @classmethod
    def initialize (cls, quartersPerMeasure, countInMeasureCount):
        """Sets value for <quartersPerMeasure> and <countInMeasureCount>"""

        Logging.trace(">>: qpm = %s, countIn = %d",
                      quartersPerMeasure, countInMeasureCount)

        cls._quartersPerMeasure  = quartersPerMeasure
        cls._countInMeasureCount = countInMeasureCount
        MyRandom.initialize()

        Logging.trace("<<")
    
    #--------------------

    def __init__ (self):
        """Initializes event humanizer; provides a list of tuples
           for storing midi events; the tuple contains
             - midiTime:   the MIDI time
             - text:       the event without time as a text string
             - kind:       information whether event is a 'note on',
                           'note off' or 'other'
             for a 'note on' or 'note off' event we additionally have
               - note:     the MIDI pitch
             for a 'note on' event we additionally have
               - velocity: the MIDI velocity
               - partner:  the index of the closing note off event"""

        Logging.trace(">>")

        self._measureToHumanizationStyleMap = {}
        self._eventList                     = []

        # the following map takes a simplified track name (like
        # keyboard) and associates a midi time to shifted time map to
        # keep different tracks for the same instrument synchronous in
        # timing (but not in velocity!)
        self._canonicalTrackNameToTimingMap = {}

        # the following map is always reset when another track is
        # processed
        self._timeToAdjustedTimeMap = None

        Logging.trace("<<")

    #--------------------

    def process (self, trackName, lineList, measureToHumanizationStyleMap):
        """Humanizes MIDI event <lineList> based on map
           <measureToHumanizationStyleMap> from measure to style
           name and returns resulting event line list"""

        Logging.trace(">>: trackName = %s, measureToStyleMap = %s",
                      trackName, measureToHumanizationStyleMap)

        cls = self.__class__
        canonicalTrackName = cls._findCanonicalTrackName(trackName)

        self._eventList = []
        self._measureToHumanizationStyleMap = measureToHumanizationStyleMap
        self._timeToAdjustedTimeMap = \
            self._canonicalTrackNameToTimingMap.get(canonicalTrackName, {})
        self._convertToEventList(lineList)
        self._processEventList(trackName)
        self._canonicalTrackNameToTimingMap[canonicalTrackName] = \
             self._timeToAdjustedTimeMap

        self._sortEventList()
        result = self._asLineList()

        Logging.trace("<<")
        return result

#====================

class _ParseState:
    """Enumeration type for midi text line parsers"""

    afterSettings     = "_ParseState.afterSettings"
    inBadTrack        = "_ParseState.inBadTrack"
    inFirstTrack      = "_ParseState.inFirstTrack"
    inInstrumentTrack = "_ParseState.inInstrumentTrack"
    inLimbo           = "_ParseState.inLimbo"
    inOtherTrack      = "_ParseState.inOtherTrack"
    inTrack           = "_ParseState.inTrack"
    inTrackPrefix     = "_ParseState.inTrackPrefix"

#====================

class MidiTransformer:
    """This class encapsulates the transformation of MIDI files by
       functions.  All transformation is done on a text representation
       that is finally converted back to the MIDI format."""

    _channelReferenceRegExp = re.compile(r" ch=(\d+)")
    _parameterChangeRegExp  = re.compile(r" Par ")
    _volumeChangeRegExp     = re.compile(r" Par .* c=7 ")
    _programChangeRegExp    = re.compile(r" PrCh ")
    _trackBeginRegExp       = re.compile(r"MTrk")
    _trackEndRegExp         = re.compile(r"TrkEnd")
    _trackNameRegExp        = re.compile(r"Meta TrkName +\"(.*)\"")

    #--------------------
    # LOCAL FEATURES
    #--------------------

    def _addMissingTrackNamesHandleTrackEnd (self, inFirstTrack, hasTrackName,
                                             inBadTrack, lineBuffer,
                                             trackCountMap, trackName,
                                             instrumentName):
        """Processes a track end when adding missing track names."""

        Logging.trace(">>")

        if inBadTrack:
            trackIsSkipped = True
        else:
            Logging.trace("--: %s", iif(inFirstTrack,
                                        "first track", "other track"))
            Logging.trace("--: %s%s", iif(not hasTrackName, "no ", ""),
                          "trackname found")

            if not hasTrackName and not inFirstTrack:
                Logging.trace("--: mapping instrument '%s'", instrumentName)
                trackName = self._instrumentNameToTrackName(instrumentName,
                                                            trackCountMap)
                lineBuffer.pop()
                lineBuffer.prepend("0 Meta TrkName \"" + trackName + "\"")
                lineBuffer.prepend("MTrk")

            if lineBuffer.length() >= 5:
                trackIsSkipped = False
            else:
                trackIsSkipped = True
                Logging.trace("--: very short track replaced by empty track")
      
        if not trackIsSkipped:
            Logging.trace("--: final track name = '%s'", trackName)
        else:
            Logging.trace("--: bad track => replaced by empty track")
            self._makeEmptyTrack(lineBuffer)

        lineBuffer.flush()

        Logging.trace("<<")

    #--------------------

    def _humanizeTrack (self, humanizer, trackName,
                        measureToHumanizationStyleMap,
                        trackLineList, lineList):
        """Humanizes entries in <trackLineList> by
           <measureToHumanizationStyleMap> and appends them to
           <lineList>"""

        Logging.trace(">>: measureToStyleMap = %s",
                      measureToHumanizationStyleMap)
        processedLineList = humanizer.process(trackName, trackLineList,
                                              measureToHumanizationStyleMap)
        lineList.extend(processedLineList)
        Logging.trace("<<")
        
    #--------------------

    def _instrumentNameToTrackName (self, instrumentName, trackCountMap):
        """Calculates track name for an anonymous track with
           instrument with <instrumentName>; <trackCountMap> gives the
           count of tracks with some track name"""

        Logging.trace(">>: %s", instrumentName)

        instrumentToTrackMap = { "power kit"         : "drums",
                                 "overdriven guitar" : "guitar",
                                 "reed organ"        : "bass",
                                 "rock organ"        : "keyboard",
                                 "synth voice"       : "vocals" }

        if instrumentName in instrumentToTrackMap:
            trackName = instrumentToTrackMap[instrumentName]
        else:
            trackName = instrumentName

        if trackName in trackCountMap:
            relativeIndex = trackCountMap[trackName] + 1
        else:
            relativeIndex = 0

        trackCountMap[trackName] = relativeIndex
        trackName = (trackName
                     + iif(relativeIndex == 0, "",
                           "-ABCDEF"[relativeIndex: relativeIndex + 1]))

        Logging.trace("<<: %s", trackName)
        return trackName

    #--------------------

    def _normalizedTrackName (self, trackName):
        """Returns standard form of <trackName> without any colons
           etc."""

        Logging.trace(">>: %s", trackName)
        result = trackName.split(":", 1)[0]
        Logging.trace("<<: %s", result)
        return result

    #--------------------

    def _makeEmptyTrack (self, lineBuffer):
        """Replaces contents of <lineBuffer> by an empty track"""

        Logging.trace(">>")

        lineBuffer.clear()
        lineBuffer.writeLine("MTrk")
        lineBuffer.writeLine("0 Meta TrkEnd")
        lineBuffer.writeLine("TrkEnd")

        Logging.trace("<<")
        
    #--------------------

    @classmethod
    def _processPositionInstrumentsLine (cls, currentLine, parseState,
                                         trackToSettingsMap, activeSettings,
                                         lineBuffer):
        """Process a single line <currentLine> in parser state
           <parseState> with given <trackToSettingsMap> while
           positioning instruments and updates <lineBuffer>
           accordingly; finally returns updated parse state and active
           settings"""

        Logging.trace(">>: [%s]#%s", parseState, currentLine)

        if cls._trackEndRegExp.match(currentLine):
            activeSettings = None
            lineBuffer.writeLine(currentLine)
            lineBuffer.flush()
            parseState = _ParseState.inLimbo
        elif cls._trackNameRegExp.search(currentLine):
            matchResult = cls._trackNameRegExp.search(currentLine)
            originalTrackName = matchResult.group(1)
            trackName = originalTrackName
            trackName = iif(trackName > "" and trackName[-1] in "ABCDEFG",
                            trackName[:-1], trackName)

            for suffix in [ "Top", "Middle", "Bottom" ]:
                if trackName.endswith(suffix):
                    trackName = trackName[:-len(suffix)]

            Logging.trace("--: trackName = '%s', normalized = '%s'",
                          originalTrackName, trackName)
            lineBuffer.writeLine(currentLine)
            parseState = iif(trackName not in trackToSettingsMap,
                             _ParseState.inOtherTrack,
                             _ParseState.inInstrumentTrack)
            activeSettings = trackToSettingsMap.get(trackName, {})
        elif cls._parameterChangeRegExp.search(currentLine):
            # ignore this line
            Logging.trace("--: skipped")
        elif cls._programChangeRegExp.search(currentLine):
            midiTime = int(currentLine.split(" ", 1)[0])

            if parseState in [_ParseState.inOtherTrack, _ParseState.inLimbo]:
                # leave line as is
                lineBuffer.writeLine(currentLine)
            elif parseState != _ParseState.inInstrumentTrack:
                Logging.trace("--: skipped program change")
            else:
                Logging.trace("--: replace by new settings")
                prefix = "%d Par ch=%d " % (midiTime,
                                            activeSettings.midiChannel)

                def lineGeneratorProc (controllerIndex, value):
                    st = (prefix + "c=%d v=%d") % (controllerIndex, value)
                    lineBuffer.writeLine(st)
                                     
                st = "%d PrCh ch=%d p=%d" % (midiTime,
                                             activeSettings.midiChannel,
                                             activeSettings.midiInstrument)
                lineGeneratorProc(0, activeSettings.midiInstrumentBank)
                lineBuffer.writeLine(st)
                lineGeneratorProc(7, activeSettings.midiVolume)
                lineGeneratorProc(10, activeSettings.panPosition)
                lineGeneratorProc(91, activeSettings.reverbLevel)
                parseState = _ParseState.afterSettings
        else:
            if (cls._channelReferenceRegExp.search(currentLine)
                and parseState != _ParseState.inOtherTrack):
                matchResult = cls._channelReferenceRegExp.search(currentLine)
                st = " ch=%d" % activeSettings.midiChannel
                currentLine = currentLine.replace(matchResult.group(0), st)
                Logging.trace("--: channel is updated - '%s'", currentLine)

            lineBuffer.writeLine(currentLine)

        Logging.trace("<<: %s", parseState)
        return parseState, activeSettings

    #--------------------
    # EXPORTED FEATURES
    #--------------------

    @classmethod
    def initialize (cls, voiceNameMap, styleNameToTextMap, trackNameSet):
        """Sets global variables for this module"""

        global _humanizationStyleNameToTextMap, _humanizedTrackNameSet
        global _voiceNameToVariationFactorMap

        Logging.trace(">>: voiceNameMap = %s, styleNameToTextMap = %s,"
                      + " trackList = %s",
                      voiceNameMap, styleNameToTextMap, trackNameSet)

        _humanizationStyleNameToTextMap = styleNameToTextMap
        _humanizedTrackNameSet          = trackNameSet
        _voiceNameToVariationFactorMap  = voiceNameMap

        Logging.trace("<<")

    #--------------------

    def __init__ (self, midiFileName, intermediateFilesAreKept=False):
        """Reads data from <midiFileName> and stores it internally in
           a text representation."""

        Logging.trace(">>: %s", midiFileName)

        self._intermediateFilesAreKept = intermediateFilesAreKept

        midiFile = MidiFileHandler()
        self._lineList = midiFile.readFile(midiFileName)

        Logging.trace("<<")

    #--------------------

    def save (self, targetMidiFileName):
        """Writes internal data to MIDI file with <targetMidiFileName>."""

        Logging.trace(">>: %s", targetMidiFileName)

        midiFile = MidiFileHandler()
        midiFile.writeFile(targetMidiFileName, self._lineList)
        
        Logging.trace("<<")

    #--------------------

    def addMissingTrackNames (self):
        """Adds track names to <self> when there are none based on
           instruments in a track."""

        Logging.trace(">>")

        cls = self.__class__
 
        trackInstrumentRegExp = re.compile(r"Meta InstrName +\"(.*)\"")
        badTrackNameRegExp    = re.compile(r"new:")

        lineList = []
        lineBuffer = _LineBuffer(lineList)
        trackCountMap = {}
        parseState = _ParseState.inLimbo

        for currentLine in self._lineList:
            Logging.trace("--: [%s]#%s", parseState, currentLine)

            if trackInstrumentRegExp.search(currentLine):
                matchResult = trackInstrumentRegExp.search(currentLine)
                instrumentName = matchResult.group(1)
                Logging.trace("--: instrumentName = %s", instrumentName)
            elif cls._trackEndRegExp.match(currentLine):
                lineBuffer.writeLine(currentLine)

                inFirstTrack = (parseState == _ParseState.inFirstTrack)
                hasTrackName = (parseState == _ParseState.inTrack)
                inBadTrack   = (parseState == _ParseState.inBadTrack)

                self._addMissingTrackNamesHandleTrackEnd(
                          inFirstTrack, hasTrackName, inBadTrack, lineBuffer,
                          trackCountMap, trackName, instrumentName)
                continue
            elif cls._trackBeginRegExp.match(currentLine):
                Logging.trace("--: track start - %s", currentLine)
                lineBuffer.activate(True)
                instrumentName = ""
                trackName      = ""
                parseState = \
                    iif(parseState == _ParseState.inLimbo,
                        _ParseState.inFirstTrack, _ParseState.inTrackPrefix)
            elif cls._trackNameRegExp.search(currentLine):
                matchResult = cls._trackNameRegExp.search(currentLine)
                trackName = matchResult.group(1)

                if badTrackNameRegExp.search(trackName):
                    parseState = _ParseState.inBadTrack
                elif parseState == _ParseState.inTrackPrefix:
                    parseState = _ParseState.inTrack
                    trackName = self._normalizedTrackName(trackName)
                    currentLine = (currentLine.split('"', 1)[0]
                                   + "\"" + trackName + "\"")

                Logging.trace("--: trackName = %s, parseState = %s",
                              trackName, parseState)

            lineBuffer.writeLine(currentLine)

        self._lineList = lineList

        Logging.trace("<<")

    #--------------------

    def addProcessingDateToTracks (self, trackNameList):

        """Tags all instrument tracks in <self> having a track name in
           <trackNameList> with a meta text with the processing date"""

        Logging.trace(">>")

        cls = self.__class__

        tagLinePrefix = "0 Meta Text \""
        tagLineSuffix = " at %s\"" % datetime.now().strftime("%Y-%m-%dT%H%M")

        lineList = []
        lineBuffer = _LineBuffer(lineList)
        isInInstrumentTrack = False

        for currentLine in self._lineList:
            Logging.trace("--: #%s", currentLine)

            if cls._trackBeginRegExp.match(currentLine):
                isInInstrumentTrack = False
                lineBuffer.activate(True)
                lineBuffer.writeLine(currentLine)
            else:
                lineBuffer.writeLine(currentLine)

                if cls._trackEndRegExp.match(currentLine):
                    lineBuffer.flush()
                elif cls._trackNameRegExp.search(currentLine):
                    matchResult = cls._trackNameRegExp.search(currentLine)
                    trackName = matchResult.group(1)
                    Logging.trace("--: trackName = %s", trackName)

                    if trackName in trackNameList:
                        tagLine = (tagLinePrefix
                                   + iif(trackName in _humanizedTrackNameSet,
                                         "humanized", "processed")
                                   + tagLineSuffix)
                        Logging.trace("--: tagLine = %s", tagLine)
                        lineBuffer.writeLine(tagLine)

        lineBuffer.flush()
        self._lineList = lineList

        Logging.trace("<<")

    #--------------------

    def filterByTrackNamePrefix (self, trackNamePrefix):
        """Analyzes tracks and leaves only those ones with track name
           that start with <trackNamePrefix>; in any case the first
           track (the midi control track) is also kept"""

        Logging.trace(">>: prefix = %s", trackNamePrefix)

        cls = self.__class__
        lineList = []
        lineBuffer = _LineBuffer(lineList)
        isFirstTrack = True
        
        for currentLine in self._lineList:
            Logging.trace("--: #%s", currentLine)

            if cls._trackBeginRegExp.match(currentLine):
                trackName = ""
                lineBuffer.activate(True)
                lineBuffer.writeLine(currentLine)
            else:
                lineBuffer.writeLine(currentLine)

                if cls._trackNameRegExp.search(currentLine):
                    matchResult = cls._trackNameRegExp.search(currentLine)
                    trackName = matchResult.group(1)
                    Logging.trace("--: trackName = %s", trackName)
                elif cls._trackEndRegExp.match(currentLine):
                    trackIsMaintained = (trackName.startswith(trackNamePrefix)
                                         or isFirstTrack)
                    message = "track is " + iif(trackIsMaintained,
                                                "maintained", "skipped")
                    Logging.trace("--: " + message)

                    if not trackIsMaintained:
                        self._makeEmptyTrack(lineBuffer)

                    lineBuffer.flush()
                    isFirstTrack = False

        lineBuffer.flush()
        self._lineList = lineList

        Logging.trace("<<")

    #--------------------

    def humanizeTracks (self, countInMeasureCount,
                        measureToHumanizationStyleNameMap):
        """Adapts instrument tracks in <self> to emulate a human player based
           on style given by <measureToHumanizationStyleNameMap>"""

        Logging.trace(">>: countIn = %s, styleMap = %s",
                      countInMeasureCount, measureToHumanizationStyleNameMap)

        cls = self.__class__

        if len(measureToHumanizationStyleNameMap) > 0:
            measureToHumanizationStyleMap = {}

            for measure, styleName in measureToHumanizationStyleNameMap.items():
                style = _HumanizationStyle(styleName)
                measureToHumanizationStyleMap[measure] = style

            # enumeration for kind of some track
            TrackKind_unknown    = 0
            TrackKind_instrument = 1
            TrackKind_other      = 2

            # TODO: algorithm can only cope with a single time signature
            fileBeginRegExp     = re.compile(r"MFile\W+(\w+)\W+(\w+)\W+(\w+)")
            timeSignatureRegExp = re.compile(r"TimeSig\W+(\w+)/(\w+)")

            lineList = []
            lineBuffer = _LineBuffer(lineList)
            humanizer = _Humanizer()

            for currentLine in self._lineList:
                Logging.trace("--: #%s", currentLine)

                if cls._trackBeginRegExp.match(currentLine):
                    trackName = ""
                    lineBuffer.activate(True)
                    lineBuffer.writeLine(currentLine)
                    trackKind = TrackKind_unknown
                else:
                    lineBuffer.writeLine(currentLine)

                    if fileBeginRegExp.match(currentLine):
                        matchResult = fileBeginRegExp.match(currentLine)
                        ticksPerQuarterNote = int(matchResult.group(3))
                        Logging.trace("--: ticks per quarter = %d",
                                      ticksPerQuarterNote)
                        _MusicTime.initialize(ticksPerQuarterNote, 4)
                    elif timeSignatureRegExp.search(currentLine):
                        matchResult = timeSignatureRegExp.search(currentLine)
                        numerator   = int(matchResult.group(1))
                        denominator = int(matchResult.group(2))
                        quartersPerMeasure = round(numerator / denominator * 4,
                                                   3)
                        Logging.trace("--: qpm = %s", quartersPerMeasure)
                        _MusicTime.initialize(ticksPerQuarterNote,
                                              quartersPerMeasure)
                        _Humanizer.initialize(quartersPerMeasure,
                                              countInMeasureCount)
                    elif cls._trackEndRegExp.match(currentLine):
                        if trackKind != TrackKind_instrument:
                            Logging.trace("--: other track end")
                            lineBuffer.flush()
                        else:
                            Logging.trace("--: instrument track end: %s",
                                          trackName)
                            trackLineList = lineBuffer.lineList()
                            lineBuffer.clear()
                            self._humanizeTrack(humanizer, trackName,
                                                measureToHumanizationStyleMap,
                                                trackLineList, lineList)
                    elif cls._trackNameRegExp.search(currentLine):
                        matchResult = cls._trackNameRegExp.search(currentLine)
                        trackName = matchResult.group(1)
                        Logging.trace("--: trackName = %s", trackName)
                        trackKind = iif(trackName in _humanizedTrackNameSet,
                                        TrackKind_instrument, TrackKind_other)

            self._lineList = lineList

        Logging.trace("<<")

    #--------------------

    def positionInstruments (self, trackToSettingsMap):
        """Scans instrument tracks in <self> and changes channel,
           player based on <trackToSettingsMap>"""

        Logging.trace(">>: %s", trackToSettingsMap)

        cls = self.__class__
 
        lineList = []
        lineBuffer = _LineBuffer(lineList)
        parseState = _ParseState.inLimbo
        activeSettings = {}

        for currentLine in self._lineList:
            parseState, activeSettings = \
                cls._processPositionInstrumentsLine(currentLine, parseState,
                                                    trackToSettingsMap,
                                                    activeSettings, lineBuffer)

        lineBuffer.flush()
        self._lineList = lineList

        Logging.trace("<<")
        
    #--------------------

    def removeVolumeChanges (self):
        """Analyzes tracks and kicks out midi volume changes"""

        Logging.trace(">>")

        cls = self.__class__
        lineList = []
        lineBuffer = _LineBuffer(lineList)
        
        for currentLine in self._lineList:
            Logging.trace("--: #%s", currentLine)

            if cls._volumeChangeRegExp.search(currentLine):
                Logging.trace("--: skipped volume change")
            else:
                lineBuffer.writeLine(currentLine)

        lineBuffer.flush()
        self._lineList = lineList

        Logging.trace("<<")

