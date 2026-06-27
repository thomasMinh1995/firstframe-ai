# Workflow

This document describes the intended Creative Reasoning Harness workflow at the contract level. Sprint 2 does not implement the workflow behavior.

## Current Sprint Boundary

Sprint 2 creates:

- immutable artifacts;
- domain plugin contracts;
- domain registry;
- runtime layer interfaces;
- API transport schemas;
- request validation;
- kernel documentation.

Sprint 2 does not create:

- chatbot behavior;
- GPT calls;
- prompt execution;
- ReAct loops;
- evaluation algorithms;
- generated story plans.

## Future Runtime Flow

```text
IdeaRequest
  |
  v
Transport Validation
  |
  v
IdeaArtifact
  |
  v
ReasoningLayer
  |
  v
ReasoningArtifact
  |
  v
PlanningLayer
  |
  v
PlanningArtifact
  |
  v
EvaluationLayer
  |
  v
EvaluationArtifact
```

API request and response models are transport contracts. Artifacts are internal kernel contracts.

## Why Harness Owns Workflow

The Harness owns workflow ordering because reasoning, planning, and evaluation are runtime concerns shared by every creative domain.

Domains should not decide when the Harness reasons, plans, or evaluates. Domains provide knowledge and criteria used by those steps.

## Why Domains Own Knowledge

Creative knowledge changes by domain. A short-film workflow, marketing workflow, and game-design workflow need different vocabulary, rubrics, examples, and prompt templates.

Keeping those assets in domain plugins prevents the kernel from becoming a pile of domain-specific branches.

## Why Providers Belong to Infrastructure

Model providers are replaceable execution mechanisms. They should be introduced later as infrastructure adapters behind stable interfaces.

The kernel should not change when a provider changes.

## Validation Before Harness Entry

Incoming HTTP payloads are validated with Pydantic transport models before any future Harness call occurs. This fail-fast boundary catches malformed or provider-specific input at the edge.
