---
trigger: always
description: "Engineering constitution and priority order. AGENTS.md section 8 is authoritative."
---

# Engineering Principles (summary of AGENTS.md section 8)

Priority order. When two principles conflict, the one EARLIER in this list wins.

1. **Make it work**: every phase runs end-to-end and is proven by a test.
2. **Secure**: repositories are untrusted. Security beats elegance.
3. **YAGNI**: no code for future phases, no speculative abstractions.
4. **Least Astonishment**: a function does what its name says, nothing more.
5. **KISS**: the simplest solution that satisfies the contract.
6. **Consistency**: same naming, structure and error handling across all adapters.
7. **DRY**: extract only after the third repetition, never into a wrong abstraction.
8. **Separation of Concerns**: `api / schemas / services / tools / core`.
   Routes contain NO business logic. Adapters contain NO orchestration.
9. **Composition over inheritance**: Protocols and constructor injection. No deep hierarchies.
10. **SOLID**: as clean design after the above, not as a goal in itself.
11. **Design patterns**: ONLY those in the Pattern Map (AGENTS.md section 8.1).
    Every pattern must be justified in one sentence by the concrete problem it solves.
12. **Performance**: only after measurement.

Additional constraints:
- Depend on Protocols (Dependency Inversion), inject through constructors.
- High cohesion / Single Responsibility: one module, one reason to change.
- Open/Closed: add a tool by adding an adapter, not by editing orchestrator logic.
- Interface Segregation: small Protocols (`AnalysisTool`, `RepositoryFetcher`), no fat interfaces.

AGENTS.md section 8 is the canonical, complete source. This file is a summary only.
