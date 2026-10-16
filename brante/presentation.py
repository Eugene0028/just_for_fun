"""Shared player-facing formatting; source commentary stays in documentation."""


def format_effects(effects):
    if effects is None:
        return 'неизвестны'
    parts = [f"{key.removeprefix('Отношения: ')} {delta:+d}" for key, delta in effects.get('stats', {}).items()]
    parts += [key if value is True else f'{key}: {value}' for key, value in effects.get('flags', {}).items()]
    return '; '.join(parts) or 'без изменений'
