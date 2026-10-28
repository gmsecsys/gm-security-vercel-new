from __future__ import annotations
import sys
from datetime import datetime
from app_fix import App
from app_modern import DB, DATA, self_test


def daily_backup_on_exit(app):
    try:
        backup_path = DATA / 'backups' / f"GM_BizFlow_{datetime.now():%Y-%m-%d}.db"
        DB.backup(backup_path)
    finally:
        app.destroy()


def main():
    if '--self-test' in sys.argv:
        return self_test()
    app = App()
    app.protocol('WM_DELETE_WINDOW', lambda: daily_backup_on_exit(app))
    app.mainloop()
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
