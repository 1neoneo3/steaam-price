.PHONY: format lint install run clean

# Default target
all: format lint

# Format code with ruff
format:
	uv pip install -e ".[dev]"
	ruff format .

# Lint code with ruff
lint:
	uv pip install -e ".[dev]"
	ruff check .

# Fix linting issues with ruff
fix:
	uv pip install -e ".[dev]"
	ruff check --fix .

# Install project
install:
	uv pip install -e .

# Run the main script
run:
	python main.py

# Clean up cache files
clean:
	rm -rf .ruff_cache
	rm -rf __pycache__
	rm -rf steam_price/__pycache__
	rm -rf .pytest_cache