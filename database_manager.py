import aiosqlite
from typing import List, Dict, Any, Optional
from security_manager import SecurityManager
import os


class DatabaseManager:
    DB_FILE = os.path.join(os.path.dirname(
        os.path.abspath(__file__)), "lobbies.db")
    _security = SecurityManager()

    async def initialize(self):
        async with aiosqlite.connect(self.DB_FILE) as db:
            await db.execute('''
                CREATE TABLE IF NOT EXISTS Lobbies (
                    hash TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    is_encrypted BOOLEAN,
                    is_public BOOLEAN,
                    password_hash TEXT
                )
            ''')
            await db.commit()
            print("Database initialized.")

    def _encrypt_string(self, lobby_hash: str, string_value: str, password: str) -> str:
        key_bytes = password.encode('utf-8')
        hash_p_value = lobby_hash+string_value
        encrypted_value = self._security.encrypt_data(hash_p_value, key_bytes)
        return encrypted_value

    def _decrypt_string(self, encrypted_string: str, password: str) -> str:
        key_bytes = password.encode('utf-8')
        decrypted_value = self._security.decrypt_data(
            encrypted_string, key_bytes)
        return decrypted_value

    async def create_lobby(self, user_id: str, name: str, is_encrypted: bool = False, is_public: bool = False, password: Optional[str] = None) -> str:
        if is_encrypted and not password:
            raise ValueError("An encrypted lobby must have a password.")

        lobby_hash = self._security.generate_lobby_hash(name)
        password_hash = self._security.hash_password(
            password) if password else None

        table_name = f"lobby_{lobby_hash}"
        if is_encrypted:
            assert password is not None
            table_name = self._encrypt_string(lobby_hash, "", password)

        async with aiosqlite.connect(self.DB_FILE) as db:
            async with db.cursor() as cursor:
                await cursor.execute(
                    "INSERT INTO Lobbies (hash, name, is_encrypted, is_public, password_hash) VALUES (?, ?, ?, ?, ?)",
                    (lobby_hash, name, is_encrypted, is_public, password_hash)
                )

                await cursor.execute(f'''
                    CREATE TABLE "{table_name}" (
                        user_id TEXT(20) PRIMARY KEY,
                        total_seconds INTEGER DEFAULT 0,
                        is_admin BOOLEAN DEFAULT FALSE,
                        is_running BOOLEAN DEFAULT FALSE,
                        last_entry TEXT
                    )
                ''')

                effective_user_id = user_id
                if is_encrypted:
                    assert password is not None
                    effective_user_id = self._encrypt_string(
                        lobby_hash, user_id, password)

                await cursor.execute(
                    f'INSERT INTO "{table_name}" (user_id, is_admin) VALUES (?, ?)',
                    (effective_user_id, True)
                )

            await db.commit()

        print(f"Successfully created lobby '{name}' with hash: {lobby_hash}")
        return lobby_hash

    async def lobby_table_exists(self, lobby_hash: str, password: Optional[str] = None) -> bool:
        lobby_table_hash = await self.get_lobby_table_hash(lobby_hash, password)
        if lobby_table_hash is None:
            return False
        async with aiosqlite.connect(self.DB_FILE) as db:
            cursor = await db.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (lobby_table_hash,))
            result = await cursor.fetchone()
            return result is not None

    async def lobby_exists(self, lobby_hash: str) -> bool:
        async with aiosqlite.connect(self.DB_FILE) as db:
            cursor = await db.execute("SELECT 1 FROM Lobbies WHERE hash=?", (lobby_hash,))
            result = await cursor.fetchone()
            return result is not None

    async def get_lobby_table_hash(self, lobby_hash: str, password: Optional[str] = None) -> Optional[str]:
        is_enc = await self.is_encrypted(lobby_hash)
        if password is None and is_enc:
            return None
        elif password is None:
            return f"lobby_{lobby_hash}"

        return self._encrypt_string(lobby_hash, "", password)

    async def is_public(self, lobby_hash: str) -> bool:
        if not await self.lobby_exists(lobby_hash):
            return False
        async with aiosqlite.connect(self.DB_FILE) as db:
            cursor = await db.execute("SELECT is_public FROM Lobbies WHERE hash=?", (lobby_hash,))
            result = await cursor.fetchone()
            return bool(result[0]) if result else False

    async def is_encrypted(self, lobby_hash: str) -> bool:
        if not await self.lobby_exists(lobby_hash):
            return False
        async with aiosqlite.connect(self.DB_FILE) as db:
            cursor = await db.execute("SELECT is_encrypted FROM Lobbies WHERE hash=?", (lobby_hash,))
            result = await cursor.fetchone()
            return bool(result[0]) if result else False

    async def find_lobby_table_name(self, lobby_hash: str, password: Optional[str]) -> Optional[str]:
        if not await self.lobby_exists(lobby_hash):
            print(f"Lobby with hash '{lobby_hash}' does not exist.")
            return None

        lobby_is_encrypted = await self.is_encrypted(lobby_hash)
        if lobby_is_encrypted and not password:
            print(f"Lobby with hash '{lobby_hash}' is locked.")
            return None

        return await self.get_lobby_table_hash(lobby_hash, password)

    async def is_admin(self, user_id: str, lobby_hash: str, password: Optional[str] = None) -> bool:
        if user_id == "admin":
            return True

        lobby_is_encrypted = await self.is_encrypted(lobby_hash)
        if lobby_is_encrypted and password is None:
            return False

        table_name = await self.find_lobby_table_name(lobby_hash, password)
        if table_name is None:
            return False

        effective_user_id = user_id
        if lobby_is_encrypted:
            assert password is not None
            effective_user_id = self._encrypt_string(
                lobby_hash, user_id, password)

        async with aiosqlite.connect(self.DB_FILE) as db:
            query = f'SELECT is_admin FROM "{table_name}" WHERE user_id = ?'
            cursor = await db.execute(query, (effective_user_id,))
            result = await cursor.fetchone()
            return bool(result[0]) if result else False

    async def add_user_to_lobby(self, lobby_hash: str, user_id_adder: str, user_id_to_add: str, password: Optional[str] = None, is_admin: bool = False):
        table_name = await self.find_lobby_table_name(lobby_hash, password)
        if table_name is None:
            return

        is_adder_admin = await self.is_admin(user_id_adder, lobby_hash, password)
        is_lobby_public = await self.is_public(lobby_hash)
        if not is_adder_admin and not is_lobby_public:
            return

        effective_user_id = user_id_to_add
        if await self.is_encrypted(lobby_hash):
            assert password is not None
            effective_user_id = self._encrypt_string(
                lobby_hash, user_id_to_add, password)

        async with aiosqlite.connect(self.DB_FILE) as db:
            query = f'SELECT 1 FROM "{table_name}" WHERE user_id = ?'
            cursor = await db.execute(query, (effective_user_id,))
            result = await cursor.fetchone()

            if not result:
                insert_query = f'INSERT INTO "{table_name}" (user_id, is_admin, is_running, last_entry) VALUES (?, ?, ?, ?)'
                await db.execute(insert_query, (effective_user_id, is_admin, False, None))
                await db.commit()
                print(f"Added user {user_id_to_add} to lobby {lobby_hash}")
            else:
                print(
                    f"User {user_id_to_add} already exists in lobby {lobby_hash}")

    async def remove_user_from_lobby(self, lobby_hash: str, user_id_remover: str, user_id_to_remove: str, password: Optional[str] = None):
        table_name = await self.find_lobby_table_name(lobby_hash, password)
        if table_name is None:
            return

        is_remover_admin = await self.is_admin(user_id_remover, lobby_hash, password)
        if not is_remover_admin:
            return

        effective_user_id = user_id_to_remove
        if await self.is_encrypted(lobby_hash):
            assert password is not None
            effective_user_id = self._encrypt_string(
                lobby_hash, user_id_to_remove, password)

        async with aiosqlite.connect(self.DB_FILE) as db:
            delete_query = f'DELETE FROM "{table_name}" WHERE user_id = ?'
            cursor = await db.execute(delete_query, (effective_user_id,))
            await db.commit()

            if cursor.rowcount > 0:
                print(
                    f"Successfully removed user {user_id_to_remove} from lobby {lobby_hash}")
            else:
                print(
                    f"User {user_id_to_remove} not found in lobby {lobby_hash}")

    async def delete_lobby(self, user_id_dropper: str, lobby_hash: str, password: Optional[str] = None):
        is_dropper_admin = await self.is_admin(user_id_dropper, lobby_hash, password)
        if not is_dropper_admin:
            print(
                f"User {user_id_dropper} does not have the required privilages to drop the lobby.")
            return

        table_name = await self.find_lobby_table_name(lobby_hash, password)

        async with aiosqlite.connect(self.DB_FILE) as db:
            await db.execute("DELETE FROM Lobbies WHERE hash = ?", (lobby_hash,))
            if table_name:
                drop_query = f'DROP TABLE IF EXISTS "{table_name}"'
                await db.execute(drop_query)
            await db.commit()
            print(f"Successfully deleted lobby with hash: {lobby_hash}")

    async def get_lobby_users(self, lobby_hash: str, password: Optional[str] = None) -> List[Dict[str, Any]]:
        if not await self.lobby_exists(lobby_hash):
            print(f"Lobby with hash '{lobby_hash}' does not exist.")
            return []

        lobby_is_encrypted = await self.is_encrypted(lobby_hash)
        if lobby_is_encrypted and password is None:
            return []

        table_name = await self.find_lobby_table_name(lobby_hash, password)
        if table_name is None:
            return []

        async with aiosqlite.connect(self.DB_FILE) as db:
            db.row_factory = aiosqlite.Row
            query = f'SELECT * FROM "{table_name}"'
            cursor = await db.execute(query)
            rows = await cursor.fetchall()
            entries = [dict(row) for row in rows]

        if lobby_is_encrypted:
            # TODO make prettier
            assert password is not None
            decrypted_entries = {
                entry['user_id']: self._decrypt_string(
                    entry['user_id'], password).removeprefix(lobby_hash)
                for entry in entries
            }
            return [decrypted_entries]
        else:
            # TODO fix. Don't be lazy
            return list(entries)
