PYTHON ?= python
MODEL_DIR ?= models
PROFILE ?= full

.PHONY: install test lint format train serve

install:
	$(PYTHON) -m pip install -r requirements-dev.txt

test:
	$(PYTHON) -m pytest

lint:
	$(PYTHON) -m flake8 .
	$(PYTHON) -m isort --check-only .
	$(PYTHON) -m black --check .

format:
	$(PYTHON) -m isort .
	$(PYTHON) -m black .

train:
	cd .. && $(PYTHON) -m ml_models.cli.train --model-dir ml_models/$(MODEL_DIR) --profile $(PROFILE)

serve:
	cd .. && MODEL_PATH=ml_models/$(MODEL_DIR) $(PYTHON) -m ml_models.serving
