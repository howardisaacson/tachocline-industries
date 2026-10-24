# 0016. Treat the data science workflow as a first-class, documented feature

- **Status:** Accepted
- **Date:** 2026-10-20
- **Deciders:** Howard Isaacson

## Context
Howard wants to **highlight data science workflow** as a skill. Many portfolios show a final chart or a model score but hide the process: how the question was framed, where the data came from, how it was cleaned, how the model was validated, and how uncertain it is. Interviewers for data science and ML roles probe exactly that process (leakage, baselines, validation, uncertainty, monitoring). TI's flagship science feature, **Drag Watch** (storm-driven orbital decay and re-entry prediction), is a natural worked example with real ground truth: actual decay dates in SATCAT.

## Options considered
### A. Notebooks only, results shown on the site
- Pros: fast; familiar.
- Cons: hard to reproduce or test; the process stays invisible; notebook diffs are unreadable in review.
### B. Productionised model code only (no process documentation)
- Pros: clean engineering.
- Cons: hides the reasoning that data-science interviews care about.
### C. A documented, reproducible workflow, published as its own site page
- Pros: makes the process the product; each step maps to repo folders, tools and ADRs; backtests against real decays give honest credibility; reusable for later models.
- Cons: more documentation and discipline; slower to the first "result".

## Decision
Adopt option C:
- [`docs/data-science-workflow.md`](../data-science-workflow.md) defines the 11-step workflow (framing → provenance → raw zone → cleaning/validation → EDA → features → modelling → backtesting → uncertainty → communication → monitoring), using Drag Watch as the example.
- It becomes a **public site page** ("How the science is done") with its own About page ([ADR 0009](0009-about-this-page-for-every-section.md)).
- Practices: `notebooks/` for exploration only (paired with Jupytext, outputs stripped); reusable code in a tested `analysis/` package; locked environments (uv); immutable raw data identified by hash with a manifest; time-aware validation and baselines that every model must beat; predictions published with intervals; a simple experiment log first, **MLflow** when variants multiply (separate ADR then).

## Consequences
- Easier: interview answers backed by a real, reproducible process; credible science claims.
- Harder: extra structure (analysis package, tests, manifests) before the first model; ongoing doc upkeep.
- Commits us to publishing honest backtest errors, including when the model is mediocre.

## How to explain this in an interview
"I treated the workflow itself as a feature: framed the question and metric first, kept raw data immutable with provenance, validated with time-ordered backtests against real satellite re-entry dates, and published predictions as ranges. The whole process is a documented page on the site, and the numbers can be reproduced with one command from raw data."

## Learn more
- The Turing Way, [Guide for reproducible research](https://book.the-turing-way.org/reproducible-research/reproducible-research/)
- scikit-learn, [`TimeSeriesSplit`](https://scikit-learn.org/stable/modules/generated/sklearn.model_selection.TimeSeriesSplit.html) (time-aware validation)
- [MLflow documentation](https://mlflow.org/docs/latest/)
