# The factory follows its own contract.
.PHONY: lint ci

lint: ## Syntax-check the hooks and scripts
	python3 -m py_compile hooks/*.py tests/*.py skills/review/scripts/*.py scripts/*.py
	bash -n skills/check/scripts/run.sh
	python3 -c "import json; json.load(open('hooks/hooks.json')); json.load(open('.claude-plugin/plugin.json'))"

ci: lint ## Lint plus the hook tests
	python3 -m unittest discover -s tests -v
