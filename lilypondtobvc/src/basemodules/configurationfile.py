# -*- coding: utf-8 -*- 
# configurationfile - provides reading from a configuration file containing
#                     comments and assignment to variables
#
# author: Dr. Thomas Tensi, 2014-04

#====================

import io
import re

from basemodules.operatingsystem import OperatingSystem
from basemodules.simpleassertion import Assertion
from basemodules.simplelogging import Logging
from basemodules.simpletypes import Dictionary, List, Natural, Object, \
                                    ObjectSet, Map, String, StringList, \
                                    StringMap, StringSet, Tuple
from basemodules.typesupport import isString
from basemodules.ttbase import iif, isStdPython, missingValue

#====================

def _reprOfStringToValueMap (stringMap : Map) -> String:
    """String representation for a string to value map <stringMap>"""

    entrySeparator = u"§"
    entryTemplate = "%s: %s"
    keyList = sorted(list(stringMap.keys()))
    result = ""
    
    for key in keyList:
        value = stringMap[key] 
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
    Kind_realNumber    = "real"
    Kind_integerNumber = "integer"

    #--------------------

    def __init__ (self,
                  start : Natural, text : String,
                  kind : String, value : Object):
        """Initializes token with start position, token text, token kind and
           value"""

        self.start = start
        self.text  = text
        self.kind  = kind
        self.value = value
        
    #--------------------

    def __repr__ (self) -> String:
        """String representation for token <self>"""

        st = ("_Token(%r, '%s', %s, %r)"
              % (self.start, self.text, self.kind, self.value))
        return st
        
#====================

if isStdPython:
    _TokenList = List[_Token]
else:
    _TokenList = List # List[_Token]

#====================

class ConfigurationFile:
    """Provides services for reading a configuration file with key -
       value assignments.  The parsing process calculates a map from
       name to value where the values may be booleans, integers,
       reals or strings."""

    _importCommandName = "INCLUDE"
    _trueBooleanValueNames = ["TRUE", "WAHR"]
    _validBooleanValueNames = _trueBooleanValueNames + ["FALSE", "FALSCH"]
    _commentMarker = "--"
    _continuationMarker = "\\"
    _realRegExp = re.compile(r"^[+\-]?[0-9]+\.[0-9]*$")
    _integerRegExp = re.compile(r"^[+\-]?[0-9]+$")
    _hexIntegerRegExp = re.compile(r"^0[xX][0-9A-Fa-f]+$")
    _keyValueRegExp = re.compile(r"^(\w+)\s*=\s*(.*)$")
    _whiteSpaceCharRegExp = re.compile(r"^\s$")
    _identifierCharRegExp = re.compile(r"[A-Za-z_0-9]")
    _identifierFirstCharRegExp = re.compile(r"[A-Za-z_]")
    _identifierLineRegExp = re.compile(r"\s*"
                                       + r"[A-Za-z_][A-Za-z0-9_]*"
                                       + r"\s*=")
    _escapeCharacter = "\\"
    _doubleQuoteCharacter = '"'

    _searchPathList = ["."]

    # error messages
    _errorMsg_badOpeningCharacter = "expected either { or ["
    
    #--------------------
    # LOCAL FEATURES
    #--------------------

    @classmethod
    def _adaptConfigurationValue (cls, value : String) -> Object:
        """Takes string <value> and constructs either a boolean, a numeric
           value or a sanitized string."""

        Logging.trace(">>: %r", value)
        uppercasedValue = value.upper()

        if uppercasedValue in cls._validBooleanValueNames:
            result = (uppercasedValue in cls._trueBooleanValueNames)
        elif cls._integerRegExp.match(value):
            result = int(value)
        elif cls._hexIntegerRegExp.match(value):
            result = int(value, 16)
        elif cls._realRegExp.match(value):
            result = float(value)
        else:
            result = value
            
        Logging.trace("<<: %r", result)
        return result
        
    #--------------------

    @classmethod
    def _combineFragmentedString (cls, st : String) -> String:
        """Combines - possibly fragmented - external representation of a
           string given by <st> into a sanitized string."""

        Logging.trace(">>: %r", st)

        ParseState_inLimbo   = 0
        ParseState_inOther   = 1
        ParseState_inString  = 2
        ParseState_inLiteral = 3
        ParseState_inEscape  = 4

        parseState = ParseState_inLimbo
        result = ""

        for ch in st:
            # process finite state automaton with three states based
            # on next character in string
            # Logging.trace("--: (%d) character: %r", parseState, ch)

            if parseState == ParseState_inLimbo:
                if ch == cls._doubleQuoteCharacter:
                    parseState = ParseState_inString
                elif not cls._whiteSpaceCharRegExp.search(ch):
                    parseState = ParseState_inLiteral
                    result += ch
            elif parseState == ParseState_inString:
                if ch == cls._doubleQuoteCharacter:
                    parseState = ParseState_inLimbo
                else:
                    result += ch
                    parseState = iif(ch == cls._escapeCharacter,
                                     ParseState_inEscape, parseState)
            elif parseState == ParseState_inLiteral:
                result += ch
                if cls._whiteSpaceCharRegExp.search(ch):
                    parseState = ParseState_inLimbo
            elif parseState == ParseState_inEscape:
                result += ch
                parseState = ParseState_inString
            else:
                Assertion.check(False,
                                "bad parse state - %s" % parseState)

        Logging.trace("<<: %r", result)
        return result

    #--------------------

    def _expandVariables (self, st : String) -> String:
        """Expands all variables embedded in <st>."""

        Logging.trace(">>: %r", st)
        cls = self.__class__

        # collect identifiers embedded in value and replace them by
        # their value
        ParseState_inLimbo      = 0
        ParseState_inString     = 1
        ParseState_inEscape     = 2
        ParseState_inIdentifier = 3
        parseStateToString = { 0 : "-", 1 : "S",
                               2 : cls._escapeCharacter, 3 : "I" }

        parseState = ParseState_inLimbo
        result = ""
        identifier = ""
        fsaTrace = ""

        for ch in st:
            # process finite state automaton with three states based
            # on next character in string
            fsaTrace += (iif(fsaTrace == "", "", " ")
                         + "[%s] %s" % (parseStateToString[parseState], ch))

            if parseState == ParseState_inLimbo:
                if cls._identifierFirstCharRegExp.search(ch):
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
            
        Logging.trace("--: accumulatedFSATrace = %s", fsaTrace)
        Logging.trace("<<: %r", result)
        return result

    #--------------------

    def _findIdentifierValue (self, identifier : String) -> String:
        """Returns string representation of associated identifier value
           for <identifier>; if not found in current key to value map, the
           identifier itself is returned"""

        Logging.trace(">>: %s", identifier)
        cls = self.__class__

        if identifier not in self._keyToValueMap:
            # leave identifier as is (it might be some value name like
            # wahr or false
            Logging.traceError("no expansion found")
            result = identifier
        else:
            result = self._keyToValueMap[identifier]

            if not isString(result):
                result = repr(result)
            else:
                result = (cls._doubleQuoteCharacter + result
                          + cls._doubleQuoteCharacter)

        Logging.trace("<<: expanded %s into %r", identifier, result)
        return result

    #--------------------

    def _lookupFileName (self,
                         enclosingDirectoryName : String,
                         originalFileName : String) -> String:
        """Returns file name in search paths based on <originalFileName>"""

        Logging.trace(">>: directory = %r, file = %r",
                      enclosingDirectoryName, originalFileName)

        cls = self.__class__
        result = None
        separator = OperatingSystem.pathSeparator
        simpleFileName = OperatingSystem.basename(originalFileName)
        searchPathList = list(cls._searchPathList)
        searchPathList.append(enclosingDirectoryName)

        for directoryName in searchPathList:
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
    def _mergeContinuationLines (cls, lineList : StringList):
        """Merges continuation lines in <lineList> into single cumulated line
           and replaces continuations by empty lines (to preserve line
           numbers); the continuation logic is simple: a new
           identifier definition line (starting with an identifier and
           an equals sign) starts a new logical line unconditionally,
           otherwise physical lines are collected and combined with
           the previous logical line; embedded comment lines are
           skipped and an empty (whitespace only) physical line stops
           the collection process (unless followed by a continuation
           character)"""

        Logging.trace(">>")

        cumulatedLine = ""
        markerLength = len(cls._continuationMarker)
        lineListLength = len(lineList)

        for i, originalLine in enumerate(lineList):
            currentLine  = originalLine.strip()
            lineList[i] = ""

            if currentLine.endswith(cls._continuationMarker):
                # strip off obsolete continuation marker
                currentLine = currentLine[:-markerLength].rstrip()

            if cls._identifierLineRegExp.match(currentLine):
                # this is a new definition

                if cumulatedLine > "":
                    lineList[i - 1] = cumulatedLine

                cumulatedLine = currentLine
                loggingFormat = "--: new definition %d (%r)"
            elif currentLine.startswith(cls._commentMarker):
                # skip comment
                loggingFormat = "--: skipped comment %d (%r)"
            elif originalLine == "":
                if cumulatedLine == "":
                    loggingFormat = "--: empty line %d (%r)"
                else:
                    lineList[i - 1] = cumulatedLine
                    loggingFormat = \
                        "--: empty line ended previous definition %d (%r)"

                cumulatedLine = ""
            else:
                # this is not an empty line and it does not start with a
                # definition sequence or an import
                cumulatedLine += " " + currentLine
                loggingFormat = "--: collected continuation %d (%r)"

            Logging.trace(loggingFormat, i+1, currentLine)

        if cumulatedLine > "":
            lineList[-1] = cumulatedLine
            Logging.trace("--: final line (%s)", currentLine);

        Logging.trace("<<")

    #--------------------

    @classmethod
    def _mustHave (cls,
                   token : _Token, kindSet : StringSet,
                   valueSet : ObjectSet = None):
        """Ensures that <token> is of a kind in <kindSet>; if
           <valueSet> is not None, token value is also checked"""

        Logging.trace(">>: token = %r, kindSet = %r, valueSet = %r",
                      token, kindSet, valueSet)

        errorPosition, errorMessage = -1, ""

        if token.kind not in kindSet:
            errorPosition = token.start
            errorMessage  = ("expected kind from %r, found %s"
                             % (kindSet, token.kind))
        elif valueSet is not None and token.value not in valueSet:
            errorPosition = token.start
            errorMessage  = ("expected value from %r, found %r"
                             % (valueSet, token.value))

        result = (errorPosition, errorMessage)
        Logging.trace("<<: %r", result)
        return result

    #--------------------

    def _parseConfiguration (self, lineList : StringList):
        """Parses configuration file data given by <lineList> and updates
           key to value and key to string value map."""

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
                    Logging.traceError("bad line %d without key-value-pair",
                                       lineNumber)
                else:
                    key = match.group(1)
                    value = match.group(2)
                    value = self._expandVariables(value)
                    value = cls._combineFragmentedString(value)
                    self._keyToStringValueMap[key] = value
                    Logging.trace("--: string value %r -> %r", key, value)
                    value = cls._adaptConfigurationValue(value)
                    self._keyToValueMap[key] = value
                    Logging.trace("--: adapted value %r -> %r", key, value)

        Logging.trace("<<: %r", self._keyToValueMap)

    #--------------------

    def _readFile (self,
                   directoryName : String,
                   fileName : String,
                   lineList : StringList,
                   visitedFileNameSet : StringSet):
        """Appends lines of configuration file with <fileName> to <lineList>
           with leading and trailing whitespace stripped; also handles
           embedded imports of files (relative to <directoryName>;
           <visitedFileNameSet> tells which files have already been
           visited"""

        Logging.trace(">>: fileName = %r, directory = %r, visitedFiles = %r",
                      fileName, directoryName, visitedFileNameSet)

        cls = self.__class__
        errorMessage = ""
        isOkay = True

        originalFileName = fileName
        fileName = self._lookupFileName(directoryName, originalFileName)

        if fileName is None:
            errorMessage = "cannot find %r" % originalFileName
            isOkay = False
        elif fileName in visitedFileNameSet:
            Logging.trace("--: file already included %r", originalFileName)
        else:
            visitedFileNameSet.add(fileName)
            directoryName = OperatingSystem.dirname(fileName)

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

                        # if isAbsolutePath:
                        #     directoryPrefix = ""
                        # else:
                        #     directoryName = OperatingSystem.dirname(fileName)
                        #     directoryPrefix = iif(directoryName == ".", "",
                        #                           directoryName
                        #                           + iif(directoryName > "",
                        #                                 "/", ""))

                        #importedFileName = directoryPrefix + importedFileName
                        Logging.trace("--: IMPORT %r", importedFileName)

                        isOkay = self._readFile(directoryName,
                                                importedFileName, lineList,
                                                visitedFileNameSet)
                        if not isOkay:
                            Logging.traceError("import failed for %r in %r",
                                               importedFileName,
                                               cls._searchPathList)
                            isOkay = False
                            break

        Logging.trace("<<: %r, %r", isOkay, errorMessage)
        return isOkay
            
    #--------------------
    # EXPORTED FEATURES
    #--------------------

    @classmethod
    def setSearchPaths (cls, searchPathList : StringList):
        """Sets list of search paths to <searchPathList>."""

        Logging.trace(">>: %r", searchPathList)
        cls._searchPathList = ["."] + searchPathList
        Logging.trace("<<")

    #--------------------

    def __init__ (self, fileName : String):
        """Parses configuration file given by <fileName> and sets
           internal key to value map."""

        Logging.trace(">>: %r", fileName)

        self._keyToValueMap = {}
        self._keyToStringValueMap = {}
        visitedFileNameSet = set()
        lineList = []
        isOkay = self._readFile("", fileName, lineList, visitedFileNameSet)
        self._parseConfiguration(lineList)

        Logging.trace("<<: %s",
                      _reprOfStringToValueMap(self._keyToValueMap))

    #--------------------

    def asStringMap (self) -> StringMap:
        """Returns mapping from all keys in configuration file to their
           effective values"""

        Logging.trace(">>")
        result = dict(self._keyToValueMap)
        Logging.trace("<<: %r", result)
        return result

    #--------------------

    def asDictionary (self) -> Dictionary:
        """Returns mapping from all keys in configuration file to their
           string values as found in the file"""

        Logging.trace(">>")
        result = dict(self._keyToStringValueMap)
        Logging.trace("<<: %r", result)
        return result

    #--------------------

    def keySet (self) -> StringSet:
        """Returns set of all keys in configuration file"""

        Logging.trace(">>")
        result = set(self._keyToValueMap.keys())
        Logging.trace("<<: %r", result)
        return result

    #--------------------

    def value (self,
               key : String,
               defaultValue : Object = missingValue) -> Object:
        """Returns value for <key> in configuration file; if
           <defaultValue> is missing, an error message is logged when
           there is no associated value, otherwise <defaultValue> is
           returned for a missing entry"""

        Logging.trace(">>: key = %s, defaultValue = %r",
                      key, defaultValue)

        isMandatory = (defaultValue == missingValue)
        result = None

        if key in self._keyToValueMap:
            result = self._keyToValueMap[key]
            if isString(result):
                result = result.replace("\\\"", "\"")
        elif isMandatory:
            Logging.traceError("cannot find value for %s", key)
        else:
            result = defaultValue

        Logging.trace("<<: %s", result)
        return result
