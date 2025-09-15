import aiosqlite
from typing import List, Dict, Any, Optional
from security_manager import SecurityManager
import os
import datetime
import enum


class DatabaseEnums(enum.IntEnum):
    UNWANTED_BEHAVIOR = 0
    SUCCESS = 1
    LOBBY_EXISTS = 32
    INVALID_PASSWORD = 33
    PASSWORD_NOT_ENTERED = 34
    INSUFFICIENT_PRIVILAGES = 35
    USER_HAS_NO_FREE_SLOTS = 36
    USER_ALREADY_EXISTS_IN_LOBBY = 36
    USER_NOT_IN_LOBBY = 37
    INVALID_LOBBY = 38
    CHRONO_ALREADY_RUNNING = 39
    CHRONO_ALREADY_NOT_RUNNING = 40


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
                    is_public BOOLEAN,
                    password_hash TEXT
                )
            ''')

            await db.execute('''
                CREATE TABLE IF NOT EXISTS Users (
                    user_id TEXT PRIMARY KEY,
                    lobby_hash_1 TEXT,
                    lobby_hash_2 TEXT,
                    lobby_hash_3 TEXT,
                    lobby_hash_4 TEXT,
                    lobby_hash_5 TEXT,
                    lobby_hash_6 TEXT,
                    lobby_hash_7 TEXT,
                    lobby_hash_8 TEXT,
                    lobby_hash_9 TEXT,
                    lobby_hash_10 TEXT
                )
            ''')

            await db.commit()
            print("Database initialized.")

    async def create_lobby(self, user_id: str, name: str, is_public: bool = False, password: Optional[str] = None) -> int:
        '''
        Returns PASSWORD_NOT_ENTERED, USER_HAS_NO_FREE_SLOTS, SUCCESS, LOBBY_EXISTS
        '''
        user_has_free_slots = await self.user_has_free_slots(user_id)
        if not user_has_free_slots:
            return DatabaseEnums.USER_HAS_NO_FREE_SLOTS

        if not is_public and not password:
            return DatabaseEnums.PASSWORD_NOT_ENTERED

        password_hash = self._security.hash_password(
            password) if password else None

        lobby_already_exists = self._check_lobby_all(name)
        if lobby_already_exists:
            return DatabaseEnums.LOBBY_EXISTS

        lobby_hash = self._security.generate_lobby_hash(name)
        table_name = f"lobby_{lobby_hash}"

        async with aiosqlite.connect(self.DB_FILE) as db:
            async with db.cursor() as cursor:
                await cursor.execute(
                    "INSERT INTO Lobbies (hash, name, is_public, password_hash) VALUES (?, ?, ?, ?)",
                    (lobby_hash, name, is_public, password_hash)
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

            await db.commit()
            await self.add_user_to_lobby(lobby_hash, "admin", user_id, is_admin=True)

        print(f"Successfully created lobby '{name}' with hash: {lobby_hash}")
        return DatabaseEnums.SUCCESS

    async def _lobby_table_exists(self, lobby_name: str) -> bool:
        lobby_hash = self._security.generate_lobby_hash(lobby_name)
        table_name = f"lobby_{lobby_hash}"
        async with aiosqlite.connect(self.DB_FILE) as db:
            cursor = await db.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table_name,))
            result = await cursor.fetchone()
            return result is not None

    async def _lobby_exists(self, lobby_name: str) -> bool:
        lobby_hash = self._security.generate_lobby_hash(lobby_name)
        async with aiosqlite.connect(self.DB_FILE) as db:
            cursor = await db.execute("SELECT 1 FROM Lobbies WHERE hash=?", (lobby_hash,))
            result = await cursor.fetchone()
            return result is not None

    async def is_public(self, lobby_name: str) -> bool:
        lobby_hash = self._security.generate_lobby_hash(lobby_name)
        if not await self._check_lobby_all(lobby_hash):
            return False
        async with aiosqlite.connect(self.DB_FILE) as db:
            cursor = await db.execute("SELECT is_public FROM Lobbies WHERE hash=?", (lobby_hash,))
            result = await cursor.fetchone()
            return bool(result[0]) if result else False

    async def is_admin(self, user_id: str, lobby_name: str) -> bool:
        lobby_hash = self._security.generate_lobby_hash(lobby_name)
        if user_id == "admin":
            return True

        table_name = f"lobby_{lobby_hash}"
        effective_user_id = user_id
        async with aiosqlite.connect(self.DB_FILE) as db:
            query = f'SELECT is_admin FROM "{table_name}" WHERE user_id = ?'
            cursor = await db.execute(query, (effective_user_id,))
            result = await cursor.fetchone()
            return bool(result[0]) if result else False

    async def user_has_free_slots(self, user_id: str) -> bool:
        user_has_room = await self._add_lobby_to_user_table(user_id, "temporary")

        if not user_has_room:
            return False
        else:
            await self._remove_lobby_from_user_table(user_id, "temporary")
            return True

    async def add_user_to_lobby(self, lobby_name: str, user_id_adder: str, user_id_to_add: str, is_admin: bool = False) -> int:
        '''
        Returns INSUFFICIENT_PRIVILAGES, USER_HAS_NO_FREE_SLOTS, SUCCESS, USER_ALREADY_EXISTS_IN_LOBBY
        '''
        lobby_hash = self._security.generate_lobby_hash(lobby_name)
        is_adder_admin = await self.is_admin(user_id_adder, lobby_hash)
        is_lobby_public = await self.is_public(lobby_hash)
        if not is_adder_admin and not is_lobby_public:
            return DatabaseEnums.INSUFFICIENT_PRIVILAGES

        table_name = f"lobby_{lobby_hash}"
        effective_user_id = user_id_to_add

        async with aiosqlite.connect(self.DB_FILE) as db:
            query = f'SELECT 1 FROM "{table_name}" WHERE user_id = ?'
            cursor = await db.execute(query, (effective_user_id,))
            result = await cursor.fetchone()

            if not result:
                user_has_empty_slots = await self._add_lobby_to_user_table(
                    user_id_to_add, lobby_hash)
                if not user_has_empty_slots:
                    return DatabaseEnums.USER_HAS_NO_FREE_SLOTS
                insert_query = f'INSERT INTO "{table_name}" (user_id, is_admin, is_running, last_entry) VALUES (?, ?, ?, ?)'
                await db.execute(insert_query, (effective_user_id, is_admin, False, None))
                await db.commit()
                print(f"Added user {user_id_to_add} to lobby {lobby_hash}")
                return DatabaseEnums.SUCCESS
            else:
                print(
                    f"User {user_id_to_add} already exists in lobby {lobby_hash}")
                return DatabaseEnums.USER_ALREADY_EXISTS_IN_LOBBY

    async def _check_lobby_all(self, lobby_name: str) -> bool:
        lobby_hash = self._security.generate_lobby_hash(lobby_name)
        lobby_exists = await self._lobby_exists(lobby_hash)
        lobby_table_exists = await self._lobby_table_exists(lobby_hash)
        return lobby_exists and lobby_table_exists

    async def join_lobby(self, lobby_name: str, user_id: str, password: str | None) -> int:
        '''
        Returns USER_HAS_NO_FREE_SLOTS, SUCCESS, USER_ALREADY_EXISTS_IN_LOBBY, INVALID_PASSWORD, INVALID_LOBBY
        '''
        lobby_hash = self._security.generate_lobby_hash(lobby_name)
        user_has_free_slots = await self.user_has_free_slots(user_id)
        if not user_has_free_slots:
            return DatabaseEnums.USER_HAS_NO_FREE_SLOTS

        lobby_exists = await self._check_lobby_all(lobby_hash)
        if not lobby_exists:
            return DatabaseEnums.INVALID_LOBBY

        lobby_is_public = await self.is_public(lobby_hash)
        if not lobby_is_public and password is None:
            return DatabaseEnums.INVALID_PASSWORD
        elif not lobby_is_public:
            lobby_password_hash = await self._get_lobby_password_hash(lobby_hash)
            if lobby_password_hash is None:
                print("This should not happen. Password hash for private lobby is None.")
                return DatabaseEnums.UNWANTED_BEHAVIOR
            # TODO make prettier
            assert (password is not None)
            passwords_correct = self._security.check_password(
                password, lobby_password_hash)
            if not passwords_correct:
                return DatabaseEnums.INVALID_PASSWORD

        user_added = await self.add_user_to_lobby(lobby_hash, "admin", user_id)

        return DatabaseEnums.SUCCESS

    async def remove_user_from_lobby(self, lobby_name: str, user_id_remover: str, user_id_to_remove: str) -> int:
        '''
        Returns INSUFFICIENT_PRIVILAGES, SUCCESS, USER_NOT_IN_LOBBY , INVALID_LOBBY
        '''
        lobby_exists = await self._check_lobby_all(lobby_name)
        if not lobby_exists:
            return DatabaseEnums.INVALID_LOBBY

        lobby_hash = self._security.generate_lobby_hash(lobby_name)
        is_remover_admin = await self.is_admin(user_id_remover, lobby_hash)
        if not is_remover_admin:
            return DatabaseEnums.INSUFFICIENT_PRIVILAGES

        table_name = f"lobby_{lobby_hash}"
        effective_user_id = user_id_to_remove

        async with aiosqlite.connect(self.DB_FILE) as db:
            removed_lobby_from_user = await self._remove_lobby_from_user_table(
                user_id_to_remove, lobby_hash)

            if not removed_lobby_from_user:
                return DatabaseEnums.USER_NOT_IN_LOBBY

            delete_query = f'DELETE FROM "{table_name}" WHERE user_id = ?'
            cursor = await db.execute(delete_query, (effective_user_id,))
            await db.commit()

            if cursor.rowcount > 0:
                print(
                    f"Successfully removed user {user_id_to_remove} from lobby {lobby_hash}")
                return DatabaseEnums.SUCCESS
            else:
                print(
                    f"User {user_id_to_remove} not found in lobby {lobby_hash}")
                return DatabaseEnums.USER_NOT_IN_LOBBY

    async def _get_lobby_name(self, lobby_name: str) -> Optional[str]:
        lobby_hash = self._security.generate_lobby_hash(lobby_name)

        lobby_exists = await self._check_lobby_all(lobby_hash)
        if not lobby_exists:
            return None

        async with aiosqlite.connect(self.DB_FILE) as db:
            cursor = await db.execute("SELECT name FROM Lobbies WHERE hash = ?", (lobby_hash,))
            result = await cursor.fetchone()
            return result[0] if result else None

    async def _get_lobby_password_hash(self, lobby_name: str) -> Optional[str]:
        lobby_hash = self._security.generate_lobby_hash(lobby_name)
        lobby_exists = await self._check_lobby_all(lobby_hash)
        if not lobby_exists:
            return None
        async with aiosqlite.connect(self.DB_FILE) as db:
            cursor = await db.execute("SELECT password_hash FROM Lobbies WHERE hash = ?", (lobby_hash,))
            result = await cursor.fetchone()
            return result[0] if result else None

    async def delete_lobby(self, user_id_dropper: str, lobby_name: str) -> int:
        '''
        Returns INSUFFICIENT_PRIVILAGES, SUCCESS, INVALID_LOBBY
        '''
        lobby_exists = await self._check_lobby_all(lobby_name)
        if not lobby_exists:
            return DatabaseEnums.INVALID_LOBBY
        lobby_hash = self._security.generate_lobby_hash(lobby_name)
        is_dropper_admin = await self.is_admin(user_id_dropper, lobby_hash)
        if not is_dropper_admin:
            print(
                f"User {user_id_dropper} does not have the required privilages to drop the lobby.")
            return DatabaseEnums.INSUFFICIENT_PRIVILAGES

        table_name = f"lobby_{lobby_hash}"
        async with aiosqlite.connect(self.DB_FILE) as db:
            await db.execute("DELETE FROM Lobbies WHERE hash = ?", (lobby_hash,))
            drop_query = f'DROP TABLE IF EXISTS "{table_name}"'
            await db.execute(drop_query)
            await db.commit()
            print(f"Successfully deleted lobby with hash: {lobby_hash}")
            return DatabaseEnums.SUCCESS

    async def get_lobby_users(self, lobby_name: str) -> List[Dict[str, Any]]:
        lobby_hash = self._security.generate_lobby_hash(lobby_name)

        lobby_exists = await self._check_lobby_all(lobby_hash)
        if not lobby_exists:
            return []

        table_name = f"lobby_{lobby_hash}"
        async with aiosqlite.connect(self.DB_FILE) as db:
            db.row_factory = aiosqlite.Row
            query = f'SELECT * FROM "{table_name}"'
            cursor = await db.execute(query)
            rows = await cursor.fetchall()
            entries = [dict(row) for row in rows]

            return list(entries)

    async def _register_user_if_not_exists(self, user_id: str):
        async with aiosqlite.connect(self.DB_FILE) as db:
            await db.execute("INSERT OR IGNORE INTO Users (user_id) VALUES (?)", (user_id,))
            await db.commit()

    async def _add_lobby_to_user_table(self, user_id: str, lobby_name: str) -> bool:
        lobby_hash = self._security.generate_lobby_hash(lobby_name)
        await self._register_user_if_not_exists(user_id)

        async with aiosqlite.connect(self.DB_FILE) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("SELECT * FROM Users WHERE user_id = ?", (user_id,))
            user_row = await cursor.fetchone()

            if user_row:
                first_empty_slot = None
                for i in range(1, 11):
                    slot_name = f"lobby_hash_{i}"
                    if user_row[slot_name] is None:
                        first_empty_slot = slot_name
                        break

                if first_empty_slot:
                    update_query = f'UPDATE Users SET {first_empty_slot} = ? WHERE user_id = ?'
                    await db.execute(update_query, (lobby_hash, user_id))
                    await db.commit()
                    print(
                        f"Added lobby {lobby_hash} to {first_empty_slot} for user {user_id}.")
                    return True
                else:
                    print(f"User {user_id} has no empty lobby slots.")
                    return False
        return False

    async def _remove_lobby_from_user_table(self, user_id: str, lobby_name: str) -> bool:
        lobby_hash = self._security.generate_lobby_hash(lobby_name)
        async with aiosqlite.connect(self.DB_FILE) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("SELECT * FROM Users WHERE user_id = ?", (user_id,))
            user_row = await cursor.fetchone()

            if user_row:
                slot_to_clear = None
                for i in range(1, 11):
                    slot_name = f"lobby_hash_{i}"
                    if user_row[slot_name] == lobby_hash:
                        slot_to_clear = slot_name
                        break

                if slot_to_clear:
                    update_query = f'UPDATE Users SET {slot_to_clear} = NULL WHERE user_id = ?'
                    await db.execute(update_query, (user_id,))
                    await db.commit()
                    print(
                        f"Removed lobby {lobby_hash} from {slot_to_clear} for user {user_id}.")
                    return True
                else:
                    print(
                        f"Lobby {lobby_hash} not found in any slots for user {user_id}.")
                    return False
        return False

    async def get_user_lobbies(self, user_id: str) -> List[str]:
        await self._register_user_if_not_exists(user_id)

        async with aiosqlite.connect(self.DB_FILE) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("SELECT * FROM Users WHERE user_id = ?", (user_id,))
            user_row = await cursor.fetchone()

            lobbies = []
            if user_row:
                for i in range(1, 11):
                    slot_name = f"lobby_hash_{i}"
                    lobby_hash = user_row[slot_name]
                    if lobby_hash is not None:
                        lobbies.append(lobby_hash)
            return lobbies

    async def _is_in_lobby(self, user_id: str, lobby_name: str) -> bool:
        lobby_hash = self._security.generate_lobby_hash(lobby_name)
        table_name = f"lobby_{lobby_hash}"
        async with aiosqlite.connect(self.DB_FILE) as db:
            query = f'SELECT 1 FROM "{table_name}" WHERE user_id = ?'
            cursor = await db.execute(query, (user_id,))
            result = await cursor.fetchone()
            return result is not None

    async def start_chrono(self, lobby_name: str, user_id: str, time: datetime.datetime) -> int:
        '''
        Returns SUCCESS, INVALID_LOBBY, USER_NOT_IN_LOBBY, CHRONO_ALREADY_RUNNING
        '''
        lobby_hash = self._security.generate_lobby_hash(lobby_name)
        if not await self._lobby_exists(lobby_hash):
            return DatabaseEnums.INVALID_LOBBY
        elif not await self._is_in_lobby(user_id, lobby_hash):
            return DatabaseEnums.USER_NOT_IN_LOBBY

        table_name = f"lobby_{lobby_hash}"
        async with aiosqlite.connect(self.DB_FILE) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(f'SELECT is_running FROM "{table_name}" WHERE user_id = ?', (user_id,))
            result = await cursor.fetchone()

            if result and result['is_running']:
                return DatabaseEnums.CHRONO_ALREADY_RUNNING

            update_query = f'UPDATE "{table_name}" SET is_running = ?, last_entry = ? WHERE user_id = ?'
            await db.execute(update_query, (True, time.isoformat(), user_id))
            await db.commit()
            return DatabaseEnums.SUCCESS

    async def stop_chrono(self, lobby_name: str, user_id: str, time: datetime.datetime) -> tuple[int, int]:
        '''
        Returns SUCCESS, INVALID_LOBBY, USER_NOT_IN_LOBBY, CHRONO_ALREADY_NOT_RUNNING
        '''
        lobby_hash = self._security.generate_lobby_hash(lobby_name)
        if not await self._lobby_exists(lobby_hash):
            return (DatabaseEnums.INVALID_LOBBY, 0)
        elif not await self._is_in_lobby(user_id, lobby_hash):
            return (DatabaseEnums.USER_NOT_IN_LOBBY, 0)

        table_name = f"lobby_{lobby_hash}"
        async with aiosqlite.connect(self.DB_FILE) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(f'SELECT is_running, last_entry, total_seconds FROM "{table_name}" WHERE user_id = ?', (user_id,))
            user_row = await cursor.fetchone()

            if not user_row or not user_row['is_running'] or user_row['last_entry'] is None:
                return (DatabaseEnums.CHRONO_ALREADY_NOT_RUNNING, 0)

            last_entry_time = datetime.datetime.fromisoformat(
                user_row['last_entry'])
            time_difference = time - last_entry_time
            seconds_to_add = int(time_difference.total_seconds())
            new_total_seconds = user_row['total_seconds'] + seconds_to_add

            update_query = f'UPDATE "{table_name}" SET is_running = ?, last_entry = NULL, total_seconds = ? WHERE user_id = ?'
            await db.execute(update_query, (False, new_total_seconds, user_id))
            await db.commit()
            return (DatabaseEnums.SUCCESS, seconds_to_add)
