# attributemanager -- services for checking and setting attributes from
#                     name-to-value maps
#
# author: Dr. Thomas Tensi, 2006 - 2017

#====================
# IMPORTS
#====================

from basemodules.simplelogging import Logging
from basemodules.simpletypes import Dictionary, Object, String, \
                                    StringList
from basemodules.stringutil import adaptToKind
from basemodules.validitychecker import ValidityChecker
from basemodules.ttbase import iif, iif3

#====================

class AttributeManager:
    """provides services for checking and setting attributes from
       name-to-value maps"""

    #--------------------

    @classmethod
    def checkForTypesAndCompleteness (cls,
                                      objectName : String,
                                      objectKind : String,
                                      attributeNameToValueMap : Dictionary,
                                      attributeNameToKindMap : Dictionary):
        """Checks for object with <objectName> and kind <objectKind>
           whether elements in <attributeNameToValueMap> occur in
           <attributeNameToKindMap> and have correct types"""

        Logging.trace(">>: name = %r, kind = %r, attributeMap = %s"
                      + " referenceMap = %s",
                      objectName, objectKind,
                      attributeNameToValueMap, attributeNameToKindMap)

        for attributeName in attributeNameToKindMap.keys():
            valueName = "(%s) %s.%s" % (objectKind, objectName, attributeName)
            isOkay = (attributeNameToValueMap.get(attributeName) is not None)
            ValidityChecker.isValid(isOkay, "no value for %s" % valueName)
            kind  = attributeNameToKindMap[attributeName]
            value = attributeNameToValueMap[attributeName]

            if kind in [ "I", "R" ]:
                isReal = (kind == "R")
                ValidityChecker.isNumberString(value, valueName, isReal)
            elif kind == "B":
                errorMessage = ("bad kind for %s: %s" % (valueName, value))
                ValidityChecker.isValid(value.upper() in ["TRUE", "FALSE"],
                                        errorMessage)
            elif kind == "{}":
                ValidityChecker.isMap(value, valueName)
            elif kind == "[]":
                ValidityChecker.isList(value, valueName)

        Logging.trace("<<")


    #--------------------

    @classmethod
    def convertToString (cls,
                         currentObject : Object,
                         className : String,
                         attributeNameList : StringList,
                         attributeNameToKindMap : Dictionary = None):
        """Returns a string representation of <currentObject> belonging to
           class with <className> using explicit metadata given by
           <attributeNameList> and <attributeNameToKindMap>"""

        templateString = "%s("
        valueList = [ className ]

        for i, attributeName in enumerate(attributeNameList):
            valueList.append(getattr(currentObject, attributeName))
            kind = attributeNameToKindMap[attributeName]
            templateString += (iif(i > 0, ", ", "")
                               + attributeName + " = "
                               + iif3(kind == "F", "%5.3f",
                                      kind == "I", "%d",
                                      kind == "S", "%r",
                                      "%r"))

        templateString += ")"
        st = templateString % tuple(valueList)
        return st

    #--------------------

    @classmethod
    def setAttributesFromMap (cls,
                              currentObject : Object,
                              attributeNameToValueMap : Dictionary,
                              attributeNameToKindMap : Dictionary = None):
        """Sets corresponding attributes in <currentObject> to associated
           values in <attributeNameToValueMap>; if
           <attributeNameToKindMap> is defined, then appropriate type
           mappings are done."""

        Logging.trace(">>: nameToValueMap = %r, nameToKindMap = %r",
                      attributeNameToValueMap, attributeNameToKindMap)

        for attributeName in attributeNameToValueMap.keys():
            value = attributeNameToValueMap[attributeName]

            if (attributeNameToKindMap is not None
                and attributeName in attributeNameToKindMap):
                kind = attributeNameToKindMap[attributeName]
                value = adaptToKind(value, kind)

            setattr(currentObject, attributeName, value)

        Logging.trace("<<")
