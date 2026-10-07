"""Read-only Owner projections. No provider discovery or environment inspection."""
from dataclasses import asdict
from awesome_stock.academy import build_academy_library


def academy():
    return {
        'mode': 'static_knowledge',
        'learning_progress_saved': False,
        'documents': [asdict(item) for item in build_academy_library().documents],
    }


def settings(store):
    with store.connection() as db:
        username = db.execute('SELECT username FROM owner WHERE slot=1').fetchone()[0]
        schema_version = db.execute('PRAGMA user_version').fetchone()[0]
    return {
        'username': username,
        'mode': 'owner_local',
        'schema_version': schema_version,
        'data_directory': str(store.directory),
        'database_file': str(store.path),
        'backup_directory': str(store.directory / 'backups'),
        'backup_encrypted': False,
        'restore_to_new_directory_only': True,
        'external_connections': False,
    }
