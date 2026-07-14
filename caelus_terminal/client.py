from __future__ import annotations

from dataclasses import dataclass
import json
from urllib.request import Request, urlopen


@dataclass(frozen=True)
class RuntimeDetails:
    model_name: str
    skills: list[str]
    mcp_servers: list[str]
    tools: list[str]


class HermesClient:
    """Small adapter for Hermes's documented local OpenAI-compatible API server."""

    def __init__(self, base_url: str, api_key: str) -> None:
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key

    def _root_url(self, path: str) -> str:
        return f"{self.base_url.removesuffix('/v1')}/{path.lstrip('/')}"

    def _post(self, url: str, payload: dict) -> dict:
        request = Request(
            url,
            data=json.dumps(payload).encode(),
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
                "Accept": "application/json",
            },
            method="POST",
        )
        with urlopen(request, timeout=120) as response:  # nosec B310: local endpoint selected by user
            return json.loads(response.read())

    def create_session(self, title: str) -> dict:
        return self._post(self._root_url("api/sessions"), {"title": title})["session"]

    def session_messages(self, session_id: str) -> list[dict]:
        response = self._get(self._root_url(f"api/sessions/{session_id}/messages"))
        return response.get("data", [])

    def start_run(self, message: str, *, session_id: str) -> str:
        response = self._post(
            f"{self.base_url}/runs", {"input": message, "session_id": session_id}
        )
        return response["run_id"]

    def stop_run(self, run_id: str) -> None:
        self._post(f"{self.base_url}/runs/{run_id}/stop", {})

    def stream_run(self, run_id: str):
        request = Request(
            f"{self.base_url}/runs/{run_id}/events",
            headers={"Authorization": f"Bearer {self.api_key}", "Accept": "text/event-stream"},
            method="GET",
        )
        with urlopen(request, timeout=120) as response:  # nosec B310: local endpoint selected by user
            for raw_line in iter(response.readline, b""):
                line = raw_line.decode().strip()
                if line.startswith("data: "):
                    yield json.loads(line[6:])

    def _get(self, path: str) -> dict:
        url = path if path.startswith(("http://", "https://")) else f"{self.base_url}/{path.lstrip('/')}"
        request = Request(
            url,
            headers={"Authorization": f"Bearer {self.api_key}"},
            method="GET",
        )
        with urlopen(request, timeout=30) as response:  # nosec B310: user supplies local endpoint
            return json.loads(response.read())

    def discover(self) -> RuntimeDetails:
        capabilities = self._get("capabilities")
        skills = self._get("skills")
        toolsets = self._get("toolsets")
        model = capabilities.get("model", "runtime connected")
        if isinstance(model, dict):
            model = model.get("id") or model.get("name") or "runtime connected"
        enabled_toolsets = [
            toolset
            for toolset in toolsets.get("data", [])
            if toolset.get("enabled")
        ]
        return RuntimeDetails(
            model_name=str(model),
            skills=[skill["name"] for skill in skills.get("data", []) if skill.get("name")],
            mcp_servers=[
                toolset["name"]
                for toolset in enabled_toolsets
                if toolset.get("name", "").startswith("mcp-")
            ],
            tools=[
                tool
                for toolset in enabled_toolsets
                for tool in toolset.get("tools", [])
            ],
        )

    def chat(self, message: str, *, conversation: str) -> str:
        payload = {
            "model": "hermes-agent",
            "messages": [{"role": "user", "content": message}],
        }
        request = Request(
            f"{self.base_url}/chat/completions",
            data=json.dumps(payload).encode(),
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
                "X-Hermes-Session-Id": conversation,
            },
            method="POST",
        )
        with urlopen(request, timeout=120) as response:  # nosec B310: user supplies local endpoint
            body = json.loads(response.read())
        return body["choices"][0]["message"]["content"]
