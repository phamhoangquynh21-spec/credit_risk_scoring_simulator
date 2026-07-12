"""Governed ML lifecycle helpers (Stage 3).

Registry, feature contract, calibration, cost-sensitive threshold and reason
codes. Heavy/optional dependencies (mlflow, sklearn.calibration) are imported
lazily inside functions so ``import src.ml`` stays cheap and never requires
mlflow — the serving/deploy paths are unaffected.
"""
