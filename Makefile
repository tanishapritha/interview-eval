.PHONY: install test lint eval clean
install:
	python -m pip install -e '.[dev]'
test:
	pytest
lint:
	ruff check src tests
eval:
	interview-eval run --dataset datasets/golden/demo.jsonl --output reports/latest.json
clean:
	rm -f reports/latest.json reports/latest.md
