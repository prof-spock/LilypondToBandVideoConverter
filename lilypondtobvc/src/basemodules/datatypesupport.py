# datatypesupport - provides support for python data classes
#
# author: Dr. Thomas Tensi, 2021

#====================
# IMPORTS
#====================

from copy import deepcopy
import dataclasses

from basemodules.regexppattern import RegExpPattern
from basemodules.simpleassertion import Assertion
from basemodules.simplelogging import Logging
from basemodules.simpletypes import Callable, DataType, Dictionary, \
                                    Object, ObjectList, String, \
                                    StringList, StringMap
from basemodules.stringutil import adaptToKind, deserializeToMap
from basemodules.ttbase import iif, iif3
from basemodules.validitychecker import ValidityChecker

#====================
# PRIVATE FEATURES
#====================

_alternativeNameKey = "alternativeName"
_deserialisationProcKey = "deserialisationProc"
_valueSelectionProcKey = "valueSelectionProc"

#====================
# EXPORTED FEATURES
#====================

# short form of setattr proc for frozen data types
SETATTR = object.__setattr__

#--------------------

def specialField (defaultValue : Object,
                  deserialisationProc : Callable,
                  alternativeName : String = None,
                  valueSelectionProc : Callable = None):
    """Makes a dataclass field with given <defaultValue> and
       <deserialisationProc> as the conversion from string to field
       value; if <alternativeName> is set, it is used as the access
       key for deserialization"""

    metadata = {}

    if deserialisationProc is not None:
        metadata[_deserialisationProcKey] = deserialisationProc

    if valueSelectionProc is not None:
        metadata[_valueSelectionProcKey] = valueSelectionProc

    if alternativeName is not None:
        metadata[_alternativeNameKey] = alternativeName

    return dataclasses.field(default=defaultValue, metadata=metadata)
    
#====================

class DataTypeSupport:
    """Provides simple support for Python data classes"""

    #--------------------
    # PRIVATE FEATURES
    #--------------------

    # the mapping from python type name to local type symbol
    _pythonTypeNameToKindMap = {
        "<class 'bool'>"  : "B",
        "<class 'float'>" : "R",
        "<class 'int'>"   : "I",
        "<class 'str'>"   : "S",
        "<class 'list'>"  : "[]",
        "<class 'dict'>"  : "{}"
    }

    #--------------------

    @classmethod
    def _attributeNameToPythonTypeNameMap (cls,
                                           dataType : DataType) -> Dictionary:
        """Returns the map from attributes names in <dataType> to the
           associated python type names"""

        dataTypeName = dataType.__name__
        Logging.trace(">>: %s", dataTypeName)
        fieldList = dataclasses.fields(dataType)
        result = { attribute.name : ("%s" % attribute.type)
                   for attribute in fieldList }
        Logging.trace("<<: %r", result)
        return result

    #--------------------

    @classmethod
    def _checkForTypesAndCompleteness (cls,
                                       currentObject : Object,
                                       attributeNameToValueMap : StringMap):
        """Checks for <currentObject> of some datatype whether elements in
           <attributeNameToValueMap> are valid and have correct types"""

        objectName   = currentObject.name
        dataType     = currentObject.__class__
        dataTypeName = dataType.__name__

        Logging.trace(">>: name = %r, kind = %r, attributeNameToValueMap = %s",
                      objectName, dataTypeName, attributeNameToValueMap)
        Assertion.pre(dataclasses.is_dataclass(dataType),
                      "object type %s must be a dataclass" % dataTypeName)

        nameToAttributeMetadataMap = \
            cls._nameToAttributeMetadataMap(dataType)
        attributeNameToPythonTypeNameMap = \
            cls._attributeNameToPythonTypeNameMap(dataType)
        attributeNameList = cls.attributeNameList

        for attributeName in attributeNameToValueMap:
            if hasattr(currentObject, attributeName):
                attributeMetadata = \
                    nameToAttributeMetadataMap.get(attributeName)
                valueName = \
                    "(%s) %s.%s" % (dataTypeName, objectName, attributeName)
                isOkay = \
                    (attributeNameToValueMap.get(attributeName) is not None)
                ValidityChecker.isValid(isOkay, "no value for %s" % valueName)
                pythonType = attributeNameToPythonTypeNameMap[attributeName]
                kind = cls._pythonTypeNameToKindMap.get(pythonType, "")
                value = attributeNameToValueMap[attributeName]

                if _valueSelectionProcKey in attributeMetadata:
                    Logging.trace("--: adapting value %r", value)
                    valueSelectionProc = \
                        attributeMetadata[_valueSelectionProcKey]
                    try:
                        value = valueSelectionProc(value)
                    except:
                        value = None

                Logging.trace("--: valueName = %s, pythonType = %r,"
                              + " kind = %r, value = %r",
                              valueName, pythonType, kind, value)

                if kind in [ "I", "R" ]:
                    isReal = (kind == "R")
                    ValidityChecker.isNumberString(value, valueName, isReal)
                elif kind == "B":
                    ValidityChecker.isBooleanString(value, valueName)
                elif kind == "{}":
                    ValidityChecker.isMap(value, valueName)
                elif kind == "[]":
                    ValidityChecker.isList(value, valueName)

        Logging.trace("<<")

    #--------------------

    @classmethod
    def _internalAttributeNameToValueMap (cls,
                                          dataType : DataType,
                                          attributeNameToValueMap : StringMap
                                          ) -> StringMap:
        """Returns the map from internal unaliased name of attributes in
           <dataType> to their values (if any) in <attributeNameToValueMap>"""

        dataTypeName = dataType.__name__
        Logging.trace(">>: dataType = %s, map = %r",
                      dataTypeName, attributeNameToValueMap)
        nameToAttributeMetadataMap = \
            cls._nameToAttributeMetadataMap(dataType)
        fieldList = dataclasses.fields(dataType)
        extAttributeNameToNameListMap = {}

        for attribute in fieldList:
            if (attribute.metadata is not None
                and _alternativeNameKey in attribute.metadata):
                extAttributeName = attribute.metadata[_alternativeNameKey]
                attributeNameList = \
                    (extAttributeNameToNameListMap.get(extAttributeName, [])
                     + [ attribute.name ])
                extAttributeNameToNameListMap[extAttributeName] = \
                    attributeNameList

        result = {}

        for extAttributeName, value in attributeNameToValueMap.items():
            # map external name to internal name and construct new map
            attributeNameList = \
                extAttributeNameToNameListMap.get(extAttributeName,
                                                  [ extAttributeName ])

            for attributeName in attributeNameList:
                result[attributeName] = value

        Logging.trace("<<: %r", result)
        return result

    #--------------------

    @classmethod
    def _nameToAttributeMetadataMap (cls,
                                     dataType : DataType) -> StringMap:
        """Returns mapping from attribute name to associated metadata for
           given <dataType>"""

        Logging.trace(">>: %s", dataType.__name__)
        result = { attribute.name : attribute.metadata
                   for attribute in dataclasses.fields(dataType) }
        Logging.trace("<<: %r", result)
        return result

    #--------------------

    @classmethod
    def _setDataClassAttributesFromMap (cls,
                                        currentObject : Object,
                                        attributeNameToValueMap : Dictionary):
        """Sets corresponding attributes in <currentObject> to associated
           values in <attributeNameToValueMap>; does not check that
           data class types and values match"""

        objectName   = currentObject.name
        dataType     = currentObject.__class__
        dataTypeName = dataType.__name__

        Logging.trace(">>: name = %r, kind = %r, attributeNameToValueMap = %s",
                      objectName, dataTypeName, attributeNameToValueMap)
        Assertion.pre(dataclasses.is_dataclass(dataType),
                      "object type %s must be a dataclass" % dataTypeName)

        nameToAttributeMetadataMap = \
            cls._nameToAttributeMetadataMap(dataType)
        attributeNameToPythonTypeNameMap = \
            cls._attributeNameToPythonTypeNameMap(dataType)
        attributeNameSet = set(cls.attributeNameList(dataType))

        for attributeName, value in attributeNameToValueMap.items():
            Logging.trace("--: set attribute %s to value %r",
                          attributeName, value)
            attributeMetadata = \
                nameToAttributeMetadataMap.get(attributeName)

            if (attributeMetadata is not None
                and _deserialisationProcKey in attributeMetadata):
                deserialisationProc = \
                    attributeMetadata[_deserialisationProcKey]
                value = deserialisationProc(value)
            else:
                attributeTypeName = \
                    attributeNameToPythonTypeNameMap[attributeName]
                valueKind = \
                    cls._pythonTypeNameToKindMap.get(attributeTypeName, "S")
                value = adaptToKind(str(value), valueKind)
                Logging.trace("--: attribute = %s, attributeTypeName = %s,"
                              + " valueKind = %s, value = %r",
                              attributeName, attributeTypeName, valueKind,
                              value)

            object.__setattr__(currentObject, attributeName, value)

        Logging.trace("<<")

    #--------------------
    # EXPORTED FEATURES
    #--------------------

    @classmethod
    def attributeNameList (cls,
                           dataType : DataType) -> StringList:
        """Returns the list of attributes names in <dataType>"""

        dataTypeName = dataType.__name__
        Logging.trace(">>: %s", dataTypeName)
        result = [ attribute.name
                   for attribute in dataclasses.fields(dataType) ]
        Logging.trace("<<: %r", result)
        return result

    #--------------------

    @classmethod
    def convertToString (cls,
                         currentObject : Object,
                         dataType : DataType = None) -> String:
        """Returns a string representation of <currentObject> belonging to
           some data class"""

        dataType = (dataType if dataType is not None
                    else currentObject.__class__)
        dataTypeName = dataType.__name__
        Assertion.pre(dataclasses.is_dataclass(dataType),
                      "object type %s must be a dataclass" % dataTypeName)

        attributeNameToPythonTypeNameMap = \
            cls._attributeNameToPythonTypeNameMap(dataType)
        attributeNameList = cls.attributeNameList(dataType)
        templateString = "%s("
        valueList = [ dataTypeName ]

        for i, attributeName in enumerate(attributeNameList):
            valueList.append(getattr(currentObject, attributeName))
            pythonType = attributeNameToPythonTypeNameMap[attributeName]
            kind = cls._pythonTypeNameToKindMap.get(pythonType, "")
            templateString += (iif(i > 0, ", ", "")
                               + attributeName + " = "
                               + iif3(kind == "R", "%5.3f",
                                      kind == "I", "%d",
                                      kind == "S", "%r",
                                      "%r"))

        templateString += ")"
        st = templateString % tuple(valueList)
        return st

    #--------------------

    @classmethod
    def checkAndSetFromMap (cls,
                            currentObject : Object,
                            attributeNameToValueMap : StringMap):
        """Checks validity of variables in <attributeNameToValueMap> and
           assigns them to object <currentObject>"""

        Logging.trace(">>: %r", attributeNameToValueMap)

        # check and set object values
        SETATTR(currentObject, "name", attributeNameToValueMap.get("name"))

        # construct the mapping from external name to associated values
        internalAttributeNameToValueMap = \
            cls._internalAttributeNameToValueMap(currentObject.__class__,
                                                 attributeNameToValueMap)
        cls._checkForTypesAndCompleteness(currentObject,
                                          internalAttributeNameToValueMap)
        cls._setDataClassAttributesFromMap(currentObject,
                                           internalAttributeNameToValueMap)

        Logging.trace("<<: %r", currentObject)

    #--------------------

    @classmethod
    def generateObjectListFromString (cls,
                                      st : String,
                                      prototypeObject : Object) -> ObjectList:
        """Generates list of objects as copies of <prototypeObject> from
           external representation <st> describing a mapping from
           object name to object value"""

        Logging.trace(">>: %r", st)

        result = []
        table = deserializeToMap(st)

        for name, attributeNameToValueMap in table.items():
            attributeNameToValueMap["name"] = name
            Logging.trace("--: converting %s = %r",
                          name, attributeNameToValueMap)
            currentObject = deepcopy(prototypeObject)
            cls.checkAndSetFromMap(currentObject, attributeNameToValueMap)
            result.append(currentObject)

        Logging.trace("<<: %r", result)
        return result

    #--------------------

    @classmethod
    def generateObjectMapFromString (cls,
                                     st : String,
                                     prototypeObject : Object) -> StringMap:
        """Generates map of objects as copies of <prototypeObject> from
           external representation <st> describing a mapping from
           object name to object value"""

        Logging.trace(">>: %r", st)

        result = {}
        table = deserializeToMap(st)

        for name, attributeNameToValueMap in table.items():
            attributeNameToValueMap["name"] = name
            Logging.trace("--: converting %s = %r",
                          name, attributeNameToValueMap)
            currentObject = deepcopy(prototypeObject)
            cls.checkAndSetFromMap(currentObject, attributeNameToValueMap)
            result[name] = currentObject

        Logging.trace("<<: %r", result)
        return result

    #--------------------

    @classmethod
    def regexpPattern (cls, dataType : DataType) -> String:
        """Returns simple regexp pattern for checking a data type string"""

        Logging.trace(">>")
        noCommaPattern = r"(?:'[^']*'|\{[^\}]*\}|[^,'\s]+)"
        attributeNameList = cls.attributeNameList(dataType)
        attributeNamePattern = \
            "(?:%s)" % ("|".join(attributeNameList))
        result = RegExpPattern.makeMapPattern(attributeNamePattern,
                                              noCommaPattern, False)
        Logging.trace("<<: %r", result)
        return result

#====================

class AbstractDataType:
    """A superclass for all simple data types providing representation and
       regexp functions"""

    #--------------------
    # EXPORTED FEATURES
    #--------------------

    def __repr__ (self) -> String:
        return DataTypeSupport.convertToString(self)

    #--------------------

    @classmethod
    def regexpPattern (cls) -> String:
        """Returns regexp pattern for checking the deserialized 
           representation of an object"""

        Logging.trace(">>")
        result = DataTypeSupport.regexpPattern(cls)
        Logging.trace("<<: %r", result)
        return result
