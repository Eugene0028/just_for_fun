"""Small desktop interface using only Python's Tkinter."""

import tkinter as tk
from tkinter import font as tkfont

from .engine import Game
from .presentation import format_effects

BG = '#14191d'
PANEL = '#1c2429'
CARD = '#242e34'
BORDER = '#344149'
TEXT = '#eeeae2'
MUTED = '#9eabb2'
ACCENT = '#dfbd80'
GREEN = '#90cfaa'
RED = '#e7a39a'


class ScrollPane(tk.Frame):
    def __init__(self, parent, background=BG, **kwargs):
        super().__init__(parent, bg=background, **kwargs)
        self.canvas = tk.Canvas(self, bg=background, highlightthickness=0, bd=0)
        self.scrollbar = tk.Scrollbar(self, orient='vertical', command=self.canvas.yview,
                                      bg=PANEL, troughcolor=background, width=11)
        self.canvas.configure(yscrollcommand=self.scrollbar.set)
        self.canvas.pack(side='left', fill='both', expand=True)
        self.scrollbar.pack(side='right', fill='y')
        self.content = tk.Frame(self.canvas, bg=background)
        self.window = self.canvas.create_window(0, 0, window=self.content, anchor='nw')
        self.content.bind('<Configure>', lambda _: self.canvas.configure(scrollregion=self.canvas.bbox('all')))
        self.canvas.bind('<Configure>', lambda event: self.canvas.itemconfigure(self.window, width=event.width))

    def clear(self):
        for widget in self.content.winfo_children():
            widget.destroy()
        self.canvas.yview_moveto(0)

    def contains(self, widget):
        while widget is not None:
            if widget == self:
                return True
            widget = widget.master
        return False


class BranteApp:
    def __init__(self, root, data, goals=()):
        self.root = root
        self.data = data
        self.goals = tuple(goals)
        self.game = Game(data)
        self.last_choice = ''
        self.last_effects = ''
        self.deltas = {}
        self.choice_buttons = []
        self.stat_values = {}
        root.title('Бранте · Детство')
        root.geometry('1120x860')
        root.minsize(940, 700)
        root.configure(bg=BG)
        default = tkfont.nametofont('TkDefaultFont')
        self.font_family = default.actual('family')
        self.body_font = (self.font_family, 11)
        self.small_font = (self.font_family, 10)
        if tkfont.Font(root=root, font=self.body_font).measure('Детство') == 0:
            root.destroy()
            raise tk.TclError('Эта сборка Tk не отображает кириллицу. Используйте системный Python с Tkinter (на Linux: /usr/bin/python3 -m brante).')
        families = set(tkfont.families(root))
        self.title_family = next((name for name in ('Georgia', 'DejaVu Serif', 'Times New Roman') if name in families), self.font_family)
        root.option_add('*Font', self.body_font)

        header = tk.Frame(root, bg=BG)
        header.pack(fill='x', padx=28, pady=(23, 18))
        self.label(header, 'Б Р А Н Т Е', color=ACCENT, font=(self.font_family, 12, 'bold')).pack(side='left')
        self.label(header, 'Глава I  /  Детство', color=MUTED).pack(side='left', padx=24)
        self.button(header, 'Начать заново', self.restart).pack(side='right')
        tk.Frame(root, bg=BORDER, height=1).pack(fill='x', padx=28)

        body = tk.Frame(root, bg=BG)
        body.pack(fill='both', expand=True, padx=22, pady=18)
        body.grid_columnconfigure(1, weight=1)
        body.grid_rowconfigure(0, weight=1)
        self.sidebar = ScrollPane(body, background=PANEL, width=275)
        self.sidebar.grid(row=0, column=0, sticky='nsew', padx=(0, 24))
        self.sidebar.pack_propagate(False)
        self.scene = ScrollPane(body)
        self.scene.grid(row=0, column=1, sticky='nsew')
        self.status = self.label(root, 'Выбери решение мышью или клавишами 1–4.', color=MUTED, font=self.small_font)
        self.status.pack(fill='x', padx=28, pady=(0, 16))
        root.bind('<MouseWheel>', self._scroll)
        root.bind('<Button-4>', self._scroll)
        root.bind('<Button-5>', self._scroll)
        for number in range(1, 5):
            root.bind(str(number), lambda _, i=number - 1: self.choose(i))
        root.bind('<Control-r>', lambda _: self.restart())
        self.render()

    def label(self, parent, text, color=TEXT, font=None, background=None, **kwargs):
        return tk.Label(parent, text=text, fg=color, bg=background or parent.cget('bg'),
                        font=font or self.body_font, anchor='w', justify='left', **kwargs)

    def button(self, parent, text, command):
        return tk.Button(parent, text=text, command=command, bg=CARD, fg=TEXT,
                         activebackground=BORDER, activeforeground=TEXT, relief='flat',
                         bd=0, padx=15, pady=9, cursor='hand2', highlightthickness=1,
                         highlightbackground=BORDER, highlightcolor=ACCENT)

    def _scroll(self, event):
        target = self.root.winfo_containing(self.root.winfo_pointerx(), self.root.winfo_pointery())
        direction = -1 if getattr(event, 'num', None) == 4 else 1
        if getattr(event, 'delta', 0):
            direction = -1 if event.delta > 0 else 1
        for pane in (self.sidebar, self.scene):
            if target is not None and pane.contains(target):
                if pane.content.winfo_height() > pane.canvas.winfo_height():
                    pane.canvas.yview_scroll(direction * 3, 'units')
                return 'break'

    def restart(self):
        self.game = Game(self.data)
        self.last_choice = self.last_effects = ''
        self.deltas = {}
        self.render()
        self.status.configure(text='Новое прохождение. Выбери решение мышью или клавишами 1–4.', fg=MUTED)

    def choose(self, index):
        if self.game.current is None or not 0 <= index < len(self.choice_buttons):
            return
        choice = self.game.events[self.game.current]['choices'][index]
        blockers = self.game.blockers(choice)
        if blockers:
            self.status.configure(text='Недоступно: ' + '; '.join(blockers), fg=RED)
            return
        previous = dict(self.game.stats)
        self.last_choice = choice['label']
        self.last_effects = format_effects(choice['effects'])
        self.game.choose(index)
        self.deltas = {key: value - previous[key] for key, value in self.game.stats.items() if value != previous[key]}
        self.render()
        self.status.configure(text='Решение принято. Изменившиеся показатели выделены цветом.', fg=MUTED)

    def render_sidebar(self):
        self.sidebar.clear()
        self.stat_values = {}
        parent = self.sidebar.content
        for group, keys in self.data.get('stat_groups', {'Статы': list(self.game.stats)}).items():
            self.label(parent, group.upper(), color=ACCENT, font=(self.font_family, 9, 'bold')).pack(fill='x', padx=18, pady=(18, 8))
            for key in keys:
                row = tk.Frame(parent, bg=PANEL)
                row.pack(fill='x', padx=18, pady=5)
                name = key.removeprefix('Отношения: ')
                self.label(row, name, color=TEXT if group == 'Характер' else MUTED, font=self.small_font).pack(side='left')
                delta = self.deltas.get(key, 0)
                value = str(self.game.stats[key]) + (f'  ({delta:+d})' if delta else '')
                widget = self.label(row, value, color=GREEN if delta > 0 else RED if delta < 0 else TEXT,
                                    font=(self.font_family, 12, 'bold'))
                widget.pack(side='right')
                self.stat_values[key] = widget
        active = [key for key, value in self.game.flags.items() if value]
        self.label(parent, 'СОСТОЯНИЯ', color=ACCENT, font=(self.font_family, 9, 'bold')).pack(fill='x', padx=18, pady=(20, 8))
        self.label(parent, '\n'.join(active) if active else 'Пока нет', color=MUTED,
                   font=self.small_font, wraplength=235).pack(fill='x', padx=18, pady=(0, 20))

    def wrapped(self, parent, text, color=TEXT, font=None, **pack):
        widget = self.label(parent, text, color=color, font=font, wraplength=550)
        widget.pack(fill='x', **pack)
        widget.bind('<Configure>', lambda event: widget.configure(wraplength=max(100, event.width - 4)))
        return widget

    def render(self):
        self.render_sidebar()
        self.scene.clear()
        self.choice_buttons = []
        parent = self.scene.content
        if self.last_choice:
            previous = tk.Frame(parent, bg=BG)
            previous.pack(fill='x', pady=(0, 22))
            self.wrapped(previous, 'Последний выбор · ' + self.last_choice, color=ACCENT, font=self.small_font)
            self.wrapped(previous, self.last_effects, color=MUTED, font=self.small_font, pady=(4, 0))
        if self.game.current is None:
            self.event_title = self.wrapped(parent, 'Детство завершено', font=(self.title_family, 27))
            self.wrapped(parent, 'Впереди — отрочество. Пока здесь заканчивается наша история.', color=MUTED, pady=(12, 25))
            self.label(parent, 'ТВОИ СВЕРШЕНИЯ', color=ACCENT, font=(self.font_family, 10, 'bold')).pack(anchor='w', pady=(0, 12))
            for achievement in self.data.get('achievements', []):
                achieved = self.game.flags[achievement]
                self.wrapped(parent, ('✓  ' if achieved else '—  ') + achievement,
                             color=GREEN if achieved else MUTED, pady=7)
            if self.goals:
                missing = [goal for goal in self.goals if not self.game.flags[goal]]
                self.wrapped(parent, 'Цели не достигнуты: ' + ', '.join(missing) if missing else 'Все твои цели достигнуты.',
                             color=RED if missing else GREEN, pady=(24, 0))
            self.button(parent, 'Пройти ещё раз', self.restart).pack(anchor='w', pady=28)
            return
        event = self.game.events[self.game.current]
        date = str(event['year']) + ' год' if event.get('year') else 'Дополнительное событие'
        self.label(parent, date, color=ACCENT, font=self.small_font).pack(anchor='w', pady=(0, 8))
        self.event_title = self.wrapped(parent, event['title'], font=(self.title_family, 27))
        if event.get('context'):
            self.wrapped(parent, event['context'], color=MUTED, pady=(12, 25))
        self.label(parent, 'КАК ТЫ ПОСТУПИШЬ?', color=ACCENT, font=(self.font_family, 9, 'bold')).pack(anchor='w', pady=(0, 12))
        for index, choice in enumerate(event['choices']):
            blockers = self.game.blockers(choice)
            card = tk.Frame(parent, bg=CARD if not blockers else PANEL,
                            highlightbackground=BORDER, highlightthickness=1, padx=16, pady=12)
            card.pack(fill='x', pady=(0, 12))
            button = tk.Button(card, text=f"{index + 1}   {choice['label']}", command=lambda i=index: self.choose(i),
                               state='disabled' if blockers else 'normal', font=(self.font_family, 12, 'bold'),
                               bg=card.cget('bg'), fg=TEXT, disabledforeground=MUTED, activebackground=BORDER,
                               activeforeground=ACCENT, relief='flat', bd=0, anchor='w', justify='left',
                               cursor='arrow' if blockers else 'hand2', highlightthickness=1,
                               highlightbackground=card.cget('bg'), highlightcolor=ACCENT, padx=0, pady=4, wraplength=520)
            button.pack(fill='x')
            button.bind('<Configure>', lambda e, b=button: b.configure(wraplength=max(100, e.width - 8)))
            self.choice_buttons.append(button)
            conditions = choice['requirements']
            condition_text = ('Не хватает: ' + '; '.join(blockers)) if blockers else (
                'Условия: ' + '; '.join(self.game.describe_requirement(req) for req in conditions) if conditions else 'Без условий')
            self.wrapped(card, condition_text, color=RED if blockers else MUTED, font=self.small_font, pady=(5, 0))
            self.wrapped(card, format_effects(choice['effects']), color=MUTED if blockers else ACCENT,
                         font=self.small_font, pady=(7, 0))
            if not blockers:
                for widget in [card] + [child for child in card.winfo_children() if child != button]:
                    widget.configure(cursor='hand2')
                    widget.bind('<Button-1>', lambda _, i=index: self.choose(i))


def launch(data, goals=()):
    root = tk.Tk()
    BranteApp(root, data, goals)
    root.mainloop()
