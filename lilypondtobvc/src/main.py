# main -- wrapper script around ltbvc program that produces lilypond
#         files and destination files for single voices, a complete
#         score, a midi file, audio and video files based on a
#         configuration file from a lilypond music fragment file
#
# author: Dr. Thomas Tensi, 2006 - 2026

import os.path
import sys

# redirect sys.path to current project package directory
_currentModulePath = os.path.dirname(__file__)
sys.path.append(_currentModulePath)

#====================
# IMPORTS
#====================

from convertermodules.ltbvc import main as ltbvc_main

#--------------------

def main ():
    ltbvc_main()
