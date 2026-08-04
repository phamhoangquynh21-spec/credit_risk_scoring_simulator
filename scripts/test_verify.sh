#!/usr/bin/env bash
#
# Failure battery for scripts/verify.py.
#
# verify.py's contract is that every failure it can detect exits with the
# right code and a message naming what failed -- never a traceback. This
# script proves that contract still holds, by breaking the tree in five
# specific ways and asserting on the exit status, the message, and the
# absence of a traceback.
#
#     bash scripts/test_verify.sh; echo "exit=$?"
#
# Exit 0 means every case that ran behaved as specified. Exit 1 means at
# least one did not, and a FAIL line names it. Exit 2 means the battery
# could not run at all (missing prerequisite).
#
# The exit codes under test are verify.py's three distinct outcomes:
#     1 results changed   2 environment changed   3 could not verify
# Case 5 is the one that proves 2 is reachable and distinguishable from
# 1. If those two ever collapse into one code, case 5 is what catches it.
#
# --- Why cases 2 and 3 substitute a directory, and must not be
# --- "simplified" back to chmod 000
#
# The battery this is ported from makes a file unreadable with
# chmod 000. That does not work here. This repository lives on a
# drvfs/9p mount (a Windows drive seen from WSL), and the mode was
# observed to change silently:
#
#     $ chmod 000 probe_file
#     $ stat -c '%a' probe_file
#     555
#     $ cat probe_file          # succeeded -- file still readable
#
# The mode became 555 rather than 000 and the file stayed readable, so
# verify.py would have exited 0 and cases 2 and 3 would have printed
# PASS having tested nothing at all. That silent pass is precisely the
# failure mode this battery exists to catch.
#
# Moving the file aside and putting a *directory* of the same name in
# its place is filesystem-independent: open() then raises
# IsADirectoryError, an OSError, which is the exact handler these cases
# target. Do not replace this with chmod.
#
# --- Why there is no root guard
#
# The ported battery refuses to run as root, because chmod 000 does not
# restrict uid 0 and the cases would silently pass. Directory
# substitution is not defeated by uid 0 -- opening a directory as a file
# fails for root too -- so that guard is unnecessary here. Its absence
# is deliberate, not an oversight.
#
# The tree is restored by a trap on EXIT, so a failed assertion, an
# error, or an interrupt part-way through cannot leave a directory
# standing where metrics.json belongs.

set -uo pipefail

SCRIPT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
REPO_ROOT=$(dirname -- "$SCRIPT_DIR")

VERIFY="$SCRIPT_DIR/verify.py"
MANIFEST="$REPO_ROOT/models/MANIFEST.md"
METRICS="$REPO_ROOT/models/metrics.json"
RAW_CSV="$REPO_ROOT/data/raw/credit_card_default.csv"

STASH_SUFFIX=".battery-stashed"
STASH_DIR=""

PASSES=0
FAILURES=0
SKIPS=0


die() {
    printf 'BATTERY ABORTED: %s\n' "$1" >&2
    exit 2
}


command -v python3 >/dev/null 2>&1 || die "python3 is not on PATH"

for required in "$VERIFY" "$MANIFEST" "$METRICS" "$RAW_CSV"; do
    [ -f "$required" ] || die "required file missing: $required"
done


# Move a path aside and stand an empty directory in its place, so that
# opening it as a file raises IsADirectoryError. See the header.
substitute_directory() {
    mv -- "$1" "$1$STASH_SUFFIX" || die "cannot stash $1"
    mkdir -- "$1" || die "cannot create a directory at $1"
}


# Undo substitute_directory, or a plain move-aside. Safe to call when
# nothing was stashed, which is what makes the EXIT trap idempotent.
unstash() {
    if [ -d "$1" ] && [ ! -L "$1" ] && [ -e "$1$STASH_SUFFIX" ]; then
        rmdir -- "$1" 2>/dev/null
    fi
    if [ -e "$1$STASH_SUFFIX" ]; then
        mv -- "$1$STASH_SUFFIX" "$1" 2>/dev/null
    fi
}


cleanup() {
    local rc=$?

    unstash "$METRICS"
    unstash "$RAW_CSV"
    unstash "$MANIFEST"

    if [ -n "$STASH_DIR" ] && [ -d "$STASH_DIR" ]; then
        for name in metrics.json MANIFEST.md; do
            if [ -f "$STASH_DIR/$name" ]; then
                cp -- "$STASH_DIR/$name" "$REPO_ROOT/models/$name" \
                    2>/dev/null || printf \
                    'WARNING: could not restore models/%s -- a copy is at %s\n' \
                    "$name" "$STASH_DIR/$name" >&2
            fi
        done
        rm -rf -- "$STASH_DIR" 2>/dev/null
    fi

    exit "$rc"
}

trap cleanup EXIT

STASH_DIR=$(mktemp -d) || die "cannot create a temporary directory"
cp -- "$METRICS" "$STASH_DIR/metrics.json" || die "cannot back up $METRICS"
cp -- "$MANIFEST" "$STASH_DIR/MANIFEST.md" || die "cannot back up $MANIFEST"


restore_backups() {
    cp -- "$STASH_DIR/metrics.json" "$METRICS" || die "cannot restore $METRICS"
    cp -- "$STASH_DIR/MANIFEST.md" "$MANIFEST" || die "cannot restore $MANIFEST"
}


fail() {
    printf 'FAIL %s\n' "$1" >&2
    printf '     %s\n' "$2" >&2
    printf '     output: %s\n' "$3" >&2
    FAILURES=$((FAILURES + 1))
}


# A skipped case is not a passed case. It is printed loudly, to stderr,
# counted in its own tally, and called out again in the summary. A skip
# that reads as a pass is the same silent-pass failure the directory
# substitution above exists to prevent.
skip() {
    printf '\n' >&2
    printf 'SKIP %s\n' "$1" >&2
    printf '  >>> THIS CASE DID NOT RUN. It asserted nothing.\n' >&2
    printf '  >>> reason: %s\n' "$2" >&2
    printf '\n' >&2
    SKIPS=$((SKIPS + 1))
}


# check NAME EXPECTED_EXIT EXPECTED_TEXT COMMAND...
#
# Asserts three things, because two of them can pass while the defect is
# still present: the exit status, a substring of the message, and that
# nothing printed a traceback. The traceback assertion is the regression
# guard -- a crash produces a non-zero status too, which an
# exit-status-only check would call a pass.
check() {
    local name=$1 want_rc=$2 want_text=$3
    shift 3

    local output rc
    output=$("$@" 2>&1)
    rc=$?

    if [ "$rc" -ne "$want_rc" ]; then
        fail "$name" "expected exit $want_rc, got $rc" "$output"
        return
    fi

    case $output in
        *"Traceback (most recent call last)"*)
            fail "$name" "exit $rc was correct, but the output is a traceback" "$output"
            return
            ;;
    esac

    case $output in
        *"$want_text"*) ;;
        *)
            fail "$name" "exit $rc was correct, but the message did not contain: $want_text" "$output"
            return
            ;;
    esac

    printf 'PASS %s (exit %s)\n' "$name" "$rc"
    PASSES=$((PASSES + 1))
}


interpreter_present() {
    [ -f "$REPO_ROOT/.venv/Scripts/python.exe" ] \
        || [ -f "$REPO_ROOT/.venv/bin/python" ]
}


corrupt_metric() {
    python3 - "$METRICS" <<'PY'
import json
import sys

path = sys.argv[1]
with open(path, encoding="utf-8") as handle:
    data = json.load(handle)
data["advanced"]["recall"] = 0.5
with open(path, "w", encoding="utf-8") as handle:
    json.dump(data, handle, indent=2)
PY
}


corrupt_manifest_version() {
    python3 - "$MANIFEST" <<'PY'
import re
import sys

path = sys.argv[1]
with open(path, encoding="utf-8") as handle:
    text = handle.read()
text, count = re.subn(
    r'("pandas":\s*")[^"]*(")', r'\g<1>0.0.0-battery\g<2>', text, count=1
)
if count != 1:
    sys.exit("could not find the pandas version in MANIFEST.md")
with open(path, "w", encoding="utf-8") as handle:
    handle.write(text)
PY
}


# --- Case 1: a corrupted metric -------------------------------------------
# Reaches the metrics.json-versus-MANIFEST comparison. This is the check
# that would catch a hand-edited number.
corrupt_metric || die "cannot corrupt $METRICS"
check "1 corrupted metric" 1 \
    "metrics.json.advanced.recall: expected 0.6269781461944235, got 0.5" \
    python3 "$VERIFY"
restore_backups

# --- Case 2: metrics.json present but unreadable --------------------------
# Reaches load_metrics() via read_text()'s OSError handler. Directory
# substitution, not chmod -- see the header.
substitute_directory "$METRICS"
check "2 metrics.json unreadable" 1 \
    "metrics.json could not be read" \
    python3 "$VERIFY"
unstash "$METRICS"

# --- Case 3: the raw CSV present but unreadable ---------------------------
# Reaches sha256_of(). metrics.json and MANIFEST.md must both be intact
# here, or an earlier check fails first and the case asserts against the
# wrong branch.
substitute_directory "$RAW_CSV"
check "3 raw CSV unreadable" 1 \
    "raw CSV could not be read" \
    python3 "$VERIFY"
check "3b raw CSV is named as a directory" 1 \
    "Is a directory" \
    python3 "$VERIFY"
unstash "$RAW_CSV"

# --- Case 4: the record itself is missing ---------------------------------
# Without MANIFEST.md the verifier has nothing to check against, and must
# say so rather than quietly verifying less.
mv -- "$MANIFEST" "$MANIFEST$STASH_SUFFIX" || die "cannot stash $MANIFEST"
check "4 MANIFEST.md missing" 1 \
    "MANIFEST.md not found" \
    python3 "$VERIFY"
unstash "$MANIFEST"

# --- Case 5: a changed library version ------------------------------------
# The case that proves exit 2 exists and is distinguishable from exit 1.
# Needs --retrain: versions are only observable by running the pipeline.
if interpreter_present; then
    corrupt_manifest_version || die "cannot corrupt $MANIFEST"
    check "5 version mismatch exits 2, not 1" 2 \
        "pandas 0.0.0-battery ->" \
        python3 "$VERIFY" --retrain
    check "5b named as an environment change" 2 \
        "the environment changed" \
        python3 "$VERIFY" --retrain
    restore_backups
else
    skip "5 version mismatch exits 2, not 1" \
        "no venv interpreter; exit 2 was NOT proven reachable"
fi

# --- Case 6: a clean tree still passes, Tier A ----------------------------
# A battery of failures alone cannot show the verifier is not simply
# broken in a way that fails everything.
restore_backups
check "6 clean tree, Tier A" 0 \
    "VERIFY OK (Tier A)" \
    python3 "$VERIFY"

# --- Case 7: a clean tree still passes, Tier A + Tier B -------------------
# The only case that checks AUC-ROC, and the only one that proves the
# retrain path reproduces rather than merely running.
if interpreter_present; then
    check "7 clean tree, Tier A + Tier B" 0 \
        "VERIFY OK (Tier A + Tier B)" \
        python3 "$VERIFY" --retrain
else
    skip "7 clean tree, Tier A + Tier B" \
        "no venv interpreter; AUC-ROC was NOT checked by this run"
fi


printf '\n%s passed, %s failed, %s skipped\n' "$PASSES" "$FAILURES" "$SKIPS"

if [ "$FAILURES" -ne 0 ]; then
    printf 'BATTERY FAILED\n' >&2
    exit 1
fi

if [ "$SKIPS" -ne 0 ]; then
    printf '\n' >&2
    printf '========================================================\n' >&2
    printf 'WARNING: %s case(s) did not run.\n' "$SKIPS" >&2
    printf 'This run does NOT prove the whole contract holds.\n' >&2
    printf 'Re-run where the project venv is available.\n' >&2
    printf '========================================================\n' >&2
    printf 'BATTERY OK (WITH %s SKIPPED -- NOT A FULL PASS)\n' "$SKIPS"
    exit 0
fi

printf 'BATTERY OK\n'
exit 0
