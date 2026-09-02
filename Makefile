.PHONY: install run dashboard test api clean
install:
	pip install -e .
run:
	PYTHONPATH=src python -m audit_engine.cli run
dashboard:
	PYTHONPATH=src python -m audit_engine.cli dashboard
test:
	PYTHONPATH=src python -m unittest discover -s tests -v
api:
	uvicorn audit_engine.api:app --reload
clean:
	find data/synthetic -type f -delete 2>/dev/null || true
	find output -type f -delete 2>/dev/null || true

