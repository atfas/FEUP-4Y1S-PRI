"""Central paths for the data pipeline.

All paths are anchored at the repository root, so the pipeline can be run from any directory.
"""
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]

DATA_DIR = PROJECT_ROOT / "data"
COLLECTION_DIR = DATA_DIR / "collection"
COLLECTION_SOLR_DIR = COLLECTION_DIR / "solr"
REPORTS_DIR = DATA_DIR / "reports"
EDA_REPORTS_DIR = REPORTS_DIR / "eda"

REPORT_DIR = PROJECT_ROOT / "report"
FIGURES_DIR = REPORT_DIR / "figures"
