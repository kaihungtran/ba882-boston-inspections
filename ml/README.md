# Machine Learning (Phase 2)

Owner: **Machine learning** (see [TEAM.md](../TEAM.md))

- `notebooks/`: EDA and experiments (clear large outputs before committing)
- `src/`: training, evaluation and batch-scoring code that Airflow runs

**Target:** does an establishment fail its next *routine* inspection?
**Split:** by time (train on older inspections, test on newer) to avoid leakage.
**Tracking:** MLflow. **Deployment:** Cloud Run or Vertex AI, scores refreshed on a schedule and written to `marts.risk_scores`.
