from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorCollection
from pymongo import ASCENDING, TEXT


class Database:
    def __init__(
        self,
        url: str | None,
        db_name: str | None
    ):
        if url is None or db_name is None:
            raise ValueError("Database does not accept NoneType arguments. Received: "
                            f"{url=} | {db_name=}")

        self._client = AsyncIOMotorClient(
            url,
            maxPoolSize=20,
            minPoolSize=5,
            serverSelectionTimeoutMS=10000
        )

        self._db = self._client[db_name]

    async def init(self):
        # creating indexes
        users_col = self.users
        await users_col.create_index("email", unique=True, name="idx_email_unique")
        await users_col.create_index("nickname", unique=True, name="idx_nickname_unique")
        await users_col.create_index([("nickname", TEXT)], name="idx_nickname_search")

        sesh_col = self.sessions
        await sesh_col.create_index(
            [("user", ASCENDING), ("session_id", ASCENDING)],
            unique=True,
            name="idx_user_sesh_unique"
        )
    
    @property
    def users(self):
        return self._db["users"]
    
    @property
    def sessions(self):
        return self._db["sessions"]

    def col(self, collection: str) -> AsyncIOMotorCollection:
        return self._db[collection]
