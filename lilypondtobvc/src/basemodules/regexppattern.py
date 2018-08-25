# -*- coding: utf-8-unix -*-
# RegExpPattern -- services for construction of patterns for regular
#                  expressions

#====================
# IMPORTS
#====================

import re

from basemodules.simplelogging import Logging
from basemodules.ttbase import iif

#====================

class RegExpPattern:
    """This module encapsulates pattern construction for regular
       expressions.  It helps for lists of elements and maps from one
       element type to another.  Those patterns may be nested, but
       stay efficient by the use of (emulated) atomic groups."""

    identifierPattern = r"[a-zA-Z]+"
    integerPattern    = r"\d+"
    floatPattern      = r"\d+(\.\d+)?"
   
    #--------------
    # LOCAL METHODS
    #--------------

    @classmethod
    def _atomicGroupName (cls, groupIndex):
        """returns group name for atomic group with <groupIndex>"""

        return "ATO%dMIC" % groupIndex

    #--------------------

    @classmethod
    def _makeAtomicPattern (cls, pattern, firstGroupIndex=1):
        """constructs an atomic group pattern from <pattern> with groups
           starting at <firstGroupIndex>"""

        pattern = cls._shiftGroups(pattern, firstGroupIndex + 1)
        groupName = cls._atomicGroupName(firstGroupIndex)
        result = r"(?=(?P<%s>%s))(?P=%s)" % (groupName, pattern, groupName)
        return result

    #--------------------

    @classmethod
    def _makeListPattern (cls, elementPattern, firstGroupIndex=1):
        """Constructs a regexp pattern for list of elements with
           <elementPattern> with groups starting at <firstGroupIndex>;
           assumes that list starts immediately"""

        patternA, patternB = \
            cls._shiftGroupsForPair(elementPattern, elementPattern,
                                    firstGroupIndex)
        result = r"(?:%s(?:\s*,\s*%s)*)" % (patternA, patternB)
        return result

    #--------------------

    @classmethod
    def _makeOptionalPattern (cls, pattern):
        """Constructs a regexp pattern for <pattern> making it optional"""

        return "(?:%s|)" % pattern

    #--------------------

    @classmethod
    def _makeMapPattern (cls, keyPattern, valuePattern, firstGroupIndex=1):
        """Constructs a regexp pattern for map of key-value-pairs with
           <keyPattern> for keys and <valuePattern> for values with
           atomic groups starting at <firstGroupIndex>; assumes that
           map starts immediately"""

        patternA, patternB = cls._shiftGroupsForPair(keyPattern,
                                                     valuePattern,
                                                     firstGroupIndex + 1)

        elementPattern = r"%s\s*:\s*%s" % (keyPattern, valuePattern)
        listPattern = cls._makeListPattern(elementPattern)
        pattern = r"\{\s*%s\s*\}" % cls._makeOptionalPattern(listPattern)
        result = cls._makeAtomicPattern(pattern, firstGroupIndex)
        return result

    #--------------------

    @classmethod
    def _scanForGroups (cls, pattern):
        """looks for atomic groups in <pattern> and returns their
           first and last group index; assumes a consecutive
           numbering"""

        firstIndex = 0
        lastIndex  = -1

        for i in range(1, 1000):
            if firstIndex > 0 and cls._atomicGroupName(i) not in pattern:
                break
            else:
                lastIndex = i
                firstIndex = iif(firstIndex == 0, i, firstIndex)

        return (firstIndex, lastIndex)

    #--------------------

    @classmethod
    def _shiftGroups (cls, pattern, firstGroupIndex):
        """looks for atomic groups in <pattern> and shifts them from
           current first position to <firstGroupIndex>"""

        patternFirstIndex, patternLastIndex = cls._scanForGroups(pattern)
        numberSequence = list(range(patternFirstIndex, patternLastIndex + 1))
        offset = firstGroupIndex - patternFirstIndex
        result = pattern

        if offset > 0:
            numberSequence.reverse()

        for i in numberSequence:
            oldGroupName = cls._atomicGroupName(i)
            newGroupName = cls._atomicGroupName(i + offset)
            result = result.replace(oldGroupName, newGroupName)

        return result

    #--------------------

    @classmethod
    def _shiftGroupsForPair (cls, patternA, patternB, firstGroupIndex):
        """looks for atomic groups in <patternA> and <patternB> and
           shifts them from their current start index to
           <firstGroupIndex> for first, and to following indices for
           second"""

        resultA = cls._shiftGroups(patternA, firstGroupIndex)
        _, lastGroupIndex = cls._scanForGroups(resultA)
        resultB = cls._shiftGroups(patternB, lastGroupIndex + 1)
        return (resultA, resultB)

    #--------------------
    # EXPORTED METHODS
    #--------------------

    @classmethod
    def makeCompactListPattern (cls, elementPattern, separator="/"):
        """Constructs string pattern for a compact list (without
           spaces) from <elementPattern> and <separator> for elements
           within list"""

        Logging.trace(">>: elementPattern = '%s'", elementPattern)
        result = (r"%s(%s%s)*" % (elementPattern, separator, elementPattern))
        Logging.trace("<<: '%s'", result)
        return result

    #--------------------

    @classmethod
    def makeListPattern (cls, elementPattern, mayBeEmpty=True):
        """Constructs string pattern for list from <elementPattern>
           for elements within list; assumes that first list element
           starts immediately; if <mayBeEmpty> is set, also allows
           empty lists"""

        Logging.trace(">>: elementPattern = '%s', mayBeEmpty = %s",
                      elementPattern, mayBeEmpty)

        listPattern = cls._makeListPattern(elementPattern)
        result = iif(not mayBeEmpty, listPattern, "(?:%s|)" % listPattern)

        Logging.trace("<<: '%s'", result)
        return result

    #--------------------

    @classmethod
    def makeMapPattern (cls, keyPattern, valuePattern, mayBeEmpty=True):
        """Constructs string pattern for map from <keyPattern> for
           keys and <valuePattern> for values; assumes that map starts
           immediately; if <mayBeEmpty> is set, also allows
           empty maps"""

        Logging.trace(">>: keyPattern = '%s', valuePattern = '%s',"
                      + " mayBeEmpty = %s",
                      keyPattern, valuePattern, mayBeEmpty)

        mapPattern = cls._makeMapPattern(keyPattern, valuePattern)
        result = iif(not mayBeEmpty, mapPattern, "(?:%s|)" % mapPattern)

        Logging.trace("<<: '%s'", result)
        return result

    #--------------------

    @classmethod
    def makeRegExp (cls, pattern):
        """Constructs regular expression from <pattern> with leading
           whitespace and trailing end-of-string"""

        return re.compile("^\s*%s\s*$" % pattern)
