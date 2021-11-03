# -*- coding: utf-8 -*- 
# jsonfile - provides reading of a json file containing
#            include references, comments and assignment to
#            variables
#
# author: Dr. Thomas Tensi, 2021-08

#====================

import io
import json

from .operatingsystem import OperatingSystem
from .simplelogging import Logging
from .simpletypes import Boolean, Dictionary, Natural, Positive, \
                         String, StringList, StringSet
from .ttbase import iif

#====================

class _Token:
    """Simple token within a JSON string"""

    Kind_closingBrace      = "closingBrace"
    Kind_closingBracket    = "closingBracket"
    Kind_identifier        = "identifier"
    Kind_keyValueSeparator = "keyValueSeparator"
    Kind_openingBrace      = "openingBrace"
    Kind_openingBracket    = "openingBracket"
    Kind_plainValue        = "plainValue"
    Kind_recordSeparator   = "recordSeparator"
    Kind_string            = "string"

    #--------------------

    recordSeparatorCharacter = ","

    simpleTokenCharacterToKindMap = {
        "}" : Kind_closingBrace,
        "]" : Kind_closingBracket,
        ":" : Kind_keyValueSeparator,
        "{" : Kind_openingBrace,
        "[" : Kind_openingBracket,
        recordSeparatorCharacter : Kind_recordSeparator
    }

    simpleTokenCharacterList = simpleTokenCharacterToKindMap.keys()

    # list of JSON plain value keywords
    keywordList = [ "true", "false", "null" ]

    #--------------------

    def __init__ (self,
                  lineNumber : Positive,
                  columnNumber : Positive,
                  text : String,
                  kind : String = None):
        """Initializes token with <lineNumber> and <columnNumber> start
           position, token text and token kind"""

        cls = self.__class__

        if kind is None:
            if text in cls.simpleTokenCharacterList:
                kind = cls.simpleTokenCharacterToKindMap[text]
            else:
                kind = cls.Kind_plainValue

        self.lineNumber   = lineNumber
        self.columnNumber = columnNumber
        self.text         = text
        self.kind         = kind
        
    #--------------------

    def __repr__ (self) -> String:
        """String representation for token <self>"""

        st = ("_Token(start=(%r,%r), kind=%s, text=%r)"
              % (self.lineNumber, self.columnNumber,
                 self.kind, self.text))
        return st

    #--------------------

    @classmethod
    def adaptKind (cls,
                   token : _Token,
                   nameToValueMap : Dictionary):
        """Handles special strings in <token> and adapts it accordingly; if
           token is an identifier, it might be replaced by value in
           <nameToValueMap>"""

        if token.kind == _Token.Kind_identifier:
            identifier = token.text
            lowercaseText = identifier.lower()

            if lowercaseText in _Token.keywordList:
                # special identifiers are plain values
                token.kind = _Token.Kind_plainValue
                token.text = lowercaseText
            elif identifier in nameToValueMap.keys():
                token.text = nameToValueMap[identifier]
                token.kind = _Token.Kind_plainValue

        if token.kind == _Token.Kind_plainValue:
            # hex numbers are converted

            if token.text.startswith("0x"):
                try:
                    token.text = "%d" % int(token.text, 0)
                except:
                    token.text = "999999"

#====================

class _TokenList:
    """List of simple tokens within a JSON string"""

    # escape character within strings
    _escapeCharacter = "\\"
    _doubleQuoteCharacter = '"'
    _minusCharacter = "-"

    _digitList = "0123456789"
    _letterList = ("abcdefghijklmnopqrstuvwxyzäöüß"
                   + "ABCDEFGHIJKLMNOPQRSTUVWXYZÄÖÜ_")

    #--------------------
    # PRIVATE FEATURES
    #--------------------

    def _toJsonString (self) -> String:
        """Returns string representation usable for JSON parser"""

        Logging.trace(">>")

        result = ""
        previousTokenKind = None
        criticalTokenKindList = (_Token.Kind_plainValue,
                                 _Token.Kind_identifier)

        for token in self._tokenList:
            if (previousTokenKind in criticalTokenKindList
                and token.kind in criticalTokenKindList):
                # add a blank to separate previous and current token
                result += " "

            result += token.text
            previousTokenKind = token.kind

        Logging.trace("<<: %r", result)
        return result
    
    #--------------------
    # EXPORTED FEATURES
    #--------------------

    def __init__ (self):
        """Initializes token list to be empty"""

        Logging.trace(">>")
        self._tokenList = []
        Logging.trace("<<")

    #--------------------

    def __repr__ (self) -> String:
        """String representation for token list <self>"""

        st = ("_TokenList("
              + ", ".join([str(token) for token in self._tokenList])
              + ")")
        return st

    #--------------------

    @classmethod
    def makeFromLine (cls,
                      lineNumber : Positive,
                      line : String,
                      nameToValueMap : Dictionary):
        """Returns list of tokens scanned from string <line> assuming
           that no token is truncated by end of string; <nameToValueMap>
           gives the mapping from name identifiers to associated values"""

        Logging.trace(">>: %04d - %s", lineNumber, line)
        
        # collect identifiers embedded in value and replace them by
        # their value
        ParseState_inLimbo      = 0
        ParseState_inMinus      = 1
        ParseState_inComment    = 2
        ParseState_inString     = 3
        ParseState_inEscape     = 4
        ParseState_inIdentifier = 5
        ParseState_inNumber     = 6
        parseStateToString = { 0 : "_", 1: "-", 2 : "#", 3: "S",
                               4 : cls._escapeCharacter, 5 : "I",
                               6 : "N" }

        parseState = ParseState_inLimbo
        fsaTrace = ""
        columnIndex = 0
        result = cls()

        while columnIndex < len(line):
            ch = line[columnIndex]
            columnIndex += 1
            fsaTrace += (iif(fsaTrace == "", "", " ")
                         + "[%s] %s" % (parseStateToString[parseState], ch))
            isWhitespace = ch in " \t"

            if parseState == ParseState_inLimbo:
                if isWhitespace:
                    pass
                elif ch == cls._minusCharacter:
                    parseState = ParseState_inMinus
                else:
                    token = _Token(lineNumber, columnIndex, ch)
                    result.append(token)

                    if ch == cls._doubleQuoteCharacter:
                        token.kind = _Token.Kind_string
                        parseState = ParseState_inString
                    elif ch in cls._digitList + "+":
                        parseState = ParseState_inNumber
                    elif ch in _Token.simpleTokenCharacterList:
                        pass
                    else:
                        token.kind = _Token.Kind_identifier
                        parseState = ParseState_inIdentifier
            elif parseState == ParseState_inMinus:
                if ch == cls._minusCharacter:
                    # this is a comment
                    parseState = ParseState_inComment
                else:
                    parseState = ParseState_inNumber
                    st = cls._minusCharacter + ch
                    token = _Token(lineNumber, columnIndex - 1, st)
                    result.append(token)
            elif parseState == ParseState_inComment:
                # this goes to the end of the line
                pass
            elif parseState == ParseState_inString:
                token.text += ch

                if ch == cls._doubleQuoteCharacter:
                    parseState = ParseState_inLimbo
                elif ch == cls._escapeCharacter:
                    parseState = ParseState_inEscape
            elif parseState == ParseState_inEscape:
                token.text += ch
                parseState = ParseState_inString
            else:
                inIdentifier = parseState == ParseState_inIdentifier
                acceptableCharacterList = \
                    (cls._digitList + (cls._letterList if inIdentifier
                                       else "x.ABCDEFabcdef"))

                if ch in acceptableCharacterList:
                    token.text += ch
                else:
                    # token is done
                    _Token.adaptKind(token, nameToValueMap)
                    columnIndex -= 1
                    parseState = ParseState_inLimbo

        # we are done, fix any missing token terminations
        if parseState == ParseState_inEscape:
            token.text += " " + cls._doubleQuoteCharacter
        elif parseState == ParseState_inString:
            token.text += cls._doubleQuoteCharacter
        elif parseState in (ParseState_inIdentifier, ParseState_inNumber):
            _Token.adaptKind(token, nameToValueMap)

        Logging.trace("--: trace = %r", fsaTrace)
        Logging.trace("<<: %r", result)
        return result

    #--------------------

    def normalize (self):
        """Adds missing tokens or remove superfluous tokens when relaxed
           syntax is used"""

        Logging.trace(">>")

        cls = self.__class__
        tokenList = self._tokenList
        adaptedTokenList = []
        lineNumber = 0

        if len(tokenList) > 0:
            previousToken = None
            firstToken = tokenList[0]
            topLevelBracesAreMissing = \
                firstToken.kind != _Token.Kind_openingBrace
            
            if topLevelBracesAreMissing:
                token = _Token(lineNumber, 1, "{")
                adaptedTokenList.append(token)

            for token in tokenList:
                lineNumber = token.lineNumber

                # change identifiers to strings
                if token.kind == _Token.Kind_identifier:
                    token.kind = _Token.Kind_string
                    token.text = (cls._doubleQuoteCharacter
                                  + token.text
                                  + cls._doubleQuoteCharacter)

                if previousToken is None:
                    adaptedTokenList.append(token)
                else:
                    # insert a record separator when a key follows a
                    # closing brace or a plain value or another string
                    tokenPairMustBeSeparated = \
                        (previousToken.kind in (_Token.Kind_closingBrace,
                                                _Token.Kind_plainValue,
                                                _Token.Kind_string)
                         and token.kind == _Token.Kind_string)

                    if tokenPairMustBeSeparated:
                        newToken = _Token(previousToken.lineNumber,
                                          previousToken.columnNumber + 1,
                                          _Token.recordSeparatorCharacter,
                                          _Token.Kind_recordSeparator)
                        adaptedTokenList.append(newToken)

                    previousTokenIsBad = \
                        (previousToken is not None
                         and previousToken.kind == _Token.Kind_recordSeparator
                         and token.kind != _Token.Kind_string)

                    if previousTokenIsBad:
                        adaptedTokenList[-1] = token
                    else:
                        adaptedTokenList.append(token)

                previousToken = token
        
            if topLevelBracesAreMissing:
                token = _Token(lineNumber + 1, 1, "}")

                if previousToken.kind == _Token.Kind_recordSeparator:
                    adaptedTokenList[-1] = token
                else:
                    adaptedTokenList.append(token)

        self._tokenList = adaptedTokenList
        Logging.trace("<<: count = %d", len(adaptedTokenList))

    #--------------------

    def append (self, token):
        """Appends <token> to current list"""

        self._tokenList.append(token)

    #--------------------

    def convertToDictionary (self) -> Dictionary:
        """Returns a dictionary constructed from JSON tokens in current
           list"""

        Logging.trace(">>")

        st = self._toJsonString()

        try:
            result = json.loads(st)
        except Exception as e:
            Logging.trace("--: JSON failed - %r", e)
            result = {}
        
        Logging.trace("<<: %r", result)
        return result
    
    #--------------------

    def count (self) -> Natural:
        """Returns number of tokens in list"""

        return len(self._tokenList)

    #--------------------

    def extend (self, otherList):
        """Appends tokens in <otherList> to current list"""

        self._tokenList.extend(otherList._tokenList)

#====================

class SimpleJsonFile:
    """Provides services for reading a JSON file with hierarchical key -
       value assignments.  If relaxed parsing is allowed, all key
       strings may be without quotes and the top level assignments are
       automatically put into a list and do not need to have
       separators."""

    _commentMarker = "--"
    _definitionCommandName = "#define"
    _importCommandName = "#include"
    _searchPathList = ["."]

    # the map from names in define statements to associated values
    _nameToValueMap = {}
    
    #--------------------
    # LOCAL FEATURES
    #--------------------

    @classmethod
    def _importFile (cls,
                     fileName : String,
                     lineList : StringList,
                     visitedFileNameSet : StringSet):
        """Imports file named <fileName> and appends line to <lineList>,
           updates <visitedFileNameSet> to break import cycles"""

        Logging.trace(">>: file = %r, visitedFiles = %r",
                      fileName, visitedFileNameSet)

        separator = OperatingSystem.pathSeparator
        isAbsolutePath = \
            OperatingSystem.isAbsoluteFileName(importedFileName)

        if isAbsolutePath:
            directoryPrefix = ""
        else:
            directoryName = OperatingSystem.dirname(fileName)
            directoryPrefix = iif(directoryName == ".", "",
                                  directoryName
                                  + iif(directoryName > "",
                                        separator, ""))

        importedFileName = directoryPrefix + importedFileName
        Logging.trace("--: IMPORT %r", importedFileName)

        isOkay = cls._readFile(importedFileName, lineList,
                               visitedFileNameSet)

        Logging.trace("<<: %r", isOkay)
        return isOkay

    #--------------------

    @classmethod
    def _lookupFileName (cls,
                         originalFileName : String) -> String:
        """Returns file name in search paths based on
           <originalFileName>"""

        Logging.trace(">>: %r", originalFileName)

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
    def _processDefinition (cls,
                            line : String):
        """Processes a name definition in <line> and updates <_nameToValueMap>
           accordingly; silently ignored definition when erroneous"""

        Logging.trace(">>: %s", line)

        partList = line.split()

        if len(partList) != 3:
            Logging.traceError("bad definition")
            definedName, associatedValue = ("", "")
        else:
            definedName, associatedValue = partList[1:3]

        if definedName > "":
            while associatedValue in cls._nameToValueMap.keys():
                associatedValue = cls._nameToValueMap[associatedValue]

            cls._nameToValueMap[definedName] = associatedValue
            Logging.trace("--: mapping from %r to %r",
                          definedName, associatedValue)

        Logging.trace("<<")

    #--------------------

    @classmethod
    def _readFile (cls,
                   fileName : String,
                   lineList : StringList,
                   visitedFileNameSet : StringSet):
        """Appends lines of configuration file with <fileName> to
           <lineList>; also handles embedded imports of files;
           <visitedFileNameSet> tells which files have already been
           visited"""

        Logging.trace(">>: fileName = %r, visitedFiles = %r",
                      fileName, visitedFileNameSet)

        errorMessage = ""
        isOkay = True

        originalFileName = fileName
        fileName = cls._lookupFileName(originalFileName)

        if fileName is None:
            errorMessage = "cannot find %r" % originalFileName
            isOkay = False
        elif fileName in visitedFileNameSet:
            Logging.trace("--: file already included %r", originalFileName)
        else:
            visitedFileNameSet.update(fileName)

            with io.open(fileName, "rt",
                         encoding="utf-8") as configurationFile:
                configFileLineList = configurationFile.readlines()

                for currentLine in configFileLineList:
                    trimmedLine = currentLine.strip()
                    currentLine = currentLine.rstrip()
                    isImportLine = \
                        trimmedLine.startswith(cls._importCommandName)
                    isDefinitionLine = \
                        trimmedLine.startswith(cls._definitionCommandName)

                    if isImportLine:
                        importedFileName = currentLine.split('"')[1]

                    if isImportLine or isDefinitionLine:
                        currentLine = cls._commentMarker + " " + currentLine

                    lineList.append(currentLine)

                    if isDefinitionLine:
                        cls._processDefinition(trimmedLine)
                    elif isImportLine:
                        isOkay = cls._importFile(importedFileName, lineList,
                                                 visitedFileNameSet)

                        if not isOkay:
                            Logging.trace("--:import failed for %r in %r",
                                          importedFileName,
                                          cls._searchPathList)
                            isOkay = False
                            break

        Logging.trace("<<: isOkay = %r, lineCount = %d, error = %r",
                      isOkay, len(lineList), errorMessage)
        return isOkay
            
    #--------------------

    @classmethod
    def _tokenize (cls,
                   lineList : StringList) -> _TokenList:
        """Returns list of tokens from lines in <lineList>"""

        Logging.trace(">>: count = %d", len(lineList))

        tokenList = _TokenList()

        for lineIndex, line in enumerate(lineList):
            line = line.rstrip()
            trimmedLine = line.strip()

            if line == "" or trimmedLine.startswith(cls._commentMarker):
                # this is an empty line or comment line => skip it
                pass
            else:
                lineTokenList = _TokenList.makeFromLine(lineIndex + 1,
                                                        line,
                                                        cls._nameToValueMap)
                tokenList.extend(lineTokenList)

        Logging.trace("<<: count = %d", tokenList.count())
        return tokenList

    #--------------------
    # EXPORTED FEATURES
    #--------------------

    @classmethod
    def setSearchPaths (cls,
                        searchPathList : StringList):
        """Sets list of search paths to <searchPathList>."""

        Logging.trace(">>: %r", searchPathList)
        cls._searchPathList = ["."] + searchPathList
        Logging.trace("<<")

    #--------------------

    @classmethod
    def read (cls,
              fileName : String,
              usesRelaxedSyntax : Boolean) -> StringMap:
        """Parses JSON file given by <fileName> and returns a dictionary of
           variable to structure mappings. If <usesRelaxedSyntax> is
           set, all key strings may be without quotes and the top
           level assignments are automatically put into a list and do
           not need to have separators."""

        Logging.trace(">>: fileName = %r, usesRelaxedSyntax = %r",
                      fileName, usesRelaxedSyntax)

        visitedFileNameSet = set()
        lineList = []
        isOkay = cls._readFile(fileName, lineList, visitedFileNameSet)

        tokenList = ([] if not isOkay else cls._tokenize(lineList))

        if isOkay and usesRelaxedSyntax:
            tokenList.normalize()

        result = ({} if not isOkay else tokenList.convertToDictionary())
        Logging.trace("<<: %r", result)
        return result
