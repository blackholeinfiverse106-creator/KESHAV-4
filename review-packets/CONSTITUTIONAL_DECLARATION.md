# CONSTITUTIONAL DECLARATION
## Phase 5 — Constitutional Closure

**Service:** KESHAV-4 Propagation Engine
**Canonical Owner:** Rajaryan
**Date:** 2026-05-26

This document constitutionally declares what KESHAV-4 is, what it is not, what it owns, what it influences, and what it explicitly does NOT do. These declarations are binding for all future development.

---

## A. Authority Owned

KESHAV-4 has **full and exclusive authority** over:

| Authority | Scope | Evidence |
|---|---|---|
| BFS traversal algorithm | The `compute_downstream_path` method is the sole implementation. No alternative traversal paths exist. | `app/engine.py:8-37` |
| Graph neighbor sorting | Neighbors are sorted alphabetically before BFS visit. This guarantees deterministic traversal order. | `app/engine.py:19,30` |
| Impact scoring | `impact_score = len(impacted_tasks)`. No heuristics, no weights, no ML. Pure count. | `app/engine.py:68` |
| Severity classification | Algebraic thresholds: LOW (<3), MEDIUM (3≤x<10), HIGH (≥10). No override mechanism. | `app/engine.py:71-76` |
| Resolution signal generation | Format: `UNBLOCK_DEPENDENCY:{root_cause}`. No alternative formats. | `app/engine.py:78` |
| Input validation | `PropagationInput.model_validate()` with `extra="forbid"`. All invalid input raises `PropagationContractViolation`. | `app/engine.py:45-48` |
| Error code vocabulary | Three codes: `SCHEMA_MISMATCH`, `BROKEN_ROOT_CAUSE`, `INVALID_GRAPH`. No other error codes exist. | `app/engine.py:48,58,62` |
| Schema definitions | `PropagationInput`, `PropagationOutput`, `PropagationContractViolation` are owned exclusively. | `shared_schemas/schemas.py` |

---

## B. Authority NOT Owned

KESHAV-4 has **NO authority** over:

| Domain | Owner | KESHAV's Relationship |
|---|---|---|
| Enforcement decisions (ALLOW/DENY/ABSTAIN) | RAJYA Validation Engine / Sarathi | KESHAV produces a `severity` and `resolution_signal` that may *influence* enforcement. It does NOT make the decision. |
| Epistemic state management | DGIC (Layer 3) | KESHAV has no knowledge of epistemic state, entropy scores, or contradiction flags. These are consumed by the integration layer, not by the engine. |
| Trace hash minting | Sarathi (Layer 1) | KESHAV passes `trace_id` through unchanged. It does NOT generate, validate, or modify trace hashes. |
| Bucket artifact writes | Layer 5 Bucket | KESHAV does NOT write to the Bucket. The integration layer calls `invoke_agent()` which eventually routes to Layer 5. |
| KSML envelope construction | Sūtradhāra Control Plane | KESHAV does NOT construct `KSMLInput` envelopes. The integration test constructs them from KESHAV output. |
| Pipeline orchestration | Sūtradhāra Control Plane | KESHAV does NOT invoke pipeline steps. It is a library called by the pipeline. |
| Schema governance of enforcement schemas | text-risk-scoring-service | KESHAV imports `KSMLInput`, `ContextSignal`, `SourceSystem` but does NOT own, modify, or fork them. |

---

## C. TANTRA Layer Position

```
Layer 0: Intelligence ──────────────────────────────┐
Layer 1: Sarathi Governance ────────────────────────┤
Layer 2: (not applicable) ──────────────────────────┤
Layer 3: DGIC Epistemic State ──────────────────────┤  KESHAV operates OUTSIDE
Layer 4: Core Execution ────────────────────────────┤  the TANTRA layer stack.
Layer 5: Bucket Artifact Storage ───────────────────┘
                                                     
                                                     KESHAV is a LIBRARY consumed
┌─────────────────────────────────────────────┐      by the pipeline. It has no
│  KESHAV-4 Propagation Engine               │      layer number. It is NOT a
│  Position: PRE-PIPELINE COMPUTATION        │      TANTRA layer.
│  Invocation: Called before pipeline entry   │
│  Output: Fed into pipeline via KSML        │
└─────────────────────────────────────────────┘
```

KESHAV is **not a TANTRA layer**. It is a stateless computation library that produces an output dictionary. That output is then mapped into a KSML envelope and fed into the TANTRA pipeline by the integration layer. KESHAV has no knowledge of the pipeline's internal structure.

---

## D. Upstream Influence

| Upstream Entity | Influence on KESHAV | KESHAV's Authority |
|---|---|---|
| Any caller providing `input_data` dict | Determines the graph, blocked task, root cause, trace ID | KESHAV has full authority to **reject** malformed input via `PropagationContractViolation`. |
| Test harness | Provides graph topologies for validation | KESHAV has no authority over what graphs are tested — but the output is deterministic regardless. |

**KESHAV does NOT influence upstream entities.** It does not send callbacks, emit events, modify upstream state, or request additional data.

---

## E. Downstream Influence

| Downstream Entity | KESHAV's Influence | Binding? |
|---|---|---|
| Integration layer (test_live_integration.py) | Provides `severity`, `resolution_signal`, `impacted_tasks` that get mapped to KSML signals | **NOT binding.** The integration layer may choose to ignore, transform, or override KESHAV's output. |
| RAJYA Validation Engine | `severity` and `resolution_signal` become `ContextSignal.value` and `metadata.proposed_action` | **NOT binding.** RAJYA makes its own enforcement decision. |
| Sarathi | No direct influence | KESHAV has zero knowledge of or influence over Sarathi. |
| Bucket (Layer 5) | `trace_id` becomes `artifact_id` in the bucket record | **Passive carry-through only.** KESHAV does not control what gets written to the bucket. |

**KESHAV produces output. It does NOT control consumption.**

---

## F. Execution Rights

| Right | Granted? | Evidence |
|---|---|---|
| Read input data | **YES** | `compute_dependency_output(input_data: dict)` |
| Compute graph traversal | **YES** | `compute_downstream_path()` — BFS over in-memory dict |
| Return output data | **YES** | Returns `PropagationOutput.model_dump()` |
| Write to filesystem | **NO** | Engine contains zero file I/O operations |
| Make network calls | **NO** | Engine contains zero network operations |
| Spawn processes/threads | **NO** | Engine runs in caller's thread |
| Log/print to stdout | **NO** | Engine contains zero print/logging statements |
| Import external packages (beyond Pydantic) | **NO** | Engine imports only `typing` and `shared_schemas.schemas` |
| Modify global state | **NO** | Engine uses `@staticmethod` with only local variables |
| Raise exceptions | **YES** | `PropagationContractViolation` on invalid input |

---

## G. Explicit Anti-Drift Guarantees

| Guarantee | Enforcement Mechanism |
|---|---|
| **No new schema fields may be silently added** | `extra="forbid"` on both `PropagationInput` and `PropagationOutput`. Any new field causes immediate `ValidationError`. |
| **No severity heuristics may be introduced** | Severity is a pure algebraic function of `impact_score`. The thresholds (3, 10) are hardcoded constants, not configurable. |
| **No caching may be introduced** | Engine is `@staticmethod` — no instance to cache on. Adding instance state requires changing the engine's fundamental architecture. |
| **No network calls may be added** | Engine imports only `typing` and `shared_schemas`. Adding `requests`, `httpx`, or any network library is a visible import change. |
| **No side effects may be introduced** | Engine returns a dict. It does not modify any external state. Adding side effects requires adding I/O operations that are visible in code review. |
| **No adaptive behavior may be introduced** | Output is strictly deterministic given input. Adding learning/adaptation requires adding state, which violates the `@staticmethod` constraint. |
| **Test suite enforces structural guarantees** | 33 tests verify determinism, replay, failure behavior, schema compliance, and integration. Any drift breaks tests. |

---

## H. Hidden-State Disclosure

**KESHAV-4 has ZERO hidden state.**

| State Surface | Status | Evidence |
|---|---|---|
| Class-level variables | **NONE** | `PropagationEngine` has no class variables. Both methods are `@staticmethod`. |
| Instance variables | **NONE** | No `__init__`, no `self`, no instances are ever created. |
| Module-level state | **NONE** | `engine.py` has no module-level mutable variables. |
| Caches / memoization | **NONE** | No `@lru_cache`, no `functools.cache`, no manual caching. |
| Thread-local storage | **NONE** | No `threading.local()` usage. |
| Global singletons | **NONE** | No singleton pattern. `PropagationEngine` is never instantiated. |
| File-based state | **NONE** | Engine does not read or write files. |
| Environment variables | **NONE** | Engine does not read `os.environ`. |

---

## I. Replay Guarantees

| Guarantee | Proof | Evidence Artifact |
|---|---|---|
| **Deterministic output** | Same input → byte-identical output, proven across 100 shuffled iterations | `test_edge_cases_and_determinism.py::test_determinism_proof` |
| **Cross-process determinism** | 12 isolated OS processes with adversarial timing all produce identical SHA-256 hash | `evidence/cross_process_replay_proof.txt` |
| **Restart equivalence** | 5 independent invocations produce identical hash | `evidence/restart_replay_proof.txt` |
| **Serialization round-trip** | Compute → serialize → delete → deserialize → fresh replay → all match | `evidence/interruption_reconstruction_proof.txt` |
| **Trace continuity** | `trace_id` passes through unchanged across compute/serialize/deserialize | `evidence/trace_continuity_proof.txt` |
| **Corruption resistance** | 6 corruption types rejected; subsequent valid input produces identical baseline hash | `evidence/corruption_injection_proof.txt` |

---

## J. Non-Bypass Guarantees

| Guarantee | Mechanism |
|---|---|
| **Input validation cannot be bypassed** | `compute_dependency_output` is the ONLY public entry point. It calls `PropagationInput.model_validate()` as its first operation. There is no alternative code path that skips validation. |
| **Root cause check cannot be bypassed** | After Pydantic validation, the engine explicitly checks `root_cause in dependency_graph`. There is no flag, config, or parameter to skip this check. |
| **Blocked task check cannot be bypassed** | After root cause check, the engine explicitly checks `blocked_task_id in dependency_graph`. No bypass mechanism. |
| **Severity classification cannot be overridden** | Severity is computed inside `compute_dependency_output` from `impact_score`. There is no parameter to override severity. |
| **Resolution signal format cannot be overridden** | Format is `f"UNBLOCK_DEPENDENCY:{root_cause}"`. There is no parameter to change the format. |
| **Output schema cannot be bypassed** | Output is constructed via `PropagationOutput(...)` with `extra="forbid"`. The engine cannot return fields outside the schema. |

---

## What KESHAV-4 Is NOT

### KESHAV is NOT a Sovereign Authority
KESHAV does not make binding decisions. It computes a severity score and a resolution signal. Downstream systems decide what to do with them. KESHAV cannot ALLOW, DENY, or ABSTAIN. Those are enforcement concepts that belong to RAJYA/Sarathi.

### KESHAV is NOT a Hidden Orchestration Layer
KESHAV does not invoke pipeline steps, coordinate services, manage execution order, or route messages. It is called, it computes, it returns. It has no knowledge of the pipeline's existence.

### KESHAV is NOT an Execution Authority
KESHAV does not execute actions, trigger workflows, spawn processes, or modify external state. Its execution rights are limited to: read input → compute graph traversal → return output.

### KESHAV is NOT a Governance Authority
KESHAV does not define policies, enforce rules, manage access control, or govern behavior. It computes mathematical graph properties. Governance belongs to Sarathi and RAJYA.

### KESHAV is NOT a Mutable Truth Authority
KESHAV does not store truth, persist state, or maintain a ledger. Every invocation is a fresh, pure computation. There is no "KESHAV truth" that persists between calls. The output is a function of the input, not of accumulated state.
