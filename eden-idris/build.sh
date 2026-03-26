#!/bin/bash
# Build the EDEN Idris2 executable (RefC backend -> GCC)
#
# Usage: ./build.sh
#
# Requires:
#   - Idris2 fork at /home/natanh/Idris2/
#   - GCC from /ucrt64/bin (MSYS2/MinGW)

set -e

IDRIS2="/home/natanh/Idris2/build/exec/idris2.exe"
IDRIS2_SUPPORT="/home/natanh/Idris2/support"

export PATH="/ucrt64/bin:/usr/bin:$PATH"
export CC=gcc

# Clean TTC cache to force full recompilation
rm -rf build/ttc

echo "=== Phase 1: Idris2 type-check + RefC codegen ==="

# Record eden.c timestamp before codegen so we can detect stale output
OLD_EDEN_C_TS=""
if [ -f build/exec/eden.c ]; then
    OLD_EDEN_C_TS=$(stat -c "%Y" build/exec/eden.c 2>/dev/null || echo "")
fi

if ! $IDRIS2 --no-banner --cg refc --build eden.ipkg 2>&1; then
    echo ""
    echo "WARNING: Idris2 exited with non-zero status."
    echo "Checking if codegen output was produced anyway..."
fi

if [ ! -f build/exec/eden.c ]; then
    echo "ERROR: Idris2 codegen failed (no build/exec/eden.c)"
    exit 1
fi

# Check if eden.c was actually regenerated
NEW_EDEN_C_TS=$(stat -c "%Y" build/exec/eden.c 2>/dev/null || echo "")
if [ -n "$OLD_EDEN_C_TS" ] && [ "$OLD_EDEN_C_TS" = "$NEW_EDEN_C_TS" ]; then
    echo "ERROR: eden.c was NOT regenerated (timestamp unchanged). Codegen likely failed."
    exit 1
fi

echo "=== Phase 2: GCC compile + link ==="
gcc -o build/exec/eden.exe \
    build/exec/eden.c \
    support/eden_term.c \
    -include support/eden_term.h \
    -I "$IDRIS2_SUPPORT/c" \
    -I "$IDRIS2_SUPPORT/refc" \
    -L "$IDRIS2_SUPPORT/refc" \
    -L "$IDRIS2_SUPPORT/c" \
    -lidris2_refc -lidris2_support \
    -lgmp -lm -lpthread -lws2_32 \
    -Wno-error=implicit-function-declaration

echo "=== Done: build/exec/eden.exe ==="
ls -la build/exec/eden.exe
