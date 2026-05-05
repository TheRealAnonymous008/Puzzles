from __future__ import annotations
from typing import List, Optional

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from puzzle_engine.puzzle import PuzzleState
from puzzle_engine.rule import RuleRegistry, Rule, Violation 
from puzzle_engine.grid import *
from puzzle_engine.lines import *