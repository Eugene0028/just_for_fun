import copy
import unittest

from brante.engine import Game


def fixture():
    # Синтетические правила для проверки движка, не события из игры.
    return {
        "initial_state": {"stats": {"сила": 1}, "flags": {"допуск": False}},
        "start": "a",
        "events": [
            {"id": "a", "title": "Тест", "choices": [
                {"label": "Подготовиться", "requirements": [],
                 "effects": {"stats": {"сила": 2}, "flags": {"допуск": True}}, "next": "b"},
                {"label": "Неудача", "requirements": [], "effects": {},
                 "next": None, "ending": "Поражение"}]},
            {"id": "b", "title": "Проверка", "choices": [
                {"label": "Пройти", "requirements": [
                    {"kind": "stat_min", "key": "сила", "value": 3},
                    {"kind": "flag", "key": "допуск", "value": True}],
                 "effects": {"stats": {"сила": -3}}, "next": None, "ending": "Успех"}]}]}


class EngineTests(unittest.TestCase):
    def test_success_path(self):
        game = Game(fixture())
        game.choose(0)
        game.choose(0)
        self.assertIsNone(game.current)
        self.assertEqual(game.ending, "Успех")
        self.assertEqual(game.stats["сила"], 0)
        self.assertEqual(len(game.history), 2)

    def test_failure_is_reachable(self):
        game = Game(fixture())
        game.choose(1)
        self.assertEqual(game.ending, "Поражение")

    def test_locked_choice_does_not_mutate_state(self):
        game = Game(fixture())
        game.current = "b"
        original = copy.deepcopy(game.__dict__)
        with self.assertRaises(ValueError):
            game.choose(0)
        self.assertEqual(game.__dict__, original)

    def test_unknown_rules_block_choice(self):
        data = fixture()
        data["events"][0]["choices"][0]["effects"] = None
        game = Game(data)
        with self.assertRaises(ValueError):
            game.choose(0)

    def test_negative_index_cannot_select_last_choice(self):
        game = Game(fixture())
        with self.assertRaises(IndexError):
            game.choose(-1)

    def test_broken_transition_rejected(self):
        data = fixture()
        data["events"][0]["choices"][0]["next"] = "missing"
        with self.assertRaises(ValueError):
            Game(data)

    def test_maximum_and_false_flag(self):
        game = Game(fixture())
        choice = {"requirements": [
            {"kind": "stat_max", "key": "сила", "value": 1},
            {"kind": "flag", "key": "допуск", "value": False}], "effects": {}}
        self.assertEqual(game.blockers(choice), [])
        game.stats["сила"] = 2
        self.assertTrue(game.blockers(choice))


if __name__ == "__main__":
    unittest.main()
