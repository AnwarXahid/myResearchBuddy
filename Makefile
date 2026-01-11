.PHONY: dev test demo

dev:
	bash scripts/dev.sh

test:
	cd backend && python -m pytest

demo:
	python scripts/load_demo.py
