# Audit

This directory is system structure only.

Runtime audit logs must not be committed to the system repository.
The active local audit log is written to:

```text
.local/runtime/audit/audit.md
```

A future sync mode may move selected runtime records to:

```text
abyss-data/runtime/
```
