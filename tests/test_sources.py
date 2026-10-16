import json
from pathlib import Path
import tempfile
import unittest
import zipfile

from tools.extract_sources import GuideParser, ods_childhood


class SourceTests(unittest.TestCase):
    def test_nested_ods_groups_and_repeated_empty_columns(self):
        xml = '''<office:document-content
        xmlns:office="urn:oasis:names:tc:opendocument:xmlns:office:1.0"
        xmlns:table="urn:oasis:names:tc:opendocument:xmlns:table:1.0"
        xmlns:text="urn:oasis:names:tc:opendocument:xmlns:text:1.0">
          <table:table table:name="Sheet1">
            <table:table-row><table:table-cell><text:p>Childhood</text:p></table:table-cell></table:table-row>
            <table:table-row-group table:display="false">
              <table:table-row><table:table-cell><text:p>Выбор</text:p></table:table-cell>
                <table:table-cell table:number-columns-repeated="2"/>
                <table:table-cell><text:p>-5 (0)</text:p></table:table-cell>
              </table:table-row>
            </table:table-row-group>
            <table:table-row><table:table-cell><text:p>Adolescence</text:p></table:table-cell></table:table-row>
            <table:table-row><table:table-cell><text:p>Не включать</text:p></table:table-cell></table:table-row>
          </table:table>
        </office:document-content>'''
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'sample.ods'
            with zipfile.ZipFile(path, 'w') as archive:
                archive.writestr('content.xml', xml)
            rows = ods_childhood(path)
        self.assertEqual(rows, [
            {'row': 1, 'cells': ['Childhood']},
            {'row': 2, 'cells': ['Выбор', '', '', '-5 (0)']},
        ])

    def test_html_sections_exclude_navigation_and_preserve_nested_text(self):
        html = '''<div>Меню</div><div class="subSection detailBox" id="42">
        <div class="subSectionTitle">Глава I. Детство</div>
        <div class="subSectionDesc">Рождение<br><b>Ладонь</b>
        <div>Чуткость +1</div></div></div><div>Комментарии</div>'''
        parser = GuideParser()
        parser.feed(html)
        self.assertEqual(len(parser.sections), 1)
        section = parser.sections[0]
        self.assertEqual(section['id'], '42')
        self.assertEqual(section['title'], 'Глава I. Детство')
        self.assertIn('Чуткость +1', section['text'])
        self.assertNotIn('Меню', section['text'])
        self.assertNotIn('Комментарии', section['text'])

    def test_saved_ods_has_starting_values_and_no_later_chapters(self):
        path = Path(__file__).resolve().parent.parent / 'data/sources/ods-childhood.json'
        rows = json.loads(path.read_text(encoding='utf-8'))
        self.assertEqual(next(row for row in rows if row['row'] == 3)['cells'][13:16], ['6', '5', '3'])
        self.assertTrue(any(row['cells'][0] == 'Fencing Lesson ' for row in rows))
        self.assertFalse(any(row['cells'][0] == 'Adolescence' for row in rows))


if __name__ == '__main__':
    unittest.main()
