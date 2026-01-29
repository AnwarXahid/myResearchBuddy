.PHONY: dev test

dev:
	bash scripts/dev.sh

test:
	cd backend && python -m pytest
