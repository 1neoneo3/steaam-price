# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

- **Install**: `uv pip install -e .` or `uv pip install -e ".[dev]"` for development
- **Format**: `make format` or `ruff format .`
- **Lint**: `make lint` or `ruff check .`
- **Fix Linting**: `make fix` or `ruff check --fix .`
- **Run**: `make run` or `python main.py`
- **Test**: `python main_test.py`
- **Create Mock Data**: `python create_mock_data.py`
- **Run Multi-Region Price Fetching**: `python fetch_multi_region.py`

## Code Style Guidelines

- **Formatting**: Single quotes, 4-space indentation (configured in ruff)
- **Line Length**: 100 characters maximum
- **Imports**: Follow isort ordering (standard lib → third-party → first-party → local)
- **Types**: Use type annotations for function parameters and return values
- **Naming**: Use snake_case for functions/variables, PascalCase for classes
- **Error Handling**: Always use try/except blocks with specific exceptions
- **Logging**: Use the logger module instead of print statements
- **Documentation**: Include docstrings for all modules, classes, and functions (Google style)
- **Path Handling**: Always use pathlib.Path for file paths, not string concatenation
- **Complexity**: Keep functions under 50 statements, max 8 arguments, complexity under 12