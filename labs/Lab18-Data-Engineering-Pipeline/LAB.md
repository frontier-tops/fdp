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

## What participants actually do

| Step | Where | Time |
|---|---|---|
| 1. Look at the raw data — 180 files, why it isn't trainable | terminal / notebook | ~10 min |
| 2. Query `subscribers` through EzPresto — no copy made | EzPresto worksheet | ~10 min |
| 3. **Run a Spark job** — Create Spark Application wizard | PCAI UI | ~15 min |
| 4. **`notebooks/Lab18_Train_Churn_Model.ipynb`** — cuDF squash, GPU join, train, MLflow | GPU notebook | ~40 min |
| 5. Compare AUCs | MLflow | ~5 min |

Airflow is covered as a **concept only** — no DAG is run during the session. The DAG below
exists for a future iteration.

### Running the Spark job (step 3)
**Data Engineering → Spark Applications → Create Spark Application**

| Screen | Setting |
|---|---|
| Details | Name `curate-student-NN` |
| Configure | Type **Python** · Source **Shared Folder** · Class Name *empty* |
| File Name | **Browse** to `data-engineering-lab/spark/curate_events.py` |
| Arguments | `NN` |
| | `file:///mounts/shared-volume/shared/data-engineering-lab/raw/watch_events` |
| | `file:///mounts/shared-volume/shared/data-engineering-lab/curated/student-NN/watch_events` |
| Driver | 1 core, 4G · Executor 1 × 1 core, 4G |

> The app file comes out as `local://`, the data arguments are `file://`. Browse fills the
> first one in for you. Substitute your own zero-padded number for `NN`.

### The notebook (step 4)
`notebooks/Lab18_Train_Churn_Model.ipynb` — 8 parts, fully documented, run top to bottom.
The only thing a participant edits is `STUDENT_ID` in Part 1.2.

**Part 1.1 installs its own dependencies in TWO ordered steps**, and the order is the whole
point:

1. `psycopg2-binary`, `xgboost`, `scikit-learn`, `mlflow` — resolved freely
2. NumPy and pandas — forced afterwards to the versions everything else needs

**Do not merge these into one pinned command.** mlflow requires `pandas<3`; cuDF 26.08
requires `pandas>=3`. Given both constraints at once, pip backtracks through mlflow releases
looking for one that satisfies them, reaches mlflow 1.27.0 (2022) whose metadata is
malformed, fails — and leaves NumPy downgraded to 1.24. Installing mlflow first and
correcting NumPy/pandas afterwards avoids the conflict; mlflow emits a version warning and
works correctly.

The cell detects whether cuDF is present and pins pandas 3.x if so, 2.2.3+ if not, then
prints both versions and warns loudly if NumPy ended up below 2.

**cuDF is deliberately not installed by the notebook.** It is a 1–2 GB download and requires
a *kernel restart*, which would break "run every cell from the top" for 30 people at once.
Bake RAPIDS into the notebook image instead — proven working set:

```
cudf-cu12 26.08 · rmm-cu12 26.08 · numpy 2.4.6 · pandas 3.0.3
xgboost · scikit-learn · psycopg2-binary · mlflow
```

Without it the notebook falls back to the CPU and everything still runs; you only lose the
timed CPU-vs-GPU comparison.

Covers: Parquet and columnar storage · partition pruning · **cuDF / RAPIDS with a timed
CPU-vs-GPU comparison** · joining across two systems · XGBoost on GPU · feature importance
(including a planted noise column) · MLflow registration.

## The DAG (not used in the session)
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
