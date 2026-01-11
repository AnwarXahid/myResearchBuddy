.PHONY: dev test demo doctor

dev:
	bash scripts/dev.sh

doctor:
	bash scripts/doctor.sh

test:
	cd backend && python -m pytest

demo:
	python scripts/load_demo.py
