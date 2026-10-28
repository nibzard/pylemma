"""Authenticated access to the Cloudflare Durable Object record boundary."""

from typing import Any
from uuid import UUID, uuid4

import httpx

from pylemma.machines import Machine
from pylemma.public_games import timestamp


class RemoteMachineStore:
    """The Worker persists records and reservations outside the container disk."""

    def __init__(
        self, url: str, token: str, transport: httpx.BaseTransport | None = None
    ):
        self.client = httpx.Client(
            base_url=url,
            headers={"Authorization": "Bearer " + token},
            timeout=10,
            transport=transport,
            follow_redirects=False,
        )

    def close(self) -> None:
        self.client.close()

    def call(self, operation: str, **values: Any) -> Any:
        response = self.client.post("/_store", json={"operation": operation, **values})
        if response.status_code == 404:
            raise KeyError(values.get("id"))
        response.raise_for_status()
        return response.json()

    def reserve(self, daily_limit: int) -> bool:
        return bool(self.call("reserve", kind="generation", limit=daily_limit))

    def reserve_challenge(self, daily_limit: int) -> bool:
        return bool(self.call("reserve", kind="challenge", limit=daily_limit))

    def put(self, machine: Machine) -> None:
        self.call(
            "put",
            kind="machine",
            id=str(machine.id),
            data=machine.model_dump(mode="json"),
        )

    def get(self, identifier: UUID) -> Machine:
        return Machine.model_validate_json(self.client_data("machine", identifier))

    def client_data(self, kind: str, identifier: UUID) -> str:
        import json

        return json.dumps(self.call("get", kind=kind, id=str(identifier)))

    def replay(self, data: dict[str, Any]) -> UUID:
        identifier = uuid4()
        self.call(
            "put",
            kind="replay",
            id=str(identifier),
            data={"created_at": timestamp(), **data},
        )
        return identifier

    def read(self, identifier: UUID) -> dict[str, Any]:
        result: dict[str, Any] = self.call("get", kind="replay", id=str(identifier))
        return result

    def public_games(
        self, *, ranked: bool, offset: int = 0, limit: int = 20
    ) -> dict[str, Any]:
        result: dict[str, Any] = self.call(
            "public_games", ranked=ranked, offset=offset, limit=limit
        )
        return result
