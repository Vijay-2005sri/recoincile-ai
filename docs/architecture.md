# Architecture

```mermaid
flowchart LR
    A[Demo CSVs or uploads] --> B[Validation]
    B -->|fatal errors| C[Stop and report]
    B -->|valid| D[Deterministic matcher]
    D --> E[Classifications and reasons]
    E --> F[Metrics and ground-truth evaluation]
    E --> G[SQLite audit]
    E --> H[Bounded AI explanation]
    H -->|failure or no key| I[Deterministic fallback]
    F --> J[Streamlit and exports]
    G --> J
    H --> J
    I --> J
```

The matcher never reads ground truth. Evaluation merges it only after results exist. Confidence is rule-based: `1.0` for unambiguous outcomes and `0.5` for manual review, not an ML probability. SQLite stores an audit entry for every result; runtime databases are ignored.

