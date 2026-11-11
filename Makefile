.PHONY: all pipeline eda exploratory flatten evaluate report clean

all: pipeline eda

# Fetch Bulbapedia + TCGCSV, extract, link and merge prices -> data/_collections/*.json
pipeline:
	uv run python -m pipeline.main

# Statistics and figures used in the report -> data/_reports/eda/stats.json, report/figures/*.pdf
eda:
	uv run python -m pipeline.src.analysis.characterize

# Exploratory text report -> data/_reports/eda/exploratory/
exploratory:
	uv run python -m pipeline.src.analysis.exploratory_analysis

# Flatten the merged corpus for Solr -> data/_solr/
schema-flatten:
	uv run python -m solr.src.flatten data/_collections/databank.json --out-dir data/_solr --sep __ --schema

evaluate:
	@if [ ! -x evaluation/trec_eval/trec_eval ]; then \
		./evaluation/build_trec_eval.sh; \
	fi

	@if [ ! -x evaluation/trec_eval/trec_eval ]; then \
		echo "Failed to build evaluation/trec_eval/trec_eval" >&2; \
		exit 1; \
	fi

	./evaluation/evaluate.sh
# Flatten Schemaless
flatten:
	uv run python -m solr.src.flatten data/_collections/databank.json --out-dir data/_solr --sep __

# Needs a LaTeX installation with the acmart class (or upload report/ to Overleaf)
report:
	cd report && latexmk -pdf main.tex

clean:
	cd report && latexmk -C main.tex
