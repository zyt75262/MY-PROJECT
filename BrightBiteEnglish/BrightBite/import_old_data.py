"""Import only this application's records from an old database, without overwriting."""
import argparse
import sqlite3
from pathlib import Path
from community.storage import Storage

TABLES = ('plans', 'favorites')

def import_database(source: Path, target: Path) -> dict:
    source=Path(source).resolve();target=Path(target).resolve()
    if not source.is_file():raise ValueError('The old database file was not found.')
    if source==target:raise ValueError('Select the old database, not this application\'s current database.')
    with sqlite3.connect(source.as_uri()+'?mode=ro',uri=True) as old:
        available={r[0] for r in old.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        if not any(t in available for t in TABLES):raise ValueError('This file contains no supported tables for this application.')
        store=Storage(target)
        with store.connection(write=True) as new:
            if any(new.execute(f'SELECT COUNT(*) FROM "{t}"').fetchone()[0] for t in TABLES):
                raise ValueError('Import canceled: the destination already contains records. Nothing was overwritten. Import before adding new records.')
            counts={}
            for table in TABLES:
                if table not in available:continue
                columns=[r[1] for r in new.execute(f'PRAGMA table_info("{table}")')]
                fields=','.join('"'+c.replace('"','""')+'"' for c in columns)
                rows=old.execute(f'SELECT {fields} FROM "{table}"').fetchall()
                placeholders=','.join('?' for _ in columns)
                new.executemany(f'INSERT INTO "{table}" ({fields}) VALUES ({placeholders})',rows)
                counts[table]=len(rows)
    return counts

def main():
    parser=argparse.ArgumentParser(description='Import this application\'s records without changing the source file.')
    parser.add_argument('source',nargs='?',type=Path)
    parser.add_argument('--data-dir',type=Path,default=Path(__file__).resolve().parent/'local_data')
    args=parser.parse_args()
    source=args.source
    if source is None:
        try:
            import tkinter as tk
            from tkinter import filedialog
            window=tk.Tk();window.withdraw()
            selected=filedialog.askopenfilename(title='Select community.sqlite3 from the old local_data folder',filetypes=[('SQLite database','*.sqlite3'),('All files','*.*')])
            window.destroy()
            if not selected:print('No file selected. Import canceled.');return 0
            source=Path(selected)
        except Exception:
            print('Specify the source on the command line: python import_old_data.py "OLD_FOLDER/community.sqlite3"');return 1
    try:
        result=import_database(source,args.data_dir/'community.sqlite3')
    except (ValueError,sqlite3.Error,OSError) as error:
        print('Import failed: '+str(error));return 1
    print('Import complete: '+str(result)+'. The source database was not changed.')
    return 0

if __name__=='__main__':raise SystemExit(main())
