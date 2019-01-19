# -*- coding: utf-8-unix -*-
# StringUtil - provides several utility string functions like conversions
#              from strings to maps or lists or tokenization

#====================

from .simplelogging import Logging
from .ttbase import iif

#====================

def adaptToKind (st, kind):
    """Returns converted value for given string <st> with type given by
       <kind>."""

    if kind == "I":
        result = int(st)
    elif kind == "F":
        result = float(st)
    elif kind == "B":
        result = (st.upper() == "TRUE")
    else:
        result = st

    return result

#--------------------

def stringToIntList (st):
    """Returns integer list for string <st>"""

    list = [ ord(st[i]) for i in range(len(st)) ]
    return list
    
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

#--------------------

def splitAndStrip (st, separator):
    """Returns split of <st> by <separator> with each part stripped from
       leading and trailing whitespace"""

    return [x.strip() for x in st.split(separator)]

#--------------------

def tokenize (st):
    """Returns a list of tokens also taking care of strings"""

    Logging.trace(">>: %s", st)

    whiteSpaceCharacterList = " "
    quoteCharacterList = "'"""
    escapeCharacter = '\\'

    ParseState_inLimbo  = 0
    ParseState_inString = 1
    ParseState_inEscape = 2
    ParseState_inToken  = 3
    parseStateToString = { 0 : "-", 1 : "S", 2 : escapeCharacter, 3 : "T" }

    parseState = ParseState_inLimbo
    result = []
    token = ""
    fsaTrace = ""

    for ch in st:
        # process finite state automaton with three states based
        # on next character in string
        fsaTrace += (iif(fsaTrace == "", "", " ")
                     + "[%s] %s" % (parseStateToString[parseState], ch))

        if parseState == ParseState_inLimbo:
            if ch in whiteSpaceCharacterList:
                pass
            elif ch in quoteCharacterList:
                endCharacter = ch
                token = ""
                parseState = ParseState_inString
            else:
                token = ch
                parseState = ParseState_inToken
        elif parseState == ParseState_inString:
            if ch == endCharacter:
                result.append(token)
                token = ""
                parseState = ParseState_inLimbo
            else:
                token += ch
                parseState = iif(ch == escapeCharacter, ParseState_inEscape,
                                 parseState)
        elif parseState == ParseState_inEscape:
            result += ch
            parseState = ParseState_inString
        elif parseState == ParseState_inToken:
            if ch in whiteSpaceCharacterList:
                result.append(token)
                token = ""
                parseState = ParseState_inLimbo
            elif ch in quoteCharacterList:
                result.append(token)
                token = ch
                parseState = ParseState_inString
            else:
                token += ch

    if parseState != ParseState_inLimbo:
        result.append(token)

    Logging.trace("--: accumulatedTrace = %s", fsaTrace)
    Logging.trace("<<: %s", result)
    return result
