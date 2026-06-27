# Architecture

FirstFrame AI is organized around a provider-independent Creative Reasoning Harness kernel. The kernel defines the runtime contracts, artifact flow, and domain plugin boundary that future creative domains will share.

Sprint 2 still does not implement AI behavior. It defines the reusable framework surface that Sprint 3 can implement without changing the contracts.

## Goals

- Keep the Harness domain-agnostic.
- Keep domain-specific knowledge in plugins.
- Exchange immutable artifacts between runtime layers.
- Keep HTTP transport models separate from internal artifacts.
- Make future provider adapters replaceable infrastructure.
- Let new domains register without changing Harness code.

## System Shape

```text
Frontend
  |
  v
FastAPI Delivery Layer
  |
  v
API Transport Schemas and Validation
  |
  v
Application Use Cases
  |
  v
Creative Reasoning Harness Kernel
  |
  +--> Domain Registry
  |      |
  |      v
  |    Domain Plugins
  |
  +--> Reasoning Layer
  +--> Planning Layer
  +--> Evaluation Layer
```

## Package Boundaries

### API

`backend/app/api/` owns HTTP concerns:

- route registration;
- request and response schemas;
- transport-level validation.

The API layer must not expose internal artifacts directly. It maps future HTTP payloads into application inputs and maps application outputs into response schemas.

### Application

`backend/app/application/` is reserved for use cases and orchestration entry points that sit outside the kernel. It should coordinate API requests, kernel calls, persistence, and other application services without owning domain knowledge.

### Core

`backend/app/core/` owns the kernel:

- immutable artifact models;
- domain plugin contracts;
- domain registry;
- Harness runtime interfaces.

Core must not import FastAPI, provider SDKs, database clients, or frontend code.

### Domain Plugins

`domains/` contains domain-owned assets. A plugin exposes metadata plus resource catalogs for:

- knowledge;
- glossary;
- prompts;
- rubrics;
- examples.

The Harness depends on the plugin contract, not on domain folder names.

## Domain Plugin Pattern

Every domain plugin must satisfy the `DomainPlugin` protocol. The plugin contract exposes metadata and typed resource collections. The Harness retrieves plugins through `DomainRegistry`; it should not import or hard-code specific domains.

This keeps future domains independent. A new domain can be added by creating a plugin and registering it with the registry. The Harness runtime remains unchanged.

## Artifact Flow

Internal Harness layers exchange immutable artifacts:

```text
IdeaArtifact
  |
  v
ReasoningArtifact
  |
  v
PlanningArtifact
  |
  v
EvaluationArtifact
```

`StoryPlanArtifact` is a structured planning artifact for story-development outputs. It is an internal artifact, not an API response.

## Runtime Responsibilities

- `ReasoningLayer`: accepts an `IdeaArtifact` and a domain plugin; returns a `ReasoningArtifact`.
- `PlanningLayer`: accepts a `ReasoningArtifact` and a domain plugin; returns a `PlanningArtifact`.
- `EvaluationLayer`: accepts a `PlanningArtifact` and a domain plugin; returns an `EvaluationArtifact`.
- `CreativeReasoningKernel`: defines the runtime boundary that will compose the registry and layers in a later sprint.

## Provider Independence

OpenAI, Claude, Gemini, local models, and other providers belong behind future infrastructure adapters. Provider adapters may implement runtime layer dependencies later, but provider objects must not appear in core artifacts, domain plugins, or API contracts.
