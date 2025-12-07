.PHONY: help install lint format typecheck test security-bandit security-pip-audit security-gitleaks security check pipeline clean run build release install-global uninstall-global version version-bump version-bump-minor version-bump-major
.DEFAULT_GOAL := help

# Configuration
S3_BUCKET := claude-code-scheduler-iac-claude-code-scheduler-logs
AWS_REGION := eu-central-1
AWS_PROFILE := sandbox-ilionx-amf
VERSION_FILE := claude_code_scheduler/_version.py

help: ## Show this help message
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-30s\033[0m %s\n", $$1, $$2}'

install: ## Install dependencies
	uv sync

lint: ## Run linting with ruff
	uv run ruff check .

format: ## Format code with ruff
	uv run ruff format .

typecheck: ## Run type checking with mypy
	uv run python -m mypy claude_code_scheduler

test: ## Run tests in parallel
	uv run python -m pytest tests/ -n auto

security-bandit: ## Run bandit security linter
	uv run python -m bandit -r claude_code_scheduler -c pyproject.toml

security-pip-audit: ## Run pip-audit for dependency vulnerabilities
	uv run python -m pip_audit

security-gitleaks: ## Run gitleaks secret scanner
	@command -v gitleaks >/dev/null 2>&1 || { echo "❌ gitleaks not found. Install: brew install gitleaks"; exit 1; }
	gitleaks detect --source . --config .gitleaks.toml --verbose

security: security-bandit security-pip-audit security-gitleaks ## Run all security checks

check: lint typecheck test security ## Run all checks (lint, typecheck, test, security)

pipeline: format lint typecheck test security build install-global ## Run full pipeline (format, lint, typecheck, test, security, build, install-global)

clean: ## Remove build artifacts and cache
	rm -rf build/ dist/ *.egg-info .pytest_cache .mypy_cache .ruff_cache
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name '*.pyc' -delete

run: ## Run claude-code-scheduler (usage: make run ARGS="...")
	uv run claude-code-scheduler $(ARGS)

build: ## Build package
	uv build --force-pep517

release: build ## Build and upload to S3 releases directory
	@VERSION=$$(sed -n 's/__version__ = "\([^"]*\)"/\1/p' $(VERSION_FILE)); \
	echo "Uploading version $$VERSION to S3..."; \
	aws s3 cp dist/claude_code_scheduler-$$VERSION-py3-none-any.whl \
		s3://$(S3_BUCKET)/releases/claude-code-scheduler.whl \
		--profile $(AWS_PROFILE) \
		--region $(AWS_REGION); \
	aws s3 cp dist/claude_code_scheduler-$$VERSION.tar.gz \
		s3://$(S3_BUCKET)/releases/claude-code-scheduler.tar.gz \
		--profile $(AWS_PROFILE) \
		--region $(AWS_REGION); \
	echo "✅ Uploaded version $$VERSION to s3://$(S3_BUCKET)/releases/"

install-global: ## Install globally with uv tool
	uv tool install . --reinstall

uninstall-global: ## Uninstall global installation
	uv tool uninstall claude-code-scheduler

# Version management (macOS compatible)
version: ## Show current version
	@sed -n 's/__version__ = "\([^"]*\)"/\1/p' $(VERSION_FILE)

version-bump: ## Bump patch version (0.1.0 -> 0.1.1)
	@CURRENT=$$(sed -n 's/__version__ = "\([^"]*\)"/\1/p' $(VERSION_FILE)); \
	MAJOR=$$(echo $$CURRENT | cut -d. -f1); \
	MINOR=$$(echo $$CURRENT | cut -d. -f2); \
	PATCH=$$(echo $$CURRENT | cut -d. -f3); \
	NEW_PATCH=$$(($$PATCH + 1)); \
	NEW_VERSION="$$MAJOR.$$MINOR.$$NEW_PATCH"; \
	sed -i '' "s/__version__ = \"$$CURRENT\"/__version__ = \"$$NEW_VERSION\"/" $(VERSION_FILE); \
	echo "Bumped version: $$CURRENT -> $$NEW_VERSION"

version-bump-minor: ## Bump minor version (0.1.0 -> 0.2.0)
	@CURRENT=$$(sed -n 's/__version__ = "\([^"]*\)"/\1/p' $(VERSION_FILE)); \
	MAJOR=$$(echo $$CURRENT | cut -d. -f1); \
	MINOR=$$(echo $$CURRENT | cut -d. -f2); \
	NEW_MINOR=$$(($$MINOR + 1)); \
	NEW_VERSION="$$MAJOR.$$NEW_MINOR.0"; \
	sed -i '' "s/__version__ = \"$$CURRENT\"/__version__ = \"$$NEW_VERSION\"/" $(VERSION_FILE); \
	echo "Bumped version: $$CURRENT -> $$NEW_VERSION"

version-bump-major: ## Bump major version (0.1.0 -> 1.0.0)
	@CURRENT=$$(sed -n 's/__version__ = "\([^"]*\)"/\1/p' $(VERSION_FILE)); \
	MAJOR=$$(echo $$CURRENT | cut -d. -f1); \
	NEW_MAJOR=$$(($$MAJOR + 1)); \
	NEW_VERSION="$$NEW_MAJOR.0.0"; \
	sed -i '' "s/__version__ = \"$$CURRENT\"/__version__ = \"$$NEW_VERSION\"/" $(VERSION_FILE); \
	echo "Bumped version: $$CURRENT -> $$NEW_VERSION"
