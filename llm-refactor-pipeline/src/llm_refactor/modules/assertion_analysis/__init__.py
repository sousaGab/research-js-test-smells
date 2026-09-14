"""Before/after assertion analysis module.

Statically compares the assertions of each experiment's original and
refactored code (Babel AST), classifies weakening patterns such as
always-true assertions and assertion deletion, and cross-references them
with execution outcomes.
"""

from .assertion_analysis import execute, AssertionAnalysisModule

__all__ = ["execute", "AssertionAnalysisModule"]
