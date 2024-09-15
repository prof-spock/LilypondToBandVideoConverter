# ArrayTypes - simple arrays for bits, integers and reals
#
# author: Dr. Thomas Tensi, 2023

#====================

from array import array
from basemodules.simpletypes import Bit, BitList, Boolean, Character, \
                                    Class, Integer, IntegerList, List, \
                                    Natural, NaturalList, Object, \
                                    RealList,  String
from basemodules.ttbase import iif

#====================

class _MyArray:
    
    #--------------------
    # PRIVATE FEATURES
    #--------------------

    def _ensureCount (self,
                      count : Natural):
        """Makes allocated size of <self> at least <count>"""

        allocatedCount = len(self._data)
        
        if allocatedCount < count:
            rest = count - allocatedCount
            dummyData = array(self._typeCode, [ self._initialValue ])
            extensionCount = 1

            while rest > 0:
                if rest & extensionCount > 0:
                    self._data.extend(dummyData)
                    rest -= extensionCount
                    
                dummyData.extend(dummyData)
                extensionCount *= 2
    
    #--------------------

    @classmethod
    def _fromList (cls,
                   type : Class,
                   data : List) -> Object:
        """Fills array from <data>"""

        count = len(data)
        result = type(count)

        for i in range(count):
            result._data[i] = data[i]

        return result

    #--------------------

    def _slice (self,
                first : Natural,
                last  : Natural = None) -> array:
        """Returns array slice from <first> to <last>"""

        count = self._count

        if last is None: last  = count
        if first < 0:    first = count + first
        if last < 0:     last  = count + last

        count = max(last - first, 0)
        result = self._data[first:last]

        return result

    #--------------------

    def _toString (self,
                   separatorIsUsed : Boolean) -> String:
        """Returns string representation"""

        count = self._count
        clsName = self.__class__.__name__
        separator = iif(separatorIsUsed, ", ", "")
        dataAsString = separator.join(( "%s" % value
                                        for value in self._data ))
        return ("%s(%s %r)" % (clsName, self._typeCode, dataAsString))

    #--------------------
    # EXPORTED FEATURES
    #--------------------

    def __init__ (self,
                  typeCode : Character,
                  initialValue : Object,
                  count : Natural):
        """Initializes array from <typeCode> with <initialValue> with
           <count> elements"""

        self._data         = array(typeCode)
        self._count        = count
        self._typeCode     = typeCode
        self._initialValue = initialValue

        self._ensureCount(count)

    #--------------------

    def __iter__ (self):
        """Returns an iterator onto self"""

        return iter(self.values())

    #--------------------
    #--------------------

    def at (self,
            i : Integer) -> Bit:
        """Returns value at position <i>"""

        return self._data[i]

    #--------------------

    def count (self) -> Natural:
        """Returns size of array"""

        return self._count
    
    #--------------------

    def find (self,
              otherArray : Object) -> Integer:
        """Returns position where <other> is sub list (or -1 on
           failure)"""

        result = -1
        count      = self._count
        otherCount = otherArray._count

        for i in range(count - otherCount):
            isFound = True
            k = i

            for j, otherValue in enumerate(otherArray):
                if otherValue == self._data[k]:
                    k += 1
                else:
                    isFound = False
                    break

            if isFound:
                result = i

        return result
    
    #--------------------

    def prepend (self,
                 otherArray : Object):
        """Prepends <otherArray> to current array"""

        originalCount = self._count
        otherCount = otherArray._count
        self._ensureCount(originalCount + otherCount)

        for i in reversed(range(originalCount)):
            self._data[i + otherCount] = self._data[i]

        for i in range(otherCount):
            self._data[i] = otherArray._data[i]

        self._count += otherCount
        
    #--------------------

    def set (self,
             i : Natural,
             value : Object):
        """Sets data at position <i> to <value>"""

        self._data[i] = value

    #--------------------

    def trim (self,
              count : Natural):
        """Sets size of list to <count>"""

        self._count = count
    
    #--------------------

    def values (self) -> List:
        return self._data[:self._count]
        
#====================

class BitArray (_MyArray):
    """An array of bits 0 and 1"""

    _typeCode = "b"

    #--------------------
    #--------------------

    def __init__ (self,
                  count : Natural = 0):
        cls = self.__class__
        _MyArray.__init__(self, cls._typeCode, 0, count)

    #--------------------

    def __repr__ (self):
        """Returns string representation"""

        return self._toString(False)

    #--------------------
    #--------------------

    @classmethod
    def fromList (cls,
                  data : BitList) -> Object:
        """Fills array from <data>"""

        return _MyArray._fromList(BitArray, data)

    #--------------------

    @classmethod
    def fromString (cls,
                    st : String):
        """Make bit list from string <st> consisting of zeros and
           ones"""

        result = BitArray(len(st))

        for i, ch in enumerate(st):
            value = iif(ch == "0", 0, 1)
            result.set(i, value)

        return result
    
    #--------------------

    def slice (self,
               first : Natural,
               last  : Natural = None) -> Object:
        """Returns slice from <first> to <last>"""

        cls = self.__class__
        return cls.fromList(self._slice(first, last))
    
    #--------------------

    def updateWithValue (self,
                         position : Natural,
                         value : Natural,
                         count : Natural = 4):
        """Updates bit array starting at <position> by value in
           little-endian manner using <count> bits"""

        ## Logging.trace(">>: position = %d, value = %d, count = %d",
        ##               position, value, count)

        for i in range(count):
            value, positionValue = divmod(int(value), 2)
            self.set(position, positionValue)
            position = position + 1

        ## Logging.trace("<<")

#====================

class IntegerArray (_MyArray):
    """An array of integer values"""

    _typeCode = "l"

    #--------------------

    def __init__ (self,
                  count : Natural = 0):
        cls = self.__class__
        _MyArray.__init__(self, cls._typeCode, 0, count)

    #--------------------

    def __repr__ (self):
        """Returns string representation"""

        return self._toString(True)

    #--------------------
    #--------------------

    @classmethod
    def fromList (cls,
                  data : IntegerList) -> Object:
        """Fills array from <data>"""

        return _MyArray._fromList(IntegerArray, data)
        
#====================

class NaturalArray (_MyArray):
    """An array of natural values"""

    _typeCode = "L"

    #--------------------

    def __init__ (self,
                  count : Natural = 0):
        cls = self.__class__
        super.__init__(self, cls._typeCode, 0, count)

    #--------------------

    def __repr__ (self):
        """Returns string representation"""

        return self._toString(True)

    #--------------------
    #--------------------

    @classmethod
    def fromList (cls,
                  data : NaturalList) -> Object:
        """Fills array from <data>"""

        return _MyArray._fromList(NaturalArray, data)
        
#====================

class RealArray (_MyArray):
    """An array of real values"""

    _typeCode = "d"

    #--------------------

    def __init__ (self,
                  count : Natural = 0):
        cls = self.__class__
        _MyArray.__init__(self, cls._typeCode, 0.0, count)

    #--------------------

    def __repr__ (self):
        """Returns string representation"""

        return self._toString(True)

    #--------------------
    #--------------------

    @classmethod
    def fromList (cls,
                  data : RealList) -> Object:
        """Fills array from <data>"""

        return _MyArray._fromList(RealArray, data)
