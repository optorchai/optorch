"""create individual - sqlite"""

import json
from optorch.storage.queries.base import BaseQuery
from optorch.identity.organization.models import Individual


class CreateIndividualQuery(BaseQuery):
    """create new individual"""

    @property
    def query_name(self) -> str:
        return "identity.create_individual"

    async def execute(self, individual: Individual) -> None:
        query = """
            INSERT INTO individuals (
                id, given_name, family_name, email, password_hash,
                status, metadata, last_login_at, created_at, updated_at, deleted_at
            ) VALUES (
                :id, :given_name, :family_name, :email, :password_hash,
                :status, :metadata, :last_login_at, :created_at, :updated_at, :deleted_at
            )
        """
        await self.store.execute(
            query,
            {
                "id": individual.id,
                "given_name": individual.given_name,
                "family_name": individual.family_name,
                "email": individual.email,
                "password_hash": individual.password_hash,
                "status": individual.status,
                "metadata": json.dumps(individual.metadata) if individual.metadata else "{}",
                "last_login_at": individual.last_login_at,
                "created_at": individual.created_at,
                "updated_at": individual.updated_at,
                "deleted_at": individual.deleted_at,
            },
        )

