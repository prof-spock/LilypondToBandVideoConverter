# -*- coding: utf-8 -*- 
# configurationfile - provides reading from a configuration file containing
#                     comments and assignment to variables
#
# author: Dr. Thomas Tensi, 2014-04

#====================

import io
import re

from .operatingsystem import OperatingSystem
from .typesupport import isString
from .simplelogging import Logging
from .ttbase import iif, missingValue

#====================

def reprOfStringToValueMap (self):
    """String representation for a string to value map <self>"""

    entrySeparator = u"§"
    entryTemplate = "%s: %s"
    keyList = sorted(list(self.keys()))
    result = ""
    
    for key in keyList:
        value = self[key] 
        result += (iif(result == "", "", entrySeparator)
                   + entryTemplate % (key, value))
    
    result = "{" + result + "}";
    return result
        
#====================

class _Token:
    """Simple token within table definition string parser"""

    Kind_number        = "number"
    Kind_string        = "string"
    Kind_operator      = "operator"
    Kind_floatNumber   = "float"
    Kind_integerNumber = "integer"

    #--------------------

    def __init__ (self, start, text, kind, value):
        """Initializes token with start position, token text, token kind and
           value"""

        self.start = start
        self.text  = text
        self.kind  = kind
        self.value = value
        
    #--------------------

    def __repr__ (self):
        """String representation for token <self>"""

        st = ("_Token(%r, '%s', %s, %r)"
              % (self.start, self.text, self.kind, self.value))
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

    _searchPathList = ["."]

    #--------------------
    # LOCAL FEATURES
    #--------------------

    @classmethod
    def _adaptConfigurationValue (cls, value):
        """Takes string <value> and constructs either a boolean, a numeric
           value or a sanitized string."""

        Logging.trace(">>: %s", value)
        uppercasedValue = value.upper()

        if uppercasedValue in cls._validBooleanValues:
            result = (uppercasedValue == cls._trueBooleanValueName)
        elif cls._integerRegExp.match(value):
            result = int(value)
        elif cls._floatRegExp.match(value):
            result = float(value)
        else:
            result = cls._parseFragmentedString(value)
            
        Logging.trace("<<: %r", result)
        return result
        
    #--------------------

    def _expandVariables (self, st):
        """Expands all variables embedded in <st>."""

        Logging.trace(">>: %r", st)
        cls = self.__class__

        # collect identifiers embedded in value and replace them by
        # their value
        ParseState_inLimbo      = 0
        ParseState_inString     = 1
        ParseState_inEscape     = 2
        ParseState_inIdentifier = 3
        parseStateToString = { 0 : "LIM", 1 : "STR", 2 : "ESC", 3 : "ID " }

        parseState = ParseState_inLimbo
        result = ""
        identifier = ""

        for ch in st:
            # process finite state automaton with three states based
            # on next character in string
            Logging.trace("--: (%s) character: %s",
                          parseStateToString[parseState], ch)

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
                    identifierValue = self._findIdentifierValue(identifier)
                    result += identifierValue
                    result += ch
                    parseState = iif(ch == cls._doubleQuoteCharacter,
                                     ParseState_inString, ParseState_inLimbo)

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

        Logging.trace(">>: %s", identifier)
        cls = self.__class__

        if identifier not in self._keyToValueMap:
            # leave identifier as is (it might be some value name like
            # wahr or false
            Logging.trace("--: no expansion found")
            result = identifier
        else:
            result = self._keyToValueMap[identifier]

            if not isString(result):
                result = repr(result)
            else:
                result = (cls._doubleQuoteCharacter + result
                          + cls._doubleQuoteCharacter)

        Logging.trace("<<: expanded %s into %s", identifier, result)
        return result

    #--------------------

    def _lookupFileName (self, originalFileName):
        """Returns file name in search paths based on <originalFileName>"""

        Logging.trace(">>: %r", originalFileName)

        cls = self.__class__
        result = None
        separator = OperatingSystem.pathSeparator
        simpleFileName = OperatingSystem.basename(originalFileName, True)

        for directoryName in cls._searchPathList:
            fileName = iif(directoryName == ".", originalFileName,
                            directoryName + separator + simpleFileName)
            isFound = OperatingSystem.hasFile(fileName)
            Logging.trace("--: %r -> found = %r", fileName, isFound)

            if isFound:
                result = fileName
                break

        Logging.trace("<<: %r", result)
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
            cumulatedLine += iif(cumulatedLine == "", "", " ")

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
    def _parseFragmentedString (cls, st):
        """Parses - possibly fragmented - external representation of a
           string given by <st> and returns sanitized string."""

        ParseState_inLimbo   = 0
        ParseState_inString  = 1
        ParseState_inLiteral = 2
        ParseState_inEscape  = 3

        parseState = ParseState_inLimbo
        result = ""

        for ch in st:
            # process finite state automaton with three states based
            # on next character in string
            # Logging.trace("--: (%d) character: %s", parseState, ch)

            if parseState == ParseState_inLimbo:
                if ch == cls._doubleQuoteCharacter:
                    parseState = ParseState_inString
                elif not cls._whiteSpaceCharRegExp.search(ch):
                    parseState = ParseState_inLiteral
                    result += ch
            elif parseState == ParseState_inString:
                if ch == cls._doubleQuoteCharacter:
                    parseState = ParseState_inLimbo
                elif ch == cls._escapeCharacter:
                    parseState = ParseState_inEscape
                else:
                    result += ch
            elif parseState == ParseState_inLiteral:
                result += ch
                if cls._whiteSpaceCharRegExp.search(ch):
                    parseState = ParseState_inLimbo
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

        Logging.trace(">>: position = %d, tokens = %r",
                      position, tokenList)

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
        Logging.trace("<<: %r", result)
        return result

    #--------------------

    def _readFile (self, fileName, lineList, visitedFileNameSet):
        """Appends lines of configuration file with <fileName> to <lineList>;
           also handles embedded imports of files; <visitedFileNameSet>
           tells which files have already been visited"""

        Logging.trace(">>: fileName = '%s', visitedFiles = %s",
                      fileName, visitedFileNameSet)

        cls = self.__class__
        errorMessage = ""
        isOkay = True

        originalFileName = fileName
        fileName = self._lookupFileName(originalFileName)

        if fileName is None:
            errorMessage = "cannot find '%s'" % originalFileName
            isOkay = False
        elif fileName in visitedFileNameSet:
            Logging.trace("--: file already included '%s'", originalFileName)
        else:
            visitedFileNameSet.update(fileName)

            with io.open(fileName, "rt",
                         encoding="utf-8") as configurationFile:
                configFileLineList = configurationFile.readlines()

                for currentLine in configFileLineList:
                    currentLine = currentLine.strip()
                    isImportLine = \
                        currentLine.startswith(cls._importCommandName)

                    if isImportLine:
                        importedFileName = currentLine.split('"')[1]
                        currentLine = cls._commentMarker + " " + currentLine

                    lineList.append(currentLine)

                    if isImportLine:
                        isAbsolutePath = (importedFileName.startswith("/")
                                          or importedFileName.startswith("\\")
                                          or importedFileName[1] == ":")

                        if isAbsolutePath:
                            directoryPrefix = ""
                        else:
                            directoryName = OperatingSystem.dirname(fileName)
                            directoryPrefix = iif(directoryName == ".", "",
                                                  directoryName
                                                  + iif(directoryName > "",
                                                        "/", ""))

                        #importedFileName = directoryPrefix + importedFileName
                        Logging.trace("--: IMPORT '%s'", importedFileName)

                        isOkay = self._readFile(importedFileName, lineList,
                                                visitedFileNameSet)
                        if not isOkay:
                            Logging.trace("--:import failed for '%s' in %s",
                                          importedFileName,
                                          cls._searchPathList)
                            isOkay = False
                            break

        Logging.trace("<<: %s, '%s'", isOkay, errorMessage)
        return isOkay
            
    #--------------------

    def _lookupFileName (self, originalFileName):
        """Returns file name in search paths based on <originalFileName>"""

        Logging.trace(">>: %s", originalFileName)

        cls = self.__class__
        result = None
        separator = OperatingSystem.pathSeparator

        for directoryName in cls._searchPathList:
            simpleFileName = OperatingSystem.basename(originalFileName, True)
            fileName = iif(directoryName == ".", originalFileName,
                            directoryName + separator + simpleFileName)
            isFound = OperatingSystem.hasFile(fileName)
            Logging.trace("--: '%s' -> found = %s", fileName, isFound)

        tokenList = []
        errorPosition, errorMessage = -1, ""
        tokenStart, tokenText, tokenKind, tokenValue = None, None, None, None
        scanState = ScanState_inLimbo
        i = 0

        while i < len(st):
            ch = st[i]
            tokenIsDone = False
            isQuoteCharacter = (ch == "'")

            if scanState == ScanState_inLimbo:
                if ch == " ":
                    pass
                elif not ch in "'" + operators + digits:
                    tokenValue = None
                    errorPosition = i
                    errorMessage = "illegal character %r" % ch
                    break
                else:
                    tokenStart = i
                    tokenText = ch
                    tokenValue = iif(isQuoteCharacter, "", ch)

                    if isQuoteCharacter:
                        tokenKind = _Token.Kind_string
                        scanState = ScanState_inString
                    elif ch in operators:
                        tokenKind = _Token.Kind_operator
                        tokenIsDone = True
                    elif ch in digits:
                        tokenKind = _Token.Kind_integerNumber
                        scanState = ScanState_inNumber
            elif scanState == ScanState_inString:
                tokenText += ch

                if not isQuoteCharacter:
                    tokenValue += ch
                else:
                    tokenIsDone = True
            elif scanState == ScanState_inNumber:
                if ch in digits:
                    tokenText  += ch
                    tokenValue += ch
                elif ch == ".":
                    tokenKind = _Token.Kind_floatNumber
                    tokenText  += ch
                    tokenValue += ch
                else:
                    i -= 1
                    tokenIsDone = True
                    tokenValue = iif(tokenKind == _Token.Kind_floatNumber,
                                     float(tokenValue), int(tokenValue))
                    tokenKind = _Token.Kind_number

            if tokenIsDone:
                token = _Token(tokenStart, tokenText, tokenKind, tokenValue)
                Logging.trace("--: adding %r", token)
                tokenList.append(token)
                tokenValue = None
                scanState = ScanState_inLimbo

            i += 1

        if tokenValue is not None:
            errorPosition = i
            errorMessage = "unterminated token %s" % tokenKind

        result = (errorPosition, errorMessage, tokenList)
        Logging.trace("<<: %r", result)
        return result
        
    #--------------------
    # EXPORTED FEATURES
    #--------------------

    @classmethod
    def setSearchPaths (cls, searchPathList):
        """Sets list of search paths to <searchPathList>."""

        Logging.trace(">>: %s", searchPathList)
        cls._searchPathList = ["."] + searchPathList
        Logging.trace("<<")

    #--------------------

    def __init__ (self, fileName):
        """Parses configuration file given by <fileName> and sets
           internal key to value map."""

        Logging.trace(">>: %s", fileName)

        self._keyToValueMap = {}

        visitedFileNameSet = set()
        lineList = []
        isOkay = self._readFile(fileName, lineList, visitedFileNameSet)
        self._parseConfiguration(lineList)

        Logging.trace("<<: %s",
                      reprOfStringToValueMap(self._keyToValueMap))

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

    def getKeySet (self):
        """Returns set of all keys in configuration file"""

        Logging.trace(">>: %r", st)

        st = "{" + st + "}"
        errorPosition, errorMessage, tokenList = cls._tokenizeTableString(st)

        if errorPosition < 0:
            errorPosition, errorMessage, table, newPosition = \
                cls._parseTableString(tokenList, 0)

        errorPosition = errorPosition + iif(errorPosition > 0, -1, 0)
        result = (errorPosition, errorMessage, table)

        Logging.trace("<<: %r", result)
        return result
