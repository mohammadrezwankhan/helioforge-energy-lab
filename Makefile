.PHONY: dev build test snapshot browser

dev:
	python scripts/dev.py

build:
	cd apps/web && npm run build

test:
	python -m pytest apps/api/tests
	cd apps/web && npm run build && npm test

snapshot:
	python scripts/generate-snapshot.py
	python scripts/generate-hybrid-assets.py
	cd apps/web && npm run build

browser:
	python scripts/browser-smoke.py --screenshots
	python scripts/browser-hybrid.py --screenshots
