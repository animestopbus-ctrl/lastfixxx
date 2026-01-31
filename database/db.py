import motor.motor_asyncio
import datetime
from typing import Optional, Dict, List, Any
from config import DB_NAME, DB_URI
from logger import LOGGER

logger = LOGGER(__name__)

class Database:
    def __init__(self, uri: str, database_name: str):
        """
        Initializes the Database connection.
        """
        self._client = motor.motor_asyncio.AsyncIOMotorClient(uri)
        self.db = self._client[database_name]
        self.col = self.db.users

    async def ensure_indexes(self) -> None:
        """
        Ensures necessary indexes are created for efficiency.
        Call this after initialization if needed.
        """
        await self.col.create_index('id', unique=True)
        await self.col.create_index('is_premium')
        await self.col.create_index('is_banned')
        logger.info("Database indexes ensured.")

    def new_user(self, id: int, name: str) -> Dict[str, Any]:
        """
        Creates a new user dictionary with all default fields.
        """
        return {
            'id': id,
            'name': name,
            'session': None,
            'caption': None,
            'thumbnail': None,
            'is_premium': False,
            'premium_expiry': None,
            'is_banned': False,
            'dump_chat': None,
            'delete_words': [],
            'replace_words': {},
            'daily_usage': 0,
            'limit_reset_time': None
        }

    async def add_user(self, id: int, name: str) -> None:
        """
        Adds a new user to the database.
        """
        user = self.new_user(id, name)
        try:
            await self.col.insert_one(user)
            logger.info(f"New user added to DB: {id} - {name}")
        except Exception as e:
            logger.error(f"Error adding user {id}: {e}")
            raise

    async def is_user_exist(self, id: int) -> bool:
        """
        Checks if a user exists in the database.
        """
        user = await self.col.find_one({'id': id})
        return bool(user)

    async def total_users_count(self) -> int:
        """
        Returns the total count of users in the database.
        """
        return await self.col.count_documents({})

    def get_all_users(self):
        """
        Returns a cursor for all users in the database.
        Use with 'async for' to iterate.
        """
        return self.col.find({})

    async def delete_user(self, user_id: int) -> None:
        """
        Deletes a user from the database.
        """
        await self.col.delete_many({'id': user_id})
        logger.info(f"User deleted from DB: {user_id}")

    async def set_session(self, id: int, session: Optional[str]) -> None:
        """
        Sets the session for a user.
        """
        await self.col.update_one({'id': id}, {'$set': {'session': session}})

    async def get_session(self, id: int) -> Optional[str]:
        """
        Gets the session for a user.
        """
        user = await self.col.find_one({'id': id})
        return user.get('session') if user else None

    # Caption Support
    async def set_caption(self, id: int, caption: Optional[str]) -> None:
        """
        Sets the caption for a user.
        """
        await self.col.update_one({'id': id}, {'$set': {'caption': caption}})

    async def get_caption(self, id: int) -> Optional[str]:
        """
        Gets the caption for a user.
        """
        user = await self.col.find_one({'id': id})
        return user.get('caption', None) if user else None

    async def del_caption(self, id: int) -> None:
        """
        Deletes the caption for a user.
        """
        await self.col.update_one({'id': id}, {'$unset': {'caption': 1}})

    # Thumbnail Support
    async def set_thumbnail(self, id: int, thumbnail: Optional[str]) -> None:
        """
        Sets the thumbnail for a user.
        """
        await self.col.update_one({'id': id}, {'$set': {'thumbnail': thumbnail}})

    async def get_thumbnail(self, id: int) -> Optional[str]:
        """
        Gets the thumbnail for a user.
        """
        user = await self.col.find_one({'id': id})
        return user.get('thumbnail', None) if user else None

    async def del_thumbnail(self, id: int) -> None:
        """
        Deletes the thumbnail for a user.
        """
        await self.col.update_one({'id': id}, {'$unset': {'thumbnail': 1}})

    # Premium Support
    async def add_premium(self, id: int, expiry_date: datetime.datetime) -> None:
        """
        Grants premium status to a user until the expiry date.
        Resets daily limits.
        """
        await self.col.update_one({'id': id}, {
            '$set': {
                'is_premium': True,
                'premium_expiry': expiry_date,
                'daily_usage': 0,
                'limit_reset_time': None
            }
        })
        logger.info(f"User {id} granted premium until {expiry_date}")

    async def remove_premium(self, id: int) -> None:
        """
        Removes premium status from a user.
        """
        await self.col.update_one({'id': id}, {'$set': {'is_premium': False, 'premium_expiry': None}})
        logger.info(f"User {id} removed from premium")

    async def check_premium(self, id: int) -> Optional[datetime.datetime]:
        """
        Checks if a user is premium and returns expiry if true, else None.
        """
        user = await self.col.find_one({'id': id})
        if user and user.get('is_premium'):
            return user.get('premium_expiry')
        return None

    async def is_premium(self, id: int) -> bool:
        """
        Checks if a user is premium and if the premium has not expired.
        Automatically removes premium if expired.
        """
        user = await self.col.find_one({'id': id})
        if user and user.get('is_premium', False):
            expiry = user.get('premium_expiry')
            if expiry and datetime.datetime.now() < expiry:
                return True
            else:
                await self.remove_premium(id)
                return False
        return False

    def get_premium_users(self):
        """
        Returns a cursor for all premium users.
        Use with 'async for' to iterate.
        """
        return self.col.find({'is_premium': True})

    async def total_premium_count(self) -> int:
        """
        Returns the total count of premium users.
        """
        return await self.col.count_documents({'is_premium': True})

    # Ban Support
    async def ban_user(self, id: int) -> None:
        """
        Bans a user.
        """
        await self.col.update_one({'id': id}, {'$set': {'is_banned': True}})
        logger.warning(f"User banned: {id}")

    async def unban_user(self, id: int) -> None:
        """
        Unbans a user.
        """
        await self.col.update_one({'id': id}, {'$set': {'is_banned': False}})
        logger.info(f"User unbanned: {id}")

    async def is_banned(self, id: int) -> bool:
        """
        Checks if a user is banned.
        """
        user = await self.col.find_one({'id': id})
        return user.get('is_banned', False) if user else False

    def get_banned_users(self):
        """
        Returns a cursor for all banned users.
        Use with 'async for' to iterate.
        """
        return self.col.find({'is_banned': True})

    async def total_banned_count(self) -> int:
        """
        Returns the total count of banned users.
        """
        return await self.col.count_documents({'is_banned': True})

    # Dump Chat Support
    async def set_dump_chat(self, id: int, chat_id: int) -> None:
        """
        Sets the dump chat for a user.
        """
        await self.col.update_one({'id': id}, {'$set': {'dump_chat': chat_id}})

    async def get_dump_chat(self, id: int) -> Optional[int]:
        """
        Gets the dump chat for a user.
        """
        user = await self.col.find_one({'id': id})
        return user.get('dump_chat', None) if user else None

    # Delete/Replace Words Support
    async def set_delete_words(self, id: int, words: List[str]) -> None:
        """
        Adds words to the delete list for a user.
        """
        await self.col.update_one({'id': id}, {'$addToSet': {'delete_words': {'$each': words}}})

    async def get_delete_words(self, id: int) -> List[str]:
        """
        Gets the delete words for a user.
        """
        user = await self.col.find_one({'id': id})
        return user.get('delete_words', []) if user else []

    async def remove_delete_words(self, id: int, words: List[str]) -> None:
        """
        Removes words from the delete list for a user.
        """
        await self.col.update_one({'id': id}, {'$pull': {'delete_words': {'$in': words}}})

    async def set_replace_words(self, id: int, repl_dict: Dict[str, str]) -> None:
        """
        Updates the replace words dictionary for a user.
        """
        user = await self.col.find_one({'id': id})
        if user:
            current_repl = user.get('replace_words', {})
            current_repl.update(repl_dict)
            await self.col.update_one({'id': id}, {'$set': {'replace_words': current_repl}})

    async def get_replace_words(self, id: int) -> Dict[str, str]:
        """
        Gets the replace words for a user.
        """
        user = await self.col.find_one({'id': id})
        return user.get('replace_words', {}) if user else {}

    async def remove_replace_words(self, id: int, words: List[str]) -> None:
        """
        Removes keys from the replace words dictionary for a user.
        """
        user = await self.col.find_one({'id': id})
        if user:
            current_repl = user.get('replace_words', {})
            for w in words:
                current_repl.pop(w, None)
            await self.col.update_one({'id': id}, {'$set': {'replace_words': current_repl}})

    # Daily Limits (Free User Restriction)
    async def check_limit(self, id: int) -> bool:
        """
        Checks if a user has hit their daily limit.
        Returns: True if BLOCKED (limit reached), False if ALLOWED.
        """
        user = await self.col.find_one({'id': id})
        if not user:
            return False  # Should be added via add_user, but safe fallback

        # 1. Premium Check: Always allowed if active premium
        if await self.is_premium(id):
            return False

        # 2. Check Time Reset
        now = datetime.datetime.now()
        reset_time = user.get('limit_reset_time')
        # If reset time has passed or was never set, reset count to 0
        if reset_time is None or now >= reset_time:
            await self.col.update_one(
                {'id': id},
                {'$set': {'daily_usage': 0, 'limit_reset_time': None}}
            )
            return False  # Allowed (count is 0)

        # 3. Check Count
        usage = user.get('daily_usage', 0)
        if usage >= 10:
            return True  # Blocked
        return False  # Allowed

    async def add_traffic(self, id: int) -> None:
        """
        Increments usage count for non-premium users.
        If it's the first use of the cycle, sets the 24h timer.
        """
        user = await self.col.find_one({'id': id})
        if not user or await self.is_premium(id):
            return

        now = datetime.datetime.now()
        reset_time = user.get('limit_reset_time')
        # If timer is not running (None), start it for 24 hours from NOW.
        if reset_time is None:
            new_reset_time = now + datetime.timedelta(hours=24)
            await self.col.update_one(
                {'id': id},
                {'$set': {'daily_usage': 1, 'limit_reset_time': new_reset_time}}
            )
        else:
            # Just increment
            await self.col.update_one(
                {'id': id},
                {'$inc': {'daily_usage': 1}}
            )

    # Additional Methods
    async def update_user_name(self, id: int, new_name: str) -> None:
        """
        Updates the name of a user.
        """
        await self.col.update_one({'id': id}, {'$set': {'name': new_name}})
        logger.info(f"Updated name for user {id} to {new_name}")

    # Info Extractor
    async def get_user_info(self, id: int) -> Optional[Dict[str, Any]]:
        """
        Extracts all information for a user as a dictionary (without _id).
        """
        user = await self.col.find_one({'id': id}, projection={'_id': 0})
        return user

db = Database(DB_URI, DB_NAME)
