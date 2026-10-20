# 0015. Where Rust could fit

- **Status:** Proposed
- **Date:** 2026-10-20
- **Deciders:** Howard Isaacson

## Context
Howard wants to learn **how and when** to use Rust. Rust is a compiled language that is memory-safe without a garbage collector, offers C-like speed, and is increasingly used in data tooling (e.g., Polars, Ruff, and the `pydantic-core` engine behind pydantic). Using it where it doesn't help would add complexity and weaken the story; using it where it measurably helps is a strong interview topic.

**Where Rust is worth it**
- **CPU-bound hot paths**: e.g., propagating orbits for **thousands of satellites × many time steps** (SGP4 or a drag model), or computing re-entry forecasts across the whole catalog under many solar-activity scenarios.
- **High-throughput parsing**: decoding large binary telemetry or stream data where Python is the bottleneck.
- **Python extensions**: write the hot function in Rust and call it from Python with **PyO3**, packaged with **maturin**, so the rest of the system stays Python.

**Where it isn't**
- **I/O-bound pollers**: they spend their time waiting on the network, so Rust saves milliseconds per 5-minute poll.
- **API glue and CRUD endpoints**: FastAPI is fast enough; the database is the bottleneck.
- Anything not yet **measured**. Profile first.

Note: Python's `sgp4` package already uses a C++ accelerated implementation when available, and NumPy vectorises well. A Rust module must beat *that* baseline honestly, not naïve Python.

## Options considered
### A. No Rust
- Pros: simpler stack.
- Cons: misses a learning goal; no systems-language story.
### B. Rewrite services in Rust (e.g., pollers with Tokio, API with Axum)
- Pros: lots of Rust practice.
- Cons: no measurable benefit for I/O-bound work; slower development; harder to explain why.
### C. Targeted Rust extension for a measured hot path (PyO3 + maturin)
- Pros: realistic industry pattern ("Python for orchestration, Rust for the inner loop"); benchmarkable; small surface area.
- Cons: Rust toolchain, CI building wheels, and the learning curve.

## Decision
Adopt **option C, later** (Roadmap Phase 5, after the orbital-decay feature exists in Python):
1. Build the Python baseline first (e.g., propagate the active LEO catalog with `sgp4`/`skyfield`; a simple drag-decay integrator using density from a model such as NRLMSIS via `pymsis`).
2. **Profile** it. If a hot loop dominates, implement it in a small crate `ti_orbits` (`crates/ti_orbits/`) using the Rust `sgp4` crate or a hand-written drag integrator, exposed to Python via **PyO3/maturin**.
3. **Benchmark** Rust against NumPy/C++ `sgp4`/pure Python on identical inputs, check numerical agreement, and publish the results in an About page, *including if Rust doesn't win*.

## Consequences
- Easier: a focused, defensible Rust story with numbers.
- Harder: Rust toolchain in Docker/CI, building wheels, and a second language to maintain.
- If benchmarks show no gain, document that and keep Python. That is still a good engineering result.

## How to explain this in an interview
"I kept the I/O-bound parts in Python and used Rust only where profiling showed a CPU-bound hot loop: propagating thousands of satellite orbits under different drag scenarios. I exposed it to Python with PyO3 and maturin and benchmarked it against the existing C++-backed sgp4 library, so the decision was driven by measurements, not hype."

## Learn more
- [The Rust Programming Language book](https://doc.rust-lang.org/book/)
- [PyO3 user guide](https://pyo3.rs/) and [maturin](https://www.maturin.rs/)
- Rust [`sgp4` crate docs](https://docs.rs/sgp4); Python [`sgp4`](https://pypi.org/project/sgp4/)
