"""Local Solace CLI for Phase 1.5 (filesystem gateway + OAuth3 integration)."""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from fs_gateway import FSPathError, FilesystemGatewayService
from oauth3.vault import OAuth3Vault

from .credential_vault import CredentialVault
from .init_workspace import init_workspace, resolve_solace_home

GENESIS_HASH = "0" * 64
DEFAULT_PHASE_1_5_DIR = Path("scratch") / "evidence" / "phase_1.5"


class SolaceCLI:
    """Phase 1.5 local CLI facade."""

    def __init__(
        self,
        *,
        solace_home: str | Path | None = None,
        oauth3_vault: OAuth3Vault | None = None,
        credential_vault: CredentialVault | None = None,
        fs_gateway: FilesystemGatewayService | None = None,
        cli_proof_log: str | Path | None = None,
    ) -> None:
        self.solace_home = resolve_solace_home(solace_home)
        init_workspace(self.solace_home)

        self.phase_dir = DEFAULT_PHASE_1_5_DIR
        self.phase_dir.mkdir(parents=True, exist_ok=True)

        vault_storage = self.solace_home / "config" / "oauth3_tokens.enc.json"
        vault_evidence = self.phase_dir / "oauth3_audit.jsonl"

        self.oauth3_vault = oauth3_vault or OAuth3Vault(
            encryption_key=self._derive_oauth3_key(self.solace_home),
            storage_path=vault_storage,
            evidence_log=vault_evidence,
        )

        self.credential_vault = credential_vault or CredentialVault(self.solace_home / "config")

        self.fs_gateway = fs_gateway or FilesystemGatewayService(
            vault=self.oauth3_vault,
            workspace_root=self.solace_home,
            proof_log=self.phase_dir / "fs_gateway_proof.jsonl",
        )

        self.cli_proof_log = Path(cli_proof_log) if cli_proof_log else self.phase_dir / "cli_workflow_proof.jsonl"
        self.cli_proof_log.parent.mkdir(parents=True, exist_ok=True)
        self._cli_prev_hash = self._load_tail_hash(self.cli_proof_log)

    @staticmethod
    def _derive_oauth3_key(solace_home: Path) -> bytes:
        seed = f"solace-oauth3::{solace_home}".encode("utf-8")
        return hashlib.sha256(seed).digest()

    def init(self) -> Dict[str, Any]:
        result = init_workspace(self.solace_home)
        self._append_cli_event("CLI_INIT", {"root": result["root"], "created": result["created"]})
        return result

    def auth_login(
        self,
        *,
        password: str,
        scopes: Optional[List[str]] = None,
        ttl_seconds: int = 3600,
        user_id: str = "user:local",
    ) -> Dict[str, Any]:
        requested_scopes = scopes or ["fs.read", "fs.write", "fs.list", "fs.hash"]
        token = self.oauth3_vault.issue_token(user_id, requested_scopes, expires_in=ttl_seconds)

        saved = self.credential_vault.save_credentials(
            password,
            {
                "oauth3_token": token["token_id"],
                "scopes": token["scopes"],
                "issued_at": token["created_at"],
                "expires_at": token["expires_at"],
            },
        )

        self._write_credential_vault_proof(requested_scopes)
        self._append_cli_event(
            "CLI_AUTH_LOGIN",
            {
                "scopes": requested_scopes,
                "credentials_path": saved["path"],
                "credentials_bytes": saved["bytes"],
            },
        )

        return {
            "status": "ok",
            "scopes": requested_scopes,
            "token_expires_at": token["expires_at"],
            "credentials_path": saved["path"],
        }

    def recipe_submit(self, recipe_path: str, *, password: str) -> Dict[str, Any]:
        token_id = self._require_token(password)

        source = self.fs_gateway.read(recipe_path, token_id)
        try:
            recipe_doc = json.loads(source["content"])
        except json.JSONDecodeError:
            recipe_doc = {
                "name": Path(recipe_path).stem,
                "raw": source["content"],
            }

        recipe_name = recipe_doc.get("name") if isinstance(recipe_doc, dict) else None
        if not recipe_name:
            recipe_name = Path(recipe_path).stem

        store_path = "vault/recipe_store.json"
        store = self._load_recipe_store(store_path, token_id)
        store["recipes"][recipe_name] = recipe_doc
        serialized = json.dumps(store, sort_keys=True, indent=2)
        write_result = self.fs_gateway.write(store_path, serialized, token_id)

        self._append_cli_event(
            "CLI_RECIPE_SUBMIT",
            {
                "recipe_name": recipe_name,
                "recipe_path": recipe_path,
                "store_path": store_path,
                "store_hash": write_result["hash"],
            },
        )

        return {
            "status": "submitted",
            "recipe_name": recipe_name,
            "store_path": store_path,
            "store_hash": write_result["hash"],
        }

    def recipe_run(self, recipe_name: str, *, password: str, seed: int = 0) -> Dict[str, Any]:
        token_id = self._require_token(password)
        store_path = "vault/recipe_store.json"

        store = self._load_recipe_store(store_path, token_id)
        recipes = store.get("recipes", {})
        if recipe_name not in recipes:
            raise KeyError(f"recipe not found: {recipe_name}")

        recipe_doc = recipes[recipe_name]
        canonical = json.dumps(
            {
                "recipe_name": recipe_name,
                "seed": int(seed),
                "recipe": recipe_doc,
            },
            sort_keys=True,
            separators=(",", ":"),
        )
        result_hash = hashlib.sha256(canonical.encode("utf-8")).hexdigest()

        output = {
            "status": "success",
            "recipe_name": recipe_name,
            "seed": int(seed),
            "result_hash": result_hash,
        }
        output_rel_path = f"outbox/recipe_outputs/{recipe_name}.result.json"
        self.fs_gateway.write(output_rel_path, json.dumps(output, sort_keys=True, indent=2), token_id)

        self._append_cli_event(
            "CLI_RECIPE_RUN",
            {
                "recipe_name": recipe_name,
                "seed": int(seed),
                "result_hash": result_hash,
                "output_path": output_rel_path,
            },
        )

        return output

    def status(self, *, password: str | None = None) -> Dict[str, Any]:
        workspace = resolve_solace_home(self.solace_home)
        status: Dict[str, Any] = {
            "workspace": str(workspace),
            "credentials": self.credential_vault.status(),
            "budget_remaining": 1000,
        }

        if password:
            creds = self.credential_vault.load_credentials(password)
            token = self.oauth3_vault.get_token(creds["oauth3_token"])
            expires_at = datetime.fromisoformat(token["expires_at"])
            ttl = int((expires_at - datetime.now(timezone.utc)).total_seconds())
            status["oauth3"] = {
                "token_present": True,
                "ttl_seconds": ttl if ttl > 0 else 0,
                "scopes": list(token["scopes"]),
                "revoked": token["revoked"],
            }
        else:
            status["oauth3"] = {
                "token_present": False,
                "ttl_seconds": None,
                "scopes": [],
                "revoked": None,
            }

        self._append_cli_event("CLI_STATUS", {"token_present": status["oauth3"]["token_present"]})
        return status

    def _require_token(self, password: str) -> str:
        creds = self.credential_vault.load_credentials(password)
        token_id = str(creds["oauth3_token"])
        return token_id

    def _load_recipe_store(self, store_path: str, token_id: str) -> Dict[str, Any]:
        try:
            payload = self.fs_gateway.read(store_path, token_id)
            loaded = json.loads(payload["content"])
            if not isinstance(loaded, dict):
                raise ValueError("recipe store must be a JSON object")
            if "recipes" not in loaded:
                loaded["recipes"] = {}
            if not isinstance(loaded["recipes"], dict):
                raise ValueError("recipe store 'recipes' must be an object")
            return loaded
        except json.JSONDecodeError as exc:
            raise ValueError(f"recipe store is not valid JSON: {store_path}") from exc
        except FSPathError as exc:
            if str(exc).startswith("read target does not exist"):
                return {"schema_version": "1.0.0", "recipes": {}}
            raise

    def _write_credential_vault_proof(self, scopes: List[str]) -> None:
        cred_file = self.credential_vault.credentials_file
        salt_file = self.credential_vault.salt_file

        cred_hash = hashlib.sha256(cred_file.read_bytes()).hexdigest()
        salt_hash = hashlib.sha256(salt_file.read_bytes()).hexdigest()

        proof = {
            "schema_version": "1.0.0",
            "cipher": "AES-256-GCM",
            "credentials_file": str(cred_file),
            "credentials_sha256": cred_hash,
            "salt_file": str(salt_file),
            "salt_sha256": salt_hash,
            "scopes": scopes,
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }

        proof_path = self.phase_dir / "credential_vault_proof.json"
        proof_path.write_text(json.dumps(proof, sort_keys=True, indent=2), encoding="utf-8")

    def _append_cli_event(self, event_type: str, data: Dict[str, Any]) -> None:
        event = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "event_type": event_type,
            "prev_hash": self._cli_prev_hash,
            "data": data,
        }
        canonical = json.dumps(event, sort_keys=True, separators=(",", ":"))
        event_hash = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
        event["event_hash"] = event_hash

        with self.cli_proof_log.open("a", encoding="utf-8") as f:
            f.write(json.dumps(event, sort_keys=True) + "\n")

        self._cli_prev_hash = event_hash

    @staticmethod
    def _load_tail_hash(path: Path) -> str:
        if not path.exists():
            return GENESIS_HASH

        last_line = ""
        with path.open("r", encoding="utf-8") as f:
            for line in f:
                stripped = line.strip()
                if stripped:
                    last_line = stripped

        if not last_line:
            return GENESIS_HASH

        payload = json.loads(last_line)
        value = payload.get("event_hash")
        return str(value) if value else GENESIS_HASH


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="solace", description="Solace Phase 1.5 CLI")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("init")

    auth = sub.add_parser("auth")
    auth_sub = auth.add_subparsers(dest="auth_command", required=True)
    login = auth_sub.add_parser("login")
    login.add_argument("--password", required=True)
    login.add_argument("--ttl", type=int, default=3600)

    recipe = sub.add_parser("recipe")
    recipe_sub = recipe.add_subparsers(dest="recipe_command", required=True)
    submit = recipe_sub.add_parser("submit")
    submit.add_argument("path")
    submit.add_argument("--password", required=True)

    run = recipe_sub.add_parser("run")
    run.add_argument("name")
    run.add_argument("--password", required=True)
    run.add_argument("--seed", type=int, default=0)

    status = sub.add_parser("status")
    status.add_argument("--password", required=False)

    return parser


def main(argv: Optional[List[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    cli = SolaceCLI()

    if args.command == "init":
        payload = cli.init()
    elif args.command == "auth" and args.auth_command == "login":
        payload = cli.auth_login(password=args.password, ttl_seconds=args.ttl)
    elif args.command == "recipe" and args.recipe_command == "submit":
        payload = cli.recipe_submit(args.path, password=args.password)
    elif args.command == "recipe" and args.recipe_command == "run":
        payload = cli.recipe_run(args.name, password=args.password, seed=args.seed)
    elif args.command == "status":
        payload = cli.status(password=args.password)
    else:
        parser.error("unsupported command")

    print(json.dumps(payload, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
