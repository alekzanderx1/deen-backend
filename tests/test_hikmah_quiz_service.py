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
    return query


def test_get_questions_for_page_returns_questions_with_correct_choice():
    db = Mock()
    page = SimpleNamespace(id=12)
    question = SimpleNamespace(
        id=100,
        lesson_content_id=12,
        prompt="Sample prompt",
        order_position=1,
        explanation="Sample explanation",
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
