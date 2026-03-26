#!/bin/bash
# Build the EDEN Idris2 executable (RefC backend -> GCC)
#
# Usage: ./build.sh
#
# Requires:
#   - Idris2 with RefC backend (idris2 must be on PATH, or set IDRIS2)
#   - GCC (cc/gcc must be available)
#
# Platform auto-detection: MSYS2/MinGW, macOS, Linux

set -e

# ── Platform detection ──────────────────────────────────────────────

OS="$(uname -s)"
case "$OS" in
    MINGW*|MSYS*|CYGWIN*)  PLATFORM="msys" ;;
    Darwin*)               PLATFORM="macos" ;;
    Linux*)                PLATFORM="linux" ;;
    *)                     PLATFORM="linux" ;;  # best guess
esac

# ── Idris2 location ────────────────────────────────────────────────

if [ -z "$IDRIS2" ]; then
    # Try common locations
    if [ -x "/home/natanh/Idris2/build/exec/idris2.exe" ]; then
        IDRIS2="/home/natanh/Idris2/build/exec/idris2.exe"
        IDRIS2_SUPPORT="/home/natanh/Idris2/support"
    elif command -v idris2 >/dev/null 2>&1; then
        IDRIS2="idris2"
        # Derive support dir from idris2 --libdir
        IDRIS2_SUPPORT="$(idris2 --libdir 2>/dev/null || echo "")"
        # Fallback: try prefix/support
        if [ -z "$IDRIS2_SUPPORT" ] || [ ! -d "$IDRIS2_SUPPORT" ]; then
            IDRIS2_PREFIX="$(dirname "$(dirname "$(command -v idris2)")")"
            IDRIS2_SUPPORT="$IDRIS2_PREFIX/support"
        fi
    else
        echo "ERROR: Cannot find idris2. Set IDRIS2=/path/to/idris2"
        exit 1
    fi
fi

# If IDRIS2_SUPPORT is not set, try to find it relative to IDRIS2
if [ -z "$IDRIS2_SUPPORT" ]; then
    IDRIS2_DIR="$(dirname "$(dirname "$(dirname "$IDRIS2")")")"
    IDRIS2_SUPPORT="$IDRIS2_DIR/support"
fi

# ── Compiler and PATH ──────────────────────────────────────────────

case "$PLATFORM" in
    msys)
        export PATH="/ucrt64/bin:/usr/bin:$PATH"
        export CC=gcc
        EXE_EXT=".exe"
        PLAT_LDFLAGS="-lws2_32"
        STAT_FMT='stat -c "%Y"'
        ;;
    macos)
        export CC="${CC:-cc}"
        EXE_EXT=""
        PLAT_LDFLAGS=""
        STAT_FMT='stat -f "%m"'
        ;;
    linux)
        export CC="${CC:-gcc}"
        EXE_EXT=""
        PLAT_LDFLAGS=""
        STAT_FMT='stat -c "%Y"'
        ;;
esac

EDEN_BIN="build/exec/eden${EXE_EXT}"
EDEN_C="build/exec/eden.c"

echo "=== Platform: $PLATFORM | CC=$CC | Idris2=$IDRIS2 ==="

# ── Clean TTC cache ───────────────────────────────────────────────

rm -rf build/ttc

# ── Phase 1: Idris2 type-check + RefC codegen ─────────────────────

echo "=== Phase 1: Idris2 type-check + RefC codegen ==="

# Record eden.c timestamp before codegen so we can detect stale output
OLD_TS=""
if [ -f "$EDEN_C" ]; then
    OLD_TS=$(eval $STAT_FMT "$EDEN_C" 2>/dev/null || echo "")
fi

if ! $IDRIS2 --no-banner --cg refc --build eden.ipkg 2>&1; then
    echo ""
    echo "WARNING: Idris2 exited with non-zero status."
    echo "Checking if codegen output was produced anyway..."
fi

if [ ! -f "$EDEN_C" ]; then
    echo "ERROR: Idris2 codegen failed (no $EDEN_C)"
    exit 1
fi

# Check if eden.c was actually regenerated
NEW_TS=$(eval $STAT_FMT "$EDEN_C" 2>/dev/null || echo "")
if [ -n "$OLD_TS" ] && [ "$OLD_TS" = "$NEW_TS" ]; then
    echo "ERROR: eden.c was NOT regenerated (timestamp unchanged). Codegen likely failed."
    exit 1
fi

# ── Phase 2: GCC compile + link ──────────────────────────────────

echo "=== Phase 2: GCC compile + link ==="

# Build include/library flags
CFLAGS="-Wno-error=implicit-function-declaration"
IFLAGS="-include support/eden_term.h"
LDFLAGS="-lm -lpthread $PLAT_LDFLAGS"

# Add Idris2 support paths if they exist
if [ -d "$IDRIS2_SUPPORT/c" ]; then
    IFLAGS="$IFLAGS -I $IDRIS2_SUPPORT/c"
fi
if [ -d "$IDRIS2_SUPPORT/refc" ]; then
    IFLAGS="$IFLAGS -I $IDRIS2_SUPPORT/refc"
    LDFLAGS="-L $IDRIS2_SUPPORT/refc $LDFLAGS"
fi
if [ -d "$IDRIS2_SUPPORT/c" ]; then
    LDFLAGS="-L $IDRIS2_SUPPORT/c $LDFLAGS"
fi

# GMP: check if available, some systems use different paths
if pkg-config --exists gmp 2>/dev/null; then
    IFLAGS="$IFLAGS $(pkg-config --cflags gmp)"
    LDFLAGS="$LDFLAGS $(pkg-config --libs gmp)"
elif [ -d "/opt/homebrew/lib" ]; then
    # Homebrew on Apple Silicon
    IFLAGS="$IFLAGS -I/opt/homebrew/include"
    LDFLAGS="$LDFLAGS -L/opt/homebrew/lib -lgmp"
elif [ -d "/usr/local/lib" ]; then
    # Homebrew on Intel Mac or manual install
    LDFLAGS="$LDFLAGS -L/usr/local/lib -lgmp"
else
    LDFLAGS="$LDFLAGS -lgmp"
fi

$CC -o "$EDEN_BIN" \
    "$EDEN_C" \
    support/eden_term.c \
    $IFLAGS $CFLAGS \
    -lidris2_refc -lidris2_support \
    $LDFLAGS

echo "=== Done: $EDEN_BIN ==="
ls -la "$EDEN_BIN"
