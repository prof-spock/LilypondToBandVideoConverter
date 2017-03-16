# -*- coding: utf-8-unix -*-
# configurationfile - provides reading from a configuration file containing
#                     comments and assignment to variables
#
# author: Dr. Thomas Tensi, 2014-04

#====================

import codecs
import re
from simplelogging import Logging
from ttbase import iif, missingValue
from operatingsystem import OperatingSystem

#====================

class _Token:
    """Simple token within table definition string parser"""

    Kind_number        = "number"
    Kind_string        = "string"
    Kind_operator      = "operator"
    Kind_floatNumber   = "float"
    Kind_integerNumber = "integer"

    #--------------------

    def __init__ (self, start, kind, value):
        """Initializes token with start position, token kind and value"""

        self.start = start
        self.kind  = kind
        self.value = value
        
    #--------------------

    def __repr__ (self):
        """String representation for token <self>"""

        st = "_Token(%s, %s, '%s')" % (self.start, self.kind, self.value)
        return st
        
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

    @classmethod
    def _mustHave (cls, token, kindList, valueList=None):
        """Ensures that <token> is of a kind in <kindList>; if
           <valueList> is not none, token value is also checked"""

        Logging.trace(">>: token = %s, kindList = %s, valueList = '%s'",
                      token, kindList, valueList)

        errorPosition = -1
        errorMessage  = ""

        if token.kind not in kindList:
            errorPosition = token.start
            errorMessage  = ("expected kind from %s, found %s"
                             % (kindList, token.kind))
        elif valueList is not None and token.value not in valueList:
            errorPosition = token.start
            errorMessage  = ("expected value from %s, found %s"
                             % (valueList, token.value))

        result = (errorPosition, errorMessage)
        Logging.trace("<<: %s", result)
        return result

    #--------------------

    def _parseConfiguration (self, lineList):
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

    @classmethod
    def _parseTableString (cls, tokenList, position):
        """Parses <tokenList> containing a table definition mapping
           keys to values where values may be tables itself; returns
           triple of dictionary object, error position within string
           and error message"""

        Logging.trace(">>: %d, %s", position, tokenList)

        table = {}
        errorPosition = -1
        errorMessage = ""

        ParseState_inLimbo    = 0
        ParseState_atKey      = 1
        ParseState_atColon    = 2
        ParseState_atValue    = 3
        ParseState_afterValue = 4
        ParseState_done       = 5
        
        parseState = ParseState_inLimbo

        currentKey   = None
        currentValue = None

        while parseState != ParseState_done:
            token = tokenList[position]
            nextParseState = parseState + 1

            if parseState == ParseState_inLimbo:
                errorPosition, errorMessage = \
                    cls._mustHave(token, [ _Token.Kind_operator ], "{")
            elif parseState == ParseState_atKey:
                allowedTokenKindList = [ _Token.Kind_number,
                                         _Token.Kind_string ]
                errorPosition, errorMessage = \
                    cls._mustHave(token, allowedTokenKindList, None)
                currentKey = token.value
            elif parseState == ParseState_atColon:
                errorPosition, errorMessage = \
                    cls._mustHave(token, [ _Token.Kind_operator ], ":")
            elif parseState == ParseState_atValue:
                if token.kind != _Token.Kind_operator:
                    currentValue = token.value
                else:
                    # value is a table itself => recursion
                    errorPosition, errorMessage = \
                        cls._mustHave(token, [ _Token.Kind_operator ], "{")
                    
                    if errorPosition < 0:
                        errorPosition, errorMessage, currentValue, position = \
                             cls._parseTableString(tokenList, position)
                        
                table[currentKey] = currentValue
            elif parseState == ParseState_afterValue:
                errorPosition, errorMessage = \
                    cls._mustHave(token, [ _Token.Kind_operator ], ",}")
                nextParseState = iif(token.value == "}", ParseState_done,
                                     ParseState_atKey)
                
            parseState = iif(errorPosition >= 0, ParseState_done,
                             nextParseState)
            position += iif(parseState == ParseState_done, 0, 1)

        result = (errorPosition, errorMessage, table, position)
        Logging.trace("<<: %s", result)
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

    @classmethod
    def _tokenizeTableString (cls, st):
        """Converts table definition string into list of tokens where
           a token is a pair of kind and value"""

        Logging.trace(">>: %s", st)

        ScanState_inLimbo  = 0
        ScanState_inString = 1
        ScanState_inNumber = 2

        digits    = "0123456789"
        operators = "{}:,"

        tokenList = []
        errorPosition, errorMessage = -1, ""
        tokenStart, tokenKind, tokenValue = None, None, None
        scanState = ScanState_inLimbo
        i = 0

        while i < len(st):
            ch = st[i]
            tokenIsDone = False

            if scanState == ScanState_inLimbo:
                if ch == " ":
                    pass
                elif not ch in "'" + operators + digits:
                    tokenValue = None
                    errorPosition = i
                    errorMessage = "illegal character %s" % ch
                    break
                else:
                    tokenStart = i
                    tokenValue = iif(ch == "'", "", ch)

                    if ch == "'":
                        tokenKind = _Token.Kind_string
                        scanState = ScanState_inString
                    elif ch in operators:
                        tokenKind = _Token.Kind_operator
                        tokenIsDone = True
                    elif ch in digits:
                        tokenKind = _Token.Kind_integerNumber
                        scanState = ScanState_inNumber
            elif scanState == ScanState_inString:
                if ch != "'":
                    tokenValue += ch
                else:
                    tokenIsDone = True
            elif scanState == ScanState_inNumber:
                if ch in digits:
                    tokenValue += ch
                elif ch == ".":
                    tokenKind = _Token.Kind_floatNumber
                    tokenValue += ch
                else:
                    i -= 1
                    tokenIsDone = True
                    tokenValue = iif(tokenKind == _Token.Kind_floatNumber,
                                     float(tokenValue), int(tokenValue))
                    tokenKind = _Token.Kind_number

            if tokenIsDone:
                token = _Token(tokenStart, tokenKind, tokenValue)
                Logging.trace("--: adding %s", token)
                tokenList.append(token)
                tokenValue = None
                scanState = ScanState_inLimbo

            i += 1

        if tokenValue is not None:
            errorPosition = i
            errorMessage = "unterminated token %s" % tokenKind

        result = (errorPosition, errorMessage, tokenList)
        Logging.trace("<<: %s", result)
        return result
        
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
        self._parseConfiguration(lineList)

        Logging.trace("<<")

    #--------------------

    def getValue (self, key, defaultValue=missingValue):
        """Returns value for <key> in configuration file; if
           <defaultValue> is missing, an error message is logged when
           there is no associated value, otherwise <defaultValue> is
           returned for a missing entry"""

        Logging.trace(">>: key = %s, defaultValue = %s", key, defaultValue)

        isMandatory = (defaultValue == missingValue)
        result = None

        if key in self._keyToValueMap:
            result = self._keyToValueMap[key]
        elif isMandatory:
            Logging.trace("--: cannot find value for %s", key)
        else:
            result = defaultValue

        Logging.trace("<<: %s", result)
        return result

    #--------------------

    @classmethod
    def parseTableDefinitionString (cls, st):
        """Parses <st> as configuration string containing a table
           definition mapping keys to values where values may be
           tables itself; returns triple of dictionary object, error
           position within string and error message"""

        Logging.trace(">>: %s", st)

        st = "{" + st + "}"
        errorPosition, errorMessage, tokenList = cls._tokenizeTableString(st)

        if errorPosition < 0:
            errorPosition, errorMessage, table, newPosition = \
                cls._parseTableString(tokenList, 0)

        errorPosition = errorPosition + iif(errorPosition > 0, -1, 0)
        result = (errorPosition, errorMessage, table)
        Logging.trace("<<: %s", result)
        return result
