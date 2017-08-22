# -*- coding: utf-8-unix -*-
# TTBase - provides several elementary functions like conditional
#          expressions

#====================

missingValue = "@!XYZZY"

#====================

def iif (condition, trueValue, falseValue):
    """Emulates conditional expressions with full value evaluation."""

    if condition:
        return trueValue
    else:
        return falseValue

#--------------------

def iif2 (condition1, trueValue1, condition2, trueValue2, falseValue2):
    """Emulates a sequence of conditional expressions with full
       condition and value evaluation."""

    return iif(condition1, trueValue1,
               iif(condition2, trueValue2, falseValue2))

#--------------------

def iif3 (condition1, trueValue1, condition2, trueValue2,
          condition3, trueValue3, falseValue3):
    """Emulates a sequence of conditional expressions with full
       condition and value evaluation."""

    return iif(condition1, trueValue1,
               iif2(condition2, trueValue2,
                    condition3, trueValue3, falseValue3))

#--------------------

def iif4 (condition1, trueValue1, condition2, trueValue2,
          condition3, trueValue3, condition4, trueValue4, falseValue4):
    """Emulates a sequence of conditional expressions with full
       condition and value evaluation."""

    return iif(condition1, trueValue1,
               iif3(condition2, trueValue2,
                    condition3, trueValue3,
                    condition4, trueValue4, falseValue4))

#--------------------

def convertStringToList (st, separator=",", kind="S"):
    """Splits <st> with parts separated by <separator> into list with
       all parts having leading and trailing whitespace removed; if
       <kind> is 'I' or 'F' the elements are transformed into ints or
       floats"""

    if st.strip() == "":
        result = []
    else:
        result = map(lambda x: x.strip(), st.split(separator))

        if kind == "I":
            result = map(lambda x: int(x), result)
        elif kind == "F":
            result = map(lambda x: float(x), result)
        
    return result

#--------------------

def isInRange (x, lowBound, highBound):
    """Tells whether x lies in the range from <lowBound> to
       <highBound>."""

    return (x >= lowBound and x <= highBound)

#--------------------

def adaptToRange (x, lowBound, highBound, isCyclic=False):
    """Adapts <x> to range [<lowBound>, <highBound>] either by
       clipping at the bounds or <ifCyclic> by shifting periodically"""

    if isInRange(x, lowBound, highBound):
        result = x
    elif not isCyclic:
        result = iif(x < lowBound, lowBound, highBound)
    else:
        intervalLength = highBound - lowBound

        if intervalLength < 1e-4:
            result = lowBound
        else:
            result = x

            while result < lowBound:
                result += intervalLength
            while result > highBound:
                result -= intervalLength

    return result

#--------------------

def stringToHex (st):
    """Returns hex representation of <st>"""

    return "".join(map(lambda x: ("%02X" % ord(x)), st))
 
#====================

class MyRandom:
    """This module provides a simple but reproducible random
       generator."""

    value = None

    #--------------------

    @classmethod
    def initialize (cls):
        cls.value = 0.123456789

    #--------------------

    @classmethod
    def random (cls):
        """Returns a random number in interval [0, 1["""

        cls.value *= 997.0
        cls.value -= int(cls.value)
        return cls.value
