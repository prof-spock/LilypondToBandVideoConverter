# types - provide the internal type names like String, Real, ...
#
# author: Dr. Thomas Tensi, 2014

#====================

import typing

#====================

ClassVar = typing.ClassVar
DataType = type

# primitive types
Boolean  = bool
Integer  = int
Natural  = int
Object   = typing.Any
Positive = int
Real     = float
String   = str

# list types
List        = typing.Sequence
IntegerList = List[Integer]
NaturalList = List[Natural]
ObjectList  = List
RealList    = List[Real]
StringList  = List[String]
Tuple       = typing.Tuple

# set types
Set         = typing.Set
ObjectSet   = Set
StringSet   = Set[String]

# mapping types
Map        = typing.Mapping
Dictionary = Map[String, String]
StringMap  = Map[String, Object]

# function types
Callable = typing.Callable
