# attributemanager -- services for checking and setting attributes from
#                     name-to-value maps
#
# author: Dr. Thomas Tensi, 2006 - 2017

#====================
# IMPORTS
#====================

from .simplelogging import Logging
from .stringutil import adaptToKind
from .validitychecker import ValidityChecker
from .ttbase import iif, iif3

#====================

class AttributeManager:

    @classmethod
    def checkForTypesAndCompleteness (cls, objectName, objectKind,
                                      attributeNameToValueMap,
                                      attributeNameToKindMap):
        """Checks for object with <objectName> and kind <objectKind>
           whether elements in <attributeNameToValueMap> occur in
           <attributeNameToKindMap> and have correct types"""

        Logging.trace(">>: name = '%s', kind = '%s', attributeMap = %s"
                      + " referenceMap = %s",
                      objectName, objectKind,
                      attributeNameToValueMap, attributeNameToKindMap)

        for attributeName in attributeNameToKindMap.keys():
            valueName = "(%s) %s.%s" % (objectKind, objectName, attributeName)
            isOkay = (attributeNameToValueMap.get(attributeName) is not None)
            ValidityChecker.isValid(isOkay, "no value for %s" % valueName)
            kind  = attributeNameToKindMap[attributeName]
            value = attributeNameToValueMap[attributeName]

            if kind in [ "I", "F" ]:
                isFloat = (kind == "F")
                ValidityChecker.isNumberString(value, valueName, isFloat)
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
    def convertToString (cls, object, className, attributeNameList,
                         attributeNameToKindMap=None):
        """Returns a string representation of <object> belonging to class with
           <className> using explicit metadata given by
           <attributeNameList> and <attributeNameToKindMap>"""

        templateString = "%s("
        valueList = [ className ]

        for i, attributeName in enumerate(attributeNameList):
            valueList.append(getattr(object, attributeName))
            kind = attributeNameToKindMap[attributeName]
            templateString += (iif(i > 0, ", ", "")
                               + attributeName + " = "
                               + iif3(kind == "F", "%5.3f",
                                      kind == "I", "%d",
                                      kind == "S", "'%s'",
                                      "%s"))
 
        templateString += ")"
        st = templateString % tuple(valueList)
        return st

    #--------------------

    @classmethod
    def setAttributesFromMap (cls, object, attributeNameToValueMap,
                              attributeNameToKindMap=None):
        """Sets corresponding attributes in <object> to associated values in
           <attributeNameToValueMap>; if <attributeNameToKindMap> is
           defined, then appropriate type mappings are done."""

        Logging.trace(">>: nameToValueMap = %s, nameToKindMap = %s",
                      attributeNameToValueMap, attributeNameToKindMap)

        for attributeName in attributeNameToValueMap.keys():
            value = attributeNameToValueMap[attributeName]

            if (attributeNameToKindMap is not None
                and attributeName in attributeNameToKindMap):
                kind = attributeNameToKindMap[attributeName]
                value = adaptToKind(value, kind)

            setattr(object, attributeName, value)

        Logging.trace("<<")


