"""Repository-anchored path resolution.

The repository root is identified by containing the `repositories/` dataset
directory. This is depth-independent: it works from any script location and
from any working directory, unlike ``Path(__file__).parent`` arithmetic or
CWD-relative paths, both of which broke whenever a script moved or was run
from outside the repository root.

Requires the package to be installed in editable mode (``pip install -e``),
so that ``__file__`` lives inside the repository tree.
"""
from pathlib import Path
from typing import Union


def find_repo_root(start: Union[Path, str]) -> Path:
    """Walk upwards from *start* until a directory containing
    ``repositories/`` is found. Raises if none exists."""
    for parent in Path(start).resolve().parents:
        if (parent / "repositories").is_dir():
            return parent
    raise RuntimeError(
        f"Repository root not found above {start}: "
        "no 'repositories/' directory in any parent. "
        "Is llm-refactor installed in editable mode from the research repo?"
    )


REPO_ROOT = find_repo_root(__file__)

# Dataset and result directories (children of the repository root)
REPOSITORIES = REPO_ROOT / "repositories"
SMELLS_DETECTED = REPO_ROOT / "smells_detected"
TESTS_OUTPUT = REPO_ROOT / "tests_output"
BATCH_SUMMARIES = REPO_ROOT / "batch_summaries"
RESEARCH_DATA = REPO_ROOT / "research_data"
RESEARCH_DB = RESEARCH_DATA / "research.db"

# The pipeline's own root (llm-refactor-pipeline/)
PIPELINE_ROOT = REPO_ROOT / "llm-refactor-pipeline"
