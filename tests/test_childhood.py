import json
from pathlib import Path
import random
import subprocess
import sys
import unittest

from brante.engine import Game


ROOT = Path(__file__).resolve().parent.parent
DATA = json.loads((ROOT / 'data/childhood.json').read_text(encoding='utf-8'))


# Choices and final personality values transcribed independently from guides.
LOYALIST = {
    'birth': 'fist', 'hide_and_seek': 'home', 'descent': 'repeat',
    'suffering': 'explain', 'poems': 'write', 'newborn': 'anger',
    'soldiers': 'truth', 'fathers_sword': 'learn', 'intrusion': 'rescue',
    'guest': 'greet', 'kaleidoscope': 'look', 'sweets': 'confess',
    'ant_farm': 'mother', 'sacrament': 'submit',
}
DEATH_ROUTE = {
    'birth': 'shadow', 'hide_and_seek': 'home', 'descent': 'distort',
    'suffering': 'accept', 'poems': 'comfort', 'newborn': 'hug',
    'soldiers': 'truth', 'intrusion': 'strike', 'fathers_sword': 'learn',
    'guest': 'greet', 'kaleidoscope': 'look', 'sweets': 'tease', 'sacrament': 'head',
}
OPTIMAL_STATS = {
    'birth': 'palm', 'hide_and_seek': 'home', 'descent': 'repeat',
    'suffering': 'deny', 'poems': 'complain', 'newborn': 'father',
    'soldiers': 'truth', 'fathers_sword': 'learn', 'intrusion': 'rescue',
    'guest': 'leave', 'ant_farm': 'alone', 'kaleidoscope': 'look',
    'sweets': 'confess', 'sacrament': 'head',
}


def play(route):
    game = Game(DATA)
    while game.current:
        choices = game.events[game.current]['choices']
        wanted = route[game.current]
        index = next(i for i, choice in enumerate(choices) if choice['id'] == wanted)
        game.choose(index)
        if len(game.history) > 14:
            raise AssertionError('Cycle in childhood')
    return game


class ChildhoodTests(unittest.TestCase):
    def test_honor_guide_final_stats_and_event_order(self):
        # Guide 3040501163, Chapter I: 5 determination, 5 perception, 0 willpower.
        game = play(LOYALIST)
        self.assertEqual([game.stats[k] for k in ('Решительность', 'Чуткость', 'Запас сил')], [5, 5, 0])
        self.assertEqual(game.stats['Смерти'], 0)
        events = [event for event, _ in game.history]
        self.assertEqual(events[7], 'fathers_sword')
        self.assertEqual(events[-2], 'ant_farm')

    def test_death_route_matches_detailed_guide(self):
        # Guide 2909473230 explicitly gives 6 / 1 / 5 and one death.
        game = play(DEATH_ROUTE)
        self.assertEqual([game.stats[k] for k in ('Решительность', 'Чуткость', 'Запас сил', 'Смерти')], [6, 1, 5, 1])
        self.assertTrue(game.flags['По ту сторону'])
        self.assertTrue(game.flags['Урок фехтования'])
        self.assertFalse(game.flags['Причастие дворянина'])
        events = [event for event, _ in game.history]
        self.assertEqual(events.index('fathers_sword'), events.index('intrusion') + 1)
        self.assertNotIn('ant_farm', events)

    def test_optimal_stats_guide_and_early_ant_farm(self):
        # English guide 2530169551 explicitly gives 6P / 6D / 0W.
        game = play(OPTIMAL_STATS)
        self.assertEqual([game.stats[k] for k in ('Решительность', 'Чуткость', 'Запас сил')], [6, 6, 0])
        self.assertTrue(game.flags['Озарение'])
        events = [event for event, _ in game.history]
        self.assertEqual(events.index('ant_farm'), events.index('guest') + 1)

    def test_gratitude_does_not_mean_positive_relationship(self):
        game = Game(DATA)
        hug = game.events['newborn']['choices'][3]
        game.stats['Отношения: Лидия Бранте'] = 10
        self.assertTrue(game.blockers(hug))
        game.flags['Лидия Бранте: благодарность'] = True
        self.assertFalse(game.blockers(hug))

    def test_guest_requires_perception_or_gratitude(self):
        game = Game(DATA)
        choice = game.events['guest']['choices'][3]
        self.assertTrue(game.blockers(choice))
        game.flags['Роберт Бранте: благодарность'] = True
        self.assertFalse(game.blockers(choice))
        game.flags['Роберт Бранте: благодарность'] = False
        game.stats['Чуткость'] = 4
        self.assertFalse(game.blockers(choice))

    def test_zero_willpower_is_enough_even_when_cost_is_ten(self):
        game = Game(DATA)
        choice = game.events['fathers_sword']['choices'][1]
        self.assertFalse(game.blockers(choice))
        game.stats['Запас сил'] = -1
        self.assertTrue(game.blockers(choice))

    def test_fourty_four_choices_are_reachable_and_no_dead_ends(self):
        rng = random.Random(1825)
        covered = set()
        all_choices = {(e['id'], c['id']) for e in DATA['events'] for c in e['choices']}
        for _ in range(100):
            game = Game(DATA)
            while game.current:
                event_id = game.current
                choices = game.events[event_id]['choices']
                available = [i for i, choice in enumerate(choices) if not game.blockers(choice)]
                self.assertTrue(available, event_id)
                index = rng.choice(available)
                covered.add((event_id, choices[index]['id']))
                game.choose(index)
                self.assertLessEqual(len(game.history), 14)
            ids = [event_id for event_id, _ in game.history]
            self.assertEqual(len(ids), len(set(ids)), 'One-off events repeated')
            if covered == all_choices:
                break
        self.assertEqual(len(all_choices), 44)
        self.assertEqual(covered, all_choices)

    def test_every_event_and_choice_has_resolvable_sources(self):
        sources = {source['id'] for source in DATA['sources']}
        for event in DATA['events']:
            for item in [event] + event['choices']:
                self.assertTrue(item['source'])
                for reference in item['source']:
                    self.assertIn(reference['source'], sources)

    def test_terminal_loyalist_playthrough_and_unmet_personal_goal(self):
        game = play(LOYALIST)
        answers = '\n'.join(str(index + 1) for _, index in game.history) + '\n'
        result = subprocess.run(
            [sys.executable, '-m', 'brante', '--goal', 'Причастие дворянина'],
            cwd=ROOT, input=answers, capture_output=True, text=True,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('Глава I завершена', result.stdout)
        self.assertIn('Решительность: 5', result.stdout)
        self.assertIn('Цели не достигнуты: Причастие дворянина', result.stdout)
        self.assertNotIn('Выбор не принят', result.stdout)


if __name__ == '__main__':
    unittest.main()
