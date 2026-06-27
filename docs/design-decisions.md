# Design Decisions

## 1. Kernel Contracts Before Runtime Behavior

Sprint 2 defines contracts only. It does not implement reasoning, planning, evaluation, prompt execution, or provider calls.

Reason:

- stabilizes the framework surface before behavior exists;
- keeps Sprint 3 focused on runtime implementation;
- prevents prototype logic from defining the architecture accidentally.

## 2. Domain Registry as the Domain Entry Point

`DomainRegistry` is the only core entry point for registering, listing, and retrieving domain plugins.

Reason:

- avoids hard-coded domain references in the Harness;
- makes duplicate domain identifiers fail fast;
- gives future discovery and loading a single place to evolve.

## 3. Domain Owns Knowledge

Domain plugins expose metadata, knowledge, glossary, prompts, rubrics, and examples.

Reason:

- creative knowledge is domain-specific;
- the Harness should own workflow, not subject matter;
- new domains should not require edits to kernel contracts.

## 4. Immutable Artifacts Inside the Kernel

Harness layers exchange frozen dataclass artifacts instead of dictionaries.

Reason:

- makes layer contracts explicit;
- reduces accidental shape drift;
- helps tests and future provider adapters target stable data objects.

## 5. API Schemas Are Transport Contracts

Pydantic models live in `backend/app/api/schemas/` and are separate from internal artifacts.

Reason:

- HTTP payloads change for product and compatibility reasons;
- artifacts change for runtime architecture reasons;
- keeping them separate prevents API leakage into the core.

## 6. Validation Happens Before Harness Entry

Incoming request validation is provider-independent and handled at the transport edge.

Reason:

- malformed input should fail before runtime orchestration;
- provider-specific fields should not leak into the API contract;
- validation can evolve without introducing model-provider coupling.

## 7. Provider Adapters Belong to Infrastructure

OpenAI, Claude, Gemini, and other providers are future infrastructure concerns.

Reason:

- provider choice should be replaceable;
- provider SDKs should not pollute core contracts;
- testable runtime layers can be composed without network calls.

## 8. Composition Over Inheritance

Future runtime implementations should compose a domain registry and concrete layer implementations.

Reason:

- each layer has a narrow responsibility;
- providers can be swapped behind layer implementations;
- domains can be registered without subclassing the Harness.
