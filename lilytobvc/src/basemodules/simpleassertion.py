# assertion - provide simple assertion checking
#
# author: Dr. Thomas Tensi, 2014

#====================

import os.path
import sys

from .simplelogging import Logging
from .simpletypes import Boolean, String

#====================

class Assertion:
    """Provides some primitive assertion handling of
       pre-/postconditions and checking conditions."""

    isActive = True

    #--------------------
    # LOCAL FEATURES
    #--------------------

    @classmethod
    def _internalCheck (cls,
                        condition : Boolean,
                        checkKind : String,
                        errorMessage : String):
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
    def check (cls,
               condition : Boolean,
               errorMessage : String):
        """Checks <condition> within function with <procName> and
           exits with <errorMessage> on failure."""

        cls._internalCheck(condition, "CHECK", errorMessage)

    #--------------------

    @classmethod
    def post (cls,
              condition : Boolean,
              errorMessage : String):
        """Checks postcondition <condition> within function with
           <procName> and exits with <errorMessage> on failure."""

        cls._internalCheck(condition, "POSTCONDITION", errorMessage)

    #--------------------

    @classmethod
    def pre (cls,
             condition : Boolean,
             errorMessage : String):
        """Checks precondition <condition> and exits with
           <errorMessage> on failure."""

        cls._internalCheck(condition, "PRECONDITION", errorMessage)

