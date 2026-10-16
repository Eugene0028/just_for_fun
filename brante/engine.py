"""Explicit conditions, one-off threshold events, no invented endings."""


class Game:
    def __init__(self, data):
        self.data = data
        self.stats = dict(data['initial_state']['stats'])
        self.flags = dict(data['initial_state']['flags'])
        self.events = {event['id']: event for event in data['events']}
        if len(self.events) != len(data['events']):
            raise ValueError('Повторяющиеся идентификаторы событий')
        self.triggers = data.get('triggers', [])
        self.current = data['start']
        self.ending = 'Глава I завершена. Продолжение в прототип не включено.'
        self.history = []
        self._triggered = set()
        self._resume = None
        self._validate()

    def _validate_requirements(self, requirements):
        if requirements is None:
            return
        for requirement in requirements:
            kind = requirement['kind']
            if kind == 'any':
                if not requirement['options']:
                    raise ValueError('Пустое условие ИЛИ')
                for option in requirement['options']:
                    self._validate_requirements([option])
            elif kind in ('stat_min', 'stat_max'):
                if requirement['key'] not in self.stats:
                    raise ValueError(f"Неизвестная характеристика: {requirement['key']}")
            elif kind == 'flag':
                if requirement['key'] not in self.flags:
                    raise ValueError(f"Неизвестное состояние: {requirement['key']}")
            else:
                raise ValueError(f'Неизвестный тип условия: {kind}')

    def _validate(self):
        if self.current is not None and self.current not in self.events:
            raise ValueError('Начальное событие отсутствует')
        targets = [trigger['event'] for trigger in self.triggers]
        if len(set(targets)) != len(targets):
            raise ValueError('Повторяющееся срабатывающее событие')
        for trigger in self.triggers:
            if trigger['event'] not in self.events:
                raise ValueError('Срабатывающее событие отсутствует')
            self._validate_requirements(trigger['requirements'])
        for event in self.events.values():
            if not event['choices']:
                raise ValueError(f"У события нет вариантов: {event['id']}")
            for choice in event['choices']:
                target = choice['next']
                if target == '$resume':
                    if event['id'] not in targets:
                        raise ValueError('Возврат допустим только для срабатывающего события')
                elif target is not None and target not in self.events:
                    raise ValueError(f'Неизвестное событие: {target}')
                self._validate_requirements(choice['requirements'])
                for key in (choice['effects'] or {}).get('stats', {}):
                    if key not in self.stats:
                        raise ValueError(f'Неизвестная характеристика: {key}')
                for key in (choice['effects'] or {}).get('flags', {}):
                    if key not in self.flags:
                        raise ValueError(f'Неизвестное состояние: {key}')

    def _satisfied(self, requirement):
        kind = requirement['kind']
        if kind == 'any':
            return any(self._satisfied(option) for option in requirement['options'])
        key, value = requirement['key'], requirement['value']
        if kind == 'stat_min':
            return self.stats[key] >= value
        if kind == 'stat_max':
            return self.stats[key] <= value
        if kind == 'flag':
            return self.flags.get(key) == value
        raise ValueError(f'Неизвестный тип условия: {kind}')

    @staticmethod
    def describe_requirement(requirement):
        kind = requirement['kind']
        if kind == 'any':
            return '(' + ' ИЛИ '.join(Game.describe_requirement(option) for option in requirement['options']) + ')'
        key, value = requirement['key'], requirement['value']
        if kind == 'flag':
            return key if value is True else f'{key}: {value}'
        return f"{key} {'≥' if kind == 'stat_min' else '≤'} {value}"

    def blockers(self, choice):
        if choice['requirements'] is None or choice['effects'] is None:
            return ['условия или последствия не подтверждены источником']
        return [self.describe_requirement(req) for req in choice['requirements'] if not self._satisfied(req)]

    def choose(self, index):
        if self.current is None:
            raise ValueError('Глава завершена')
        choices = self.events[self.current]['choices']
        if index < 0 or index >= len(choices):
            raise IndexError('Введите номер варианта из списка')
        choice = choices[index]
        reasons = self.blockers(choice)
        if reasons:
            raise ValueError('; '.join(reasons))
        for key, delta in choice['effects'].get('stats', {}).items():
            self.stats[key] += delta
        self.flags.update(choice['effects'].get('flags', {}))
        self.history.append((self.current, index))
        candidate = self._resume if choice['next'] == '$resume' else choice['next']
        self.current = candidate
        if candidate is None:
            self.ending = choice.get('ending', self.ending)
            return
        # Interrupt the main sequence; never append events after the final choice.
        for trigger in self.triggers:
            if trigger['event'] not in self._triggered and all(self._satisfied(req) for req in trigger['requirements']):
                self._triggered.add(trigger['event'])
                self._resume = candidate
                self.current = trigger['event']
                break
