.PHONY: setup lint test eval run

setup:
	pip install -e ".[dev]"
	pre-commit install

lint:
	ruff check . && ruff format --check .

test:
	pytest tests/ -v

eval:
	python -m evals.run

run:
	streamlit run app.py
