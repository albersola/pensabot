from dataclasses import dataclass
from typing import Literal


@dataclass
class SavedMemoryResult:
    operation: Literal["save_memory"] = "save_memory"
    saved_content: str = ""


@dataclass
class RetrievedMemory:
    content: str


@dataclass
class SearchMemoryResult:
    operation: Literal["search_memory"] = "search_memory"
    query: str = ""
    memories: list[RetrievedMemory] | None = None


MemoryOperationResult = SavedMemoryResult | SearchMemoryResult
