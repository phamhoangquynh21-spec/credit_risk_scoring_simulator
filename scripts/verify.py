"""Deterministically verify credit_risk_scoring_simulator against MANIFEST.

Checks the committed raw dataset, models/metrics.json and src/config.py
against models/MANIFEST.md, the committed human record.

    python3 scripts/verify.py                # Tier A, stdlib only, ~0.2s
    python3 scripts/verify.py --retrain      # Tier A + Tier B, ~15s

Exit codes -- three distinct outcomes that call for different responses:

    0  every check passed
    1  RESULTS CHANGED   a value mismatch, or an input that is missing,
                         unreadable or malformed
    2  ENVIRONMENT CHANGED  library versions differ from MANIFEST.md
    3  COULD NOT VERIFY  --retrain was asked for but the check could not
                         be run at all

1 and 2 are deliberately separate. A metric that moved means the results
changed and needs investigating. A version that moved means the
environment changed and needs a deliberate re-record. Collapsing them
into one code would hide which of the two happened.

Tier A uses the standard library only: no pandas, no sklearn, no network,
no model. It runs under any Python 3.9+, including an interpreter with no
third-party packages installed at all.

Tier B (--retrain) re-runs the pipeline through the project's own venv
interpreter and checks the two AUC-ROC figures, which Tier A structurally
cannot reach -- AUC needs the 6,000 predicted probabilities, and those are
never persisted. Tier A alone proves metrics.json is self-consistent; only
Tier B proves the numbers are the ones this code actually produces.

Why --retrain is opt-in, when the pattern this is ported from re-runs by
default and offers --no-run to suppress it:

    That flag exists because re-running overwrites the results file,
    which would destroy a deliberate corruption before it could be
    detected. Tier B here never writes -- it calls train_baseline,
    train_advanced and evaluate_model directly and never touches
    run_training(), which is the only function that writes metrics.json
    and model.pkl. The hazard the flag guards against is absent, so the
    flag is not needed. Making the slow, environment-dependent tier
    opt-in instead keeps the default runnable on a bare checkout.

Every expected value lives in models/MANIFEST.md, not in this file. That
is the point: verifying metrics.json against constants transcribed from
metrics.json would be circular. If a check fails, the response is to find
out what changed -- never to edit MANIFEST.md until the check passes.
"""

import argparse
import ast
import csv
import hashlib
import json
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
MANIFEST_PATH = REPO_ROOT / "models" / "MANIFEST.md"
METRICS_PATH = REPO_ROOT / "models" / "metrics.json"
MODEL_PATH = REPO_ROOT / "models" / "model.pkl"
CONFIG_PATH = REPO_ROOT / "src" / "config.py"

EXIT_OK = 0
EXIT_RESULTS = 1
EXIT_ENVIRONMENT = 2
EXIT_CANNOT_VERIFY = 3

# The raw CSV's target column, before src.preprocessing.clean_data renames
# it to config.TARGET. Dropped, with "ID", when re-deriving the feature
# list from the raw header.
RAW_TARGET_COLUMN = "default.payment.next.month"
RAW_ID_COLUMN = "id"

# Tried in order, relative to the repo root. The Windows layout comes
# first and covers two cases at once: a native Windows run, and a WSL run
# against a repo on /mnt/c, where binfmt interop executes the .exe
# directly. The POSIX layout covers a venv created on Linux or macOS.
INTERPRETER_CANDIDATES = (
    Path(".venv") / "Scripts" / "python.exe",
    Path(".venv") / "bin" / "python",
)

RETRAIN_TIMEOUT_SECONDS = 900

# Markers delimiting the child's JSON, so unrelated output on stdout --
# a library deprecation notice, a progress line -- cannot corrupt it.
RETRAIN_BEGIN = "---VERIFY-RETRAIN-JSON-BEGIN---"
RETRAIN_END = "---VERIFY-RETRAIN-JSON-END---"

# Byte markers identifying the estimator class inside models/model.pkl.
# A pickle stores the qualified class name as plain bytes, so the model
# type can be read without joblib, sklearn or xgboost -- and without
# unpickling, which would execute code from the file.
MODEL_CLASS_MARKERS = {
    "xgboost": b"XGBClassifier",
    "randomforest": b"RandomForestClassifier",
}


def parse_args(argv=None):
    """Return the parsed command-line arguments as a Namespace."""
    parser = argparse.ArgumentParser(
        description=(
            "Verify the repository against models/MANIFEST.md. "
            "Exits 0 on a full match, 1 if results changed, 2 if the "
            "environment changed, 3 if verification could not run."
        )
    )
    parser.add_argument(
        "--retrain",
        action="store_true",
        help=(
            "also re-run the pipeline through the project's venv and "
            "check the library versions and both AUC-ROC figures "
            "(~15s; writes nothing to disk)"
        ),
    )
    return parser.parse_args(argv)


def read_text(path, label):
    """Return (text, None), or (None, message) if ``path`` is unreadable.

    A missing file, a directory in its place, a permissions error and
    non-UTF-8 bytes all become messages rather than exceptions.

    The guard tests exists(), not is_file(). A directory standing where
    the file belongs must reach the OSError handler below and be
    reported as unreadable -- is_file() would call it "not found",
    which is a different and misleading diagnosis.
    """
    if not path.exists():
        return None, f"{label} not found: {path}"
    try:
        return path.read_text(encoding="utf-8"), None
    except UnicodeDecodeError as error:
        return None, f"{label} is not valid UTF-8: {error}"
    except OSError as error:
        return None, f"{label} could not be read: {error}"


def extract_record(text):
    """Return (record_text, None) for MANIFEST.md's ```json block.

    Returns (None, message) if the block is absent or never closed.
    """
    lines = text.splitlines()
    start = None
    for index, line in enumerate(lines):
        if line.strip() == "```json":
            start = index + 1
            break
    if start is None:
        return None, (
            "MANIFEST.md contains no ```json record block -- the "
            "verifier has nothing to check against"
        )

    body = []
    for line in lines[start:]:
        if line.strip() == "```":
            return "\n".join(body), None
        body.append(line)
    return None, "MANIFEST.md's ```json record block is never closed"


def load_manifest():
    """Return (record_dict, None), or (None, message) if unusable."""
    text, failure = read_text(MANIFEST_PATH, "MANIFEST.md")
    if failure:
        return None, failure

    record_text, failure = extract_record(text)
    if failure:
        return None, failure

    try:
        record = json.loads(record_text)
    except json.JSONDecodeError as error:
        return None, f"MANIFEST.md's record block is not valid JSON: {error}"

    for section in ("raw_data", "derived", "metrics", "environment"):
        if section not in record:
            return None, f"MANIFEST.md's record has no {section!r} section"
    return record, None


def load_metrics():
    """Return (metrics_dict, None), or (None, message) if unusable."""
    text, failure = read_text(METRICS_PATH, "metrics.json")
    if failure:
        return None, failure
    try:
        return json.loads(text), None
    except json.JSONDecodeError as error:
        return None, f"metrics.json is not valid JSON: {error}"


def sha256_of(path):
    """Return the lowercase hex SHA-256 digest of the file at ``path``.

    Raises OSError if the file cannot be opened or read; the caller turns
    that into a message. Kept a pure digest so it has one job.
    """
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for block in iter(lambda: handle.read(65536), b""):
            digest.update(block)
    return digest.hexdigest()


def scan_raw_csv(path, target_column):
    """Return (summary, None) for the raw CSV, or (None, message).

    Streams the file rather than loading it, and returns the header, the
    row count and the count of positive targets. Positives are recounted
    from the data so the stored default rate is never simply trusted.
    """
    try:
        with open(path, newline="", encoding="utf-8") as handle:
            reader = csv.reader(handle)
            try:
                header = next(reader)
            except StopIteration:
                return None, f"raw CSV is empty: {path}"

            if target_column not in header:
                return None, (
                    f"raw CSV has no {target_column!r} column; header "
                    f"is {header}"
                )
            target_index = header.index(target_column)

            rows = 0
            positives = 0
            for row in reader:
                rows += 1
                if len(row) <= target_index:
                    return None, (
                        f"raw CSV row {rows} has {len(row)} fields, "
                        f"too few to read {target_column!r}"
                    )
                value = row[target_index].strip()
                if value == "1":
                    positives += 1
                elif value != "0":
                    return None, (
                        f"raw CSV row {rows} has target {value!r}, "
                        f"expected '0' or '1'"
                    )
    except UnicodeDecodeError as error:
        return None, f"raw CSV is not valid UTF-8: {error}"
    except csv.Error as error:
        return None, f"raw CSV could not be parsed: {error}"
    except OSError as error:
        return None, f"raw CSV could not be read: {error}"

    return {"header": header, "rows": rows, "positives": positives}, None


def engineered_from_config():
    """Return (engineered_list, None) read from src/config.py.

    Parses the module with ``ast`` and literal-evaluates the ENGINEERED
    assignment. Deliberately does not import config: importing would
    execute the module, and the verifier must not depend on the project
    being importable to check a list of strings.
    """
    text, failure = read_text(CONFIG_PATH, "src/config.py")
    if failure:
        return None, failure

    try:
        tree = ast.parse(text)
    except SyntaxError as error:
        return None, f"src/config.py could not be parsed: {error}"

    for node in tree.body:
        if not isinstance(node, ast.Assign):
            continue
        for target in node.targets:
            if isinstance(target, ast.Name) and target.id == "ENGINEERED":
                try:
                    return ast.literal_eval(node.value), None
                except ValueError as error:
                    return None, (
                        f"src/config.py ENGINEERED is not a literal: "
                        f"{error}"
                    )
    return None, "src/config.py has no ENGINEERED assignment"


def derive_features(header, engineered):
    """Return the model feature list implied by the raw header.

    Mirrors src.preprocessing.clean_data (lowercase every column, drop
    the id column and the target) followed by engineer_features (append
    config.ENGINEERED). Re-deriving this is what catches src/config.py
    drifting away from models/metrics.json.
    """
    dropped = {RAW_ID_COLUMN, RAW_TARGET_COLUMN}
    kept = [name.lower() for name in header]
    return [name for name in kept if name not in dropped] + list(engineered)


def metrics_from_confusion(matrix):
    """Return (derived_metrics, None) for a [[TN, FP], [FN, TP]] matrix.

    Reproduces the formulae in src.train_model.evaluate_model, including
    sklearn's zero_division=0 behaviour, so a hand-edited precision,
    recall, f1 or accuracy can be caught without re-running anything.
    """
    if (
        not isinstance(matrix, list)
        or len(matrix) != 2
        or any(not isinstance(row, list) or len(row) != 2 for row in matrix)
    ):
        return None, f"confusion_matrix is not a 2x2 list: {matrix!r}"

    values = [value for row in matrix for value in row]
    if any(not isinstance(value, int) or value < 0 for value in values):
        return None, (
            f"confusion_matrix holds a non-negative-integer entry: "
            f"{matrix!r}"
        )

    (true_negative, false_positive), (false_negative, true_positive) = matrix
    total = true_negative + false_positive + false_negative + true_positive
    if total == 0:
        return None, "confusion_matrix is all zeros"

    predicted_positive = true_positive + false_positive
    actual_positive = true_positive + false_negative
    f1_denominator = 2 * true_positive + false_positive + false_negative

    return {
        "precision": (
            true_positive / predicted_positive if predicted_positive else 0.0
        ),
        "recall": (
            true_positive / actual_positive if actual_positive else 0.0
        ),
        "f1": (
            2 * true_positive / f1_denominator if f1_denominator else 0.0
        ),
        "accuracy": (true_negative + true_positive) / total,
        "total": total,
        "actual_positive": actual_positive,
    }, None


def iter_value_mismatches(expected, actual, path):
    """Yield a message for each value in ``actual`` differing from expected.

    Walks both structures in the expected value's key order, so the first
    message yielded is deterministic. Reports type mismatches, missing
    keys, unexpected extra keys, wrong list lengths and unequal scalars,
    each labelled with a dotted path. Yields nothing on a full match.
    """
    if isinstance(expected, dict):
        if not isinstance(actual, dict):
            yield f"{path}: expected an object, got {type(actual).__name__}"
            return
        for key, expected_value in expected.items():
            if key not in actual:
                yield f"{path}.{key}: missing"
                continue
            yield from iter_value_mismatches(
                expected_value, actual[key], f"{path}.{key}"
            )
        for key in actual:
            if key not in expected:
                yield f"{path}.{key}: unexpected key, not in MANIFEST.md"
        return

    if isinstance(expected, list):
        if not isinstance(actual, list):
            yield f"{path}: expected a list, got {type(actual).__name__}"
            return
        if len(expected) != len(actual):
            yield (
                f"{path}: expected {len(expected)} items, got {len(actual)}"
            )
            return
        for index, expected_item in enumerate(expected):
            yield from iter_value_mismatches(
                expected_item, actual[index], f"{path}[{index}]"
            )
        return

    if expected != actual or type(expected) is not type(actual):
        yield f"{path}: expected {expected!r}, got {actual!r}"


def expected_metrics_file(manifest):
    """Return metrics.json as MANIFEST.md says it should look."""
    derived = manifest["derived"]
    metrics = manifest["metrics"]
    return {
        "advanced": metrics["advanced"],
        "baseline": metrics["baseline"],
        "model_type": metrics["model_type"],
        "n_train": derived["n_train"],
        "n_test": derived["n_test"],
        "default_rate": derived["default_rate"],
        "features": derived["features"],
    }


def check_model_pickle(expected_type):
    """Return (note, failure) after byte-scanning models/model.pkl.

    ``note`` is a line for stdout; ``failure`` is a message or None. A
    missing pickle is a note, not a failure: models/*.pkl is gitignored,
    so it is a regenerated artefact rather than a committed record.
    """
    if not MODEL_PATH.exists():
        return (
            "note: models/model.pkl absent (gitignored) -- "
            "model_type not cross-checked against the pickle"
        ), None

    try:
        blob = MODEL_PATH.read_bytes()
    except OSError as error:
        return None, f"model.pkl could not be read: {error}"

    found = sorted(
        name
        for name, marker in MODEL_CLASS_MARKERS.items()
        if marker in blob
    )
    if expected_type not in found:
        return None, (
            f"model.pkl does not contain the estimator class for "
            f"model_type {expected_type!r} "
            f"(found: {found or 'no known estimator class'})"
        )
    marker = MODEL_CLASS_MARKERS[expected_type].decode()
    return f"note: model.pkl contains {marker}", None


def first_tier_a_failure(manifest, metrics):
    """Return (first_failure_message, notes) for the stdlib checks.

    Checks run most-explanatory-failure-first: a changed CSV also changes
    every number downstream, so naming the file is the more useful
    diagnosis than naming a metric that moved because of it.
    """
    notes = []
    raw = manifest["raw_data"]
    derived = manifest["derived"]
    raw_path = REPO_ROOT / raw["path"]

    # 1. Raw dataset hash. exists() rather than is_file(), so a
    # directory in the CSV's place reaches sha256_of and is reported as
    # unreadable rather than as missing.
    if not raw_path.exists():
        return f"raw CSV not found: {raw_path}", notes
    try:
        actual_hash = sha256_of(raw_path)
    except OSError as error:
        return f"raw CSV could not be read: {error}", notes
    if actual_hash != raw["sha256"]:
        return (
            f"SHA-256 mismatch for {raw['path']}: expected "
            f"{raw['sha256']}, got {actual_hash} -- re-verify the "
            f"ingest against UCI; do not edit MANIFEST.md"
        ), notes

    # 2-3. Raw shape, and the target recounted from the data.
    summary, failure = scan_raw_csv(raw_path, RAW_TARGET_COLUMN)
    if failure:
        return failure, notes
    if summary["header"] != raw["columns"]:
        return (
            f"raw CSV header does not match MANIFEST.md: expected "
            f"{raw['columns']}, got {summary['header']}"
        ), notes
    if summary["rows"] != raw["rows"]:
        return (
            f"raw CSV row count: expected {raw['rows']}, got "
            f"{summary['rows']}"
        ), notes
    if summary["positives"] != derived["target_positives"]:
        return (
            f"raw CSV target positives: expected "
            f"{derived['target_positives']}, got {summary['positives']}"
        ), notes

    counted_rate = summary["positives"] / summary["rows"]
    if counted_rate != derived["default_rate"]:
        return (
            f"default_rate recounted from the CSV is {counted_rate!r}, "
            f"but MANIFEST.md records {derived['default_rate']!r}"
        ), notes

    # 4. Split arithmetic.
    split_total = derived["n_train"] + derived["n_test"]
    if split_total != raw["rows"]:
        return (
            f"n_train + n_test is {split_total}, but the raw CSV has "
            f"{raw['rows']} rows"
        ), notes

    # 5. Feature list re-derived from the header and src/config.py.
    engineered, failure = engineered_from_config()
    if failure:
        return failure, notes
    rederived = derive_features(summary["header"], engineered)
    if rederived != derived["features"]:
        return (
            f"features re-derived from the raw header and "
            f"config.ENGINEERED do not match MANIFEST.md: expected "
            f"{derived['features']}, got {rederived}"
        ), notes

    # 6. Each metric block is internally consistent with its own matrix.
    for name in ("baseline", "advanced"):
        block = manifest["metrics"][name]
        computed, failure = metrics_from_confusion(block["confusion_matrix"])
        if failure:
            return f"manifest metrics.{name}: {failure}", notes

        if computed["total"] != derived["n_test"]:
            return (
                f"metrics.{name}.confusion_matrix sums to "
                f"{computed['total']}, but n_test is {derived['n_test']}"
            ), notes
        if computed["actual_positive"] != derived["test_positives"]:
            return (
                f"metrics.{name}.confusion_matrix has "
                f"{computed['actual_positive']} actual positives, but "
                f"MANIFEST.md records {derived['test_positives']}"
            ), notes

        for key in ("precision", "recall", "f1", "accuracy"):
            if block[key] != computed[key]:
                return (
                    f"metrics.{name}.{key} is inconsistent with its own "
                    f"confusion_matrix: recorded {block[key]!r}, "
                    f"matrix implies {computed[key]!r}"
                ), notes

    # 7. model_type cross-checked against the pickle's bytes.
    note, failure = check_model_pickle(manifest["metrics"]["model_type"])
    if failure:
        return failure, notes
    notes.append(note)

    # 8. metrics.json matches the record.
    for message in iter_value_mismatches(
        expected_metrics_file(manifest), metrics, "metrics.json"
    ):
        return message, notes

    return None, notes


RETRAIN_SCRIPT = r'''
import json
import sys

sys.path.insert(0, ".")

from src import config
from src.preprocessing import build_processed_dataset, split_data
from src.train_model import evaluate_model, train_advanced, train_baseline


def version_of(distribution, module_name=None):
    try:
        module = __import__(module_name or distribution)
    except Exception:
        return "absent"
    return getattr(module, "__version__", "unknown")


environment = {
    "python": "%d.%d.%d" % sys.version_info[:3],
    "pandas": version_of("pandas"),
    "numpy": version_of("numpy"),
    "scikit-learn": version_of("scikit-learn", "sklearn"),
    "xgboost": version_of("xgboost"),
    "joblib": version_of("joblib"),
    "scipy": version_of("scipy"),
}

# Deliberately not run_training(): that writes metrics.json and
# model.pkl. Calling the components keeps --retrain non-mutating.
frame = build_processed_dataset()
X_train, X_test, y_train, y_test = split_data(frame)
baseline = train_baseline(X_train, y_train)
advanced = train_advanced(X_train, y_train)

payload = {
    "environment": environment,
    "n_train": int(len(X_train)),
    "n_test": int(len(X_test)),
    "default_rate": float(frame[config.TARGET].mean()),
    "features": list(X_train.columns),
    "metrics": {
        "model_type": getattr(advanced, "model_type_", "unknown"),
        "baseline": evaluate_model(baseline, X_test, y_test),
        "advanced": evaluate_model(advanced, X_test, y_test),
    },
}

print("@BEGIN@")
print(json.dumps(payload))
print("@END@")
'''


def find_interpreter():
    """Return the project venv's interpreter, or None if there is none."""
    for relative in INTERPRETER_CANDIDATES:
        candidate = REPO_ROOT / relative
        if candidate.is_file():
            return candidate
    return None


def run_retrain():
    """Return (payload, None), or (None, message) if it could not run.

    Every failure here means verification could not happen, not that
    verification failed -- the caller maps them to exit 3.
    """
    interpreter = find_interpreter()
    if interpreter is None:
        tried = ", ".join(str(path) for path in INTERPRETER_CANDIDATES)
        return None, (
            f"--retrain needs the project venv, which needs pandas, "
            f"scikit-learn and xgboost; no interpreter at any of: {tried}"
        )

    script = (
        RETRAIN_SCRIPT
        .replace("@BEGIN@", RETRAIN_BEGIN)
        .replace("@END@", RETRAIN_END)
    )

    try:
        completed = subprocess.run(
            [str(interpreter), "-"],
            input=script,
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
            timeout=RETRAIN_TIMEOUT_SECONDS,
        )
    except subprocess.TimeoutExpired:
        return None, (
            f"the retrain did not finish within "
            f"{RETRAIN_TIMEOUT_SECONDS}s"
        )
    except OSError as error:
        return None, f"the retrain interpreter could not be run: {error}"

    if completed.returncode != 0:
        return None, (
            f"the retrain exited {completed.returncode}; stderr: "
            f"{completed.stderr.strip() or '(empty)'}"
        )

    output = completed.stdout
    if RETRAIN_BEGIN not in output or RETRAIN_END not in output:
        return None, (
            f"the retrain produced no delimited JSON; stdout: "
            f"{output.strip()[:400] or '(empty)'}"
        )

    body = output.split(RETRAIN_BEGIN, 1)[1].split(RETRAIN_END, 1)[0]
    try:
        return json.loads(body), None
    except json.JSONDecodeError as error:
        return None, f"the retrain produced invalid JSON: {error}"


def iter_version_mismatches(manifest, payload):
    """Yield one message per package whose version differs from MANIFEST."""
    expected = manifest["environment"]
    actual = payload.get("environment", {})
    for package, want in expected.items():
        got = actual.get(package, "not reported")
        if got != want:
            yield f"{package} {want} -> {got}"


def iter_retrain_mismatches(manifest, payload):
    """Yield a message for each recomputed value differing from MANIFEST."""
    derived = manifest["derived"]
    expected = {
        "n_train": derived["n_train"],
        "n_test": derived["n_test"],
        "default_rate": derived["default_rate"],
        "features": derived["features"],
        "metrics": manifest["metrics"],
    }
    actual = {
        key: value for key, value in payload.items() if key != "environment"
    }
    yield from iter_value_mismatches(expected, actual, "retrain")


def main(argv=None):
    """Return the process exit code, printing the outcome."""
    args = parse_args(argv)

    manifest, failure = load_manifest()
    if failure:
        print(f"VERIFY FAILED: {failure}", file=sys.stderr)
        return EXIT_RESULTS

    metrics, failure = load_metrics()
    if failure:
        print(f"VERIFY FAILED: {failure}", file=sys.stderr)
        return EXIT_RESULTS

    failure, notes = first_tier_a_failure(manifest, metrics)
    for note in notes:
        print(note)
    if failure:
        print(f"VERIFY FAILED: {failure}", file=sys.stderr)
        return EXIT_RESULTS

    if not args.retrain:
        print(
            "VERIFY OK (Tier A): the raw CSV hash, its shape, the "
            "recounted default rate, the re-derived feature list, both "
            "metric blocks' internal consistency and every value in "
            "metrics.json match models/MANIFEST.md"
        )
        print(
            "note: AUC-ROC was not checked -- it needs the predicted "
            "probabilities. Run with --retrain to check it."
        )
        return EXIT_OK

    payload, failure = run_retrain()
    if failure:
        print(f"VERIFY COULD NOT RUN: {failure}", file=sys.stderr)
        return EXIT_CANNOT_VERIFY

    version_mismatches = list(iter_version_mismatches(manifest, payload))
    value_mismatches = list(iter_retrain_mismatches(manifest, payload))

    # A version mismatch wins the exit code even when the metrics still
    # match. The record's environment block is stale either way, and
    # re-recording it should be a deliberate act rather than a silent
    # one. When both differ, the version change is reported as the
    # likelier explanation of the value change.
    if version_mismatches:
        print("VERIFY FAILED: the environment changed", file=sys.stderr)
        for message in version_mismatches:
            print(f"  {message}", file=sys.stderr)
        if value_mismatches:
            print(
                f"  {len(value_mismatches)} recomputed value(s) also "
                f"differ, starting with: {value_mismatches[0]}",
                file=sys.stderr,
            )
            print(
                "  the version change is the likely cause; re-check "
                "after restoring the recorded versions",
                file=sys.stderr,
            )
        else:
            print(
                "  every recomputed value still matches, so the results "
                "reproduce under the new versions",
                file=sys.stderr,
            )
        print(
            "  update MANIFEST.md's environment block deliberately, "
            "then re-run",
            file=sys.stderr,
        )
        return EXIT_ENVIRONMENT

    if value_mismatches:
        print(f"VERIFY FAILED: {value_mismatches[0]}", file=sys.stderr)
        return EXIT_RESULTS

    print(
        "VERIFY OK (Tier A + Tier B): every Tier A check passed, the "
        "7 recorded library versions match, and the retrained pipeline "
        "reproduced every value including both AUC-ROC figures"
    )
    return EXIT_OK


if __name__ == "__main__":
    sys.exit(main())
