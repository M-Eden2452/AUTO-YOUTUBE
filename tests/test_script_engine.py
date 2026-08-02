"""Stage Q1: the script engine, its providers and its validator.

The engine replaced a generator that built every video from six fixed phrases and
the duration table ``[3.5, 7.0, 10.0, 13.0, 10.0, 8.0]``. Two things therefore have
to be true at once and are pinned here:

- the old generator still produces exactly what it always did, byte for byte, when
  it is asked for by name (``legacy_template``);
- the new default (``deterministic_local``) does not reproduce that shape at all -
  scene count and scene length follow the source material.

No network (``tests.network_guard`` is installed package-wide), no paid API, no
TTS, no downloads, no render: every provider exercised here is offline, and the
LLM one is only ever driven through an injected mock.
"""

from __future__ import annotations

import json
import unittest

from src.content.script_engine import (
    DEFAULT_PROVIDER_ID,
    SCENE_ROLE_CTA,
    SCENE_ROLE_DEVELOPMENT,
    SCENE_ROLE_HOOK,
    SCENE_ROLE_PAYOFF,
    SCRIPT_SCHEMA_VERSION,
    SOURCE_NARRATION_TEXT,
    SOURCE_RESEARCH,
    SOURCE_TOPIC,
    SOURCE_USER_SCRIPT,
    ScriptConstraints,
    ScriptProviderInputError,
    ScriptProviderResponseError,
    ScriptProviderUnavailableError,
    ScriptRequest,
    ScriptResult,
    ScriptScene,
    from_legacy_script,
    generate_script,
    get_provider,
    list_capabilities,
    list_provider_ids,
    resolve_provider_id,
    to_legacy_script,
    validate_script,
)
from src.content.script_engine.legacy_format import infer_roles
from src.content.script_engine.providers.legacy_template import (
    EMOTIONS,
    TARGET_DURATIONS,
    LegacyTemplateScriptProvider,
)
from src.content.script_engine.providers.llm import LLMScriptProvider, build_prompt, parse_response

# A real article's worth of material: enough sentences that the deterministic
# provider has something to choose from.
ARTICLE = (
    "Почему вороны узнают лица людей и помнят их годами? "
    "Исследователи из Вашингтонского университета надевали одну и ту же маску и ловили птиц. "
    "Вороны запоминали эту маску и потом кричали на любого человека, который её носил. "
    "Реакция сохранялась больше пяти лет подряд, хотя птиц больше никто не трогал. "
    "Более того, птицы передавали информацию сородичам, которые сами никогда не попадали в ловушку. "
    "Это значит, что у ворон работает социальная передача знания о конкретной угрозе."
)


def _claims(count: int = 3, *, uncertain_last: bool = True) -> list[dict]:
    claims = [
        {
            "claim_id": f"claim_{index:03d}",
            "text": f"Утверждение номер {index} про птиц и маски.",
            "safe_for_script": True,
            "claim_type": "fact",
        }
        for index in range(1, count + 1)
    ]
    if uncertain_last and claims:
        claims[-1]["claim_type"] = "hypothesis"
    return claims


def _request(**overrides) -> ScriptRequest:
    base = {
        "source_kind": SOURCE_RESEARCH,
        "language": "ru",
        "topic": "Почему вороны узнают лица",
        "raw_text": ARTICLE,
        "constraints": ScriptConstraints(target_duration_sec=55.0),
    }
    base.update(overrides)
    return ScriptRequest(**base)


class LegacyTemplateRegressionTest(unittest.TestCase):
    """The previous generator, preserved exactly.

    GOLDEN is the literal output of ``src.news.script_generator.build_script`` as it
    stood at commit 3021b83, before the engine existed. It is not a re-derivation:
    it was captured by running that committed code.
    """

    GOLDEN = json.loads(
        r"""
{
    "title": "Почему вороны узнают лица",
    "hook": "Почему вороны узнают лица?",
    "language": "ru",
    "target_duration_sec": 55,
    "estimated_duration_sec": 51.5,
    "narration_text": "Почему вороны узнают лица?\nНаблюдение выглядит простым, но за ним стоит важная деталь: Утверждение номер 1 про птиц и маски.\nИсследователи связывают историю с проверяемыми фактами: Утверждение номер 2 про птиц и маски.\nНо это не доказанный факт: ученые предполагают, что Утверждение номер 3 про птиц и маски.\nГлавное здесь не эффектная картинка, а то, как меняется наше понимание темы: Почему вороны узнают лица\nИ пока появляются новые данные, самый интересный вопрос остается открытым: что мы упускаем в этой истории?",
    "description": "Короткий научный ролик: Почему вороны узнают лица",
    "source_claim_ids": ["claim_001", "claim_002", "claim_003"],
    "scenes": [
        {
            "scene_id": "scene_001",
            "start_sec": 0.0,
            "target_duration_sec": 3.5,
            "narration": "Почему вороны узнают лица?",
            "claim_ids": ["claim_001"],
            "visual_intent": "Почему вороны узнают лица?",
            "on_screen_text": "Почему вороны узнают лица?",
            "emotion": "intrigue"
        },
        {
            "scene_id": "scene_002",
            "start_sec": 3.5,
            "target_duration_sec": 7.0,
            "narration": "Наблюдение выглядит простым, но за ним стоит важная деталь: Утверждение номер 1 про птиц и маски.",
            "claim_ids": ["claim_002"],
            "visual_intent": "Наблюдение выглядит простым, но за ним стоит важная деталь: Утверждение номер 1 про птиц и маски.",
            "on_screen_text": "Наблюдение выглядит простым, но за",
            "emotion": "context"
        },
        {
            "scene_id": "scene_003",
            "start_sec": 10.5,
            "target_duration_sec": 10.0,
            "narration": "Исследователи связывают историю с проверяемыми фактами: Утверждение номер 2 про птиц и маски.",
            "claim_ids": ["claim_003"],
            "visual_intent": "Исследователи связывают историю с проверяемыми фактами: Утверждение номер 2 про птиц и маски.",
            "on_screen_text": "Исследователи связывают историю с проверяемыми",
            "emotion": "discovery"
        },
        {
            "scene_id": "scene_004",
            "start_sec": 20.5,
            "target_duration_sec": 13.0,
            "narration": "Но это не доказанный факт: ученые предполагают, что Утверждение номер 3 про птиц и маски.",
            "claim_ids": ["claim_003"],
            "visual_intent": "Но это не доказанный факт: ученые предполагают, что Утверждение номер 3 про птиц и маски.",
            "on_screen_text": "Но это не доказанный факт",
            "emotion": "explanation"
        },
        {
            "scene_id": "scene_005",
            "start_sec": 33.5,
            "target_duration_sec": 10.0,
            "narration": "Главное здесь не эффектная картинка, а то, как меняется наше понимание темы: Почему вороны узнают лица",
            "claim_ids": ["claim_003"],
            "visual_intent": "Главное здесь не эффектная картинка, а то, как меняется наше понимание темы: Почему вороны узнают лица",
            "on_screen_text": "Главное здесь не эффектная картинка,",
            "emotion": "detail"
        },
        {
            "scene_id": "scene_006",
            "start_sec": 43.5,
            "target_duration_sec": 8.0,
            "narration": "И пока появляются новые данные, самый интересный вопрос остается открытым: что мы упускаем в этой истории?",
            "claim_ids": ["claim_003"],
            "visual_intent": "И пока появляются новые данные, самый интересный вопрос остается открытым: что мы упускаем в этой истории?",
            "on_screen_text": "И пока появляются новые данные,",
            "emotion": "question"
        }
    ]
}
"""
    )

    def _legacy_script(self, request: ScriptRequest) -> dict:
        result = LegacyTemplateScriptProvider().generate(request)
        return to_legacy_script(result, target_duration_sec=55, include_engine_fields=False)

    def test_output_is_byte_for_byte_the_pre_engine_script(self) -> None:
        script = self._legacy_script(_request(claims=_claims(3), raw_text=""))
        self.assertEqual(
            json.dumps(script, ensure_ascii=False, sort_keys=False),
            json.dumps(self.GOLDEN, ensure_ascii=False, sort_keys=False),
        )

    def test_key_order_is_preserved(self) -> None:
        """json.dumps output depends on insertion order, so order is part of the contract."""
        script = self._legacy_script(_request(claims=_claims(3), raw_text=""))
        self.assertEqual(list(script), list(self.GOLDEN))
        self.assertEqual(list(script["scenes"][0]), list(self.GOLDEN["scenes"][0]))

    def test_fixed_table_and_emotions_are_unchanged(self) -> None:
        self.assertEqual(TARGET_DURATIONS, [3.5, 7.0, 10.0, 13.0, 10.0, 8.0])
        self.assertEqual(EMOTIONS, ["intrigue", "context", "discovery", "explanation", "detail", "question"])

    def test_always_six_scenes_regardless_of_material(self) -> None:
        for claim_count in (0, 1, 2, 6):
            with self.subTest(claims=claim_count):
                result = LegacyTemplateScriptProvider().generate(_request(claims=_claims(claim_count)))
                self.assertEqual(len(result.scenes), 6)
                self.assertEqual([scene.duration_sec for scene in result.scenes], TARGET_DURATIONS)

    def test_title_falls_back_to_the_old_constant_not_to_the_job_title(self) -> None:
        """Since stage B3 a job always carries a generated title; consulting it here
        would silently replace the constant the old generator used."""
        result = LegacyTemplateScriptProvider().generate(
            _request(topic="", title="Сгенерированный заголовок", claims=[])
        )
        self.assertEqual(result.title, "Научная новость")

    def test_unsafe_claims_are_dropped(self) -> None:
        claims = _claims(3)
        claims[1]["safe_for_script"] = False
        result = LegacyTemplateScriptProvider().generate(_request(claims=claims))
        self.assertEqual(result.source_claim_ids, ["claim_001", "claim_003"])


class DeterministicProviderTest(unittest.TestCase):
    """The new default: offline, free, reproducible, and not the fixed six."""

    def test_is_the_default_provider(self) -> None:
        self.assertEqual(DEFAULT_PROVIDER_ID, "deterministic_local")
        self.assertEqual(resolve_provider_id(_request()), "deterministic_local")

    def test_declares_itself_free_and_offline(self) -> None:
        capabilities = get_provider(DEFAULT_PROVIDER_ID).capabilities
        self.assertFalse(capabilities.requires_network)
        self.assertFalse(capabilities.requires_paid_api)
        self.assertTrue(capabilities.deterministic)

    def test_does_not_use_the_fixed_six_scene_shape(self) -> None:
        result = generate_script(_request()).result
        durations = [scene.duration_sec for scene in result.scenes]
        self.assertNotEqual(durations, TARGET_DURATIONS)
        self.assertGreater(len(set(durations)), 1, "scene lengths must follow the text, not a table")

    def test_scene_count_follows_the_material(self) -> None:
        """More distinct material, more scenes. Repeating the same text does not
        count - identical statements are de-duplicated on purpose."""
        extra = (
            "Отдельная группа наблюдала за воронами в городских парках Японии. "
            "Птицы там научились раскалывать орехи под колёсами автомобилей. "
            "Затем они дожидались красного сигнала светофора, чтобы забрать ядро. "
            "Похожее поведение независимо описали орнитологи в Германии."
        )
        short = generate_script(_request(raw_text=ARTICLE)).result
        long = generate_script(_request(raw_text=ARTICLE + " " + extra)).result
        self.assertGreater(len(long.scenes), len(short.scenes))

    def test_identical_sentences_are_not_repeated_as_scenes(self) -> None:
        duplicated = " ".join([ARTICLE] * 3)
        result = generate_script(_request(raw_text=duplicated)).result
        narrations = [scene.narration for scene in result.scenes]
        self.assertEqual(len(narrations), len(set(narrations)))

    def test_every_sentence_comes_from_the_source(self) -> None:
        """Nothing is invented: each narration must appear in the input material."""
        result = generate_script(_request()).result
        for scene in result.scenes:
            with self.subTest(scene=scene.scene_id):
                self.assertIn(scene.narration.strip(), ARTICLE)

    def test_is_reproducible(self) -> None:
        first = generate_script(_request()).result.to_dict()
        second = generate_script(_request()).result.to_dict()
        self.assertEqual(first, second)

    def test_structure_opens_with_hook_and_closes_with_payoff(self) -> None:
        result = generate_script(_request()).result
        self.assertEqual(result.scenes[0].role, SCENE_ROLE_HOOK)
        self.assertEqual(result.scenes[-1].role, SCENE_ROLE_PAYOFF)

    def test_cta_is_never_added_automatically(self) -> None:
        without = generate_script(_request()).result
        self.assertEqual(without.scenes_by_role(SCENE_ROLE_CTA), [])
        with_cta = generate_script(_request(include_cta=True, cta_text="Подпишитесь на канал.")).result
        self.assertEqual(with_cta.scenes[-1].role, SCENE_ROLE_CTA)
        self.assertEqual(with_cta.scenes[-1].narration, "Подпишитесь на канал.")

    def test_thin_input_falls_back_to_the_legacy_template_and_says_so(self) -> None:
        outcome = generate_script(_request(source_kind=SOURCE_TOPIC, raw_text="", claims=[]))
        self.assertEqual(outcome.provider_id, "legacy_template")
        self.assertTrue(outcome.used_fallback)
        self.assertTrue(any("insufficient_source_material" in warning for warning in outcome.result.warnings))

    def test_thin_input_can_be_made_an_error_instead(self) -> None:
        with self.assertRaises(ScriptProviderInputError) as caught:
            generate_script(
                _request(
                    source_kind=SOURCE_TOPIC,
                    raw_text="",
                    claims=[],
                    provider_options={"allow_legacy_fallback": False},
                )
            )
        self.assertEqual(caught.exception.code, "insufficient_source_material")
        self.assertIn("article", str(caught.exception).lower())
        self.assertIn("source text", str(caught.exception).lower())

    def test_no_scene_exceeds_the_per_scene_limit(self) -> None:
        limits = ScriptConstraints(target_duration_sec=55.0)
        result = generate_script(_request(raw_text=" ".join([ARTICLE] * 4))).result
        for scene in result.scenes:
            with self.subTest(scene=scene.scene_id):
                self.assertLessEqual(scene.duration_sec, limits.max_scene_duration_sec)


class UserSuppliedProviderTest(unittest.TestCase):
    """A finished script keeps the author's words."""

    SCRIPT = (
        "Вороны узнают человеческие лица и помнят обидчиков.\n\n"
        "Учёные надевали маску и ловили птиц, чтобы проверить эту память.\n\n"
        "Поэтому вороны предупреждают сородичей об опасном человеке."
    )

    def test_is_chosen_automatically_for_a_ready_script(self) -> None:
        self.assertEqual(resolve_provider_id(_request(source_kind=SOURCE_USER_SCRIPT)), "user_supplied")
        self.assertEqual(resolve_provider_id(_request(source_kind=SOURCE_NARRATION_TEXT)), "user_supplied")

    def test_blank_lines_become_scene_boundaries(self) -> None:
        result = generate_script(_request(source_kind=SOURCE_USER_SCRIPT, raw_text=self.SCRIPT)).result
        self.assertEqual(len(result.scenes), 3)
        self.assertEqual(
            [scene.narration for scene in result.scenes],
            [block.strip() for block in self.SCRIPT.split("\n\n")],
        )

    def test_not_one_word_is_rewritten(self) -> None:
        result = generate_script(_request(source_kind=SOURCE_USER_SCRIPT, raw_text=self.SCRIPT)).result
        spoken = " ".join(scene.narration for scene in result.scenes)
        for block in self.SCRIPT.split("\n\n"):
            self.assertIn(block.strip(), spoken)

    def test_narration_text_is_accepted_as_a_whole(self) -> None:
        result = generate_script(_request(source_kind=SOURCE_NARRATION_TEXT, raw_text=ARTICLE)).result
        self.assertTrue(result.scenes)
        for scene in result.scenes:
            self.assertIn(scene.narration.split(".")[0], ARTICLE)

    def test_explicit_scene_markers_are_honoured_and_stripped(self) -> None:
        text = "[hook] Первый вопрос про ворон и их память.\n\nСцена 2: Учёные ловили птиц в масках.\n\n[payoff] Значит знание передаётся."
        result = generate_script(_request(source_kind=SOURCE_USER_SCRIPT, raw_text=text)).result
        self.assertEqual([scene.role for scene in result.scenes], [SCENE_ROLE_HOOK, SCENE_ROLE_DEVELOPMENT, SCENE_ROLE_PAYOFF])
        self.assertTrue(result.scenes[0].narration.startswith("Первый вопрос"))
        self.assertTrue(result.scenes[1].narration.startswith("Учёные ловили"))

    def test_empty_text_is_a_clear_error(self) -> None:
        with self.assertRaises(ScriptProviderInputError) as caught:
            generate_script(_request(source_kind=SOURCE_USER_SCRIPT, raw_text="   "))
        self.assertIn("пуст", str(caught.exception))

    def test_roles_are_assigned_when_the_author_declared_none(self) -> None:
        result = generate_script(_request(source_kind=SOURCE_USER_SCRIPT, raw_text=self.SCRIPT)).result
        self.assertEqual(result.scenes[0].role, SCENE_ROLE_HOOK)
        self.assertEqual(result.scenes[-1].role, SCENE_ROLE_PAYOFF)


class LLMProviderTest(unittest.TestCase):
    """Interface only. Every call here goes through an injected mock."""

    ANSWER = {
        "title": "Вороны и человеческие лица",
        "description": "Как вороны запоминают тех, кто их обидел.",
        "scenes": [
            {"role": "hook", "narration": "Почему ворона помнит ваше лицо через пять лет?"},
            {"role": "development", "narration": "Учёные ловили птиц в одной и той же маске, а потом просто гуляли в ней."},
            {"role": "development", "narration": "Вороны кричали на маску, даже если сами никогда не попадали в ловушку."},
            {"role": "payoff", "narration": "Это значит, что птицы передают знание об угрозе друг другу."},
        ],
    }

    def _mock(self, payload=None, *, raw: str | None = None):
        calls: list[str] = []

        def completion(prompt: str, options: dict) -> str:
            calls.append(prompt)
            if raw is not None:
                return raw
            return json.dumps(payload if payload is not None else self.ANSWER, ensure_ascii=False)

        completion.calls = calls  # type: ignore[attr-defined]
        return completion

    def test_module_imports_nothing_that_can_reach_a_network(self) -> None:
        import src.content.script_engine.providers.llm as module

        source = module.__doc__ or ""
        self.assertIn("no network", source.lower())
        for forbidden in ("requests", "urllib", "httpx", "openai", "socket"):
            self.assertNotIn(forbidden, dir(module), f"{forbidden} must not be importable here")

    def test_declares_itself_paid_and_networked(self) -> None:
        capabilities = get_provider("llm").capabilities
        self.assertTrue(capabilities.requires_paid_api)
        self.assertTrue(capabilities.requires_network)
        self.assertEqual(capabilities.implementation_status, "planned")

    def test_is_never_the_default(self) -> None:
        self.assertNotEqual(DEFAULT_PROVIDER_ID, "llm")
        for source_kind in (SOURCE_TOPIC, SOURCE_RESEARCH, SOURCE_USER_SCRIPT, SOURCE_NARRATION_TEXT):
            with self.subTest(source_kind=source_kind):
                self.assertNotEqual(resolve_provider_id(_request(source_kind=source_kind)), "llm")

    def test_without_a_model_it_refuses_and_says_why(self) -> None:
        with self.assertRaises(ScriptProviderUnavailableError) as caught:
            generate_script(_request(provider_id="llm"))
        self.assertIn("не подключён", str(caught.exception))

    def test_without_approval_it_refuses_even_with_a_model(self) -> None:
        with self.assertRaises(ScriptProviderUnavailableError) as caught:
            generate_script(_request(), provider=LLMScriptProvider(self._mock(), approved=False))
        self.assertIn("подтверждения", str(caught.exception))

    def test_mocked_answer_produces_a_script(self) -> None:
        completion = self._mock()
        outcome = generate_script(
            _request(), provider=LLMScriptProvider(completion, approved=True, model_id="mock-model")
        )
        self.assertEqual(outcome.provider_id, "llm")
        self.assertEqual(len(outcome.result.scenes), 4)
        self.assertEqual(outcome.result.provider_version, "mock-model")
        self.assertEqual(len(completion.calls), 1)

    def test_durations_are_computed_not_taken_from_the_model(self) -> None:
        """A model must not be able to claim 3 seconds for a 40-word sentence."""
        payload = json.loads(json.dumps(self.ANSWER))
        payload["scenes"][0]["duration_sec"] = 99.0
        outcome = generate_script(
            _request(), provider=LLMScriptProvider(self._mock(payload), approved=True)
        )
        durations = [scene.duration_sec for scene in outcome.result.scenes]
        self.assertNotIn(99.0, durations)
        self.assertTrue(all(0 < duration <= 16.0 for duration in durations))

    def test_invalid_json_is_a_clear_error(self) -> None:
        with self.assertRaises(ScriptProviderResponseError) as caught:
            generate_script(_request(), provider=LLMScriptProvider(self._mock(raw="не json"), approved=True))
        self.assertIn("JSON", str(caught.exception))

    def test_answer_without_scenes_is_a_clear_error(self) -> None:
        with self.assertRaises(ScriptProviderResponseError) as caught:
            generate_script(_request(), provider=LLMScriptProvider(self._mock({"title": "x"}), approved=True))
        self.assertIn("нет сцен", str(caught.exception))

    def test_scene_without_narration_is_a_clear_error(self) -> None:
        payload = {"scenes": [{"role": "hook", "narration": ""}]}
        with self.assertRaises(ScriptProviderResponseError) as caught:
            generate_script(_request(), provider=LLMScriptProvider(self._mock(payload), approved=True))
        self.assertIn("без текста озвучки", str(caught.exception))

    def test_unknown_role_degrades_instead_of_failing(self) -> None:
        payload = json.loads(json.dumps(self.ANSWER))
        payload["scenes"][1]["role"] = "нечто"
        outcome = generate_script(_request(), provider=LLMScriptProvider(self._mock(payload), approved=True))
        self.assertEqual(outcome.result.scenes[1].role, SCENE_ROLE_DEVELOPMENT)

    def test_fenced_json_is_accepted(self) -> None:
        fenced = "```json\n" + json.dumps(self.ANSWER, ensure_ascii=False) + "\n```"
        outcome = generate_script(
            _request(), provider=LLMScriptProvider(self._mock(raw=fenced), approved=True)
        )
        self.assertEqual(len(outcome.result.scenes), 4)

    def test_prompt_forbids_inventing_facts_and_a_fixed_scene_count(self) -> None:
        prompt = build_prompt(_request())
        self.assertIn("Не выдумывай", prompt)
        self.assertIn("количество сцен определяется смыслом", prompt)

    def test_prompt_asks_for_no_cta_unless_requested(self) -> None:
        self.assertIn("НЕ добавляй", build_prompt(_request()))
        self.assertIn("призыв к действию", build_prompt(_request(include_cta=True)).lower())

    def test_parse_response_accepts_a_dict_without_a_round_trip(self) -> None:
        result = parse_response(self.ANSWER, _request())
        self.assertEqual(len(result.scenes), 4)


class ProviderFallbackTest(unittest.TestCase):
    """A remote provider's failure must not strand a run - loudly, never silently."""

    def test_no_fallback_by_default(self) -> None:
        with self.assertRaises(ScriptProviderUnavailableError):
            generate_script(_request(provider_id="llm"))

    def test_unusable_model_answer_falls_back_when_asked(self) -> None:
        outcome = generate_script(
            _request(),
            provider=LLMScriptProvider(lambda prompt, options: "мусор", approved=True),
            fallback_provider_id=DEFAULT_PROVIDER_ID,
        )
        self.assertTrue(outcome.result.scenes)
        self.assertEqual(outcome.result.metadata["fallback_reason"], "invalid_response")
        self.assertTrue(any("provider_fallback" in warning for warning in outcome.result.warnings))

    def test_unwired_model_falls_back_when_asked(self) -> None:
        outcome = generate_script(_request(provider_id="llm"), fallback_provider_id=DEFAULT_PROVIDER_ID)
        self.assertTrue(outcome.result.scenes)
        self.assertEqual(outcome.result.metadata["fallback_reason"], "provider_unavailable")
        self.assertTrue(outcome.used_fallback)

    def test_fallback_never_recurses_into_itself(self) -> None:
        with self.assertRaises(ScriptProviderUnavailableError):
            generate_script(_request(provider_id="llm"), fallback_provider_id="llm")


class RegistryTest(unittest.TestCase):
    def test_the_four_providers_are_registered(self) -> None:
        self.assertEqual(
            sorted(list_provider_ids()),
            ["deterministic_local", "legacy_template", "llm", "user_supplied"],
        )

    def test_only_free_offline_providers_may_be_default(self) -> None:
        capabilities = get_provider(DEFAULT_PROVIDER_ID).capabilities
        self.assertFalse(capabilities.requires_paid_api)
        self.assertFalse(capabilities.requires_network)

    def test_unknown_provider_names_the_available_ones(self) -> None:
        with self.assertRaises(ScriptProviderUnavailableError) as caught:
            get_provider("нет такого")
        self.assertIn("deterministic_local", str(caught.exception))

    def test_capabilities_are_serialisable(self) -> None:
        for capability in list_capabilities():
            with self.subTest(provider=capability.provider_id):
                json.dumps(capability.to_dict(), ensure_ascii=False)

    def test_explicit_request_wins_over_source_kind_default(self) -> None:
        self.assertEqual(
            resolve_provider_id(_request(source_kind=SOURCE_USER_SCRIPT, provider_id="legacy_template")),
            "legacy_template",
        )


class ValidationTest(unittest.TestCase):
    """Every check the validator is required to make."""

    def _scene(self, **overrides) -> ScriptScene:
        base = {
            "scene_id": "scene_001",
            "index": 1,
            "role": SCENE_ROLE_HOOK,
            "narration": "Почему вороны запоминают человеческие лица на годы?",
            "duration_sec": 5.0,
            "start_sec": 0.0,
        }
        base.update(overrides)
        return ScriptScene(**base)

    def _result(self, scenes: list[ScriptScene], **overrides) -> ScriptResult:
        base = {"scenes": scenes, "language": "ru", "target_duration_sec": 55.0}
        base.update(overrides)
        return ScriptResult(**base)

    def _codes(self, result: ScriptResult, **kwargs) -> list[str]:
        return validate_script(result, **kwargs).codes()

    def test_empty_script_is_an_error(self) -> None:
        validation = validate_script(self._result([]))
        self.assertIn("empty_script", validation.codes())
        self.assertFalse(validation.valid)

    def test_empty_narration_is_an_error(self) -> None:
        scenes = [self._scene(), self._scene(scene_id="scene_002", role=SCENE_ROLE_PAYOFF, narration="   ", start_sec=5.0)]
        self.assertIn("empty_narration", self._codes(self._result(scenes)))

    def test_verbatim_repetition_is_an_error(self) -> None:
        text = "Вороны запоминают лица людей на очень долгий срок."
        scenes = [
            self._scene(narration=text),
            self._scene(scene_id="scene_002", role=SCENE_ROLE_PAYOFF, narration=text, start_sec=5.0),
        ]
        self.assertIn("duplicate_scene", self._codes(self._result(scenes)))

    def test_near_repetition_is_a_warning(self) -> None:
        scenes = [
            self._scene(narration="Вороны запоминают лица людей на очень долгий срок."),
            self._scene(
                scene_id="scene_002",
                role=SCENE_ROLE_PAYOFF,
                narration="Вороны запоминают лица людей на очень долгий срок вообще.",
                start_sec=5.0,
            ),
        ]
        validation = validate_script(self._result(scenes))
        self.assertIn("near_duplicate_scene", validation.codes())
        self.assertEqual([issue.severity for issue in validation.issues if issue.code == "near_duplicate_scene"], ["warning"])

    def test_weak_hook_is_reported(self) -> None:
        scenes = [
            self._scene(narration="Ага."),
            self._scene(scene_id="scene_002", role=SCENE_ROLE_PAYOFF, narration="Поэтому это важно для науки.", start_sec=5.0),
        ]
        self.assertIn("weak_hook", self._codes(self._result(scenes)))

    def test_missing_hook_is_reported(self) -> None:
        scenes = [
            self._scene(role=SCENE_ROLE_DEVELOPMENT),
            self._scene(scene_id="scene_002", role=SCENE_ROLE_PAYOFF, narration="Поэтому это важно.", start_sec=5.0),
        ]
        self.assertIn("missing_hook", self._codes(self._result(scenes)))

    def test_missing_payoff_is_reported(self) -> None:
        scenes = [self._scene(), self._scene(scene_id="scene_002", role=SCENE_ROLE_DEVELOPMENT, narration="Развитие темы.", start_sec=5.0)]
        self.assertIn("missing_payoff", self._codes(self._result(scenes)))

    def test_overlong_scene_is_reported(self) -> None:
        scenes = [
            self._scene(duration_sec=45.0),
            self._scene(scene_id="scene_002", role=SCENE_ROLE_PAYOFF, narration="Поэтому это важно.", start_sec=45.0),
        ]
        codes = self._codes(self._result(scenes))
        self.assertIn("scene_too_long", codes)

    def test_scene_slightly_over_the_budget_is_only_a_warning(self) -> None:
        scenes = [
            self._scene(duration_sec=18.0),
            self._scene(scene_id="scene_002", role=SCENE_ROLE_PAYOFF, narration="Поэтому это важно.", start_sec=18.0),
        ]
        validation = validate_script(self._result(scenes))
        too_long = [issue for issue in validation.issues if issue.code == "scene_too_long"]
        self.assertEqual([issue.severity for issue in too_long], ["warning"])

    def test_non_positive_duration_is_an_error(self) -> None:
        for bad in (0.0, -3.0):
            with self.subTest(duration=bad):
                scenes = [
                    self._scene(duration_sec=bad),
                    self._scene(scene_id="scene_002", role=SCENE_ROLE_PAYOFF, narration="Поэтому это важно.", start_sec=1.0),
                ]
                self.assertIn("invalid_duration", self._codes(self._result(scenes)))

    def test_nan_duration_is_an_error(self) -> None:
        scenes = [
            self._scene(duration_sec=float("nan")),
            self._scene(scene_id="scene_002", role=SCENE_ROLE_PAYOFF, narration="Поэтому это важно.", start_sec=5.0),
        ]
        self.assertIn("invalid_duration", self._codes(self._result(scenes)))

    def test_scenes_out_of_order_are_an_error(self) -> None:
        scenes = [
            self._scene(start_sec=10.0),
            self._scene(scene_id="scene_002", role=SCENE_ROLE_PAYOFF, narration="Поэтому это важно.", start_sec=1.0),
        ]
        self.assertIn("invalid_duration", self._codes(self._result(scenes)))

    def test_cta_must_be_last(self) -> None:
        scenes = [
            self._scene(),
            self._scene(scene_id="scene_002", role=SCENE_ROLE_CTA, narration="Подпишитесь на канал.", start_sec=5.0),
            self._scene(scene_id="scene_003", role=SCENE_ROLE_PAYOFF, narration="Поэтому это важно.", start_sec=10.0),
        ]
        self.assertIn("cta_not_last", self._codes(self._result(scenes)))

    def test_language_mismatch_is_reported(self) -> None:
        scenes = [
            self._scene(narration="Why do crows remember human faces for years?"),
            self._scene(
                scene_id="scene_002",
                role=SCENE_ROLE_PAYOFF,
                narration="This means the knowledge is shared between birds.",
                start_sec=5.0,
            ),
        ]
        self.assertIn("language_mismatch", self._codes(self._result(scenes), expected_language="ru"))

    def test_template_filler_is_invalid_in_strict_mode(self) -> None:
        scenes = [
            self._scene(duration_sec=4.0),
            self._scene(
                scene_id="scene_002",
                index=2,
                role=SCENE_ROLE_PAYOFF,
                narration="This is placeholder material that must not pass strict validation.",
                duration_sec=5.0,
                start_sec=4.0,
            ),
        ]
        validation = validate_script(
            self._result(
                scenes,
                provider_id="legacy_template",
                metadata={
                    "fallback_provider": "legacy_template",
                    "fallback_reason": "insufficient_source_material",
                },
            )
        )

        self.assertIn("template_filler_in_strict_mode", validation.codes())
        self.assertFalse(validation.valid)
        self.assertEqual(validation.status, "failed")

    def test_a_good_script_passes_cleanly(self) -> None:
        scenes = [
            self._scene(duration_sec=4.0),
            self._scene(
                scene_id="scene_002",
                index=2,
                role=SCENE_ROLE_DEVELOPMENT,
                narration="Учёные ловили птиц в одной и той же маске несколько лет подряд.",
                duration_sec=5.0,
                start_sec=4.0,
                on_screen_text="Учёные ловили птиц",
            ),
            self._scene(
                scene_id="scene_003",
                index=3,
                role=SCENE_ROLE_PAYOFF,
                narration="Это значит, что вороны передают знание об угрозе сородичам.",
                duration_sec=5.0,
                start_sec=9.0,
                on_screen_text="Это значит вороны",
            ),
        ]
        validation = validate_script(
            self._result(scenes), constraints=ScriptConstraints(target_duration_sec=14.0)
        )
        self.assertTrue(validation.valid, validation.codes())
        self.assertEqual(validation.status, "passed")

    def test_warnings_never_block(self) -> None:
        scenes = [
            self._scene(duration_sec=1.0),
            self._scene(scene_id="scene_002", role=SCENE_ROLE_PAYOFF, narration="Поэтому это важно для науки.", duration_sec=1.0, start_sec=1.0),
        ]
        validation = validate_script(self._result(scenes))
        self.assertTrue(validation.warnings)
        self.assertTrue(validation.valid)
        self.assertEqual(validation.status, "needs_review")


class LegacyFormatTest(unittest.TestCase):
    """script.json is extended, never replaced."""

    PRE_ENGINE_SCRIPT = {
        "title": "Почему киты поют",
        "hook": "Почему киты поют в океане?",
        "language": "ru",
        "target_duration_sec": 55,
        "estimated_duration_sec": 51.5,
        "narration_text": "Почему киты поют в океане?\nЗвуки разносятся на сотни километров.",
        "description": "Короткий научный ролик",
        "source_claim_ids": ["claim_001"],
        "scenes": [
            {
                "scene_id": "scene_001",
                "start_sec": 0.0,
                "target_duration_sec": 3.5,
                "narration": "Почему киты поют в океане?",
                "claim_ids": ["claim_001"],
                "visual_intent": "кит под водой",
                "on_screen_text": "Почему киты поют",
                "emotion": "intrigue",
            },
            {
                "scene_id": "scene_002",
                "start_sec": 3.5,
                "target_duration_sec": 7.0,
                "narration": "Звуки разносятся на сотни километров.",
                "claim_ids": [],
                "visual_intent": "океан сверху",
                "on_screen_text": "Звуки разносятся",
                "emotion": "context",
            },
        ],
    }

    def test_a_pre_engine_script_is_read_without_migration(self) -> None:
        result = from_legacy_script(self.PRE_ENGINE_SCRIPT)
        self.assertEqual(len(result.scenes), 2)
        self.assertEqual(result.schema_version, 1)
        self.assertEqual(result.title, "Почему киты поют")
        self.assertEqual(result.scenes[0].duration_sec, 3.5)

    def test_roles_are_inferred_for_a_script_that_never_had_them(self) -> None:
        result = from_legacy_script(self.PRE_ENGINE_SCRIPT)
        self.assertEqual([scene.role for scene in result.scenes], [SCENE_ROLE_HOOK, SCENE_ROLE_PAYOFF])
        self.assertEqual(infer_roles(6), [SCENE_ROLE_HOOK] + [SCENE_ROLE_DEVELOPMENT] * 4 + [SCENE_ROLE_PAYOFF])
        self.assertEqual(infer_roles(0), [])

    def test_real_narration_timings_win_over_the_plan(self) -> None:
        """A resumed project is described by what was spoken, not by the estimate."""
        data = json.loads(json.dumps(self.PRE_ENGINE_SCRIPT))
        data["scenes"][0]["actual_duration_sec"] = 4.27
        self.assertEqual(from_legacy_script(data).scenes[0].duration_sec, 4.27)

    def test_new_scripts_keep_every_key_the_old_readers_use(self) -> None:
        script = generate_script(_request()).to_legacy_script(target_duration_sec=55)
        for key in self.PRE_ENGINE_SCRIPT:
            self.assertIn(key, script)
        for key in self.PRE_ENGINE_SCRIPT["scenes"][0]:
            self.assertIn(key, script["scenes"][0])

    def test_engine_fields_are_additive(self) -> None:
        script = generate_script(_request()).to_legacy_script(target_duration_sec=55)
        self.assertEqual(script["script_schema_version"], SCRIPT_SCHEMA_VERSION)
        self.assertEqual(script["script_provider"], "deterministic_local")
        self.assertEqual(script["scene_count"], len(script["scenes"]))

    def test_round_trip_preserves_scenes(self) -> None:
        original = generate_script(_request()).result
        restored = from_legacy_script(to_legacy_script(original, target_duration_sec=55))
        self.assertEqual(
            [(scene.scene_id, scene.role, scene.narration) for scene in original.scenes],
            [(scene.scene_id, scene.role, scene.narration) for scene in restored.scenes],
        )

    def test_target_duration_stays_the_jobs_number(self) -> None:
        """The job's requested length and the sum of scene lengths are different things."""
        script = generate_script(_request()).to_legacy_script(target_duration_sec=55)
        self.assertEqual(script["target_duration_sec"], 55)
        self.assertNotEqual(script["estimated_duration_sec"], 55)

    def test_a_script_json_is_serialisable(self) -> None:
        script = generate_script(_request()).to_legacy_script(target_duration_sec=55)
        json.loads(json.dumps(script, ensure_ascii=False))


if __name__ == "__main__":
    unittest.main()
