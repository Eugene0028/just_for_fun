import argparse
import json
from pathlib import Path
import sys

from .engine import Game
from .presentation import format_effects


DEFAULT_DATA = Path(__file__).resolve().parent.parent / 'data/childhood.json'


def show_state(game):
    groups = game.data.get('stat_groups', {'Статы': list(game.stats)})
    for group, keys in groups.items():
        print(group + ': ' + ' · '.join(f"{key.removeprefix('Отношения: ')}: {game.stats[key]}" for key in keys))
    active = [key for key, value in game.flags.items() if value]
    print('Состояния: ' + (', '.join(active) or 'нет'))


def show_event(game):
    event = game.events[game.current]
    when = f" · {event['year']} год" if event.get('year') else ' · дополнительное событие'
    print('\n' + '=' * 64)
    print(event['title'] + when)
    show_state(game)
    if event.get('context'):
        print('\nСитуация: ' + event['context'])
    for i, choice in enumerate(event['choices'], 1):
        blocked = game.blockers(choice)
        print(f"\n{i}. {choice['label']}" + (' [недоступно]' if blocked else ''))
        requirements = choice['requirements']
        print('   Условия: ' + ('неизвестны' if requirements is None else
              '; '.join(game.describe_requirement(req) for req in requirements) or 'без условий'))
        print('   Последствия: ' + format_effects(choice['effects']))
        if blocked:
            print('   Не хватает: ' + '; '.join(blocked))


def main(argv=None):
    parser = argparse.ArgumentParser(description='Глава I «Детство»: графическая игра с запасным терминальным режимом')
    parser.add_argument('--data', type=Path, default=DEFAULT_DATA)
    parser.add_argument('--list-events', action='store_true', help='Показать события и число вариантов без запуска игры')
    parser.add_argument('--audit', action='store_true', help='Показать ограничения достоверности данных')
    parser.add_argument('--goal', action='append', default=[], help='Личная цель: название свершения; можно указать несколько')
    parser.add_argument('--cli', action='store_true', help='Запустить терминальный режим вместо окна')
    args = parser.parse_args(argv)
    try:
        game = Game(json.loads(args.data.read_text(encoding='utf-8')))
    except (OSError, ValueError, KeyError, TypeError) as error:
        parser.error(str(error))
    achievements = game.data.get('achievements', [])
    for goal in args.goal:
        if goal not in achievements:
            parser.error('Неизвестная цель. Доступны: ' + ', '.join(achievements))
    if args.audit:
        print('\n'.join(game.data.get('limitations', [])))
        print('Разбор расхождений: docs/sources.md')
        return 0
    if args.list_events:
        for event in game.events.values():
            suffix = ' [по достижению стата]' if event['id'] in {t['event'] for t in game.triggers} else ''
            print(f"{event['title']}: {len(event['choices'])} вариантов{suffix}")
        return 0
    if not game.events:
        print('Данные главы ещё не получены из источников.')
        return 0
    if not args.cli:
        try:
            from .gui import launch
        except ImportError:
            parser.exit(1, 'Для окна нужен Tkinter. На Debian/Ubuntu: sudo apt install python3-tk.\nТерминальный режим: python3 -m brante --cli\n')
        from tkinter import TclError
        try:
            launch(game.data, args.goal)
        except TclError as error:
            parser.exit(1, f'Не удалось открыть окно: {error}\nТерминальный режим: python3 -m brante --cli\n')
        return 0
    print(game.data.get('chapter', 'Игра'))
    print('Введите номер выбора. q — выход.')
    if args.goal:
        print('Твои цели: ' + ', '.join(args.goal))
    while game.current is not None:
        show_event(game)
        while True:
            try:
                answer = input('\nТвой выбор: ').strip().lower()
                if answer == 'q':
                    print('Прохождение прервано.')
                    return 0
                game.choose(int(answer) - 1)
                break
            except (ValueError, IndexError) as error:
                print('Выбор не принят:', error)
            except (EOFError, KeyboardInterrupt):
                print('\nПрохождение прервано.')
                return 0
    print('\n' + game.ending)
    show_state(game)
    print('\nСвершения:')
    for achievement in achievements:
        print(('  + ' if game.flags[achievement] else '  — ') + achievement)
    if args.goal:
        missing = [goal for goal in args.goal if not game.flags[goal]]
        print('Цели не достигнуты: ' + ', '.join(missing) if missing else 'Все твои цели достигнуты.')
    return 0


if __name__ == '__main__':
    sys.exit(main())
