"""create session - timescale"""

from optorch.storage.queries.base import BaseQuery


class CreateSessionQuery(BaseQuery):
    """create user session"""

    @property
    def query_name(self) -> str:
        return "identity.create_session"

    async def execute(
        self, 
        session_id: str,
        individual_id: str,
        data: str,
        expires_at: str
    ) -> None:
        query = """
            INSERT INTO user_sessions (
                id, session_id, individual_id, data, expires_at, created_at, updated_at
            ) VALUES (
                :id, :session_id, :individual_id, :data, :expires_at, 
                CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
            )
        """
        import uuid
        await self.store.execute(query, {
            "id": str(uuid.uuid4()),
            "session_id": session_id,
            "individual_id": individual_id,
            "data": data,
            "expires_at": expires_at
        })
