"""What kind of material a scene needs, and therefore which providers to ask.

Before this, ``provider_routing`` scored every provider against one blob of scene
text using English keyword sets. On a Russian script nothing matched, every provider
scored the same, and the order collapsed to "whoever was registered first" - which is
how a scene about the McMurdo Dry Valleys was answered by a stock library rather than
by Wikimedia or NASA.

A scene is classified once, into a *source class*, and the class decides the provider
order. The class comes from the scene's visual brief when the author supplied one
(``source_class``), and otherwise from evidence the planner really has: the shot type,
the media kind, and a small bilingual glossary. When there is not enough evidence the
answer is ``generic_broll`` - never a confident guess.

Nothing here talks to a provider or ranks a candidate. It answers one question: given
this scene, in what order should providers be asked, and why.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

# --- Source classes ----------------------------------------------------------
# Every class below has a consumer in PROVIDER_PRIORITY. Do not add one without.
CLASS_EXACT_LOCATION = "exact_location"
CLASS_SATELLITE = "satellite_or_earth_observation"
CLASS_SCIENTIFIC_EQUIPMENT = "scientific_equipment"
CLASS_RESEARCH_ACTIVITY = "research_activity"
CLASS_SPECIFIC_OBJECT = "specific_object"
CLASS_ARCHIVE = "archive"
CLASS_GENERIC_BROLL = "generic_broll"
CLASS_DATA_INFOGRAPHIC = "data_infographic"
# A process no camera can honestly film: what happens inside a cell, a neuron, a
# molecule, a body. Owner decision 2026-08-20 (ADR 0026). It is not "the scene may be
# a drawing" - ``data_infographic`` already means that and is never answered by a
# search. This class *is* answered by a search; what changes is that a scientific
# animation stops being disqualified for being an animation.
CLASS_SCIENTIFIC_VISUALIZATION = "scientific_visualization"
CLASS_MANUAL_REQUIRED = "manual_required"

SOURCE_CLASSES = (
    CLASS_EXACT_LOCATION,
    CLASS_SATELLITE,
    CLASS_SCIENTIFIC_EQUIPMENT,
    CLASS_RESEARCH_ACTIVITY,
    CLASS_SPECIFIC_OBJECT,
    CLASS_ARCHIVE,
    CLASS_GENERIC_BROLL,
    CLASS_DATA_INFOGRAPHIC,
    CLASS_SCIENTIFIC_VISUALIZATION,
    CLASS_MANUAL_REQUIRED,
)

# Provider preference per class, most specific source first. A name that is not
# registered in this run is skipped, so an order may list providers that do not exist
# here - that is what makes the table readable rather than conditional.
#
# "local_library" is always first where it appears: it is the only source whose rights
# are already settled, which is a property of the library and not of the scene.
PROVIDER_PRIORITY: dict[str, list[str]] = {
    CLASS_EXACT_LOCATION: ["local_library", "nasa_images", "wikimedia", "internet_archive", "pexels", "pixabay"],
    CLASS_SATELLITE: ["local_library", "nasa_images", "wikimedia", "internet_archive", "pexels", "pixabay"],
    CLASS_SCIENTIFIC_EQUIPMENT: ["local_library", "wikimedia", "internet_archive", "nasa_images", "pexels", "pixabay"],
    CLASS_SPECIFIC_OBJECT: ["local_library", "wikimedia", "internet_archive", "nasa_images", "pexels", "pixabay"],
    CLASS_RESEARCH_ACTIVITY: ["local_library", "wikimedia", "internet_archive", "nasa_images", "pexels", "pixabay"],
    CLASS_ARCHIVE: ["local_library", "internet_archive", "wikimedia", "nasa_images", "pexels", "pixabay"],
    CLASS_GENERIC_BROLL: ["local_library", "pexels", "pixabay", "wikimedia", "internet_archive", "nasa_images"],
    # Not a search at all: the picture is drawn from the scene's own numbers.
    CLASS_DATA_INFOGRAPHIC: ["local_library"],
    # Scientific visualisation lives in curated collections before it lives on a
    # general stock site, so the order follows the material and not the class's novelty.
    CLASS_SCIENTIFIC_VISUALIZATION: [
        "local_library", "wikimedia", "internet_archive", "nasa_images", "pexels", "pixabay",
    ],
    CLASS_MANUAL_REQUIRED: [],
}

# Classes whose whole point is a specific real thing. A candidate that carries no
# provider metadata cannot be shown to be that thing, so these classes refuse it.
EXACTING_CLASSES = frozenset(
    {CLASS_EXACT_LOCATION, CLASS_SATELLITE, CLASS_SCIENTIFIC_EQUIPMENT, CLASS_SPECIFIC_OBJECT}
)

# Classes that must never be answered by a general stock library, whatever it returns.
NO_GENERIC_STOCK = frozenset({CLASS_DATA_INFOGRAPHIC, CLASS_MANUAL_REQUIRED})

# Classes whose provider list is exhaustive rather than merely preferred. Nothing
# outside PROVIDER_PRIORITY may be asked, however many providers happen to be
# registered - see the note in build_strategy.
RESTRICTED_TO_PREFERRED = frozenset({CLASS_DATA_INFOGRAPHIC, CLASS_MANUAL_REQUIRED})

_MANUAL_FALLBACK_PROVIDERS = ("envato_manual",)

# --- Evidence vocabulary -----------------------------------------------------
# Bilingual on purpose: the brief is written in English, the narration is not, and a
# classifier that only reads one of them is the bug this module exists to fix. These
# are recognition hints only - they never become a provider query.
# Subjects a camera cannot honestly point at: what happens below the resolution of
# sight, or inside a living body. Bilingual for the same reason as every vocabulary
# here - the brief is English and the narration is not - and read from the scene's
# *declared subject* only, never from its narration. A scene that merely mentions a
# hormone out loud is still whatever it shows.
_VISUALIZATION_TERMS = {
    "neuron", "neural", "synapse", "brain", "cell", "cells", "cellular",
    "molecule", "molecular", "dna", "protein", "bloodstream", "blood flow",
    "immune", "virus", "bacteria", "atom", "hormone", "metabolism", "nervous system",
    "нейрон", "нейронн", "синапс", "мозг", "клетк", "клеточн", "молекул", "днк", "белок",
    "кровоток", "кровообращ", "иммун", "вирус", "бактери", "атом", "гормон",
    "обмен веществ", "нервная систем",
}

_SATELLITE_TERMS = {
    "satellite", "orbit", "earth observation", "aerial view from space", "spaceborne",
    "спутник", "орбит", "из космоса", "космическ",
}
_LOCATION_TERMS = {
    "valley", "desert", "glacier", "antarctica", "arctic", "mountain range", "island",
    "continent", "landscape", "terrain",
    "антарктид", "долин", "пустын", "ледник", "материк", "ландшафт", "местност",
}
_EQUIPMENT_TERMS = {
    "spectrometer", "microscope", "laboratory", "instrument", "centrifuge", "telescope",
    "analyser", "analyzer", "equipment", "apparatus",
    "спектрометр", "микроскоп", "лаборатор", "прибор", "оборудован", "телескоп",
}
_RESEARCH_TERMS = {
    "researcher", "scientist", "expedition", "fieldwork", "sampling", "collecting samples",
    "field camp", "research station", "survey",
    "исследовател", "учён", "учен", "экспедиц", "отбор проб", "образц", "станци", "полев",
}
_ARCHIVE_TERMS = {
    "archival", "archive", "historical", "newsreel", "vintage footage",
    "архив", "историческ", "хроник",
}
_DATA_TERMS = {
    "infographic", "chart", "diagram", "percentage", "proportion", "cross-section",
    "инфографик", "диаграмм", "график", "процент", "разрез", "схем",
}


@dataclass
class SceneAssetStrategy:
    """The retrieval plan for one scene: what it needs and who to ask."""

    scene_id: str = ""
    source_class: str = CLASS_GENERIC_BROLL
    media_type: str = "video"
    provider_order: list[str] = field(default_factory=list)
    skipped_providers: dict[str, str] = field(default_factory=dict)
    reasons: dict[str, list[str]] = field(default_factory=dict)
    classification_reason: str = ""
    classified_from: str = "default"
    requires_provider_metadata: bool = False
    allows_generic_stock: bool = True

    def to_dict(self) -> dict[str, Any]:
        return {
            "scene_id": self.scene_id,
            "source_class": self.source_class,
            "media_type": self.media_type,
            "provider_order": list(self.provider_order),
            "skipped_providers": dict(self.skipped_providers),
            "reasons": {name: list(values) for name, values in self.reasons.items()},
            "classification_reason": self.classification_reason,
            "classified_from": self.classified_from,
            "requires_provider_metadata": self.requires_provider_metadata,
            "allows_generic_stock": self.allows_generic_stock,
        }


def classify_scene(scene: dict[str, Any]) -> tuple[str, str, str]:
    """Return ``(source_class, reason, classified_from)`` for one plan scene.

    An explicit ``source_class`` in the scene's visual brief always wins: it is the
    author saying what the shot is, which no amount of keyword matching can improve on.
    """
    brief = scene.get("visual_brief") if isinstance(scene.get("visual_brief"), dict) else {}
    declared = str(brief.get("source_class") or scene.get("source_class") or "").strip()
    if declared in SOURCE_CLASSES:
        return declared, "declared in visual brief", "visual_brief"

    media = _media_type(scene)
    if media in {"diagram", "animated_image"} or str(scene.get("fallback_type") or "") == "diagram":
        return CLASS_DATA_INFOGRAPHIC, "scene asks for a drawn figure, not footage", "media_type"

    # Read before the free-text cascade and from a *narrower* source than it. This
    # class relaxes the footage rule, so it may not be entered by a word the shot is
    # not about: the alarm-clock scene of the 2026-08-19 run says "гормон" in its
    # narration and shows a clock.
    if _has_any(_subject_text(scene), _VISUALIZATION_TERMS):
        return (
            CLASS_SCIENTIFIC_VISUALIZATION,
            "scene's subject is a process no camera can film",
            "glossary",
        )

    text = _evidence_text(scene)
    if _has_any(text, _DATA_TERMS) and _has_number(text):
        return CLASS_DATA_INFOGRAPHIC, "scene states a figure to be shown", "glossary"
    if _has_any(text, _SATELLITE_TERMS):
        return CLASS_SATELLITE, "scene names a view from orbit", "glossary"
    if _has_any(text, _EQUIPMENT_TERMS):
        return CLASS_SCIENTIFIC_EQUIPMENT, "scene names an instrument or a laboratory", "glossary"
    if _has_any(text, _ARCHIVE_TERMS):
        return CLASS_ARCHIVE, "scene names archival material", "glossary"
    if _has_any(text, _RESEARCH_TERMS):
        return CLASS_RESEARCH_ACTIVITY, "scene shows people doing research", "glossary"
    # A filled ``place`` is deliberately not evidence here. The field means "where it
    # happens" and is a stock-search phrase, so a semantic brief fills it with whatever
    # surrounds the subject - ``open ocean``, ``nature outdoors``, ``indoor glass wall``.
    # Treating it as a *named* place sent five of six scenes of the confirmed run
    # 2026-08-09_diagnostic-ru-semantic-live-2 to NASA and Wikimedia under a class that
    # also refuses any candidate without provider metadata. ``brief`` already refuses
    # ``place`` as an answer on its own for the same reason. Geography has to be named
    # for this class - either the author declared it above, or a glossary term says so.
    if _has_any(text, _LOCATION_TERMS):
        return CLASS_EXACT_LOCATION, "scene names geography", "glossary"
    return CLASS_GENERIC_BROLL, "no specific source evidence in the scene", "default"


def build_strategy(
    scene: dict[str, Any],
    *,
    available_providers: list[str] | None = None,
    provider_enabled: dict[str, bool] | None = None,
    policy_eligible: dict[str, bool] | None = None,
    capabilities: dict[str, dict[str, Any]] | None = None,
) -> SceneAssetStrategy:
    """Classify the scene, then order the providers that can actually serve it."""
    source_class, reason, classified_from = classify_scene(scene)
    media_type = _provider_media_type(scene)
    available = list(available_providers or [])
    enabled = provider_enabled or {}
    eligible = policy_eligible or {}
    caps = capabilities or {}

    preferred = PROVIDER_PRIORITY.get(source_class, PROVIDER_PRIORITY[CLASS_GENERIC_BROLL])
    ordered: list[str] = []
    skipped: dict[str, str] = {}
    reasons: dict[str, list[str]] = {}

    # Preferred order first, then anything else still available, so a newly registered
    # provider is used rather than silently dropped.
    #
    # Except for the restricted classes. Their priority list is not a preference, it is
    # the whole permitted set: a scene whose picture the project draws itself has no
    # business asking a photo archive. Appending "everything else available" here is
    # what sent the 54% statistic to Wikimedia, NASA and the Internet Archive in the
    # confirmed retest and brought back a photograph of Mars.
    ranked = [name for name in preferred if name in available]
    if source_class not in RESTRICTED_TO_PREFERRED:
        ranked += [name for name in available if name not in preferred and name not in _MANUAL_FALLBACK_PROVIDERS]
    else:
        for name in available:
            if name not in preferred and name not in _MANUAL_FALLBACK_PROVIDERS:
                skipped[name] = f"not_permitted_for_{source_class}"

    for name in ranked:
        if enabled.get(name, True) is False:
            skipped[name] = "disabled"
            continue
        if eligible.get(name, True) is False:
            skipped[name] = "policy_blocked"
            continue
        provider_caps = caps.get(name, {})
        supported = provider_caps.get("media_types")
        if supported and media_type not in supported:
            skipped[name] = "unsupported_media_type"
            continue
        if name in _GENERIC_STOCK and source_class in NO_GENERIC_STOCK:
            skipped[name] = f"generic_stock_not_allowed_for_{source_class}"
            continue
        ordered.append(name)
        reasons[name] = _provider_reasons(name, source_class, preferred)

    manual = [name for name in available if name in _MANUAL_FALLBACK_PROVIDERS and enabled.get(name, True) is not False]
    for name in manual:
        reasons[name] = ["manual_fallback_only"]

    return SceneAssetStrategy(
        scene_id=str(scene.get("scene_id") or ""),
        source_class=source_class,
        media_type=media_type,
        provider_order=ordered + manual,
        skipped_providers=skipped,
        reasons=reasons,
        classification_reason=reason,
        classified_from=classified_from,
        requires_provider_metadata=source_class in EXACTING_CLASSES,
        allows_generic_stock=source_class not in NO_GENERIC_STOCK,
    )


_GENERIC_STOCK = frozenset({"pexels", "pixabay", "unsplash"})


# Reason vocabulary that predates the strategy classes. Kept so the manifest and the
# review board stay readable across old and new projects, and so existing callers that
# assert on these strings keep working.
_LEGACY_REASONS: dict[tuple[str, str], str] = {
    ("nasa_images", CLASS_SATELLITE): "space_or_earth_observation",
    ("nasa_images", CLASS_EXACT_LOCATION): "space_or_earth_observation",
    ("internet_archive", CLASS_ARCHIVE): "historical_or_archival",
    ("wikimedia", CLASS_SCIENTIFIC_EQUIPMENT): "specific_or_rare_subject",
    ("wikimedia", CLASS_SPECIFIC_OBJECT): "specific_or_rare_subject",
    ("wikimedia", CLASS_EXACT_LOCATION): "specific_or_rare_subject",
    ("wikimedia", CLASS_RESEARCH_ACTIVITY): "reference_source_fallback",
    ("pexels", CLASS_GENERIC_BROLL): "generic_cinematic_broll",
    ("pixabay", CLASS_GENERIC_BROLL): "generic_cinematic_broll",
}


def _provider_reasons(provider: str, source_class: str, preferred: list[str]) -> list[str]:
    reasons: list[str] = []
    legacy = _LEGACY_REASONS.get((provider, source_class))
    if legacy:
        reasons.append(legacy)
    if provider == "local_library":
        return reasons + ["local_rights_already_settled"]
    if provider not in preferred:
        return reasons + [f"available_but_not_preferred_for_{source_class}"]
    if provider in _GENERIC_STOCK and source_class != CLASS_GENERIC_BROLL:
        return reasons + ["generic_stock_last_resort"]
    return reasons + [f"preferred_for_{source_class}", f"priority_{preferred.index(provider)}"]


def _media_type(scene: dict[str, Any]) -> str:
    return str(scene.get("visual_type") or "").strip().lower()


def _provider_media_type(scene: dict[str, Any]) -> str:
    """What a provider should be asked for. Drawn figures are still images to them."""
    return "image" if _media_type(scene) in {"image", "animated_image", "diagram"} else "video"


def _evidence_text(scene: dict[str, Any]) -> str:
    """Everything the scene says about itself, in whatever language it says it."""
    brief = scene.get("visual_brief") if isinstance(scene.get("visual_brief"), dict) else {}
    semantic = scene.get("semantic") if isinstance(scene.get("semantic"), dict) else {}
    pieces: list[str] = [
        str(brief.get("visual_description") or ""),
        str(brief.get("subject") or ""),
        str(brief.get("action") or ""),
        str(brief.get("place") or brief.get("location") or ""),
        " ".join(str(item) for item in (brief.get("exact_entities") or [])),
        " ".join(str(item) for item in (brief.get("must_include") or [])),
        str(scene.get("primary_query") or ""),
        " ".join(str(item) for item in (scene.get("alternative_queries") or [])),
        str(scene.get("visual_description") or ""),
        str(scene.get("visual_intent") or ""),
        str(scene.get("narration") or ""),
        " ".join(str(item) for item in (semantic.get("subject") or [])),
        " ".join(str(item) for item in (semantic.get("location") or [])),
        " ".join(str(item) for item in (semantic.get("environment") or [])),
    ]
    return " ".join(pieces).lower()


def _subject_text(scene: dict[str, Any]) -> str:
    """Only what the scene declared it is *about* - never its narration.

    The same two fields the topic anchor and the query ladder call the subject
    (``visual_brief.subject``/``exact_entities``), plus the semantic subject the
    planner derived from them. Everything else ``_evidence_text`` reads describes the
    shot or speaks the script aloud, and neither says what the frame is of.
    """

    brief = scene.get("visual_brief") if isinstance(scene.get("visual_brief"), dict) else {}
    semantic = scene.get("semantic") if isinstance(scene.get("semantic"), dict) else {}
    pieces = [
        str(brief.get("subject") or ""),
        " ".join(str(item) for item in (brief.get("exact_entities") or [])),
        " ".join(str(item) for item in (semantic.get("subject") or [])),
    ]
    return " ".join(pieces).lower()


def _has_any(text: str, terms: set[str]) -> bool:
    return any(term in text for term in terms)


def _has_number(text: str) -> bool:
    return any(character.isdigit() for character in text)


__all__ = [
    "CLASS_ARCHIVE",
    "CLASS_DATA_INFOGRAPHIC",
    "CLASS_EXACT_LOCATION",
    "CLASS_GENERIC_BROLL",
    "CLASS_MANUAL_REQUIRED",
    "CLASS_RESEARCH_ACTIVITY",
    "CLASS_SATELLITE",
    "CLASS_SCIENTIFIC_EQUIPMENT",
    "CLASS_SPECIFIC_OBJECT",
    "EXACTING_CLASSES",
    "NO_GENERIC_STOCK",
    "PROVIDER_PRIORITY",
    "RESTRICTED_TO_PREFERRED",
    "SOURCE_CLASSES",
    "SceneAssetStrategy",
    "build_strategy",
    "classify_scene",
]
