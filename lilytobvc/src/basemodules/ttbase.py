# -*- coding: utf-8-unix -*-
# TTBase - provides several elementary functions like conditional
#          expressions

#====================

import sys

#====================

missingValue = "@!XYZZY"

#====================

def iif (condition, trueValue, falseValue):
    """Emulates conditional expressions with full value evaluation."""

    if condition:
        return trueValue
    else:
        return falseValue

#--------------------

def iif2 (condition1, trueValue1, condition2, trueValue2, falseValue2):
    """Emulates a sequence of conditional expressions with full
       condition and value evaluation."""

    return iif(condition1, trueValue1,
               iif(condition2, trueValue2, falseValue2))

#--------------------

def iif3 (condition1, trueValue1, condition2, trueValue2,
          condition3, trueValue3, falseValue3):
    """Emulates a sequence of conditional expressions with full
       condition and value evaluation."""

    return iif(condition1, trueValue1,
               iif2(condition2, trueValue2,
                    condition3, trueValue3, falseValue3))

#--------------------

def iif4 (condition1, trueValue1, condition2, trueValue2,
          condition3, trueValue3, condition4, trueValue4, falseValue4):
    """Emulates a sequence of conditional expressions with full
       condition and value evaluation."""

    return iif(condition1, trueValue1,
               iif3(condition2, trueValue2,
                    condition3, trueValue3,
                    condition4, trueValue4, falseValue4))

#--------------------

def isInRange (x, lowBound, highBound):
    """Tells whether x lies in the range from <lowBound> to
       <highBound>."""

    return (x >= lowBound and x <= highBound)

#--------------------

def adaptToRange (x, lowBound, highBound, isCyclic=False):
    """Adapts <x> to range [<lowBound>, <highBound>] either by
       clipping at the bounds or <ifCyclic> by shifting periodically"""

    if isInRange(x, lowBound, highBound):
        result = x
    elif not isCyclic:
        result = iif(x < lowBound, lowBound, highBound)
    else:
        intervalLength = highBound - lowBound

        if intervalLength < 1e-4:
            result = lowBound
        else:
            result = x

            while result < lowBound:
                result += intervalLength
            while result > highBound:
                result -= intervalLength

    return result

#--------------------

def stringToIntList (st):
    """Returns integer list for string <st>"""

    list = [ ord(st[i]) for i in range(len(st)) ]
    return list
    
#--------------------

def intListToHex (list):
    """Returns hex representation of integer <list>"""

    return "".join(map(lambda x: ("%02X" % x), list))

#--------------------

def stringToHex (st):
    """Returns hex representation of <st>"""

    return intListToHex(stringToIntList(st))

#===============================
# STRING TO CONTAINER CONVERSION
#===============================

_quoteCharacterSet           = set(["\"", "'"])
_structureLeadinCharacterSet = set(["{", "[", "("])

#--------------------

def _convertStringToList (st, startPosition, separator):
    """Splits <st> starting from <startPosition> at <separator> into
       list of parts; sublists or submaps are correctly handled and
       embedded into the list; returns end position and resulting list"""

    # do a finite state automaton with "{", "[", "(", " ", "\"" and "'"
    # as state changing inputs
    ParseState_beforeElement = 1
    ParseState_inElement     = 2
    ParseState_inString      = 3
    ParseState_afterElement  = 4
    ParseState_afterList     = 5

    result = []
    lastPosition = len(st) - 1
    listEndCharacter = iif(st[startPosition] == "[", "]", ")")
    position = startPosition + 1
    parseState = ParseState_beforeElement

    while position <= lastPosition:
        ch = st[position]

        if parseState == ParseState_beforeElement:
            if ch == listEndCharacter:
                break
            elif ch == " ":
                pass
            elif ch == separator:
                # unexpected separator => ignore
                pass
            elif ch in _quoteCharacterSet:
                endQuote = ch
                currentElement = ""
                parseState = ParseState_inString
            elif ch in _structureLeadinCharacterSet:
                if ch == "{":
                    position, currentElement = \
                              _convertStringToMap(st, position, separator)
                else:
                    position, currentElement = \
                              _convertStringToList(st, position, separator)

                result.append(currentElement)
                parseState = ParseState_afterElement
            else:
                currentElement = ch
                parseState = ParseState_inElement
        elif parseState == ParseState_inElement:
            if ch != " " and ch != separator and ch != listEndCharacter:
                currentElement += ch
            else:
                result.append(currentElement)

                if ch == listEndCharacter:
                    break
                else:
                    parseState = iif(ch == " ", ParseState_afterElement,
                                     ParseState_beforeElement)
        elif parseState == ParseState_inString:
            if ch != endQuote:
                currentElement += ch
            else:
                result.append(currentElement)
                parseState = ParseState_afterElement
        elif parseState == ParseState_afterElement:
            # ignore everything except a separator
            if ch == separator:
                parseState = ParseState_beforeElement

        position += 1

    return (position, result)

#--------------------

def _convertStringToMap (st, startPosition, separator):
    """Splits <st> starting from <startPosition> at <separator> into map
       of key-value-pairs; sublists or submaps as values are correctly
       handled and embedded into the map; returns end position and
       resulting map"""

    # do a finite state automaton with "{", "[", "(", " ", "\"" and "'"
    # as state changing inputs
    ParseState_beforeKey     = 1
    ParseState_inKey         = 2
    ParseState_inKeyString   = 3
    ParseState_afterKey      = 4
    ParseState_beforeValue   = 5
    ParseState_inValue       = 6
    ParseState_inValueString = 7
    ParseState_afterValue    = 8
    ParseState_afterMap      = 9

    result = {}

    mapEndCharacter = "}"
    lastPosition = len(st) - 1
    position = startPosition + 1
    parseState = ParseState_beforeKey

    while position <= lastPosition:
        ch = st[position]

        if parseState == ParseState_beforeKey:
            currentKey = ""

        if parseState in [ParseState_beforeKey, ParseState_beforeValue]:
            elementIsUnhandled = True

            if ch == mapEndCharacter:
                break
            elif ch == " ":
                pass
            elif ch == separator:
                # unexpected separator => ignore
                pass
            elif ch in _quoteCharacterSet:
                endQuote = ch
                currentElement = ""
                parseState += 2
            elif ch in _structureLeadinCharacterSet:
                if ch == "{":
                    position, currentElement = \
                              _convertStringToMap(st, position, separator)
                else:
                    position, currentElement = \
                              _convertStringToList(st, position, separator)

                parseState += 3
            else:
                currentElement = ch
                parseState += 1
        elif parseState in [ParseState_inKey, ParseState_inValue]:
            if (ch != " " and ch != separator and ch != ":"
                and ch != mapEndCharacter):
                currentElement += ch
            else:
                parseState += 2
                position -= iif(ch == " ", 0, 1)
        elif parseState in [ParseState_inKeyString, ParseState_inValueString]:
            if ch != endQuote:
                currentElement += ch
            else:
                parseState += 1
        elif parseState in [ParseState_afterKey, ParseState_afterValue]:
            if elementIsUnhandled:
                elementIsUnhandled = False

                if parseState == ParseState_afterKey:
                    currentKey = currentElement
                else:
                    result[currentKey] = currentElement

            # ignore everything except a separator or a colon
            if ch == mapEndCharacter:
                position -= 1
                parseState = ParseState_beforeKey
            elif ch == separator:
                parseState = ParseState_beforeKey
            elif ch == ":":
                parseState = ParseState_beforeValue

        position += 1

    return (position, result)
            
#--------------------

def adaptToKind (st, kind):
    """Returns converted value for given string <st> with type given by
       <kind>."""

    if kind == "I":
        result = int(st)
    elif kind == "F":
        result = float(st)
    else:
        result = st

    return result

#--------------------

def convertStringToList (st, separator=",", kind="S"):
    """Splits <st> with parts separated by <separator> into list with
       all parts having leading and trailing whitespace removed; if
       <kind> is 'I' or 'F' the elements are transformed into ints or
       floats"""

    position, result = _convertStringToList("[" + st + "]", 0, separator)
    result = list(map(lambda x: adaptToKind(x, kind), result))
    return result

#--------------------

def convertStringToMap (st, separator=","):
    """Splits <st> with parts separated by <separator> into map where
       key and value is separated by colons with all parts
       having leading and trailing whitespace removed"""

    result = {}
    st = st.strip()

    if not st.startswith("{"):
        st = "{" + st + "}"

    position, result = _convertStringToMap(st, 0, separator)
    return result

#====================

class MyRandom:
    """This module provides a simple but reproducible random
       generator."""

    value = None

    #--------------------

    @classmethod
    def initialize (cls):
        cls.value = 0.123456789

    #--------------------

    @classmethod
    def random (cls):
        """Returns a random number in interval [0, 1["""

        cls.value *= 997.0
        cls.value -= int(cls.value)
        return cls.value
