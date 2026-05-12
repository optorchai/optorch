"""update individual password - mysql"""

from optorch.storage.queries.base import BaseQuery


class UpdateIndividualPasswordQuery(BaseQuery):
    """update individual password hash"""

    @property
    def query_name(self) -> str:
        return "identity.update_individual_password"

    async def execute(self, individual_id: str, password_hash: str) -> None:
        query = """
            UPDATE individuals 
            SET password_hash = :password_hash,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = :individual_id
        """
        await self.store.execute(query, {
            "individual_id": individual_id,
            "password_hash": password_hash
        })
