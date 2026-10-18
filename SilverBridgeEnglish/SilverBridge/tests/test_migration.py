import sqlite3,tempfile,unittest
from pathlib import Path
from import_old_data import import_database
from community.storage import Storage
class MigrationTests(unittest.TestCase):
    def test_only_app_tables_import_and_existing_records_are_preserved(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);source=root/'old.sqlite3';target=root/'new.sqlite3'
            Storage(source)
            with sqlite3.connect(source) as conn:
                conn.execute('CREATE TABLE unrelated_private_notes (body TEXT)')
                conn.execute("INSERT INTO unrelated_private_notes VALUES ('must not transfer')")
                conn.execute("INSERT INTO tickets(category,body,status,created_at) VALUES ('手机操作','保留旧求助','pending','2026-10-18')")
            result=import_database(source,target)
            self.assertEqual(sum(result.values()),1)
            with sqlite3.connect(target) as conn:
                self.assertEqual(conn.execute('SELECT COUNT(*) FROM "'+'tickets'+'"').fetchone()[0],1)
                self.assertIsNone(conn.execute("SELECT name FROM sqlite_master WHERE name='unrelated_private_notes'").fetchone())
            with self.assertRaises(ValueError):import_database(source,target)
            with sqlite3.connect(source) as conn:self.assertEqual(conn.execute('SELECT COUNT(*) FROM unrelated_private_notes').fetchone()[0],1)
