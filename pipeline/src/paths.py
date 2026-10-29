"""Central paths for the data pipeline.

All paths are anchored at the repository root, so the pipeline can be run from any directory.
"""
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]

DATA_DIR = PROJECT_ROOT / "data"
COLLECTION_DIR = DATA_DIR / "_collections"
SOLR_DIR = DATA_DIR / "_solr"
REPORTS_DIR = DATA_DIR / "_reports"
EDA_REPORTS_DIR = REPORTS_DIR / "eda"

REPORT_DIR = PROJECT_ROOT / "report"
FIGURES_DIR = REPORT_DIR / "figures"
