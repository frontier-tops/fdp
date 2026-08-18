# Lab 18 — Data Engineering Pipeline (Airflow · Spark · EzPresto · RAPIDS · MLflow)

**Duration** ~3 h · **GPU required** Yes (1 slice per participant) · **Backend** HPE PCAI
**Status** 🚧 In build — proven end to end for a single participant

## What this lab does
Takes **20 million raw event rows** sitting in object storage and turns them into a
**200,000-row training table**, trains a churn model on the GPU, versions it in MLflow, and
deploys it. One tool per concept, each appearing at the moment it becomes necessary.

The business question: *will this subscriber cancel in the next 30 days?*

## The shape of the problem
A model needs **one row per person, with the answer attached**. What exists instead is:

| | rows | where | has the label? |
|---|---|---|---|
| `watch_events` | 20,010,929 | object storage / shared volume | no |
| `subscribers` | 200,000 | Postgres | **yes** |

Neither table can train anything alone. The entire data-engineering task is to squash
20M event rows into 200k people rows and attach the answer from the other system.

## Pipeline
```
raw CSV (180 daily files, 849 MB)
   │  SPARK — read · clean · convert            [distributed compute, columnar formats]
   ▼
curated Parquet (232 MB, 3.66x smaller)
   │  cuDF — aggregate 20M -> 200k              [RAPIDS, the GPU doing real work]
   │  EzPresto — read subscribers from Postgres [federation]
   │  cuDF — join on the GPU
   ▼
training table (200k x 12)
   │  XGBoost on GPU -> AUC 0.868
   ▼
MLflow registry -> MLIS endpoint

AIRFLOW runs the Spark step, parameterised per participant.
```

## Objectives
- Explain what an orchestrator does, and why it never touches the data itself.
- See parallelism as a number: 180 files → 180 Spark tasks.
- Understand columnar storage — measured 3.66x smaller, and only reads the columns asked for.
- Understand federation: query a live database without copying it.
- Run the same aggregation on CPU and GPU with identical code.
- Read a model registry: parameters, metrics, versions, promotion.

## Concepts (the actual syllabus)
Fact vs dimension tables · orchestration & DAGs · idempotency · parameterised runs ·
lazy evaluation · partitions & parallelism · shuffle · columnar storage · partition pruning ·
aggregation & feature engineering · federation · labels & supervised learning ·
hardware acceleration · reproducibility & registry · promotion gates

## The DAG
`dags/churn_pipeline_dag.py` — **one** DAG, triggered once per participant:

> Airflow UI → `churn_pipeline` → **Trigger DAG w/ config** → `{"student_id": 7}`

Every path and object name derives from that number, so 30 people produce 30 independent
runs of the same DAG. Nobody edits a file.

It submits a `SparkApplication` and polls it to completion, tailing the driver log into the
Airflow task log. Three details in the spec are platform-specific and easy to get wrong:

- the API group is `sparkoperator.hpe.com/v1beta2`, **not** `sparkoperator.k8s.io`
- three PVCs must be mounted (user, shared, spark-history event log)
- the MapR `sparkConf` keys and the `imagepull` secret are required

### Platform requirement: `access_control`
PCAI refuses to load a DAG that does not declare who may use it — the scheduler reports
*"Unprotected DAG Detected"*. The DAG sets:

```python
access_control = {
    "Admin": {"can_read", "can_edit", "can_delete"},
    "All":   {"can_read", "can_edit"},
}
```

**Triggering a DAG requires `can_edit`**, not just `can_read`, so participants need both or
the Trigger button silently does nothing for them. They do not get `can_delete` — 30 people
should be able to run this DAG, not remove it.

### Before it will run
1. **Airflow pool** — Admin → Pools → `spark_pool`, **8** slots. Caps concurrent Spark jobs
   while `max_active_runs=40` still lets every participant see their run start.
2. **RBAC** — Airflow's service account needs `create/get/delete` on
   `sparkapplications.sparkoperator.hpe.com` in the target namespace, and `get` on `pods/log`.
3. **CONFIG block** — namespace, image, service account and `SPARK_USER` at the top of the
   DAG are cluster-specific. Take them from a `SparkApplication` that has actually completed:
   `kubectl get sparkapplication <name> -n <ns> -o yaml`.

## Measured, not assumed
| Figure | Value |
|---|---|
| Events | 20,010,929 |
| Subscribers | 200,000 |
| Raw CSV | 849 MB, 180 files |
| Curated Parquet | 232 MB — **3.66x** compression |
| Churn rate | 0.119 |
| Test AUC | 0.868 |
| Spark job wall-clock | ~1 min 50 s |

Every number here is a measurement. Re-measure before re-quoting if the dataset changes.
