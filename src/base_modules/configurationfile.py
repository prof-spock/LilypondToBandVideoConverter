# -*- coding: utf-8 -*-
# configurationfile - provides reading from a configuration file containing
#                     comments and assignment to variables
#
# author: Dr. Thomas Tensi, 2014-04

#====================

import codecs
import re
from simplelogging import Logging
from ttbase import iif
from operatingsystem import OperatingSystem

#====================

missingDefaultValueIndicator = "@!XYZZY"

#====================

class ConfigurationFile:
    """Provides services for reading a configuration file with key -
       value assignments.  The parsing process calculates a map from
       name to value where the values may be booleans, integers,
       floats or strings."""

    _importCommandName = "INCLUDE"
    _trueBooleanValueName = "TRUE"
    _validBooleanValues = [_trueBooleanValueName, "FALSE"]
    _commentMarker = "--"
    _continuationMarker = "\\"
    _floatRegExp = re.compile(r"^[+\-]?[0-9]+\.[0-9]*$")
    _integerRegExp = re.compile(r"^[+\-]?[0-9]+$")
    _keyValueRegExp = re.compile(r"^(\w+)\s*=\s*(.*)$", re.UNICODE)
    _whiteSpaceCharRegExp = re.compile(r"^\s$")
    _identifierCharRegExp = re.compile(r"[A-Za-z0-9_]")
    _escapeCharacter = "\\"
    _doubleQuoteCharacter = '"'

    #--------------------
    # LOCAL FEATURES
    #--------------------

    @classmethod
    def _adaptConfigurationValue (cls, value):
        """Takes string valued <value> and constructs either a
           boolean, a numeric value or a sanitized string."""

        Logging.trace(">>: %s", value)
        uppercasedValue = value.upper()

        if uppercasedValue in cls._validBooleanValues:
            result = (uppercasedValue == cls._trueBooleanValueName)
        elif cls._integerRegExp.match(value):
            result = long(value)
        elif cls._floatRegExp.match(value):
            result = float(value)
        else:
            result = cls._parseFragmentedString(value)
            
        Logging.trace("<<: %s", repr(result))
        return result
        
    #--------------------

    def _expandVariables (self, value):
        """Expands all variables embedded in <value>."""

        Logging.trace(">>: %s", value)
        cls = self.__class__

        # collect identifiers embedded in value and replace them by
        # their value
        ParseState_inLimbo      = 0
        ParseState_inString     = 1
        ParseState_inEscape     = 2
        ParseState_inIdentifier = 3

        parseState = ParseState_inLimbo
        result = ""
        identifier = ""

        for ch in value:
            # process finite state automaton with three states based
            # on next character in string
            Logging.trace("--: (%d) character: %s", parseState, ch)

            if parseState == ParseState_inLimbo:
                if cls._identifierCharRegExp.search(ch):
                    identifier = ch
                    parseState = ParseState_inIdentifier
                else:
                    result += ch
                    if ch == cls._doubleQuoteCharacter:
                        parseState = ParseState_inString
            elif parseState == ParseState_inString:
                result += ch
                if ch == cls._doubleQuoteCharacter:
                    parseState = ParseState_inLimbo
                elif ch == cls._escapeCharacter:
                    parseState = ParseState_inEscape
            elif parseState == ParseState_inEscape:
                result += ch
                parseState = ParseState_inString
            elif parseState == ParseState_inIdentifier:
                if cls._identifierCharRegExp.search(ch):
                    identifier += ch
                else:
                    parseState = ParseState_inLimbo
                    identifierValue = self._findIdentifierValue(identifier)
                    result += identifierValue
                    result += ch

        if parseState == ParseState_inIdentifier:
            identifierValue = self._findIdentifierValue(identifier)
            result += identifierValue
            
        Logging.trace("<<: %s", repr(result))
        return result

    #--------------------

    def _findIdentifierValue (self, identifier):
        """Returns string representation of associated identifier value
           for <identifier>; if not found in current key to value map, the
           identifier itself is returned"""

        cls = self.__class__

        if identifier not in self._keyToValueMap:
            # leave identifier as is (it might be some value name like
            # wahr or false
            result = identifier
        else:
            result = self._keyToValueMap[identifier]

            if not isinstance(result, basestring):
                result = repr(result)
            else:
                result = (cls._doubleQuoteCharacter + result
                          + cls._doubleQuoteCharacter)

        Logging.trace("--: expanded %s into %s", identifier, result)
        return result

    #--------------------

    @classmethod
    def _mergeContinuationLines (cls, lineList):
        """Merges continuation lines in <lineList> into single
           cumulated line and replaces continuations by empty lines
           (to preserve line numbers)."""

        Logging.trace(">>")

        cumulatedLine = ""
        markerLength = len(cls._continuationMarker)
        lineListLength = len(lineList)

        for i, currentLine in enumerate(lineList):
            currentLine = currentLine.rstrip()

            if (currentLine.endswith(cls._continuationMarker)
                and i < lineListLength - 1):
                # strip off marker, add to cumulated line and empty
                # entry in line list
                currentLine = currentLine[:-markerLength].rstrip()
                cumulatedLine += currentLine
                lineList[i] = ""
                loggingFormat = "--: collected %d (%s)"
            else:
                cumulatedLine += currentLine
                lineList[i] = cumulatedLine
                cumulatedLine = ""
                loggingFormat = "--: cumulated into %d (%s)"

            Logging.trace(loggingFormat, i+1, currentLine)

        Logging.trace("<<")

    #--------------------

    def _parse (self, lineList):
        """Parses configuration file data given by <lineList> and updates
           key to value map."""

        Logging.trace(">>")

        cls = self.__class__
        cls._mergeContinuationLines(lineList)

        for i, currentLine in enumerate(lineList):
            lineNumber = i + 1

            # remove leading and trailing white space from line
            currentLine = currentLine.strip()
            Logging.trace("--: (%d) %s", i+1, currentLine)

            if (currentLine == ""
                or currentLine.startswith(cls._commentMarker)):
                # this is an empty line or comment line => skip it
                pass
            else:
                match = cls._keyValueRegExp.search(currentLine)

                if not match:
                    Logging.trace("--: bad line %d without key-value-pair",
                                  lineNumber)
                else:
                    key = match.group(1)
                    value = match.group(2)
                    value = self._expandVariables(value)
                    value = cls._adaptConfigurationValue(value)
                    self._keyToValueMap[key] = value

                    Logging.trace("--: %s -> %s", key, repr(value))

        Logging.trace("<<: %s", repr(self._keyToValueMap))

    #--------------------

    @classmethod
    def _parseFragmentedString (cls, value):
        """Parses - possibly fragmented - external representation of a
           string given by <value> and returns sanitized string."""

        ParseState_inLimbo  = 0
        ParseState_inString = 1
        ParseState_inEscape = 2

        parseState = ParseState_inLimbo
        result = ""

        for ch in value:
            # process finite state automaton with three states based
            # on next character in string
            # Logging.trace("--: (%d) character: %s", parseState, ch)

            if parseState == ParseState_inLimbo:
                if ch == cls._doubleQuoteCharacter:
                    parseState = ParseState_inString
                elif not cls._whiteSpaceCharRegExp.search(ch):
                    Logging.trace("--: bad white space character: %s", ch)
            elif parseState == ParseState_inString:
                if ch == cls._doubleQuoteCharacter:
                    parseState = ParseState_inLimbo
                elif ch == cls._escapeCharacter:
                    parseState = ParseState_inEscape
                else:
                    result += ch
            else:
                assert (parseState == ParseState_inEscape)
                result += ch
                parseState = ParseState_inString

        return result

    #--------------------

    def _readFile (self, fileName, lineList):
        """Appends lines of configuration file with <fileName> to
           <lineList>; also handles embedded imports of files"""

        Logging.trace(">>: %s", fileName)

        cls = self.__class__
        configurationFile = codecs.open(fileName, "r", "utf-8")
        configFileLineList = configurationFile.readlines()
        configurationFile.close()

        for currentLine in configFileLineList:
            currentLine = currentLine.strip()
            isImportLine = currentLine.startswith(cls._importCommandName)

            if isImportLine:
                importedFileName = currentLine.split('"')[1]
                currentLine = cls._commentMarker + " " + currentLine

            lineList.append(currentLine)

            if isImportLine:
                isAbsolutePath = (importedFileName.startswith("/")
                                  or importedFileName[1] == ":")

                if not isAbsolutePath:
                    directoryName = OperatingSystem.dirname(fileName)
                    directoryName += iif(directoryName > "", "/", "")
                    importedFileName = directoryName + importedFileName

                self._readFile(importedFileName, lineList)

        Logging.trace("<<")
            
    #--------------------
    # EXPORTED FEATURES
    #--------------------

    def __init__ (self, fileName):
        """Parses configuration file given by <fileName> and sets
           internal key to value map."""

        Logging.trace(">>: %s", fileName)

        self._keyToValueMap = {}
        lineList = []
        self._readFile(fileName, lineList)
        self._parse(lineList)

        Logging.trace("<<")

    #--------------------

    def getValue (self, key, defaultValue=missingDefaultValueIndicator):
        """Returns value for <key> in configuration file; if
           <defaultValue> is missing, an error message is logged when
           there is no associated value, otherwise <defaultValue> is
           returned for a missing entry"""

        Logging.trace(">>: key = %s, defaultValue = %s", key, defaultValue)

        isMandatory = (defaultValue == missingDefaultValueIndicator)
        result = None

        if key in self._keyToValueMap:
            result = self._keyToValueMap[key]
        elif isMandatory:
            Logging.trace("--: cannot find value for %s", key)
        else:
            result = defaultValue

        Logging.trace("<<: %s", result)
        return result
