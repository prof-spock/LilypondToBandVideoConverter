# types - provide the internal type names like String, Real, ...
#
# author: Dr. Thomas Tensi, 2014

#====================

import basemodules.typing as typing

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
BitList     = List #List[Bit]
ByteList    = List #List[Byte]
IntegerList = List #List[Integer]
NaturalList = List #List[Natural]
ObjectList  = List
RealList    = List #List[Real]
StringList  = List #List[String]
Tuple       = typing.Tuple
Pair        = Tuple
TupleList   = List #List[Tuple]

# set types
Set         = typing.Set
ObjectSet   = Set
StringSet   = Set #Set[String]

# mapping types
Map        = typing.Mapping
Dictionary = Map #Map[String, String]
StringMap  = Map #Map[String, Object]

# function types
Callable = typing.Callable
