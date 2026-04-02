from __future__ import annotations

import httpx
import pytest

from api.app import create_app
from db.session import session_scope
from services.datasets import DatasetService
from services.prompts import PromptService
from services.runs import RunService
from tests.fixtures.sample_data import dataset_request, prompt_request, run_request


async def _register_and_create_key(client: httpx.AsyncClient, identifier: str, label: str) -> dict:
    register = await client.post(
        "/v1/auth/register",
        json={
            "identifier": identifier,
            "password": "test-password-123",
            "display_name": identifier.split("@", 1)[0],
        },
    )
    assert register.status_code == 200
    register_payload = register.json()

    create_key = await client.post(
        "/v1/auth/api-keys",
        json={
            "identifier": identifier,
            "onboarding_token": register_payload["onboarding_token"],
            "label": label,
        },
    )
    assert create_key.status_code == 200
    key_payload = create_key.json()
    return {
        "identifier": register_payload["identifier"],
        "project_slug": register_payload["project_slug"],
        "project_id": register_payload["project_id"],
        "api_key": key_payload["api_key"],
    }


@pytest.mark.asyncio
async def test_hosted_onboarding_and_project_isolation(test_database) -> None:
    transport = httpx.ASGITransport(app=create_app())
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        alice = await _register_and_create_key(client, "alice@example.com", "alice-main")
        bob = await _register_and_create_key(client, "bob@example.com", "bob-main")

        async with session_scope() as session:
            await PromptService(session).register_prompt(
                prompt_request(alice["project_slug"], prompt_key="qa", content="good prompt", version=1)
            )
            await PromptService(session).register_prompt(
                prompt_request(bob["project_slug"], prompt_key="qa", content="bad prompt", version=1)
            )
            alice_dataset = await DatasetService(session).register_dataset(dataset_request(alice["project_slug"], "alice_ds"))
            bob_dataset = await DatasetService(session).register_dataset(dataset_request(bob["project_slug"], "bob_ds"))
            bob_run = await RunService(session).run_eval_suite(run_request(bob["project_slug"], bob_dataset.dataset_name, "qa"))

        alice_headers = {"x-api-key": alice["api_key"]}

        whoami = await client.get("/v1/auth/whoami", headers=alice_headers)
        assert whoami.status_code == 200
        assert whoami.json()["project_slug"] == alice["project_slug"]

        projects = await client.get("/v1/projects", headers=alice_headers)
        assert projects.status_code == 200
        assert len(projects.json()["items"]) == 1
        assert projects.json()["items"][0]["slug"] == alice["project_slug"]

        own_datasets = await client.get(f"/v1/projects/{alice['project_slug']}/datasets", headers=alice_headers)
        assert own_datasets.status_code == 200
        assert own_datasets.json()["items"]

        cross_datasets = await client.get(f"/v1/projects/{bob['project_slug']}/datasets", headers=alice_headers)
        assert cross_datasets.status_code == 401

        cross_history = await client.post(
            "/v1/history/query",
            headers=alice_headers,
            json={"project": bob["project_slug"], "page": 1, "page_size": 20},
        )
        assert cross_history.status_code == 401

        cross_status = await client.get(f"/v1/runs/{bob_run.run_id}/status", headers=alice_headers)
        assert cross_status.status_code == 401

        cross_suggestions = await client.post(
            "/v1/suggestions",
            headers=alice_headers,
            json={"run_id": bob_run.run_id, "case_limit": 5, "cluster_limit": 3},
        )
        assert cross_suggestions.status_code == 401

        own_run = await client.post(
            "/v1/runs/eval",
            headers=alice_headers,
            json={
                "project": alice["project_slug"],
                "prompt_reference": {"prompt_key": "qa", "version": 1},
                "dataset_reference": {"dataset_name": alice_dataset.dataset_name},
                "metrics": ["answer_correctness"],
                "model_config": {"provider": "stub", "model_name": "stub-evaluator"},
                "runtime_config": {},
            },
        )
        assert own_run.status_code == 200
        assert own_run.json()["run_id"]


@pytest.mark.asyncio
async def test_invalid_and_unregistered_keys_are_rejected(test_database) -> None:
    transport = httpx.ASGITransport(app=create_app())
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        invalid = await client.get("/v1/auth/whoami", headers={"x-api-key": "totally-invalid"})
        assert invalid.status_code == 401

        fake_structured = await client.get(
            "/v1/auth/whoami",
            headers={"x-api-key": "emcp_deadbeef_notregisteredsecret"},
        )
        assert fake_structured.status_code == 401


@pytest.mark.asyncio
async def test_onboarding_token_is_one_time_and_authenticated_project_management_works(test_database) -> None:
    transport = httpx.ASGITransport(app=create_app())
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        register = await client.post(
            "/v1/auth/register",
            json={"identifier": "carol@example.com", "password": "carol-password", "display_name": "carol"},
        )
        assert register.status_code == 200
        register_payload = register.json()

        first_key = await client.post(
            "/v1/auth/api-keys",
            json={
                "identifier": "carol@example.com",
                "onboarding_token": register_payload["onboarding_token"],
                "label": "carol-main",
            },
        )
        assert first_key.status_code == 200
        api_key = first_key.json()["api_key"]

        second_key_with_same_token = await client.post(
            "/v1/auth/api-keys",
            json={
                "identifier": "carol@example.com",
                "onboarding_token": register_payload["onboarding_token"],
                "label": "carol-reuse",
            },
        )
        assert second_key_with_same_token.status_code == 400

        auth_headers = {"x-api-key": api_key}
        project_create = await client.post(
            "/v1/auth/projects",
            headers=auth_headers,
            json={"name": "Carol Project Two", "slug": "carol-project-two"},
        )
        assert project_create.status_code == 200
        assert project_create.json()["slug"] == "carol-project-two"

        second_key = await client.post(
            "/v1/auth/api-keys/current",
            headers=auth_headers,
            json={"label": "carol-project-two-key", "project": "carol-project-two"},
        )
        assert second_key.status_code == 200
        assert second_key.json()["project_slug"] == "carol-project-two"


@pytest.mark.asyncio
async def test_password_login_can_recover_account_with_new_api_key(test_database) -> None:
    transport = httpx.ASGITransport(app=create_app())
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        register = await client.post(
            "/v1/auth/register",
            json={"identifier": "dana@example.com", "password": "dana-password", "display_name": "dana"},
        )
        assert register.status_code == 200

        login = await client.post(
            "/v1/auth/login",
            json={"identifier": "dana@example.com", "password": "dana-password"},
        )
        assert login.status_code == 200
        login_payload = login.json()
        assert login_payload["identifier"] == "dana@example.com"
        assert login_payload["api_key"].startswith("emcp_")

        whoami = await client.get("/v1/auth/whoami", headers={"x-api-key": login_payload["api_key"]})
        assert whoami.status_code == 200
        assert whoami.json()["identifier"] == "dana@example.com"


@pytest.mark.asyncio
async def test_register_existing_account_with_wrong_password_is_rejected(test_database) -> None:
    transport = httpx.ASGITransport(app=create_app())
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        first = await client.post(
            "/v1/auth/register",
            json={"identifier": "erin@example.com", "password": "erin-password", "display_name": "erin"},
        )
        assert first.status_code == 200

        second = await client.post(
            "/v1/auth/register",
            json={"identifier": "erin@example.com", "password": "wrong-password", "display_name": "erin"},
        )
        assert second.status_code == 400


@pytest.mark.asyncio
async def test_login_with_invalid_password_is_rejected(test_database) -> None:
    transport = httpx.ASGITransport(app=create_app())
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        register = await client.post(
            "/v1/auth/register",
            json={"identifier": "frank@example.com", "password": "frank-password", "display_name": "frank"},
        )
        assert register.status_code == 200

        login = await client.post(
            "/v1/auth/login",
            json={"identifier": "frank@example.com", "password": "wrong-password"},
        )
        assert login.status_code == 400
