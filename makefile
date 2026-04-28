VENV		= .venv
SRC_DIR		= src
MAIN		= $(SRC_DIR)/main.py

install:
	uv sync

run:
	@echo "Running fly-in..."
	@uv run $(MAIN)

lint: 
	flake8 $(SRC_DIR)
	mypy --warn-return-any --warn-unused-ignores --ignore-missing-imports --disallow-untyped-defs --check-untyped-defs

lint-strict:
	flake8 $(SRC_DIR)
	mypy --strict

debug:
	@echo "Running in debug mode..."
	@uv run python -m pdb -m $(SRC_DIR)

clean:
	@echo "Cleaning project..."
	@uv clean
	@rm -rf $(VENV)
	@find . -type d -name "__pycache__" -exec rm -rf {} +
	@find . -type d -name ".mypy_cache" -exec rm -rf {} +
	@echo "Clean complete"
