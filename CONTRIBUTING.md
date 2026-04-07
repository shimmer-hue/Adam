# Contributing to EDEN/Adam

## Ways to Contribute

**1. Use it and report what happens.**
The most valuable contribution is honest feedback from real use. File issues describing what worked, what didn't, and what confused you.

**2. Build a tradition module.**
Follow [docs/TRADITION_EMBEDDING_GUIDE.md](docs/TRADITION_EMBEDDING_GUIDE.md). Even a partial implementation — just the text analysis functions, or just the priority hierarchy — is valuable. The project needs worked examples beyond the Tanakh module to prove the pattern is general.

**3. Improve documentation.**
If something confused you, fix it. The standard: a developer in Addis Ababa with good English and no prior exposure to this project should be able to understand it.

**4. Port missing features from Python to Idris2.**
[docs/IDRIS_IMPLEMENTATION_STATUS.md](docs/IDRIS_IMPLEMENTATION_STATUS.md) tracks every gap. Each gap has enough specification in the Python code and normative docs to guide implementation.

**5. Add language support.**
Concept extraction currently works for English and Hebrew. Every additional language makes the system accessible to another community.

**6. Write proofs.**
The Idris2 build has 55 machine-checked theorems. More are possible. If you can prove a property that the current code doesn't verify, that's a high-value contribution.

## Development Standards

**Honesty is non-negotiable.** This project is fanatically honest about what it can and cannot do. Never claim a capability that isn't implemented and tested. If something is aspirational, say "planned" or "not yet implemented."

**Docs travel with code.** The whitepaper and specs are executable documentation. If you add a feature, the relevant docs must be updated in the same PR.

**Label your evidence.** Synthetic data is always labeled synthetic. Observed data is always labeled observed. Never blur this boundary.

**The governance layers are load-bearing.** The membrane, measurement ledger, and feedback system carry the trust contract. Changes to them require extra scrutiny and thorough testing.

## Code Standards

### Idris2

- Pure functions where possible
- Total where possible (the type checker verifies termination)
- Dependent types for invariants (e.g., memode materialization requires 2+ members)
- `covering` for IO functions that can't be proven total
- Follow existing patterns in the codebase

### Python

- Tests required for new functionality
- Docstrings required for public functions
- Type hints preferred
- Run `pytest` before submitting

### Both Implementations

The turn loop invariant is constitutional:

```
input -> retrieve/assemble -> generate -> membrane -> feedback -> graph update
```

Do not add hidden governors, planners, or pre-generation layers. This is an active design boundary, not a gap.

## Vocabulary

Use the project's exact terminology. Do not introduce synonyms.

| Term | Meaning | Not This |
|------|---------|----------|
| meme | First-class persistent graph unit | Social media meme |
| memode | Derived structure from 2+ behavior memes | Cluster label |
| regard | Durable selection pressure | Importance score |
| membrane | Post-generation control surface | Filter, governor |
| active set | Bounded retrieval slice for a turn | The full identity |
| observatory | Browser measurement workbench | Dashboard |
| measurement event | Attributable graph mutation | Analytics event |

## Submitting Changes

1. Fork the repository
2. Create a feature branch from `main`
3. Make your changes
4. Verify the build: `cd eden-idris && ./build.sh`
5. Update relevant documentation
6. Submit a pull request with a clear description of what changed and why

For tradition modules, use the issue template "Tradition Module Proposal" to discuss your approach before implementing.

## Code of Conduct

This project exists to serve communities worldwide. Treat contributors with respect regardless of origin, tradition, or experience level. Technical disagreements are welcome; personal attacks are not.
