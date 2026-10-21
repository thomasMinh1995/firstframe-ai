from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import TypeVar
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field

from app.application.ai_provider import StructuredProvider, StructuredRequest
from app.application.dataset import recording_provider
from app.application.example_loader import DomainExample, ExampleLoader
from app.application.fidelity import FidelityReport, audit_suggestions, scan_fidelity
from app.application.knowledge_loader import KnowledgeLoader
from app.application.language import ResponseLanguage, resolve_response_language
from app.application.prompt_loader import PromptLoader
from app.core.artifacts import (
    ArtifactKind,
    ArtifactMetadata,
    Constraint,
    EvaluationArtifact,
    EvaluationFinding,
    IdeaArtifact,
    PlanningArtifact,
    PlanSection,
    ReasoningArtifact,
    ReasoningNote,
    StoryPlanArtifact,
)
from app.core.domains import (
    DomainMetadata,
    DomainPlugin,
    DomainRegistry,
    DomainResource,
    DomainResourceCatalog,
)
from app.core.harness import EvaluationLayer, PlanningLayer, ReasoningLayer
from app.infrastructure.provider_factory import create_provider

DEFAULT_DOMAIN_ID = "short-film"
MAX_PLANNING_EXAMPLES = 3
OutputT = TypeVar("OutputT", bound=BaseModel)


class _ReasoningNoteOutput(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    label: str
    content: str


class _ReasoningOutput(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    summary: str
    notes: list[_ReasoningNoteOutput] = Field(default_factory=list)
    missing_information: list[str] = Field(default_factory=list, max_length=3)


class _PlanningOutput(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    story_plan: _StructuredStoryPlanOutput


class EvaluationRubricScores(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    story_clarity: int = Field(ge=1, le=5)
    character: int = Field(ge=1, le=5)
    conflict: int = Field(ge=1, le=5)
    emotional_impact: int = Field(ge=1, le=5)
    ending: int = Field(ge=1, le=5)
    production_feasibility: int = Field(ge=1, le=5)


class _EvaluationOutput(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    passed: bool
    rubric_scores: EvaluationRubricScores
    strengths: list[str]
    weaknesses: list[str]
    suggestions: list[str]


class WorkingTitle(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    title: str


class Logline(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    text: str


class Characters(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    protagonist: str
    supporting_characters: list[str]
    antagonist_or_obstacle: str | None


class Conflict(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    external: str
    internal: str | None
    stakes: str | None


class Beginning(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    setup: str
    key_event: str | None


class Middle(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    escalation: str
    turning_point: str | None


class Ending(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    resolution: str
    final_image: str | None


class Theme(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    statement: str


class VisualStyle(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    description: str | None
    visual_motifs: list[str]


class Tone(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    description: str


class ProductionNotes(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    notes: str
    locations: list[str]
    cast_size: str | None


class _StructuredStoryPlanOutput(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    working_title: WorkingTitle
    logline: Logline
    characters: Characters
    conflict: Conflict
    beginning: Beginning
    middle: Middle
    ending: Ending
    theme: Theme
    visual_style: VisualStyle
    tone: Tone
    production_notes: ProductionNotes


_PlanningOutput.model_rebuild()


@dataclass(frozen=True)
class _LLMPlanningArtifact(PlanningArtifact):
    title: str | None = None
    logline: str | None = None
    target_response_language: str = "English"
    creator_context: str = ""


@dataclass(frozen=True)
class StaticDomainPlugin:
    metadata: DomainMetadata
    resources: DomainResourceCatalog = field(default_factory=DomainResourceCatalog)

    @property
    def knowledge(self) -> tuple[DomainResource, ...]:
        return self.resources.knowledge

    @property
    def glossary(self) -> tuple[DomainResource, ...]:
        return self.resources.glossary

    @property
    def prompts(self) -> tuple[DomainResource, ...]:
        return self.resources.prompts

    @property
    def rubrics(self) -> tuple[DomainResource, ...]:
        return self.resources.rubrics

    @property
    def examples(self) -> tuple[DomainResource, ...]:
        return self.resources.examples


@dataclass(frozen=True)
class HarnessRun:
    analysis: ReasoningArtifact
    story_plan: StoryPlanArtifact
    evaluation: EvaluationArtifact


@dataclass(frozen=True)
class _LLMReasoningArtifact(ReasoningArtifact):
    creator_context: str = ""


class LLMReasoningLayer(ReasoningLayer):
    def __init__(self, provider: StructuredProvider, prompt_loader: PromptLoader) -> None:
        self._provider = provider
        self._prompt_loader = prompt_loader

    def reason(self, idea: IdeaArtifact, domain: DomainPlugin) -> ReasoningArtifact:
        target_language = _target_response_language(idea)
        result = self._provider.request_structured(
            StructuredRequest(
                instructions=self._prompt_loader.load("story_mentor", domain),
                input_text=_idea_input(idea),
                response_model=_ReasoningOutput,
                stage="reasoning",
            )
        )
        output = _expect_output(result.output, _ReasoningOutput)
        return _LLMReasoningArtifact(
            metadata=_metadata(idea.metadata.domain_id, "reasoning"),
            source_idea_id=idea.metadata.artifact_id,
            creator_context=_creator_input(idea.text, idea.constraints, idea.clarifications),
            notes=(
                ReasoningNote(label="Original idea", content=idea.text),
                ReasoningNote(label="Target response language", content=target_language),
                ReasoningNote(label="Analysis summary", content=output.summary),
                *(ReasoningNote(label=note.label, content=note.content) for note in output.notes),
            ),
            open_questions=tuple(output.missing_information[:3]),
        )


class LLMPlanningLayer(PlanningLayer):
    def __init__(
        self,
        provider: StructuredProvider,
        prompt_loader: PromptLoader,
        knowledge_loader: KnowledgeLoader,
        example_loader: ExampleLoader,
        *,
        compact_context: bool = False,
    ) -> None:
        self._provider = provider
        self._prompt_loader = prompt_loader
        self._knowledge_loader = knowledge_loader
        self._example_loader = example_loader
        self._compact_context = compact_context

    def plan(self, reasoning: ReasoningArtifact, domain: DomainPlugin) -> PlanningArtifact:
        knowledge = {
            "film_glossary": self._knowledge_loader.load("film_glossary", domain),
            "film_rules": self._knowledge_loader.load("film_rules", domain),
            "story_patterns": self._knowledge_loader.load("story_patterns", domain),
        }
        examples = self._example_loader.load(domain, limit=MAX_PLANNING_EXAMPLES)
        input_text = _reasoning_input(reasoning, knowledge, examples)
        if self._compact_context:
            input_text = compact_qwen_planning_input(input_text)
        result = self._provider.request_structured(
            StructuredRequest(
                instructions=self._prompt_loader.load("story_planner", domain),
                input_text=input_text,
                response_model=_PlanningOutput,
                stage="planning",
            )
        )
        output = _expect_output(result.output, _PlanningOutput)
        story_plan = output.story_plan
        return _LLMPlanningArtifact(
            metadata=_metadata(reasoning.metadata.domain_id, "planning"),
            source_reasoning_id=reasoning.metadata.artifact_id,
            title=story_plan.working_title.title,
            logline=story_plan.logline.text,
            sections=tuple(_structured_plan_sections(story_plan)),
            target_response_language=_find_note(reasoning, "Target response language"),
            creator_context=getattr(reasoning, "creator_context", ""),
        )


class LLMEvaluationLayer(EvaluationLayer):
    def __init__(
        self,
        provider: StructuredProvider,
        prompt_loader: PromptLoader,
        knowledge_loader: KnowledgeLoader,
    ) -> None:
        self._provider = provider
        self._prompt_loader = prompt_loader
        self._knowledge_loader = knowledge_loader

    def evaluate(self, planning: PlanningArtifact, domain: DomainPlugin) -> EvaluationArtifact:
        language = getattr(planning, "target_response_language", "English")
        draft = json.loads(_planning_input(planning))
        raw_author = getattr(planning, "creator_context", "")
        try:
            author = json.loads(raw_author or "{}")
        except ValueError:
            author = {"creator_context": raw_author}
        if not author:
            report = FidelityReport(status="unverified", checks=[])
            return self._result(planning, report)
        scan, checks = scan_fidelity(
            self._provider, self._prompt_loader.load("fidelity", domain), draft, author, language,
        )
        if scan.status == "uncertain":
            return self._result(planning, FidelityReport(status="unverified", checks=checks))
        output = None
        if scan.issues:
            candidates = [issue.model_dump() for issue in scan.issues]
        else:
            rubric = self._knowledge_loader.load_rubric("story_rubric", domain)
            prompt_name = "script_critic_vi" if _is_vietnamese_language(language) else "script_critic"
            result = self._provider.request_structured(StructuredRequest(
                instructions=self._prompt_loader.load(prompt_name, domain),
                input_text=_evaluation_input(planning, rubric),
                response_model=_EvaluationOutput, stage="evaluation",
            ))
            output = _expect_output(result.output, _EvaluationOutput)
            if len(output.weaknesses) != len(output.suggestions) or len(output.suggestions) > 3:
                return self._result(planning, FidelityReport(
                    status="unverified", checks=[], withheld_count=len(output.suggestions),
                ))
            candidates = [{"explanation": weakness, "suggestion": suggestion}
                          for weakness, suggestion in zip(output.weaknesses, output.suggestions)]
        if candidates:
            report = audit_suggestions(
                self._provider, self._prompt_loader.load("fidelity_audit", domain),
                draft, author, language, candidates, checks,
            )
            if not scan.issues:
                for check in report.checks:
                    check.kind = "craft"
                if report.status != "unverified":
                    report.status = "clear"
        else:
            report = FidelityReport(status="clear", checks=[])
        return self._result(planning, report, output)

    def _result(self, planning: PlanningArtifact, report: FidelityReport,
                output: _EvaluationOutput | None = None) -> EvaluationArtifact:
        # Unverified criticism must not appear as a score or an approved revision.
        findings = []
        if output is not None and report.status == "clear":
            findings = list(_evaluation_findings(output, getattr(planning, "target_response_language", "English")))
        return EvaluationArtifact(
            metadata=_metadata(planning.metadata.domain_id, "evaluation"),
            source_planning_id=planning.metadata.artifact_id,
            passed=output.passed if output is not None and report.status == "clear" else None,
            findings=tuple(findings), fidelity=report.model_dump(),
        )


class CreativeReasoningHarness:
    def __init__(
        self,
        domains: DomainRegistry,
        reasoning_layer: ReasoningLayer,
        planning_layer: PlanningLayer,
        evaluation_layer: EvaluationLayer,
    ) -> None:
        self.domains = domains
        self._reasoning_layer = reasoning_layer
        self._planning_layer = planning_layer
        self._evaluation_layer = evaluation_layer

    def generate(self, idea: IdeaArtifact) -> HarnessRun:
        domain = self.domains.get(idea.metadata.domain_id)
        reasoning = self._reasoning_layer.reason(idea, domain)
        return self.plan(reasoning)

    def analyze(self, idea: IdeaArtifact) -> ReasoningArtifact:
        return self._reasoning_layer.reason(idea, self.domains.get(idea.metadata.domain_id))

    def plan(self, reasoning: ReasoningArtifact) -> HarnessRun:
        domain = self.domains.get(reasoning.metadata.domain_id)
        planning = self._planning_layer.plan(reasoning, domain)
        story_plan = StoryPlanArtifact(
            metadata=_metadata(reasoning.metadata.domain_id, "story_plan"),
            source_planning_id=planning.metadata.artifact_id,
            title=getattr(planning, "title", None) or "Untitled Short Film",
            logline=getattr(planning, "logline", None)
            or _make_logline(_find_note(reasoning, "Original idea")),
            sections=planning.sections,
        )
        evaluation = self._evaluation_layer.evaluate(planning, domain)
        return HarnessRun(analysis=reasoning, story_plan=story_plan, evaluation=evaluation)

    def review(self, planning: PlanningArtifact) -> EvaluationArtifact:
        return self._evaluation_layer.evaluate(
            planning, self.domains.get(planning.metadata.domain_id)
        )


class StoryGenerationService:
    def __init__(self, harness: CreativeReasoningHarness) -> None:
        self._harness = harness

    def analyze(
        self,
        idea_text: str,
        constraints: tuple[Constraint, ...] = (),
        answers: tuple[tuple[str, str], ...] = (),
        response_language: ResponseLanguage = "auto",
    ) -> ReasoningArtifact:
        return self._harness.analyze(
            IdeaArtifact(
                metadata=_metadata(DEFAULT_DOMAIN_ID, "idea"),
                text=idea_text,
                constraints=(
                    *constraints,
                    Constraint(
                        name="target_response_language",
                        value=resolve_response_language(idea_text, response_language),
                    ),
                ),
                clarifications=answers,
            )
        )

    def plan(
        self,
        idea_text: str,
        answers: tuple[tuple[str, str], ...],
        constraints: tuple[Constraint, ...] = (),
        response_language: ResponseLanguage = "auto",
    ) -> HarnessRun:
        return self._harness.plan(
            _LLMReasoningArtifact(
                metadata=_metadata(DEFAULT_DOMAIN_ID, "reasoning"),
                source_idea_id=str(uuid4()),
                creator_context=_creator_input(idea_text, constraints, answers),
                notes=(
                    ReasoningNote(label="Original idea", content=idea_text),
                    ReasoningNote(
                        label="Target response language",
                        content=resolve_response_language(idea_text, response_language),
                    ),
                    ReasoningNote(
                        label="Creator constraints",
                        content=json.dumps(
                            [item.value for item in constraints], ensure_ascii=False
                        ),
                    ),
                    *(
                        ReasoningNote(label=question, content=answer)
                        for question, answer in answers
                    ),
                ),
            )
        )

    def review(
        self,
        idea_text: str,
        title: str,
        logline: str,
        sections: tuple[PlanSection, ...],
        creator_context: str,
        response_language: ResponseLanguage = "auto",
    ) -> EvaluationArtifact:
        return self._harness.review(
            _LLMPlanningArtifact(
                metadata=_metadata(DEFAULT_DOMAIN_ID, "planning"),
                source_reasoning_id=str(uuid4()),
                title=title,
                logline=logline,
                sections=sections,
                target_response_language=resolve_response_language(idea_text, response_language),
                creator_context=creator_context,
            )
        )

    def generate(
        self,
        idea_text: str,
        domain_id: str = DEFAULT_DOMAIN_ID,
        constraints: tuple[Constraint, ...] = (),
        response_language: ResponseLanguage = "auto",
    ) -> HarnessRun:
        target_response_language = resolve_response_language(idea_text, response_language)
        idea = IdeaArtifact(
            metadata=_metadata(domain_id, "idea"),
            text=idea_text,
            constraints=(
                *constraints,
                Constraint(name="target_response_language", value=target_response_language),
            ),
        )
        return self._harness.generate(idea)


def create_story_generation_service(
    provider: StructuredProvider | None = None,
) -> StoryGenerationService:
    selected_provider = provider if provider is not None else create_provider()
    selected_provider = recording_provider(selected_provider)
    metadata = selected_provider.metadata
    qwen_profile = metadata.provider == "ollama" and metadata.model == "qwen2.5:3b"
    prompt_loader = PromptLoader(variant="ollama-qwen2.5-3b" if qwen_profile else None)
    knowledge_loader = KnowledgeLoader()
    example_loader = ExampleLoader()
    registry = DomainRegistry(
        [
            StaticDomainPlugin(
                metadata=DomainMetadata(
                    domain_id=DEFAULT_DOMAIN_ID,
                    display_name="Short Film Story Development",
                    version="0.1.0",
                    description="Demo domain for short film story planning.",
                    tags=("story", "film", "demo"),
                ),
                resources=DomainResourceCatalog(
                    knowledge=(
                        DomainResource(
                            resource_id="short-film-placeholder-knowledge",
                            title="Short Film Knowledge Placeholder",
                            path=Path("domains/short-film/knowledge"),
                            description="Reserved for future short-film knowledge assets.",
                        ),
                    )
                ),
            )
        ]
    )
    harness = CreativeReasoningHarness(
        domains=registry,
        reasoning_layer=LLMReasoningLayer(selected_provider, prompt_loader),
        planning_layer=LLMPlanningLayer(
            selected_provider,
            prompt_loader,
            knowledge_loader,
            example_loader,
            compact_context=qwen_profile,
        ),
        # Compact critic trials broke intent/feedback pairing; retain its full prompt and context.
        evaluation_layer=LLMEvaluationLayer(
            selected_provider, PromptLoader() if qwen_profile else prompt_loader, knowledge_loader
        ),
    )
    return StoryGenerationService(harness)


def _metadata(domain_id: str, kind: ArtifactKind) -> ArtifactMetadata:
    return ArtifactMetadata(
        artifact_id=str(uuid4()),
        domain_id=domain_id,
        kind=kind,
        created_at=datetime.now(UTC),
    )


def _target_response_language(idea: IdeaArtifact) -> str:
    for constraint in idea.constraints:
        if constraint.name == "target_response_language":
            return constraint.value
    return _detect_response_language(idea.text)


def _detect_response_language(text: str) -> str:
    return resolve_response_language(text)


def _is_vietnamese_language(language: str) -> bool:
    return language.strip().lower() in {"vietnamese", "tiếng việt", "tieng viet", "vi"}


def _find_note(reasoning: ReasoningArtifact, label: str) -> str:
    for note in reasoning.notes:
        if note.label == label:
            return note.content
    return "A vague creative idea."


def _make_logline(idea_text: str) -> str:
    return (
        "When an unresolved situation starts closing in, one character must make a visible "
        f"choice that transforms the idea: {idea_text}"
    )


def _creator_input(
    idea_text: str,
    constraints: tuple[Constraint, ...],
    answers: tuple[tuple[str, str], ...] = (),
) -> str:
    return json.dumps(
        {
            "idea": idea_text,
            "constraints": [
                constraint.value
                for constraint in constraints
                if constraint.name != "target_response_language"
            ],
            "clarifications": [
                {"question": question, "answer": answer} for question, answer in answers
            ],
        },
        ensure_ascii=False,
    )


def _story_language_header(target_language: str) -> str:
    return (
        f"Target response language: {target_language}\n"
        "Write new narrative, explanations and questions in the target language, even when "
        "the brief uses another language. Keep author terms, names and verbatim source "
        "quotations in their original language. Preserve JSON field names in English.\n\n"
    )


def _idea_input(idea: IdeaArtifact) -> str:
    target_language = _target_response_language(idea)
    return (
        f"Domain ID: {idea.metadata.domain_id}\n\n"
        f"{_story_language_header(target_language)}"
        f"Creator brief (JSON data):\n"
        f"{_creator_input(idea.text, idea.constraints, idea.clarifications)}"
    )


def _reasoning_input(
    reasoning: ReasoningArtifact,
    knowledge: dict[str, object],
    examples: tuple[DomainExample, ...],
) -> str:
    notes = "\n".join(f"- {note.label}: {note.content}" for note in reasoning.notes)
    questions = "\n".join(f"- {question}" for question in reasoning.open_questions)
    target_language = _find_note(reasoning, "Target response language")
    return (
        f"{_story_language_header(target_language)}"
        f"Creator intent and decisions:\n{getattr(reasoning, 'creator_context', '')}\n\n"
        f"Reasoning notes:\n{notes}\n\n"
        f"Missing information / mentor questions:\n{questions or '- None'}\n\n"
        f"Short-film domain knowledge:\n{json.dumps(knowledge, ensure_ascii=False)}\n\n"
        f"Reusable domain examples:\n{json.dumps(_example_payloads(examples), ensure_ascii=False)}"
    )


def compact_qwen_planning_input(input_text: str) -> str:
    # Keep every author decision and AI note; encyclopedic references distract this small model.
    context, separator, _ = input_text.partition("\n\nShort-film domain knowledge:\n")
    return context if separator else input_text


def _example_payloads(examples: tuple[DomainExample, ...]) -> list[dict[str, object]]:
    return [
        {
            "source_id": example.source_id,
            "theme": example.theme,
            "genre": example.genre,
            "user_idea": example.user_idea,
            "example": example.payload,
        }
        for example in examples
    ]


def _structured_plan_sections(story_plan: _StructuredStoryPlanOutput) -> list[PlanSection]:
    section_specs = [
        (
            "Core idea",
            "State the short film's central promise.",
            story_plan.logline.text,
        ),
        (
            "Main character",
            "Define the protagonist and key character pressure.",
            _characters_text(story_plan.characters),
        ),
        (
            "Main conflict",
            "Describe the obstacle and stakes.",
            _conflict_text(story_plan.conflict),
        ),
        (
            "Beginning",
            "Set up the story world and first dramatic turn.",
            _beginning_text(story_plan.beginning),
        ),
        (
            "Middle",
            "Escalate pressure and reveal the emotional turn.",
            _middle_text(story_plan.middle),
        ),
        (
            "Ending",
            "Resolve the short film through a visible choice or image.",
            _ending_text(story_plan.ending),
        ),
        (
            "Theme",
            "Name the human idea underneath the plot.",
            story_plan.theme.statement,
        ),
        (
            "Visual Style",
            "Capture the visual approach and recurring motifs.",
            _visual_style_text(story_plan.visual_style),
        ),
        (
            "Tone",
            "Describe the intended emotional register.",
            story_plan.tone.description,
        ),
        (
            "Production Notes",
            "Keep the idea grounded for short-film production.",
            _production_notes_text(story_plan.production_notes),
        ),
    ]
    return [
        PlanSection(
            section_id=f"section-{index + 1}",
            title=title,
            purpose=purpose,
            content=content,
        )
        for index, (title, purpose, content) in enumerate(section_specs)
    ]


def _characters_text(characters: Characters) -> str:
    details = [characters.protagonist]
    if characters.supporting_characters:
        details.append(", ".join(characters.supporting_characters))
    if characters.antagonist_or_obstacle:
        details.append(characters.antagonist_or_obstacle)
    return " ".join(details)


def _conflict_text(conflict: Conflict) -> str:
    details = [conflict.external]
    if conflict.internal:
        details.append(conflict.internal)
    if conflict.stakes:
        details.append(conflict.stakes)
    return " ".join(details)


def _beginning_text(beginning: Beginning) -> str:
    if beginning.key_event:
        return f"{beginning.setup} {beginning.key_event}"
    return beginning.setup


def _middle_text(middle: Middle) -> str:
    if middle.turning_point:
        return f"{middle.escalation} {middle.turning_point}"
    return middle.escalation


def _ending_text(ending: Ending) -> str:
    if ending.final_image:
        return f"{ending.resolution} {ending.final_image}"
    return ending.resolution


def _visual_style_text(visual_style: VisualStyle) -> str:
    details: list[str] = []
    if visual_style.description:
        details.append(visual_style.description)
    if visual_style.visual_motifs:
        details.append(", ".join(visual_style.visual_motifs))
    return " ".join(details) or "Use simple, readable visual choices that support the emotion."


def _production_notes_text(production_notes: ProductionNotes) -> str:
    details = [production_notes.notes]
    if production_notes.locations:
        details.append(", ".join(production_notes.locations))
    if production_notes.cast_size:
        details.append(production_notes.cast_size)
    return " ".join(details)


def _planning_input(planning: PlanningArtifact) -> str:
    return json.dumps(
        {
            "title": getattr(planning, "title", None),
            "logline": getattr(planning, "logline", None),
            "sections": [
                {"title": section.title, "content": section.content}
                for section in planning.sections
            ],
        },
        ensure_ascii=False,
    )


def _feedback_language_header(target_language: str) -> str:
    return (
        f"Target response language: {target_language}\n"
        "Write explanations and new revision examples in the target language, even when the "
        "draft uses another language. Keep author terms, names, section anchors and verbatim "
        "quotations from the CURRENT draft in their original language. Newly invented examples "
        "are not quotations from the draft. Preserve JSON field names in English.\n\n"
    )


def _evaluation_input(planning: PlanningArtifact, rubric: object) -> str:
    target_language = getattr(planning, "target_response_language", "English")
    return (
        _feedback_language_header(target_language)
        + f"Creator intent and decisions:\n{getattr(planning, 'creator_context', '')}\n\n"
        f"Current draft (JSON data):\n{_planning_input(planning)}\n\n"
        f"Short-film story rubric:\n{json.dumps(rubric, ensure_ascii=False)}"
    )


def _evaluation_findings(
    output: _EvaluationOutput,
    target_language: str = "English",
) -> list[EvaluationFinding]:
    findings: list[EvaluationFinding] = []
    for criterion_id, score in output.rubric_scores.model_dump().items():
        findings.append(
            EvaluationFinding(
                criterion_id=criterion_id,
                message=_score_message(criterion_id, score, target_language),
                severity="info",
                score=score,
            )
        )
    for index, strength in enumerate(output.strengths, start=1):
        findings.append(
            EvaluationFinding(
                criterion_id=f"strength-{index}",
                message=strength,
                severity="info",
            )
        )
    for index, weakness in enumerate(output.weaknesses, start=1):
        findings.append(
            EvaluationFinding(
                criterion_id=f"weakness-{index}",
                message=weakness,
                severity="warning",
            )
        )
    for index, suggestion in enumerate(output.suggestions, start=1):
        findings.append(
            EvaluationFinding(
                criterion_id=f"suggestion-{index}",
                message=suggestion,
                severity="info",
            )
        )
    return findings


def _score_message(criterion_id: str, score: int, target_language: str) -> str:
    if _is_vietnamese_language(target_language):
        labels = {
            "story_clarity": "Độ rõ của câu chuyện",
            "character": "Nhân vật",
            "conflict": "Xung đột",
            "emotional_impact": "Tác động cảm xúc",
            "ending": "Kết thúc",
            "production_feasibility": "Tính khả thi sản xuất",
        }
        return f"{labels.get(criterion_id, criterion_id.replace('_', ' '))}: {score}/5."
    return f"{criterion_id.replace('_', ' ').title()} score: {score}/5."


def _expect_output(output: BaseModel, expected_type: type[OutputT]) -> OutputT:
    if not isinstance(output, expected_type):
        raise TypeError("Provider returned an unexpected structured response type.")
    return output
