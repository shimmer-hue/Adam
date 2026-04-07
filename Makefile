.PHONY: build-idris test-idris build-python test-python clean

# Idris2 native binary
build-idris:
	cd eden-idris && ./build.sh

# Idris2 run (mock backend, no API key needed)
run-mock:
	cd eden-idris && ./build/exec/eden.exe --repl --backend mock

# Idris2 TUI with Claude backend
run-tui:
	cd eden-idris && ./build/exec/eden.exe --tui --backend claude

# Idris2 export
export:
	cd eden-idris && ./build/exec/eden.exe --export

# Python setup
build-python:
	python3 -m venv .venv && .venv/bin/pip install -e '.[dev]'

# Python tests
test-python:
	.venv/bin/pytest -q tests/

# Python TUI
run-python-tui:
	.venv/bin/python -m eden.main --tui

# Clean build artifacts
clean:
	rm -rf eden-idris/build/
