from aidebot.lessons import GLOSSARY, LESSON_PATHS, QUIZZES, get_lesson, glossary_lookup, path_size


def test_every_path_has_multiple_lessons():
    for key in LESSON_PATHS:
        assert path_size(key) >= 5


def test_get_lesson_respects_bounds():
    assert get_lesson("discord", 1) is not None
    assert get_lesson("discord", 999) is None
    assert get_lesson("unknown", 1) is None


def test_each_quiz_has_valid_correct_index():
    for questions in QUIZZES.values():
        for question in questions:
            assert len(question.options) >= 2
            assert 0 <= question.correct < len(question.options)
            assert question.explanation


def test_glossary_exact_and_partial_lookup():
    assert glossary_lookup("intent") == GLOSSARY["intent"]
    assert glossary_lookup("fail") is not None
    assert glossary_lookup("terme-qui-nexiste-pas") is None


def test_core_learning_topics_have_quizzes():
    for key in ("discord", "serveur", "permissions", "bot"):
        assert key in LESSON_PATHS
        assert key in QUIZZES
