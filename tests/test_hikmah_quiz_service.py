from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import Mock

import services.hikmah_quiz_service as quiz_service_module
from services.hikmah_quiz_service import HikmahQuizService, process_quiz_submission_background


def _build_query(result=None, first_result=None):
    query = Mock()
    query.filter.return_value = query
    query.order_by.return_value = query
    query.all.return_value = result if result is not None else []
    query.first.return_value = first_result
    query.delete.return_value = 1
    return query


def _valid_choices_payload():
    return [
        {"choice_key": "A", "choice_text": "First", "order_position": 1, "is_correct": True},
        {"choice_key": "B", "choice_text": "Second", "order_position": 2, "is_correct": False},
    ]


# ---------------------
# Learner-facing methods
# ---------------------
def test_get_questions_for_page_returns_questions_with_correct_choice():
    db = Mock()
    page = SimpleNamespace(id=12)
    question = SimpleNamespace(
        id=100,
        lesson_content_id=12,
        prompt="Sample prompt",
        order_position=1,
        explanation="Sample explanation",
        is_active=True,
        tags=["topic"],
    )
    choice_a = SimpleNamespace(id=200, question_id=100, choice_key="A", choice_text="A text", order_position=1, is_correct=True)
    choice_b = SimpleNamespace(id=201, question_id=100, choice_key="B", choice_text="B text", order_position=2, is_correct=False)

    db.get.return_value = page
    db.query.side_effect = [
        _build_query(result=[question]),
        _build_query(result=[choice_a, choice_b]),
    ]

    service = HikmahQuizService(db)
    result = service.get_questions_for_page(12)

    assert result["lesson_content_id"] == 12
    assert len(result["questions"]) == 1
    assert result["questions"][0]["id"] == 100
    assert result["questions"][0]["correct_choice_id"] == 200
    assert len(result["questions"][0]["choices"]) == 2


def test_get_questions_for_page_raises_when_page_missing():
    db = Mock()
    db.get.return_value = None

    service = HikmahQuizService(db)

    try:
        service.get_questions_for_page(88)
        assert False, "Expected LookupError"
    except LookupError:
        assert True


# -----------------
# Authoring CRUD API
# -----------------
def test_create_question_success(monkeypatch):
    db = Mock()
    db.get.return_value = SimpleNamespace(id=12)

    added_objects = []

    def add_side_effect(obj):
        added_objects.append(obj)

    def flush_side_effect():
        for obj in added_objects:
            if getattr(obj, "question_id", None) is None and getattr(obj, "id", None) is None:
                obj.id = 501

    db.add.side_effect = add_side_effect
    db.flush.side_effect = flush_side_effect

    service = HikmahQuizService(db)
    monkeypatch.setattr(
        service,
        "get_question_for_page",
        lambda lesson_content_id, question_id: {
            "id": question_id,
            "lesson_content_id": lesson_content_id,
            "prompt": "Q",
            "order_position": 1,
            "choices": [],
            "correct_choice_id": 1,
            "explanation": None,
            "tags": None,
            "is_active": True,
        },
    )

    payload = {
        "prompt": "Question prompt",
        "explanation": "Explanation",
        "tags": ["tag1"],
        "order_position": 1,
        "is_active": True,
        "choices": _valid_choices_payload(),
    }

    result = service.create_question(12, payload)

    assert result["id"] == 501
    assert result["lesson_content_id"] == 12
    assert db.commit.call_count == 1
    # 1 question + 2 choices
    assert len(added_objects) == 3


def test_create_question_raises_for_invalid_correct_choice_count():
    db = Mock()
    db.get.return_value = SimpleNamespace(id=12)

    service = HikmahQuizService(db)

    payload = {
        "prompt": "Question prompt",
        "choices": [
            {"choice_key": "A", "choice_text": "One", "is_correct": True},
            {"choice_key": "B", "choice_text": "Two", "is_correct": True},
        ],
    }

    try:
        service.create_question(12, payload)
        assert False, "Expected ValueError"
    except ValueError as exc:
        assert "Exactly one choice" in str(exc)


def test_list_questions_for_page_admin_passes_include_inactive(monkeypatch):
    db = Mock()
    service = HikmahQuizService(db)

    captured = {"include_inactive": None}

    def fake_list_models(lesson_content_id, include_inactive):
        captured["include_inactive"] = include_inactive
        return []

    monkeypatch.setattr(service, "_list_questions_for_page_models", fake_list_models)
    monkeypatch.setattr(service, "_serialize_questions", lambda questions, include_admin_fields: [])

    service.list_questions_for_page_admin(lesson_content_id=12, include_inactive=True)

    assert captured["include_inactive"] is True


def test_replace_question_rejects_when_attempts_exist():
    db = Mock()
    db.get.return_value = SimpleNamespace(id=12)

    question = SimpleNamespace(
        id=100,
        lesson_content_id=12,
        prompt="Old",
        explanation=None,
        tags=None,
        order_position=1,
        is_active=True,
    )
    existing_attempt = SimpleNamespace(id=1)

    db.query.side_effect = [
        _build_query(first_result=question),
        _build_query(first_result=existing_attempt),
    ]

    service = HikmahQuizService(db)

    payload = {
        "prompt": "New prompt",
        "explanation": None,
        "tags": ["tag"],
        "order_position": 2,
        "is_active": True,
        "choices": _valid_choices_payload(),
    }

    try:
        service.replace_question(12, 100, payload)
        assert False, "Expected ValueError"
    except ValueError as exc:
        assert "already has attempts" in str(exc)


def test_patch_question_updates_metadata(monkeypatch):
    db = Mock()
    db.get.return_value = SimpleNamespace(id=12)

    question = SimpleNamespace(
        id=100,
        lesson_content_id=12,
        prompt="Old",
        explanation="Old explanation",
        tags=["old"],
        order_position=1,
        is_active=True,
    )

    db.query.side_effect = [_build_query(first_result=question)]

    service = HikmahQuizService(db)
    monkeypatch.setattr(
        service,
        "get_question_for_page",
        lambda lesson_content_id, question_id: {"id": question_id, "lesson_content_id": lesson_content_id},
    )

    result = service.patch_question(12, 100, {"prompt": "New", "is_active": False})

    assert result["id"] == 100
    assert question.prompt == "New"
    assert question.is_active is False
    assert question.explanation == "Old explanation"
    assert db.commit.call_count == 1


def test_delete_question_hard_delete_commits():
    db = Mock()
    db.get.return_value = SimpleNamespace(id=12)

    question = SimpleNamespace(id=100, lesson_content_id=12)
    db.query.side_effect = [_build_query(first_result=question)]

    service = HikmahQuizService(db)
    service.delete_question(12, 100)

    assert db.delete.call_count == 1
    assert db.commit.call_count == 1


# -----------------------------
# Async submit + memory behavior
# -----------------------------
def test_process_submission_correct_answer_persists_attempt_without_memory_trigger(monkeypatch):
    db = Mock()
    page = SimpleNamespace(id=12, lesson_id=300)
    question = SimpleNamespace(id=100, lesson_content_id=12, tags=["topic-1"], prompt="Prompt")
    selected_choice = SimpleNamespace(id=200, question_id=100, choice_key="A", choice_text="A", is_correct=True)
    correct_choice = SimpleNamespace(id=200, question_id=100, choice_key="A", choice_text="A", is_correct=True)

    db.get.return_value = page
    db.query.side_effect = [
        _build_query(first_result=question),
        _build_query(first_result=selected_choice),
        _build_query(first_result=correct_choice),
    ]

    run_called = {"count": 0}

    def fake_run(coro):
        run_called["count"] += 1
        coro.close()

    monkeypatch.setattr(quiz_service_module.asyncio, "run", fake_run)

    service = HikmahQuizService(db)
    service.process_submission(
        lesson_content_id=12,
        user_id="user-1",
        question_id=100,
        selected_choice_id=200,
        answered_at=datetime.now(timezone.utc),
    )

    assert db.add.call_count == 1
    assert db.commit.call_count == 1
    assert run_called["count"] == 0


def test_process_submission_incorrect_answer_triggers_memory(monkeypatch):
    db = Mock()
    page = SimpleNamespace(id=12, lesson_id=300)
    lesson = SimpleNamespace(id=300, tags=["imamate"])
    question = SimpleNamespace(id=100, lesson_content_id=12, tags=["wilayah"], prompt="Prompt")
    selected_choice = SimpleNamespace(id=201, question_id=100, choice_key="B", choice_text="B", is_correct=False)
    correct_choice = SimpleNamespace(id=200, question_id=100, choice_key="A", choice_text="A", is_correct=True)

    db.get.side_effect = [page, lesson]
    db.query.side_effect = [
        _build_query(first_result=question),
        _build_query(first_result=selected_choice),
        _build_query(first_result=correct_choice),
    ]

    run_called = {"count": 0}

    def fake_run(coro):
        run_called["count"] += 1
        coro.close()

    monkeypatch.setattr(quiz_service_module.asyncio, "run", fake_run)

    service = HikmahQuizService(db)
    service.process_submission(
        lesson_content_id=12,
        user_id="user-1",
        question_id=100,
        selected_choice_id=201,
        answered_at=datetime.now(timezone.utc),
    )

    assert db.add.call_count == 1
    assert db.commit.call_count == 1
    assert run_called["count"] == 1


def test_process_quiz_submission_background_closes_session(monkeypatch):
    fake_db = Mock()
    fake_service = Mock()

    monkeypatch.setattr(quiz_service_module, "SessionLocal", lambda: fake_db)
    monkeypatch.setattr(quiz_service_module, "HikmahQuizService", lambda db: fake_service)

    process_quiz_submission_background(
        lesson_content_id=22,
        user_id="u-1",
        question_id=9,
        selected_choice_id=11,
        answered_at=None,
    )

    assert fake_service.process_submission.call_count == 1
    assert fake_db.close.call_count == 1
