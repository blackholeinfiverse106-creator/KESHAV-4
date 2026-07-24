# What is KESHAV?

**KESHAV** is the **Deterministic Dependency Intelligence Layer** of the TANTRA ecosystem. 

In simple terms, KESHAV is an analytical engine. When a complex system of inter-dependent tasks experiences a failure or blockage, KESHAV's job is to look at the entire graph of tasks, figure out exactly what broke, why it broke, and propose a specific action to fix it.

---

## 1. What does KESHAV actually do?

When KESHAV receives an input payload (usually from an upstream source like **SETU**), it executes a strict 5-phase analysis process:

1. **Detect Blocked Tasks**: It scans the input for any tasks that failed constraint validation.
2. **Trace Root Causes**: It traverses the dependency graph to find the true origin of the failure (e.g., Task C failed because Task B failed, but Task B failed because Task A was the actual root cause).
3. **Detect Bottlenecks**: It analyzes propagation results to find tasks that have the highest "blast radius" or impact score.
4. **Generate Resolution Signal**: Based on the root cause and bottleneck, it deterministically generates a fix (e.g., `UNBLOCK_DEPENDENCY:T1`).
5. **Structure Output**: It formats its findings into a strict, predefined JSON output contract to be passed down the pipeline.

---

## 2. Where does KESHAV fit in?

KESHAV does **not** act alone. It is the **second layer** (the Analyzer) in the strict 6-layer **TANTRA Pipeline**:

1. **SETU (Input Bridge)**: Accepts raw signals and ensures a `trace_id` exists.
2. 👉 **KESHAV (Analyzer)**: *Finds the root cause and proposes a fix.*
3. **RAJYA (Decision)**: A strict checkpoint that ensures KESHAV didn't mutate the `trace_id` or break the contract.
4. **Sarathi (Enforcement)**: Converts KESHAV's proposed fix into a formal authorization ticket.
5. **Core (Execution)**: Actually executes the authorization.
6. **Bucket (Truth)**: Saves the final result in an append-only, permanent memory store.

*Note: While KESHAV is running, a sidecar system called **InsightFlow** quietly observes its output for monitoring and dashboarding, without interfering with the pipeline.*

---

## 3. Core Design Principles

KESHAV is built with extreme rigidity and predictability. Its design is governed by these core principles:

* **Strictly Deterministic**: Given the exact same JSON input payload, KESHAV will *always* produce the exact same root cause and resolution signal. There is zero randomness.
* **Zero Mutation (No Global State)**: KESHAV only reads input and generates output. It does not modify external databases, it does not alter the incoming `trace_id`, and it doesn't hold hidden states.
* **Fail-Closed**: If an upstream service sends a payload that breaks the strict KESHAV input contract (e.g., missing a `trace_id`), KESHAV will immediately reject it with an HTTP 400 error. It prefers halting completely over processing corrupted data.
* **Separation of Authority**: KESHAV has no power to actually *execute* a fix. It is strictly an intelligence layer. It only *proposes* the resolution signal; the downstream layers (RAJYA and Sarathi) decide whether to authorize and execute it.
