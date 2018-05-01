# -*- coding: utf-8-unix -*-
# assertion - provide simple assertion checking

#====================

import os.path
import sys

from basemodules.simplelogging import Logging

#====================

class Assertion:
    """Provides some primitive assertion handling of
       pre-/postconditions and checking conditions."""

    isActive = True

    #--------------------
    # LOCAL FEATURES
    #--------------------

    @classmethod
    def _internalCheck (cls, condition, checkKind, errorMessage):
        """Checks whether <condition> holds, otherwise exits with
           <errorMessage> containing <checkKind>."""
        
        if cls.isActive:
            if not condition:
                Logging.trace("--: %s FAILED - %s", checkKind, errorMessage)
                programName = os.path.basename(sys.argv[0])
                sys.exit(programName + ": ERROR - " + errorMessage)
    
    #--------------------
    # EXPORTED FEATURES
    #--------------------

    @classmethod
    def check (cls, condition, errorMessage):
        """Checks <condition> within function with <procName> and
           exits with <errorMessage> on failure."""

        cls._internalCheck(condition, "CHECK", errorMessage)

    #--------------------

    @classmethod
    def post (cls, condition, errorMessage):
        """Checks postcondition <condition> within function with
           <procName> and exits with <errorMessage> on failure."""

        cls._internalCheck(condition, "POSTCONDITION", errorMessage)

    #--------------------

    @classmethod
    def pre (cls, condition, errorMessage):
        """Checks precondition <condition> and exits with
           <errorMessage> on failure."""

        cls._internalCheck(condition, "PRECONDITION", errorMessage)

