# -*- coding: utf-8-unix -*-
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
            isOkay = (attributeNameToValueMap.get(attributeName) is not None)
            ValidityChecker.isValid(isOkay,
                                    "no value for %s in %s %s"
                                    % (attributeName, objectKind, objectName))
            kind  = attributeNameToKindMap[attributeName]
            value = attributeNameToValueMap[attributeName]
            errorMessage = ("bad kind for %s in %s %s: %s"
                            % (attributeName, objectKind, objectName, value))

            if kind in [ "I", "F" ]:
                isFloat = (kind == "F")
                ValidityChecker.isNumberString(value, errorMessage, isFloat)
            elif kind == "B":
                ValidityChecker.isValid(value.upper() in ["TRUE", "FALSE"],
                                        errorMessage)

        Logging.trace("<<")

    #--------------------

    @classmethod
    def setAttributesFromMap (cls, object, attributeNameToValueMap,
                              attributeNameToTypeMap=None):
        """Sets corresponding attributes in <object> to associated values in
           <attributeNameToValueMap>; if <attributeNameToTypeMap> is
           defined, then appropriate type mappings are done."""

        Logging.trace(">>: nameToValueMap = %s, nameToTypeMap = %s",
                      attributeNameToValueMap, attributeNameToTypeMap)

        for attributeName in attributeNameToValueMap.keys():
            value = attributeNameToValueMap[attributeName]

            if (attributeNameToTypeMap is not None
                and attributeName in attributeNameToTypeMap):
                kind = attributeNameToTypeMap[attributeName]
                value = adaptToKind(value, kind)

            setattr(object, attributeName, value)

        Logging.trace("<<")


