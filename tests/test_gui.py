import copy
import json
import os
from pathlib import Path
import sys
import unittest

try:
    import tkinter as tk
except ImportError:
    tk = None

if tk is not None:
    from brante.gui import GREEN
from test_childhood import LOYALIST


ROOT = Path(__file__).resolve().parent.parent
HAS_DISPLAY = bool(os.environ.get('DISPLAY')) or sys.platform in ('win32', 'darwin')


@unittest.skipUnless(tk is not None and HAS_DISPLAY, 'GUI tests require Tkinter and a display')
class GuiTests(unittest.TestCase):
    def setUp(self):
        from brante.gui import BranteApp
        self.root = tk.Tk()
        self.addCleanup(self.root.destroy)
        data = json.loads((ROOT / 'data/childhood.json').read_text(encoding='utf-8'))
        self.app = BranteApp(self.root, data)
        self.root.update()

    def test_click_advances_event_and_highlights_delta(self):
        self.app.choice_buttons[0].invoke()
        self.root.update()
        self.assertEqual(self.app.game.current, 'hide_and_seek')
        self.assertEqual(self.app.event_title.cget('text'), 'Прятки')
        self.assertEqual(self.app.stat_values['Чуткость'].cget('text'), '1  (+1)')
        self.assertEqual(self.app.stat_values['Чуткость'].cget('fg'), GREEN)
        self.assertEqual(self.app.last_choice, 'Потянуться к ладони')

    def test_locked_choice_cannot_be_clicked_or_selected_with_shortcut(self):
        self.app.game.current = 'poems'
        self.app.render()
        self.root.update()
        self.assertEqual(str(self.app.choice_buttons[0].cget('state')), 'disabled')
        self.assertEqual(str(self.app.choice_buttons[1].cget('state')), 'disabled')
        self.assertEqual(str(self.app.choice_buttons[2].cget('state')), 'normal')
        before = copy.deepcopy(self.app.game.__dict__)
        self.app.choice_buttons[0].invoke()
        self.app.choose(0)
        self.assertEqual(before, self.app.game.__dict__)
        self.assertIn('Недоступно', self.app.status.cget('text'))

    def test_full_route_through_buttons_then_restart(self):
        while self.app.game.current:
            event = self.app.game.events[self.app.game.current]
            index = next(i for i, choice in enumerate(event['choices']) if choice['id'] == LOYALIST[event['id']])
            self.app.choice_buttons[index].invoke()
            self.root.update()
            self.assertLessEqual(len(self.app.game.history), 14)
        self.assertEqual(self.app.event_title.cget('text'), 'Детство завершено')
        self.assertEqual(self.app.game.stats['Решительность'], 5)
        self.assertEqual(self.app.game.stats['Чуткость'], 5)
        self.assertEqual(self.app.game.stats['Запас сил'], 0)
        self.assertEqual(self.app.choice_buttons, [])
        self.app.restart()
        self.root.update()
        self.assertEqual(self.app.game.current, 'birth')
        self.assertEqual(self.app.game.stats['Решительность'], 0)
        self.assertEqual(len(self.app.choice_buttons), 3)
        self.assertFalse(self.app.deltas)

    def test_number_shortcut_selects_choice(self):
        self.root.focus_force()
        self.root.update()
        self.root.event_generate('<KeyPress-2>')
        self.root.update()
        self.assertEqual(self.app.game.current, 'hide_and_seek')
        self.assertEqual(self.app.game.stats['Решительность'], 1)

    def test_small_window_scroll_keeps_last_choice_accessible(self):
        self.root.geometry('940x700')
        self.app.game.current = 'guest'
        self.app.render()
        self.root.update()
        self.app.scene.canvas.yview_moveto(1)
        self.root.update()
        button = self.app.choice_buttons[-1]
        canvas = self.app.scene.canvas
        self.assertGreaterEqual(button.winfo_rooty(), canvas.winfo_rooty())
        self.assertLessEqual(button.winfo_rooty() + button.winfo_height(), canvas.winfo_rooty() + canvas.winfo_height())

    def test_source_comments_are_not_in_game_widgets(self):
        self.app.game.current = 'poems'
        self.app.render()
        widgets = [self.root]
        texts = []
        while widgets:
            widget = widgets.pop()
            widgets.extend(widget.winfo_children())
            if isinstance(widget, (tk.Label, tk.Button)):
                texts.append(str(widget.cget('text')))
        text = '\n'.join(texts).lower()
        self.assertNotIn('ods', text)
        self.assertNotIn('источник', text)
        self.assertNotIn('примечание', text)


if __name__ == '__main__':
    unittest.main()
