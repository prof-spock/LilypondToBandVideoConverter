# midiTransformer -- processes midi file and provides several
#                    transformations on it (e.g. drum humanization,
#                    volume adaptation, etc.)
#
# author: Dr. Thomas Tensi, 2006 - 2016

#====================
# IMPORTS
#====================

from array import array
from datetime import datetime
import re

from basemodules.simpleassertion import Assertion
from basemodules.simplelogging import Logging
from basemodules.simpletypes import Boolean, Dictionary, Integer, \
                                    List, Map, Natural, Object, Real, \
                                    String, StringList, StringMap, \
                                    StringSet, Tuple
from basemodules.stringutil import deserializeToMap
from basemodules.ttbase import adaptToRange, iif, iif2, isInRange, \
                               MyRandom
from basemodules.validitychecker import ValidityChecker

from .midifilehandler import MidiFileHandler

#====================

_infinity = 999999999
_humanizationStyleNameToTextMap = {}
_humanizedTrackNameSet = set()
_voiceNameToVariationFactorMap  = {}

#====================

def sign (x) -> Integer:
    """Returns the sign of x, 0 for 0, -1 for a negative number and +1
       for a positive number"""

    return iif2(x == 0, 0, x < 0, -1, 1)

#--------------------

def _canonicalTrackName (trackName : String) -> String:
    """Returns track name without any suffixes appended for
       multiple MIDI tracks of the same instrument."""

    for suffix in ["Bottom", "Middle", "Top"]:
        if trackName.endswith(suffix):
            trackName = trackName.replace(suffix, "")

    return trackName

#====================

class _LineBuffer:
    """This class is a utility for providing buffered output to a line
       list.  The line list is given upon construction of the buffer
       and the buffer may be manipulated, cleared or appended to the
       line list."""

    #--------------------

    def __init__ (self,
                  associatedLineList : StringList):
        """Prepares <self> as a buffer for <associatedLineList>"""

        self._info = []
        self._isActive = False
        self._lineList = associatedLineList

    #--------------------

    def activate (self,
                  isActive : Boolean):
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

    def length (self) -> Natural:
        """Returns count of lines in <self>."""

        return len(self._info)

    #--------------------

    def lineList (self) -> StringList:
        """Returns list of lines in <self>."""

        return self._info

    #--------------------

    def pop (self) -> String:
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

    # the vector of scaling factors for converting from music time to
    # midi time
    _factorVector = None
    
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
    def initialize (cls,
                    ticksPerQuarterNote : Natural,
                    quartersPerMeasure : Real):
        """Sets values for <ticksPerQuarterNote> and
           <quartersPerMeasure>"""

        Logging.trace(">>: tpq = %d, qpm = %r",
                      ticksPerQuarterNote, quartersPerMeasure)

        cls._quartersPerMeasure   = quartersPerMeasure
        cls._ticksPerQuarterNote  = ticksPerQuarterNote
        cls._factorVector = \
            array('i',
                  ( int(ticksPerQuarterNote * quartersPerMeasure),
                    int(ticksPerQuarterNote),
                    int(ticksPerQuarterNote / 4),
                    1 ))

        cls.measureDuration      = _MusicTime(1, 0, 0, 0, True)
        cls.semibreveDuration    = _MusicTime(0, 4, 0, 0, True)
        cls.quarterDuration      = cls.semibreveDuration.multiply(0.25)
        cls.sixteenthDuration    = cls.quarterDuration.multiply(0.25)
        cls.thirtysecondDuration = cls.quarterDuration.multiply(0.125)

        cls.firstPosition = _MusicTime(1, 1, 1, 1, False)

        Logging.trace("<<")

    #--------------------

    def __init__ (self,
                  measureCount : Integer,
                  quartersCount : Natural,
                  sixteenthsCount : Natural,
                  remainderCount : Natural,
                  isDuration : Boolean):
        """Creates a music time object, which is either a time or a
           duration"""

        self._isDuration = isDuration
        self._data = array('i',
                           (measureCount, quartersCount,
                            sixteenthsCount, remainderCount))

    #--------------------

    def __repr__ (self) -> String:
        """Returns the string representation of a music time object"""

        return ("MusicTime(%s/%s)"
                % (":".join([ "%d" % element for element in self._data ]),
                   iif(self._isDuration, "du", "tm")))

    #--------------------

    def absolute (self) -> Object:
        """Calculates absolute value of <self>"""

        result = _MusicTime(abs(self._data[0]), self._data[1],
                            self._data[2],  self._data[3],
                            self._isDuration)
        return result

    #--------------------

    def add (self,
             duration : Object) -> Object:
        """Returns sum of <self> and <duration>"""

        Logging.trace(">>: time = %r, duration = %r", self, duration)

        Assertion.pre(not self._isDuration and duration._isDuration,
                      "bad parameters for add")

        cls = self.__class__

        midiTime       = self.toMidiTime()
        midiDuration   = duration.toMidiTime()
        midiResultTime = midiTime + midiDuration

        result = cls.fromMidiTime(midiResultTime, False)

        Logging.trace("<<: %r", result)
        return result

    #--------------------

    @classmethod
    def fromMidiTime (cls,
                      midiTime : Integer,
                      isDuration : Boolean) -> Object:
        """Splits up absolute midi time in <midiTime> into measure
           number, quarter number within measure, sixteenth number
           within quarter and remainder ticks; counting starts with 1
           for a time and with 0 for a duration; result is returned as
           a music time; also assumes that <quartersPerMeasure>
           contains the right number of quarters within a measure"""

        Logging.trace(">>: midiTime = %d, isDuration = %r",
                      midiTime, isDuration)

        isNegative = (midiTime < 0)
        remainingMidiTime = int(abs(midiTime))
        ticksPerQuarterNote = cls._ticksPerQuarterNote

        partList = []
        offset = iif(isDuration, 0, 1)

        for factor in cls._factorVector:
            part = int(remainingMidiTime / factor)
            remainingMidiTime -= int(factor * part)
            part += offset
            partList.append(part)

        measureCount, quarterCount, sixteenthCount, \
            remainderCount = partList
        result = _MusicTime(measureCount, quarterCount, sixteenthCount,
                            remainderCount, isDuration)

        Logging.trace("<<: %r", result)
        return result

    #--------------------

    def isAt (self,
              reference : Object,
              rasterSize : Object) -> Boolean:
        """Tells whether <self> is near <reference> for some measure
           where <reference> is given as float factor of a semibreve;
           must be within a symmetric interval of <rasterSize>; a
           wraparound at the measure boundary is accounted for"""

        Logging.trace(">>: %r, reference = %r, rasterSize = %r",
                      self, reference, rasterSize)
        Assertion.pre(not self._isDuration,
                      "first parameter must be a time")

        cls = self.__class__

        tpqn = cls._ticksPerQuarterNote

        # find relative position in midi ticks
        measure = self.measure()
        midiMeasureDuration = round(cls._quartersPerMeasure * tpqn)
        midiTime = (self.toMidiTime()
                    - (measure - 1) * midiMeasureDuration)

        # check whether relative position is near <referenceTime>
        midiReferenceTime   = round(4 * tpqn * reference)
        midiHalfRasterSize  = round(4 * tpqn * rasterSize / 2.0)

        Logging.trace("--: midiTime = %d, midiReferenceTime = %d,"
                      + " midiHalfRaster = %d, midiMeasure = %d,"
                      + " qpm = %r, tpqn = %d",
                      midiTime, midiReferenceTime,
                      midiHalfRasterSize, midiMeasureDuration,
                      cls._quartersPerMeasure, tpqn)

        # check positive range
        midiOtherTime = midiReferenceTime + midiHalfRasterSize
        isNear = isInRange(midiTime, midiReferenceTime, midiOtherTime)
        Logging.trace("--: midiOtherTimeA = %d, isNear = %r",
                      midiOtherTime, isNear)

        if not isNear and midiOtherTime > midiMeasureDuration:
            # wraparound
            midiOtherTime -= midiMeasureDuration
            isNear = isInRange(midiTime, 0, midiOtherTime)
            Logging.trace("--: midiOtherTimeB = %d, isNear = %r",
                          midiOtherTime, isNear)

        # check negative range
        if not isNear:
            midiOtherTime = midiReferenceTime - midiHalfRasterSize
            isNear = isInRange(midiTime, midiOtherTime, midiReferenceTime)
            Logging.trace("--: midiOtherTimeC = %d, isNear = %r",
                          midiOtherTime, isNear)

            if not isNear and midiOtherTime < 0:
                # wraparound
                midiOtherTime += midiMeasureDuration
                isNear = isInRange(midiTime, midiOtherTime,
                                   midiMeasureDuration)
                Logging.trace("--: midiOtherTimeD = %d, isNear = %r",
                              midiOtherTime, isNear)

        result = isNear
        Logging.trace("<<: %r", result)
        return result

    #--------------------

    def measure (self) -> Integer:
        """Tells the measure of <self>"""

        return self._data[0]

    #--------------------

    def normalize (self) -> Object:
        """Calculates a standard representation of <self> and returns
           it"""

        Assertion.pre(not self._isDuration, "parameter must be a time")
        cls = self.__class__
        midiTime = self.toMidiTime()
        return cls.fromMidiTime(midiTime, False)

    #--------------------

    def multiply (self,
                  factor : Real) -> Object:
        """Does a scalar multiplication of duration <self> by <factor>
           and returns scaled duration"""

        Logging.trace(">>: duration = %r, factor = %f", self, factor)
        Assertion.pre(self._isDuration, "parameter must be a duration")

        cls = self.__class__
        midiDuration = self.toMidiTime()
        result = cls.fromMidiTime(round(midiDuration * factor), True)

        Logging.trace("<<: %r", result)
        return result

    #--------------------

    def subtract (self,
                  other : Object) -> Object:
        """Calculates difference of <self> and <other> and returns a
           duration"""

        Logging.trace(">>: %r, %r", self, other)

        cls = self.__class__
        midiTimeA = self.toMidiTime()
        midiTimeB = other.toMidiTime()
        midiDuration = midiTimeA - midiTimeB
        result = cls.fromMidiTime(midiDuration, True)

        Logging.trace("<<: %r", result)
        return result

    #--------------------

    def toMidiTime (self) -> Integer:
        """Converts <self> into midi time and returns value; assumes
           that <quartersPerMeasure> contains the right number of
           quarters within a measure; if <self._isDuration> is true,
           given time is a duration (starting at '0:0:0:0')"""

        Logging.trace(">>: %r", self)

        cls = self.__class__
        isNegative = self.measure() < 0
        offset = iif(self._isDuration, 0, -1)
        result = sum(map(lambda x, y: (x + offset) * y,
                         self._data, cls._factorVector))
        result = round(iif(isNegative, -result, result))

        Logging.trace("<<: %d", result)
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

        Logging.trace("<<")

    #--------------------

    def __init__ (self,
                  styleName : String):
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

        style = deserializeToMap(styleAsString)
        Logging.trace("--: style = %s", style)

        rasterSize = style.get("RASTER", "0.03125")
        ValidityChecker.isNumberString(rasterSize,
                                       "raster invalid in %r" % styleName,
                                       True)
        rasterSize = float(rasterSize)

        slackValue = style.get("SLACK")
        ValidityChecker.isNumberString(slackValue,
                                       "slack invalid in %r" % styleName,
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

            Logging.trace("--: position = %r, value = %r",
                          positionKey, velocityAndTiming)
            Assertion.check(separator in velocityAndTiming,
                            "bad value for %r in %r"
                            % (positionKey, styleName))
            velocity, timing = velocityAndTiming.split(separator)
            direction = timing[0]

            if direction not in "AB":
                direction = "-"
            else:
                timing = timing[1:]

            velocity = float(velocity)
            timing   = float(timing)

            self._positionToVelocityVariationMap[positionKey] = velocity
            self._positionToDirectionMap[positionKey]         = direction
            self._positionToTimeVariationMap[positionKey]     = timing
            Logging.trace("--: %r -> %4.2f/%s%4.2f",
                          positionKey, velocity, direction, timing)

        Logging.trace("<<: %r", self)

    #--------------------

    def __repr__ (self) -> String:
        """Returns the string representation of <self>"""

        st = ("_HumanizationStyle(%s,"
              + " RASTER = %r, SLACK = %r,"
              + " VELOCITY = %r, DIRECTIONS = %r, TIMING = %r)")
        result = st % (self._name,
                       self._rasterSize, self._slack,
                       self._positionToVelocityVariationMap,
                       self._positionToDirectionMap,
                       self._positionToTimeVariationMap)
        return result

    #--------------------

    def hasDirectionalShiftAt (self,
                               eventPositionInMeasure : Real) -> Boolean:
        """Tells whether there is a directional timing shift at
           <eventPositionInMeasure> and returns it"""

        Logging.trace(">>: %r", eventPositionInMeasure)
        result = self._positionToDirectionMap[eventPositionInMeasure]
        Logging.trace("<<: %r", result)
        return result

    #--------------------

    @classmethod
    def instrumentVariationFactors (cls,
                                    instrumentName : String) -> Tuple:
        """Returns the instrument specific variation factors
           for <instrumentName>"""

        Logging.trace(">>: %r", instrumentName)
        result = _voiceNameToVariationFactorMap.get(instrumentName,
                                                    [1.0,1.0])
        Logging.trace("<<: [%4.3f, %4.3f]", result[0], result[1])
        return result

    #--------------------

    def keys (self) -> List:
        """Returns all time positions"""

        return self._validPositions

    #--------------------

    def timingVariationFactor (self,
                               eventPositionInMeasure : Real) -> Real:
        """Returns the associated timing variation factor (in percent)
           for the <eventPositionInMeasure>"""

        Logging.trace(">>: %r", eventPositionInMeasure)
        result = \
            self._positionToTimeVariationMap.get(eventPositionInMeasure, 0)
        Logging.trace("<<: %r", result)
        return result

    #--------------------

    def raster (self) -> Real:
        """Returns the raster of current style"""

        Logging.trace(">>")
        result = self._rasterSize
        Logging.trace("<<: %r", result)
        return result

    #--------------------

    def velocityEmphasisFactor (self,
                                eventPositionInMeasure : Real) -> Real:
        """Returns the associated velocity factor (in percent) for the
           <eventPositionInMeasure>"""

        Logging.trace(">>: %r", eventPositionInMeasure)
        result = self._positionToVelocityVariationMap \
                     .get(eventPositionInMeasure, 1.0)
        Logging.trace("<<: %r", result)
        return result

    #--------------------

    def velocitySlack (self) -> Real:
        """Returns the associated slack (in percent)"""

        Logging.trace(">>")
        result = self._slack
        Logging.trace("<<: %r", result)
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

        def __repr__ (self) -> String:
            st = ("_HumanizerEvent(midiTime = %r, text = %r, kind = %r,"
                  + " channel = %r, note = %r, velocity = %r,"
                  + " partner = %r)")
            return (st % (self.midiTime, self.text, self.kind,
                          self.channel, self.note, self.velocity,
                          self.partner))

    #--------------------
    # LOCAL FEATURES
    #--------------------

    def _adjustTiming (self,
                       eventIndex : Natural,
                       musicTime : _MusicTime,
                       eventPositionInMeasure : Real,
                       instrumentTimingVariationFactor : Real,
                       timeToAdjustedTimeMap : Map):
        """Adjusts timing of note event given at <eventIndex> with
           parameters <musicTime> and <noteKind>;
           <instrumentTimingVariationFactor> gives an instrument
           specific factor and <timeToAdjustedTimeMap> the list of
           already processed timestamps with their adjusted values"""

        Logging.trace(">>: index = %d, time = %r, positionInMeasure = %r,"
                      + " instrumentTimingVariation = %4.3f",
                      eventIndex, musicTime, eventPositionInMeasure,
                      instrumentTimingVariationFactor)

        cls = self.__class__
        result = None
        timeAsString = str(musicTime)
        style = self._styleForTime(musicTime)
        effectiveMeasureIndex = (musicTime.measure()
                                 - cls._countInMeasureCount)

        if effectiveMeasureIndex <= 0:
            # leave as is, because those measures are count-ins
            result = musicTime
        elif timeAsString in timeToAdjustedTimeMap:
            # we already have seen this event time => reuse cached value
            result = timeToAdjustedTimeMap[timeAsString]
        else:
            direction = \
                style.hasDirectionalShiftAt(eventPositionInMeasure)
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
            timeToAdjustedTimeMap[timeAsString] = result

        Logging.trace("<<: %r", result)
        return result

    #--------------------

    def _adjustVelocity (self,
                         eventIndex : Natural,
                         musicTime : _MusicTime,
                         velocity : Natural,
                         eventPositionInMeasure : Real,
                         instrumentVelocityVariationFactor : Real):
        """Adjusts velocity of note event given at <eventIndex> with
           parameters <musicTime> and <noteKind>;
           <instrumentTimingVariationFactor> gives an instrument
           specific factor"""

        Logging.trace(">>: index = %d, time = %r, velocity = %d,"
                      + " positionInMeasure = %r,"
                      + " instrumentVelocityVariation = %4.3f",
                      eventIndex, musicTime, velocity, eventPositionInMeasure,
                      instrumentVelocityVariationFactor)

        cls = self.__class__
        result = None
        style = self._styleForTime(musicTime)
        measure = musicTime.measure() - cls._countInMeasureCount

        if measure <= 0:
            # leave as is, because those measures are count-ins
            result = velocity
        else:
            # randomFactor shall be between -1 and 1
            randomFactor = cls._squaredrand() * 2 - 1
            # adjust by instrument
            randomFactor *= instrumentVelocityVariationFactor

            slack  = style.velocitySlack()

            # whenever some velocity variation is in the measure, do
            # not apply the emphasis
            factor = style.velocityEmphasisFactor(eventPositionInMeasure)
            factor = iif(measure in self._varyingVelocityMeasureSet,
                         1.0, factor)

            factor += randomFactor * slack
            velocity = int(velocity * factor)
            velocity = adaptToRange(velocity, 0, 127)
            result = velocity

        Logging.trace("<<: %d", result)
        return result

    #--------------------

    def _asLineList (self) -> StringList:
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

    def _collectMeasuresWithVaryingVelocity (self):
        """Finds all measures where events have varying velocity that is not
           regular (like e.g. a crescendo); those measures will later
           only get a slight humanization in velocity, but will not
           have a velocity humanization pattern applied"""

        Logging.trace(">>: eventListCount = %d", len(self._eventList))

        cls = self.__class__
        midiTimeToVelocityMap = {}

        # collect maximum velocities for given midi times
        for event in self._eventList:
            if event.kind == "On":
                midiTime = event.midiTime
                velocity = \
                    max(event.velocity, midiTimeToVelocityMap.get(midiTime, 0))
                midiTimeToVelocityMap[midiTime] = velocity

        measureToVelocityMap = {}
        measureToDeltaVelocityMap = {}
        self._varyingVelocityMeasureSet.clear()

        # for each measure check whether the velocity is monotonously
        # increasing or decreasing or has some jumps
        for midiTime in sorted(midiTimeToVelocityMap.keys(), key=int):
            musicTime = _MusicTime.fromMidiTime(midiTime, False)
            velocity  = midiTimeToVelocityMap[midiTime]
            measure   = musicTime.measure() - cls._countInMeasureCount
            Logging.trace("--: m2v[%s] = %d", musicTime, velocity)

            if measure in measureToVelocityMap:
                delta = velocity - measureToVelocityMap[measure]

                if measure in measureToDeltaVelocityMap:
                    otherDelta = measureToDeltaVelocityMap[measure]
                    Logging.trace("--: delta = %r, otherDelta = %r",
                                  delta, otherDelta)

                    if (delta != 0 and otherDelta != 0
                        and sign(delta) != sign(otherDelta)):
                        Logging.trace("--: varying measure %d", measure)
                        self._varyingVelocityMeasureSet.add(measure)

                measureToDeltaVelocityMap[measure] = delta

            measureToVelocityMap[measure] = velocity
            Logging.trace("--: velocity[%s] = %r", measure, velocity)

        Logging.trace("--: %r", self._varyingVelocityMeasureSet)
        Logging.trace("<<")

    #--------------------

    def _convertToEventList (self,
                             lineList : StringList):
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
            Logging.trace("--: event = %r", str(event))
            self._eventList.append(event)

        Logging.trace("<<")

    #--------------------

    def _findEventPositionInMeasure (self,
                                     musicTime : _MusicTime) -> Real:
        """Finds position of event within measure and returns it as
           a float value"""

        Logging.trace(">>: %r", musicTime)

        result = None
        style = self._styleForTime(musicTime)
        rasterSize = style.raster()

        # traverse all time positions
        for position in style.keys():
            if musicTime.isAt(position, rasterSize):
                result = position
                break

        result = iif(result is None, "OTHER", result)
        Logging.trace("<<: %r", result)
        return result

    #--------------------

    def _processEventList (self,
                           trackName : String,
                           timeToAdjustedTimeMap : Map):
        """Traverses all events in the internal event list for track with
           <trackName> and transforms note events;
           <timeToAdjustedTimeMap> gives the list of already processed
           timestamps with their adjusted values"""

        Logging.trace(">>: %r", trackName)

        instrumentVelocityVariationFactor, \
        instrumentTimingVariationFactor = \
            _HumanizationStyle.instrumentVariationFactors(trackName)
        eventCount = len(self._eventList)
        noteToStartIndexMap = {}

        for i in reversed(range(eventCount)):
            event    = self._eventList[i]

            if event.kind == "On":
                partnerEvent  = self._eventList[event.partner]
                note          = event.note
                startMidiTime = event.midiTime
                endMidiTime   = partnerEvent.midiTime
                midiDuration  = endMidiTime - startMidiTime
                self._processSingleEvent(i, startMidiTime, note,
                                         event.velocity, midiDuration,
                                         instrumentVelocityVariationFactor,
                                         instrumentTimingVariationFactor,
                                         timeToAdjustedTimeMap)

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

    def _processSingleEvent (self,
                             eventIndex : Natural,
                             midiTime : Natural,
                             note : Natural,
                             velocity : Natural,
                             midiDuration : Natural,
                             instrumentVelocityVariation : Real,
                             instrumentTimingVariation : Real,
                             timeToAdjustedTimeMap : Map):
        """Humanizes note event given at <eventIndex> with parameters
           <midiTime>, <note>, <velocity> and <midiDuration>;
           <instrumentVelocityVariation> and
           <instrumentTimingVariation> give the instrument specific
           factors for the variation and <timeToAdjustedTimeMap> the
           list of already processed timestamps with their adjusted values"""

        Logging.trace(">>: index = %d, midiTime = %r,"
                      + " note = %r, velocity = %r,"
                      + " midiDuration = %r, instrumentVelocityVariation = %r,"
                      + " instrumentTimingVariation = %r",
                      eventIndex, midiTime, note, velocity,
                      midiDuration, instrumentVelocityVariation,
                      instrumentTimingVariation)

        musicTime  = _MusicTime.fromMidiTime(midiTime, False)
        eventPositionInMeasure = self._findEventPositionInMeasure(musicTime)

        velocity  = self._adjustVelocity(eventIndex, musicTime, velocity,
                                         eventPositionInMeasure,
                                         instrumentVelocityVariation)
        musicTime = self._adjustTiming(eventIndex, musicTime,
                                       eventPositionInMeasure,
                                       instrumentTimingVariation,
                                       timeToAdjustedTimeMap)

        event = self._eventList[eventIndex]
        event.midiTime = musicTime.toMidiTime()
        event.velocity = velocity

        Logging.trace("<<: %r", event)

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
    def _squaredrand (cls) -> Real:
        """Returns a random distribution around 0.5 with a root
           probability density around 0.5"""

        result = MyRandom.random()
        result = result * 2 - 1
        result =  sign(result) * result * result
        result = result / 2.0 + 0.5
        Logging.trace("--: %f", result)
        return result

    #--------------------

    def _styleForMeasure (self,
                          measureIndex : Integer):
        """Returns style that is valid at given <measureIndex>"""

        Logging.trace(">>: %r", measureIndex)

        if measureIndex in self._measureToHumanizationStyleMap:
            result = self._measureToHumanizationStyleMap[measureIndex]
        else:
            if measureIndex > 1:
                result = self._styleForMeasure(measureIndex - 1)
            else:
                styleName = _HumanizationStyle.defaultStyleName
                result    = _HumanizationStyle(styleName)

            self._measureToHumanizationStyleMap[measureIndex] = result

        Logging.trace("<<: %r", result._name)
        return result

    #--------------------

    def _styleForTime (self,
                       musicTime : _MusicTime):
        """Returns style that is valid at given <musicTime>"""

        Logging.trace(">>: %r", musicTime)

        cls = self.__class__
        measure = musicTime.measure() #  - cls._countInMeasureCount
        result = self._styleForMeasure(measure)

        Logging.trace("<<: %r", result._name)
        return result

    #--------------------
    # EXPORTED FEATURES
    #--------------------

    @classmethod
    def initialize (cls,
                    quartersPerMeasure : Real,
                    countInMeasureCount : Natural):
        """Sets value for <quartersPerMeasure> and <countInMeasureCount>"""

        Logging.trace(">>: qpm = %r, countIn = %d",
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
        self._varyingVelocityMeasureSet     = set()

        # the following map takes a simplified track name (like
        # keyboard) and associates a midi time to shifted time map to
        # keep different tracks for the same instrument synchronous in
        # timing (but not in velocity!)
        self._canonicalTrackNameToTimingMap = {}

        Logging.trace("<<")

    #--------------------

    def process (self,
                 trackName : String,
                 trackLineList : StringList,
                 measureToHumanizationStyleMap : Map):
        """Humanizes MIDI events in <trackLineList> based on map
           <measureToHumanizationStyleMap> from measure to style
           name and returns resulting event line list"""

        Logging.trace(">>: trackName = %r, measureToStyleMap = %r",
                      trackName, measureToHumanizationStyleMap)

        cls = self.__class__
        canonicalTrackName = _canonicalTrackName(trackName)
        timeToAdjustedTimeMap = \
            self._canonicalTrackNameToTimingMap.get(canonicalTrackName, {})

        self._eventList = []
        self._varyingVelocityMeasureSet = set()
        self._measureToHumanizationStyleMap = measureToHumanizationStyleMap

        self._convertToEventList(trackLineList)
        self._collectMeasuresWithVaryingVelocity()
        self._processEventList(trackName, timeToAdjustedTimeMap)
        self._sortEventList()
        result = self._asLineList()

        self._canonicalTrackNameToTimingMap[canonicalTrackName] = \
             timeToAdjustedTimeMap

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
    _panChangeRegExp        = re.compile(r" Par .* c=10 ")
    _programChangeRegExp    = re.compile(r" PrCh ")
    _reverbChangeRegExp     = re.compile(r" Par .* c=91 ")
    _trackBeginRegExp       = re.compile(r"MTrk")
    _trackEndRegExp         = re.compile(r"TrkEnd")
    _trackNameRegExp        = re.compile(r"Meta TrkName +\"(.*)\"")

    #--------------------
    # LOCAL FEATURES
    #--------------------

    def _addMissingTrackNamesHandleTrackEnd (self,
                                             inFirstTrack : Boolean,
                                             hasTrackName : Boolean,
                                             inBadTrack : Boolean,
                                             lineBuffer : StringList,
                                             trackCountMap : Map,
                                             trackName : String,
                                             instrumentName : String):
        """Processes a track end when adding missing track names."""

        Logging.trace(">>")

        cls = self.__class__

        if inBadTrack:
            trackIsSkipped = True
        else:
            Logging.trace("--: %s", iif(inFirstTrack,
                                        "first track", "other track"))
            Logging.trace("--: %s%s", iif(not hasTrackName, "no ", ""),
                          "trackname found")

            if not hasTrackName and not inFirstTrack:
                Logging.trace("--: mapping instrument %r", instrumentName)
                trackName = cls._instrumentNameToTrackName(instrumentName,
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
            Logging.trace("--: final track name = %r", trackName)
        else:
            Logging.trace("--: bad track => replaced by empty track")
            cls._makeEmptyTrack(lineBuffer)

        lineBuffer.flush()

        Logging.trace("<<")

    #--------------------

    @classmethod
    def _humanizeTrack (cls,
                        humanizer : _Humanizer,
                        trackName : String,
                        measureToHumanizationStyleMap : Map,
                        trackLineList : StringList,
                        lineList : StringList):
        """Humanizes entries in <trackLineList> by
           <measureToHumanizationStyleMap> and appends them to
           <lineList>"""

        Logging.trace(">>")
        processedLineList = humanizer.process(trackName, trackLineList,
                                              measureToHumanizationStyleMap)
        lineList.extend(processedLineList)
        Logging.trace("<<")

    #--------------------

    @classmethod
    def _instrumentNameToTrackName (cls,
                                    instrumentName : String,
                                    trackCountMap : Map) -> String:
        """Calculates track name for an anonymous track with
           instrument with <instrumentName>; <trackCountMap> gives the
           count of tracks with some track name"""

        Logging.trace(">>: %r", instrumentName)

        instrumentToTrackMap = { "power kit"         : "drums",
                                 "overdriven guitar" : "guitar",
                                 "reed organ"        : "bass",
                                 "rock organ"        : "keyboard",
                                 "synth voice"       : "vocals" }

        trackName = instrumentToTrackMap.get(instrumentName, instrumentName)

        if trackName in trackCountMap:
            relativeIndex = trackCountMap[trackName] + 1
        else:
            relativeIndex = 0

        trackCountMap[trackName] = relativeIndex
        trackName = (trackName
                     + iif(relativeIndex == 0, "",
                           "-ABCDEF"[relativeIndex: relativeIndex + 1]))

        Logging.trace("<<: %r", trackName)
        return trackName

    #--------------------

    @classmethod
    def _normalizedTrackName (cls,
                              trackName : String) -> String:
        """Returns standard form of <trackName> without any colons
           etc."""

        Logging.trace(">>: %r", trackName)
        result = trackName.split(":", 1)[0]
        Logging.trace("<<: %r", result)
        return result

    #--------------------

    @classmethod
    def _makeEmptyTrack (cls,
                         lineBuffer : StringList):
        """Replaces contents of <lineBuffer> by an empty track"""

        Logging.trace(">>")

        lineBuffer.clear()
        lineBuffer.writeLine("MTrk")
        lineBuffer.writeLine("0 Meta TrkEnd")
        lineBuffer.writeLine("TrkEnd")

        Logging.trace("<<")

    #--------------------

    @classmethod
    def _processPositionInstrumentsLine (cls,
                                         currentLine : String,
                                         parseState : _ParseState,
                                         trackToSettingsMap : Map,
                                         activeSettings : Map,
                                         lineBuffer : StringList):
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

            Logging.trace("--: trackName = %r, normalized = %r",
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

            if parseState == _ParseState.inOtherTrack:
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
                lineGeneratorProc( 0, activeSettings.midiInstrumentBank)
                lineBuffer.writeLine(st)
                lineGeneratorProc( 7, activeSettings.midiVolume)
                lineGeneratorProc(10, activeSettings.midiPanPosition)
                lineGeneratorProc(91, activeSettings.midiReverbLevel)
                parseState = _ParseState.afterSettings
        else:
            if (cls._channelReferenceRegExp.search(currentLine)
                and parseState != _ParseState.inOtherTrack):
                matchResult = cls._channelReferenceRegExp.search(currentLine)
                st = " ch=%d" % activeSettings.midiChannel
                currentLine = currentLine.replace(matchResult.group(0), st)
                Logging.trace("--: channel is updated - %r", currentLine)

            lineBuffer.writeLine(currentLine)

        Logging.trace("<<: %s", parseState)
        return parseState, activeSettings

    #--------------------
    # EXPORTED FEATURES
    #--------------------

    @classmethod
    def initialize (cls,
                    voiceNameMap : StringMap,
                    styleNameToTextMap : Dictionary,
                    trackNameSet : StringSet):
        """Sets global variables for this module"""

        global _humanizationStyleNameToTextMap, _humanizedTrackNameSet
        global _voiceNameToVariationFactorMap

        Logging.trace(">>: voiceNameMap = %r, styleNameToTextMap = %r,"
                      + " trackList = %r",
                      voiceNameMap, styleNameToTextMap, trackNameSet)

        _humanizationStyleNameToTextMap = styleNameToTextMap
        _humanizedTrackNameSet          = trackNameSet
        _voiceNameToVariationFactorMap  = voiceNameMap

        Logging.trace("<<")

    #--------------------

    def __init__ (self,
                  midiFileName : String,
                  intermediateFilesAreKept : Boolean = False):
        """Reads data from <midiFileName> and stores it internally in
           a text representation."""

        Logging.trace(">>: %r", midiFileName)

        self._intermediateFilesAreKept = intermediateFilesAreKept

        midiFile = MidiFileHandler()
        self._lineList = midiFile.readFile(midiFileName)

        Logging.trace("<<")

    #--------------------

    def save (self,
              targetMidiFileName : String):
        """Writes internal data to MIDI file with <targetMidiFileName>."""

        Logging.trace(">>: %r", targetMidiFileName)

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
                Logging.trace("--: instrumentName = %r", instrumentName)
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
                    trackName = cls._normalizedTrackName(trackName)
                    currentLine = (currentLine.split('"', 1)[0]
                                   + "\"" + trackName + "\"")

                Logging.trace("--: trackName = %r, parseState = %s",
                              trackName, parseState)

            lineBuffer.writeLine(currentLine)

        self._lineList = lineList

        Logging.trace("<<")

    #--------------------

    def addProcessingDateToTracks (self,
                                   trackNameList : StringList):
        """Tags all instrument tracks in <self> having a track name in
           <trackNameList> with a meta text with the processing date"""

        Logging.trace(">>")

        cls = self.__class__

        tagLinePrefix = "0 Meta Text \""
        tagLineSuffix = " at %s\"" % datetime.now().strftime("%Y-%m-%dT%H%M")

        lineList = []
        lineBuffer = _LineBuffer(lineList)

        for currentLine in self._lineList:
            Logging.trace("--: #%s", currentLine)

            if cls._trackBeginRegExp.match(currentLine):
                lineBuffer.activate(True)
                lineBuffer.writeLine(currentLine)
            else:
                lineBuffer.writeLine(currentLine)

                if cls._trackEndRegExp.match(currentLine):
                    lineBuffer.flush()
                elif cls._trackNameRegExp.search(currentLine):
                    matchResult = cls._trackNameRegExp.search(currentLine)
                    trackName = matchResult.group(1)
                    canonicalTrackName = _canonicalTrackName(trackName)
                    Logging.trace("--: trackName = %r, canonical = %r",
                                  trackName, canonicalTrackName)

                    if canonicalTrackName in trackNameList:
                        isHumanized = (canonicalTrackName
                                       in _humanizedTrackNameSet)
                        tagLine = (tagLinePrefix
                                   + iif(isHumanized,
                                         "humanized", "processed")
                                   + tagLineSuffix)
                        Logging.trace("--: tagLine = %r", tagLine)
                        lineBuffer.writeLine(tagLine)

        lineBuffer.flush()
        self._lineList = lineList

        Logging.trace("<<")

    #--------------------

    def filterByTrackNamePrefix (self,
                                 trackNamePrefix : String):
        """Analyzes tracks and leaves only those ones with track name
           that start with <trackNamePrefix>; in any case the first
           track (the midi control track) is also kept"""

        Logging.trace(">>: prefix = %r", trackNamePrefix)

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
                    Logging.trace("--: trackName = %r", trackName)
                elif cls._trackEndRegExp.match(currentLine):
                    trackIsMaintained = (trackName.startswith(trackNamePrefix)
                                         or isFirstTrack)
                    message = "track is " + iif(trackIsMaintained,
                                                "maintained", "skipped")
                    Logging.trace("--: " + message)

                    if not trackIsMaintained:
                        cls._makeEmptyTrack(lineBuffer)

                    lineBuffer.flush()
                    isFirstTrack = False

        lineBuffer.flush()
        self._lineList = lineList

        Logging.trace("<<")

    #--------------------

    def humanizeTracks (self,
                        countInMeasureCount : Natural,
                        measureToHumanizationStyleNameMap : Map):
        """Adapts instrument tracks in <self> to emulate a human player based
           on style given by <measureToHumanizationStyleNameMap>"""

        Logging.trace(">>: countIn = %r, styleMap = %r",
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
                ## Logging.trace("--: #%s", currentLine)

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
                        quartersPerMeasure = \
                            round(numerator / denominator * 4, 3)
                        Logging.trace("--: qpm = %r", quartersPerMeasure)
                        _MusicTime.initialize(ticksPerQuarterNote,
                                              quartersPerMeasure)
                        _Humanizer.initialize(quartersPerMeasure,
                                              countInMeasureCount)
                    elif cls._trackEndRegExp.match(currentLine):
                        if trackKind != TrackKind_instrument:
                            Logging.trace("--: other track end")
                            lineBuffer.flush()
                        else:
                            Logging.trace("--: instrument track end: %r",
                                          trackName)
                            trackLineList = lineBuffer.lineList()
                            lineBuffer.clear()
                            cls._humanizeTrack(humanizer, trackName,
                                               measureToHumanizationStyleMap,
                                               trackLineList, lineList)
                    elif cls._trackNameRegExp.search(currentLine):
                        matchResult = cls._trackNameRegExp.search(currentLine)
                        trackName = matchResult.group(1)
                        canonicalTrackName = _canonicalTrackName(trackName)
                        isHumanized = (canonicalTrackName
                                       in _humanizedTrackNameSet)
                        trackKind = iif(isHumanized,
                                        TrackKind_instrument, TrackKind_other)
                        Logging.trace("--: trackName = %r, kind = %r",
                                      canonicalTrackName, trackKind)

            self._lineList = lineList

        Logging.trace("<<")

    #--------------------

    def positionInstruments (self,
                             trackToSettingsMap : StringMap):
        """Scans instrument tracks in <self> and changes channel,
           player based on <trackToSettingsMap>"""

        Logging.trace(">>: %r", trackToSettingsMap)

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

    def removeUnwantedControlCodes (self):
        """Analyzes tracks and kicks out midi volume changes, reverb effect
           and pan settings"""

        Logging.trace(">>")

        cls = self.__class__
        lineList = []
        lineBuffer = _LineBuffer(lineList)

        for currentLine in self._lineList:
            Logging.trace("--: #%s", currentLine)

            if cls._volumeChangeRegExp.search(currentLine):
                Logging.trace("--: skipped volume change")
            elif cls._reverbChangeRegExp.search(currentLine):
                Logging.trace("--: skipped reverb change")
            elif cls._panChangeRegExp.search(currentLine):
                Logging.trace("--: skipped pan change")
            else:
                lineBuffer.writeLine(currentLine)

        lineBuffer.flush()
        self._lineList = lineList

        Logging.trace("<<")
