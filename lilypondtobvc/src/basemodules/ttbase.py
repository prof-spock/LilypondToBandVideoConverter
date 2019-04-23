# TTBase - provides several elementary functions like conditional
#          expressions
#
# author: Dr. Thomas Tensi, 2014

#====================

missingValue = "@!XYZZY"

#====================

def iif (condition, trueValue, falseValue):
    """Emulates conditional expressions with full value evaluation."""

    if condition:
        result = trueValue
    else:
        result = falseValue

    return result

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

def isInRange (x, lowBound, highBound):
    """Tells whether x lies in the range from <lowBound> to
       <highBound>."""

    return (lowBound <= x <= highBound)

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

def intListToHex (currentList):
    """Returns hex representation of integer <currentList>"""

    return "".join(map(lambda x: ("%02X" % x), currentList))

#====================

class MyRandom:
    """This module provides a simple but reproducible random
       generator."""

    value = None

    #--------------------

    @classmethod
    def initialize (cls):
        """Initializes seed to predefined value"""
        cls.value = 0.123456789

    #--------------------

    @classmethod
    def random (cls):
        """Returns a random number in interval [0, 1["""

        cls.value *= 997.0
        cls.value -= int(cls.value)
        return cls.value
