# -*- coding: utf-8 -*-
# midiTransformer -- processes midi file and provides several
#                    transformations on it (e.g. drum humanization,
#                    volume adaptation, etc.)
#
# author: Dr. Thomas Tensi, 2006 - 2016

#====================

from configurationfile import ConfigurationFile
from datetime import datetime
import math
from midifilehandler import MidiFileHandler
from operatingsystem import OperatingSystem
import random
import re
from simpleassertion import Assertion
from simplelogging import Logging
from ttbase import adaptToRange, iif, iif2, iif4, isInRange, MyRandom

#====================

maximumInteger = 999999999
humanizerConfigurationFilePath = ""
humanizedTrackList = []

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
    sixteenthDuration = None
    thirtysecondDuration = None

    #--------------------

    @classmethod
    def initialize (cls, ticksPerQuarterNote, quartersPerMeasure):
        """Sets values for <ticksPerQuarterNote> and
           <quartersPerMeasure>"""

        Logging.trace(">>: tpq = %d, qpm = %d",
                      ticksPerQuarterNote, quartersPerMeasure)
 
        cls._quartersPerMeasure   = quartersPerMeasure
        cls._ticksPerQuarterNote  = ticksPerQuarterNote
        cls.sixteenthDuration = _MusicTime("0:0:1:0", True)
        st = "0:0:0:" + str(ticksPerQuarterNote / 8)
        cls.thirtysecondDuration = _MusicTime(st, True)

        Logging.trace("<<")
    
    #--------------------

    def __init__ (self, value, isDuration):
        """Creates a music time object, which is either a time or a
           duration"""

        self._data       = value
        self._isDuration = isDuration

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

        Logging.trace(">>: time = %s, duration = %s", str(self), duration)

        Assertion.pre(not self._isDuration and duration._isDuration,
                      "bad parameters for add")

        cls = self.__class__
        midiTime     = self.toMidiTime()
        midiDuration = duration.toMidiTime()
        resultTime   = midiTime + midiDuration
        result       = cls.fromMidiTime(resultTime, False)

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
        remainingMidiTime = abs(midiTime)
        ticksPerQuarterNote = cls._ticksPerQuarterNote

        factorList = [ ticksPerQuarterNote * cls._quartersPerMeasure,
                       ticksPerQuarterNote, ticksPerQuarterNote / 4, 1 ]
        partList = []

        for factor in factorList:
            part = remainingMidiTime // factor
            remainingMidiTime -= factor * part
            partList.append(part)
        
        measure, quarter, sixteenth, remainder = partList

        if not isDuration:
            measure   += 1
            quarter   += 1
            sixteenth += 1
            remainder += 1

        st = (iif(isNegative, "-", "")
              + str(measure) + cls._separator
              + str(quarter) + cls._separator
              + str(sixteenth) + cls._separator
              + str(remainder))
        result = _MusicTime(st, isDuration)

        ##Logging.trace("<<: %s", str(result))
        return result

    #--------------------

    def isAt (self, timeWithinMeasure):
        """Tells whether <self> is near <timeWithinMeasure> for some
           measure where <timeWithinMeasure> is given as a position in
           the first measure without measure indication; allows a
           maximum deviation of 1/32nd"""

        ##Logging.trace(">>: %s, reference = %s",
        ##              str(self), str(timeWithinMeasure))
        Assertion.pre(not self._isDuration, "parameter must be a time")

        cls = self.__class__

        # shift <time> into first measure replacing measure by 1
        measure, relativeTime = self._data.split(cls._separator, 1)
        st = "1" + cls._separator + relativeTime
        time = _MusicTime(st, False)

        st = "1" + cls._separator + timeWithinMeasure._data
        referenceTime = _MusicTime(st, False)
        
        midiTimeA = time.toMidiTime()
        midiTimeB = referenceTime.toMidiTime()
        maxDeviation = cls._ticksPerQuarterNote / 8
        difference = abs(midiTimeA - midiTimeB)
        result = (maxDeviation >= difference)

        ##Logging.trace("<<: %s", result)
        return result

    #--------------------

    def isLess (self, otherTime):
        """Tells whether <self> is less than <otherTime>"""

        return (self.toMidiTime() < otherTime.toMidiTime())

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
        """Calculates a standard representation of <time> and returns
           it"""

        Assertion.pre(not self._isDuration, "parameter must be a time")
        cls = self.__class__
        midiTime = self.toMidiTime()
        return cls.fromMidiTime(midiTime, False)

    #--------------------

    def scalarMultiply (self, factor):
        """Does a scalar multiplication of duration <self> by <factor>
           and returns scaled duration"""

        Logging.trace(">>: duration = %s, factor = %f", str(self), factor)
        Assertion.pre(self._isDuration, "parameter must be a duration")

        cls = self.__class__
        midiDuration = self.toMidiTime()
        result = cls.fromMidiTime(int(midiDuration * factor), True)

        Logging.trace("<<: %s", str(result))
        return result

    #--------------------

    def subtract (self, otherTime):
        """Calculates difference of <self> and <otherTime> and returns a
           duration"""

        Logging.trace(">>: %s, %s", str(self), str(otherTime))

        cls = self.__class__
        midiTimeA = self.toMidiTime()
        midiTimeB = otherTime.toMidiTime()
        midiDuration = midiTimeA - midiTimeB
        result = cls.fromMidiTime(midiDuration, True)

        Logging.trace("<<: %s", str(result))
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
            for i in xrange(len(timePartList)):
                # for a time: make all entries in part list zero-based
                # instead of one-based
                timePartList[i] = str(int(timePartList[i]) - 1)

        result = ((((int(timePartList[0]) * cls._quartersPerMeasure
                     + int(timePartList[1])) * 4
                    + int(timePartList[2])) * cls._ticksPerQuarterNote / 4)
                  + int(timePartList[3]))
        result = iif(isNegative, -result, result)

        ##Logging.trace("<<: %d", result)
        return result

#====================

class _HumanizationStrategy:
    """This class encapsulates all services for midi track
       humanization. The strategy describes how many count-in measures
       are skipped, how the timing and the velocity may be changed
       depending on the position of a hit within a measure."""

    _partSeparator      = "/"
    _tagSeparator       = ":"
    _keyValueSeparator  = ":"
    _entrySeparator     = ","
    _styleNameSeparator = "|"
    _nameToStrategyStringMap = None
    _instrumentToScalingFactorPairMap = None
    _defaultStrategyAsString = ("COUNTIN: 2"
                                + "/"
                                + "TIMING: 1:0, 2:25, 3:10, 4:25, S:D50,"
                                + " OTHER:D35"
                                + "/"
                                + "VELOCITY: 1:115, 2:100, 3:110, 4:100,"
                                + " S:105, OTHER:85, SLACK:10")

    #--------------------
    # LOCAL FEATURES
    #--------------------

    @classmethod
    def _parseConfigurationFile(cls, configurationFilePath):
        """Fills mapping from strategy name to associated strategy
           string effectively from already checked configuration file"""
    
        Logging.trace(">>: %s", configurationFilePath)

        configurationFile = ConfigurationFile(configurationFilePath)
        getValueProc = configurationFile.getValue

        styleNameListAsString = getValueProc("styleNameList", True)
        styleNameList = styleNameListAsString.split(cls._styleNameSeparator)

        cls._nameToStrategyStringMap = {}

        for styleName in styleNameList:
            capitalizationProc = (lambda x: x.capitalize())
            namePartList = map(capitalizationProc, styleName.split("_"))
            adaptedStyleName = "style" + "".join(namePartList)
            Logging.trace("--: looking for %s for %s",
                          adaptedStyleName, styleName)
            strategyAsString = getValueProc(adaptedStyleName, True)
            cls._nameToStrategyStringMap[styleName] = strategyAsString

        variationFactors = getValueProc("variationFactors", True)
        variationFactorRegExp = re.compile(r"([a-z]+:[0-9]+/[0-9]+ ?)+")
        Assertion.check(variationFactorRegExp.match(variationFactors),
                        ("wrong format for variationFactors: %s"
                         % variationFactors))
        
        variationFactorList = map(lambda x: x.strip(),
                                  variationFactors.split(" "))
        cls._instrumentToScalingFactorPairMap = {}

        for variationTuple in variationFactorList:
            Logging.trace("--: processing variation %s", variationTuple)

            if variationTuple == "":
                # skip over empty entries
                pass
            else:
                instrumentName, factors = variationTuple.split(":")
                scalingFactors = map(lambda x: float(x) / 100,
                                     factors.split("/"))
                cls._instrumentToScalingFactorPairMap[instrumentName] = \
                         scalingFactors

        Logging.trace("--: scaling factors = %s",
                      str(cls._instrumentToScalingFactorPairMap))

        Logging.trace("<<")

    #--------------------
    # EXPORTED FEATURES
    #--------------------

    @classmethod
    def initialize (cls):
        """Fills mapping from strategy name to associated strategy
           string from configuration file"""

        Logging.trace(">>")

        scriptFileName = OperatingSystem.scriptFileName()
        scriptFilePath = OperatingSystem.dirname(scriptFileName)
        configurationFilePath = (scriptFilePath
                                 + OperatingSystem.pathSeparator
                                 + humanizerConfigurationFilePath)

        if not OperatingSystem.hasFile(configurationFilePath):
            Logging.trace("--: ERROR configuration file not found %s",
                          configurationFilePath)
        else:
            cls._parseConfigurationFile(configurationFilePath)

        Logging.trace("<<")

    #--------------------

    def __init__ (self, strategyName):
        """Finds strategy for given <strategyName> and returns it as a
           structure; if name is unknown, returns None"""

        Logging.trace(">>: %s", strategyName)

        cls = self.__class__

        if cls._nameToStrategyStringMap is None:
            cls.initialize()

        if strategyName not in cls._nameToStrategyStringMap:
            Logging.trace("--: could not find strategy name %s", strategyName)

        strategyAsString = \
            cls._nameToStrategyStringMap.get(strategyName,
                                             cls._defaultStrategyAsString)
        partList = strategyAsString.split(cls._partSeparator)

        if len(partList) != 3:
            Logging.trace("--: ERROR: bad strategy string - %s",
                          strategyAsString)
        else:
            self._name                       = strategyName
            self._introMeasureCount          = None
            self._draggedBeatSet             = set()
            self._beatToTimeVariationMap     = {}
            self._beatToVelocityVariationMap = {}
            
            for i in range(1, 4):
                part = partList[i - 1]
                tagName, tagValue = part.split(cls._tagSeparator, 1)
                Logging.trace("--: i = %d, tagName = %s, tagValue = %s",
                              i, tagName, tagValue)

                if i == 1:
                    # count-in definition
                    measureCount = int(tagValue)
                    self._introMeasureCount = measureCount
                    Logging.trace("--: count in = %d", measureCount)
                else:
                    # timing or velocity definition
                    entryList = tagValue.split(cls._entrySeparator)

                    for entry in entryList:
                        key, value = entry.split(cls._keyValueSeparator)
                        key   = key.strip()
                        value = value.strip()
                        Logging.trace("--: %s -> %s", key, value)

                        if i == 3:
                            isDragged = False
                            value = float(value) / 100
                            self._beatToVelocityVariationMap[key] = value
                        else:
                            # timing may contain a dragging indicator
                            isDragged = (value[0] == "D")
                            value = value[1:] if isDragged else value
                            value = float(value) / 100

                            if isDragged:
                                self._draggedBeatSet.add(key)

                            self._beatToTimeVariationMap[key] = value

                        Logging.trace("--: %s|%s -> %s%d",
                                      tagName, key, iif(isDragged, "D", ""),
                                      value)

        Logging.trace("<<")

    #--------------------

    def __str__ (self):
        """Returns the string representation of <self>"""

        st = ("_HumanizationStrategy(%s, COUNTIN = %s,"
              + " VELOCITY = %s, DRAGGING = %s, TIMING = %s)")
        result = st % (self._name, self._introMeasureCount,
                       repr(self._beatToVelocityVariationMap),
                       repr(self._draggedBeatSet),
                       repr(self._beatToTimeVariationMap))
        return result
    
    #--------------------

    def isDraggedAt (self, eventPositionKind):
        """Returns the associated factor (in percent) for the
           <eventPositionKind>"""

        Logging.trace(">>: %s", eventPositionKind)
        result = (eventPositionKind in self._draggedBeatSet)
        Logging.trace("<<: %s", result)
        return result

    #--------------------

    @classmethod
    def instrumentVariationFactors (cls, instrumentName):
        """Returns the instrument specific variation factors
           for <instrumentName>"""

        Logging.trace(">>: %s", instrumentName)
        result = cls._instrumentToScalingFactorPairMap.get(instrumentName,
                                                           [1,1])
        Logging.trace("<<: [%4.3f, %4.3f]", result[0], result[1])
        return result

    #--------------------

    def timingVariationFactor (self, eventPositionKind):
        """Returns the associated timing variation factor (in percent)
           for the <eventPositionKind>"""

        Logging.trace(">>: %s", eventPositionKind)
        result = self._beatToTimeVariationMap.get(eventPositionKind, 0)
        Logging.trace("<<: %d", result)
        return result

    #--------------------

    def velocityFactor (self, eventPositionKind):
        """Returns the associated velocity factor (in percent) for the
           <eventPositionKind>"""

        Logging.trace(">>: %s", eventPositionKind)
        result = self._beatToVelocityVariationMap.get(eventPositionKind, 0)
        Logging.trace("<<: %d", result)
        return result

    #--------------------

    def velocitySlack (self):
        """Returns the associated delta slack (in percent) for the
           <eventPositionKind>"""

        Logging.trace(">>")
        result = self._beatToVelocityVariationMap.get("SLACK", 0)
        Logging.trace("<<: %d", result)
        return result

#====================

class _Humanizer:
    """This class encapsulates the service for humanization of one or
       more MIDI event lists based on a humanization strategy.  It
       uses an internal event list and processes each single
       note-on/note-off event as well as the timing of other events."""

    _quartersPerMeasure = None
    
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

    def _adjustTiming (self, eventIndex, time, eventPositionKind,
                       instrumentTimingVariationFactor):
        """Adjusts timing of note event given at <eventIndex> with
          parameters <time> and <noteKind>;
          <instrumentTimingVariationFactor> gives an instrument specific
          factor"""

        Logging.trace(">>: index = %d, time = %s, positionKind = %s,"
                      + " instrumentTimingVariation = %4.3f",
                      eventIndex, str(time), eventPositionKind,
                      instrumentTimingVariationFactor)

        cls = self.__class__
        result = None
        strategy = self._strategy
        timeAsString = str(time) 

        if time.measure() <= strategy._introMeasureCount:
            # leave as is, because those measures are count-ins
            result = time
        elif timeAsString in self._timeToAdjustedTimeMap:
            result = self._timeToAdjustedTimeMap[timeAsString]
        else:
            isDragged = strategy.isDraggedAt(eventPositionKind)
            variationFactor = \
                strategy.timingVariationFactor(eventPositionKind)
            variationDuration = \
                _MusicTime.thirtysecondDuration.scalarMultiply(variationFactor)

            # do a random variation with a square distribution
            randomFactor = cls._squaredrand() * 2 - 1

            # if dragged, only a delay is possible
            randomFactor = iif(isDragged, abs(randomFactor), randomFactor)
            # adjust by instrument
            randomFactor *= instrumentTimingVariationFactor
            variationDuration = variationDuration.scalarMultiply(randomFactor)
            result = time.add(variationDuration)
            self._timeToAdjustedTimeMap[timeAsString] = result

        Logging.trace("<<: %s", str(result))
        return result

    #--------------------

    def _adjustVelocity (self, eventIndex, time, velocity, eventPositionKind,
                         instrumentVelocityVariationFactor):
        """Adjusts velocity of note event given at <eventIndex> with
           parameters <time> and <noteKind>;
           <instrumentTimingVariationFactor> gives an instrument
           specific factor"""

        Logging.trace(">>: index = %d, time = %s, velocity = %d,"
                      + " positionKind = %s,"
                      + " instrumentVelocityVariation = %4.3f",
                      eventIndex, str(time), velocity, eventPositionKind,
                      instrumentVelocityVariationFactor)

        cls = self.__class__
        result = None
        strategy = self._strategy

        if time.measure() <= strategy._introMeasureCount:
            # leave as is, because those measures are count-ins
            result = velocity
        else:
            factor = strategy.velocityFactor(eventPositionKind)
            slack  = strategy.velocitySlack()

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
            currentLine = iif(isInRange(midiTime, 0, maximumInteger - 1),
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
        for i in xrange(eventCount):
            currentLine = lineList[i]

            if " " in currentLine:
                midiTime, st = currentLine.split(" ", 1)
                midiTime = int(midiTime)
                tokenList = st.split(" ")
                kind = tokenList[0]
            else:
                st = currentLine
                midiTime = iif(currentLine == "MTrk", -1, maximumInteger)
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

    def _findEventPositionKind (self, time):
        """Finds position of event within measure and returns it as
           full quarter number, 'S' for off beat sixteenth and 'OTHER'
           for all the other positions"""

        Logging.trace(">>: %s", str(time))

        cls = self.__class__
        result = None

        # traverse all quarter beats and the sixteenth notes and
        # check for match
        for i in xrange(1, cls._quartersPerMeasure + 1):
            if result is None:
                for j in xrange(1, 5):
                    referenceTime = _MusicTime("%d:%d:1" % (i, j), False)

                    if time.isAt(referenceTime):
                        result = iif(j == 1, str(i), "S")
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
            _HumanizationStrategy.instrumentVariationFactors(trackName)
        eventCount = len(self._eventList)
        noteToStartIndexMap = {}

        for i in reversed(xrange(eventCount)):
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

        Logging.trace(">>: %d", eventIndex)

        time              = _MusicTime.fromMidiTime(midiTime, False)
        eventPositionKind = self._findEventPositionKind(time)
        velocity          = self._adjustVelocity(eventIndex, time, velocity,
                                                 eventPositionKind,
                                                 instrumentVelocityVariation)
        time              = self._adjustTiming(eventIndex, time,
                                               eventPositionKind,
                                               instrumentTimingVariation)

        event = self._eventList[eventIndex]
        event.midiTime = time.toMidiTime()
        event.velocity = velocity

        Logging.trace("<<")

    #--------------------

    def _sortEventList (self):
        """Sorts events in <eventList> by time"""

        Logging.trace(">>")

        kindOrder = { "special":0, "Meta":1, "PrCh":2, "Par":3, "KeySig":4,
                      "TimeSig":5, "Tempo":6, "Off":7, "On":8 }
        trackEndMetaEventText = "Meta TrkEnd"
        eventComparisonProc = (lambda x,y:
                               iif4(x.midiTime < y.midiTime, -1,
                                    x.midiTime > y.midiTime, 1,
                                    x.text == trackEndMetaEventText, 1,
                                    y.text == trackEndMetaEventText, -1,
                                    cmp(kindOrder[x.kind], kindOrder[y.kind])))
        self._eventList.sort(eventComparisonProc)

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
    # EXPORTED FEATURES
    #--------------------

    @classmethod
    def initialize (cls, quartersPerMeasure):
        """Sets value for <quartersPerMeasure>"""

        Logging.trace(">>: qpm = %d", quartersPerMeasure)
        cls._quartersPerMeasure = quartersPerMeasure
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

        self._strategy  = None
        self._eventList = None

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

    def process (self, trackName, lineList, humanizationStrategy):
        """Humanizes MIDI event <lineList> with <humanizationStrategy>
           and returns resulting event line list."""

        Logging.trace(">>: trackName = %s", trackName)

        cls = self.__class__
        canonicalTrackName = cls._findCanonicalTrackName(trackName)
        self._strategy = humanizationStrategy
        self._eventList = []
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

    def _humanizeTrack (self, humanizer, trackName, strategy,
                        trackLineList, lineList):
        """Humanizes entries in <trackLineList> by <strategy> and
           appends them to <lineList>"""

        Logging.trace(">>: strategy = %s", str(strategy))
        processedLineList = humanizer.process(trackName, trackLineList,
                                              strategy)
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
    def initialize (cls, configurationFileName, trackList):
        """Sets global variables for this module"""

        global humanizerConfigurationFilePath, humanizedTrackList

        Logging.trace(">>: configurationFileName = '%s', trackList = %s",
                      configurationFileName, trackList)
        humanizerConfigurationFilePath = configurationFileName
        humanizedTrackList             = trackList
        Logging.trace("<<")

    #--------------------

    def __init__ (self, midiFileName, debuggingIsActive=False):
        """Reads data from <midiFileName> and stores it internally in
           a text representation."""

        Logging.trace(">>: %s", midiFileName)

        self._debuggingIsActive = debuggingIsActive

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

    def addProcessingDateToTracks (self):
        """Tags all instrument tracks in <self> with a meta text with
           the processing date"""

        Logging.trace(">>")

        cls = self.__class__
 
        tagLine = ("0 Meta Text \"processed at %s\""
                   % datetime.now().strftime("%Y-%m-%dT%H%M"))

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

                    if trackName in humanizedTrackList:
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
                    if trackName.startswith(trackNamePrefix) or isFirstTrack:
                        # this is a track to be maintained
                        Logging.trace("--: track is maintained")
                    else:
                        self._makeEmptyTrack(lineBuffer)

                    lineBuffer.flush()
                    isFirstTrack = False

        lineBuffer.flush()
        self._lineList = lineList

        Logging.trace("<<")

    #--------------------

    def humanizeTracks (self, strategyName):
        """Adapts instrument tracks in <self> to emulate a human
           player based on strategy given by <strategyName>"""

        Logging.trace(">>: strategy = %s", strategyName)

        cls = self.__class__
        humanizationStrategy = _HumanizationStrategy(strategyName)

        if humanizationStrategy is not None:
            # enumeration for kind of some track
            TrackKind_unknown    = 0
            TrackKind_instrument = 1
            TrackKind_other      = 2

            # TODO: algorithm can only cope with a single time signature
            fileBeginRegExp     = re.compile(r"MFile\W+(\w+)\W+(\w+)\W+(\w+)")
            timeSignatureRegExp = re.compile(r"TimeSig\W+(\w+)")

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
                        quartersPerMeasure = int(matchResult.group(1)[0:1])
                        Logging.trace("--: qpm = %d", quartersPerMeasure)
                        _MusicTime.initialize(ticksPerQuarterNote,
                                              quartersPerMeasure)
                        _Humanizer.initialize(quartersPerMeasure)
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
                                                humanizationStrategy,
                                                trackLineList, lineList)
                    elif cls._trackNameRegExp.search(currentLine):
                        matchResult = cls._trackNameRegExp.search(currentLine)
                        trackName = matchResult.group(1)
                        Logging.trace("--: trackName = %s", trackName)
                        trackKind = iif(trackName in humanizedTrackList,
                                        TrackKind_instrument, TrackKind_other)

            self._lineList = lineList

        Logging.trace("<<")

    #--------------------

    def positionInstruments (self, trackToSettingsMap):
        """Scans instrument tracks in <self> and changes channel,
           player based on strategy given by <strategyName>"""

        Logging.trace(">>: %s", str(trackToSettingsMap))

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
        
