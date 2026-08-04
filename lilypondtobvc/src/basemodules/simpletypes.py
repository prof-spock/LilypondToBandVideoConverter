# simpletypes - provide the internal type names like String, Real, ...
#
# author: Dr. Thomas Tensi, 2014

#====================

import sys

isMicroPython = (sys.implementation.name == "micropython")

if isMicroPython:
    import basemodules.typing as typing
else:
    import typing

#====================

Class    = type
ClassVar = typing.ClassVar
DataType = type

# primitive types
Bit       = int
Boolean   = bool
Byte      = int
Character = str
Integer   = int
Natural   = int
Object    = typing.Any
Positive  = int
Real      = float
String    = str

# list types
List        = typing.Sequence
ObjectList  = List
Tuple       = typing.Tuple
Pair        = Tuple

if isMicroPython:
    BitList     = List #List[Bit]
    ByteList    = List #List[Byte]
    IntegerList = List #List[Integer]
    NaturalList = List #List[Natural]
    RealList    = List #List[Real]
    StringList  = List #List[String]
    TupleList   = List #List[Tuple]
else:
    BitList     = List[Bit]
    ByteList    = bytearray
    IntegerList = List[Integer]
    NaturalList = List[Natural]
    RealList    = List[Real]
    StringList  = List[String]
    TupleList   = List[Tuple]

# set types
Set         = typing.Set
ObjectSet   = Set

if isMicroPython:
    StringSet   = Set #Set[String]
else:
    StringSet   = Set[String]

# mapping types
Map        = typing.Mapping

if isMicroPython:
    Dictionary = Map #Map[String, String]
    StringMap  = Map #Map[String, Object]
else:
    Dictionary = Map[String, String]
    StringMap  = Map[String, Object]

# function types
Callable = typing.Callable
