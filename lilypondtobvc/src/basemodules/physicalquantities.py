# -*- coding:utf-8 -*-
# PhysicalQuantities - provides physical quantities in SI units
#
# author: Dr. Thomas Tensi, 2023-11

#====================
# IMPORTS
#====================

from basemodules.simpletypes import Real, String

#====================

Duration = Real # in seconds
Time = Real # in seconds

#====================

def durationToString (d : Duration) -> String:
    return "%ss" % d

#--------------------

def timeToString (t : Time) -> String:
    return "%ss" % t

