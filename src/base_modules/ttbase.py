# TTBase - provides several elementary functions like conditional
#          expressions

#--------------------

def iif (condition, true_value, false_value):
    """Emulates conditional expressions with full value evaluation."""

    if condition:
        return true_value
    else:
        return false_value


#--------------------

def iif2 (condition1, true_value1, condition2, true_value2, false_value2):
    """Emulates a sequence of conditional expressions with full
       condition and value evaluation."""

    return iif(condition1, true_value1,
               iif(condition2, true_value2, false_value2))

#--------------------

def iif3 (condition1, true_value1, condition2, true_value2,
          condition3, true_value3, false_value3):
    """Emulates a sequence of conditional expressions with full
       condition and value evaluation."""

    return iif(condition1, true_value1,
               iif2(condition2, true_value2,
                    condition3, true_value3, false_value3))

#--------------------

def iif4 (condition1, true_value1, condition2, true_value2,
          condition3, true_value3, condition4, true_value4, false_value4):
    """Emulates a sequence of conditional expressions with full
       condition and value evaluation."""

    return iif(condition1, true_value1,
               iif3(condition2, true_value2,
                    condition3, true_value3,
                    condition4, true_value4, false_value4))

#--------------------

def convertStringToList (st, separator=",", kind="S"):
    """Splits <st> with parts separated by <separator> into list with
       all parts having leading and trailing whitespace removed; if
       <kind> is 'I' or 'F' the elements are transformed into ints or
       floats"""

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
