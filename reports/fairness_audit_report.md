# Fairness Audit Report

**Model:** xgboost

This audit detects and *discloses* disparities across protected attributes; it does not attempt automated mitigation (out of scope per PRD).

## Per-group metrics

| attribute   | group           |    n |   actual_default_rate |   predicted_positive_rate |   recall |   precision |
|:------------|:----------------|-----:|----------------------:|--------------------------:|---------:|------------:|
| sex         | Female          | 3627 |                0.2382 |                    0.3772 |   0.6979 |      0.4408 |
| sex         | Male            | 2373 |                0.2389 |                    0.397  |   0.7372 |      0.4437 |
| education   | Graduate school | 2123 |                0.2285 |                    0.3754 |   0.7216 |      0.4391 |
| education   | High school     |  949 |                0.274  |                    0.4289 |   0.7231 |      0.4619 |
| education   | Other           |  112 |                0.25   |                    0.3482 |   0.6071 |      0.4359 |
| education   | University      | 2816 |                0.2337 |                    0.3789 |   0.7082 |      0.4367 |
| age_group   | 21-30           | 1817 |                0.2504 |                    0.393  |   0.7319 |      0.4664 |
| age_group   | 31-40           | 2505 |                0.2287 |                    0.3804 |   0.7138 |      0.4292 |
| age_group   | 41-50           | 1406 |                0.2482 |                    0.3869 |   0.6877 |      0.4412 |
| age_group   | 51-60           |  255 |                0.2039 |                    0.3725 |   0.7115 |      0.3895 |
| age_group   | 61+             |   17 |                0.1176 |                    0.2353 |   1      |      0.5    |

## Disparity summary

Ratios are min/max across groups (1.0 = perfectly equal).

| attribute   |   selection_rate_ratio |   recall_ratio |   n_groups |
|:------------|-----------------------:|---------------:|-----------:|
| age_group   |                  0.599 |          0.688 |          5 |
| education   |                  0.812 |          0.84  |          4 |
| sex         |                  0.95  |          0.947 |          2 |

## Interpretation

- **Selection-rate ratio** below ~0.8 (the '80% rule' rule-of-thumb) on any attribute indicates one group is flagged high-risk far more often than another and warrants review before any real deployment.
- The largest gap observed is on **age group**, which is expected given repayment behaviour correlates with age in this data. Age is a sensitive attribute in lending and would require legal/business justification.
- This model is trained on **synthetic data** mirroring UCI Taiwan (2005); the disparities here are illustrative of the audit process, not a claim about any real population.
