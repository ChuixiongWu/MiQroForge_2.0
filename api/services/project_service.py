"""项目管理服务 — 文件系统 CRUD。"""

from __future__ import annotations

import json
import secrets
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from api.config import get_settings
from api.models.projects import (
    CanvasState,
    ConversationDetail,
    ConversationMeta,
    ProjectMeta,
    SnapshotMeta,
)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _new_project_id() -> str:
    return f"proj_{secrets.token_hex(5)}"


def _new_conversation_id() -> str:
    date_part = datetime.now(timezone.utc).strftime("%Y%m%d")
    rand = secrets.token_hex(3)
    return f"conv_{date_part}-{rand}"


def _new_snapshot_id() -> str:
    ts = int(datetime.now(timezone.utc).timestamp())
    rand = secrets.token_hex(3)
    return f"snap_{ts}-{rand}"


class ProjectService:
    def __init__(self) -> None:
        self.settings = get_settings()
        self.projects_root: Path = self.settings.userdata_root / "projects"
        self.projects_root.mkdir(parents=True, exist_ok=True)
        self.registry_path = self.projects_root / "registry.json"

    # ── Registry helpers ───────────────────────────────────────────────────

    def _read_registry(self) -> dict[str, Any]:
        if self.registry_path.exists():
            try:
                reg = json.loads(self.registry_path.read_text())
                # 自动修复：registry 条目数明显少于磁盘目录数 → 重建
                disk_count = sum(1 for c in self.projects_root.iterdir()
                                 if c.is_dir() and c.name.startswith("proj_"))
                if disk_count > len(reg.get("projects", [])):
                    return self._rebuild_registry()
                return reg
            except (json.JSONDecodeError, OSError):
                pass
        return {"version": 1, "projects": []}

    def _write_registry(self, reg: dict[str, Any]) -> None:
        # 原子写入：先写临时文件再 rename，避免并发覆盖
        tmp = self.registry_path.with_suffix(".tmp")
        tmp.write_text(json.dumps(reg, indent=2, ensure_ascii=False))
        tmp.replace(self.registry_path)

    def _rebuild_registry(self) -> dict[str, Any]:
        """扫描 projects/ 目录重建 registry。"""
        projects: list[dict[str, Any]] = []
        for child in sorted(self.projects_root.iterdir()):
            if not child.is_dir() or not child.name.startswith("proj_"):
                continue
            pj = child / "project.json"
            if pj.exists():
                try:
                    data = json.loads(pj.read_text())
                    projects.append(data)
                except (json.JSONDecodeError, OSError):
                    pass
        reg: dict[str, Any] = {"version": 1, "projects": projects}
        self._write_registry(reg)
        return reg

    def _update_registry_entry(self, meta: dict[str, Any]) -> None:
        reg = self._read_registry()
        found = False
        for i, p in enumerate(reg["projects"]):
            if p.get("id") == meta["id"]:
                reg["projects"][i] = meta
                found = True
                break
        if not found:
            reg["projects"].append(meta)
        self._write_registry(reg)

    def _remove_registry_entry(self, project_id: str) -> None:
        reg = self._read_registry()
        reg["projects"] = [p for p in reg["projects"] if p.get("id") != project_id]
        self._write_registry(reg)

    def _count_runs(self, project_dir: Path) -> int:
        runs_dir = project_dir / "runs"
        if not runs_dir.is_dir():
            return 0
        return sum(1 for d in runs_dir.iterdir() if d.is_dir())

    @staticmethod
    def _parse_ts(iso: str) -> float:
        try:
            return datetime.fromisoformat(iso).timestamp()
        except (ValueError, TypeError):
            return 0.0

    def _count_conversations(self, project_dir: Path) -> int:
        conv_dir = project_dir / "conversations"
        if not conv_dir.is_dir():
            return 0
        return sum(1 for d in conv_dir.iterdir() if d.is_dir())

    def _canvas_node_count(self, project_dir: Path) -> int:
        canvas_file = project_dir / "canvas.json"
        if not canvas_file.exists():
            return 0
        try:
            data = json.loads(canvas_file.read_text())
            return len(data.get("nodes", []))
        except (json.JSONDecodeError, OSError):
            return 0

    def _build_meta(self, raw: dict[str, Any], project_dir: Path) -> dict[str, Any]:
        return {
            **raw,
            "canvas_node_count": self._canvas_node_count(project_dir),
            "run_count": self._count_runs(project_dir),
            "conversation_count": self._count_conversations(project_dir),
        }

    # ── CRUD ───────────────────────────────────────────────────────────────

    def list_projects(self) -> list[dict[str, Any]]:
        reg = self._read_registry()
        results: list[dict[str, Any]] = []
        for p in reg["projects"]:
            pid = p.get("id", "")
            project_dir = self.projects_root / pid
            if project_dir.is_dir():
                results.append(self._build_meta(p, project_dir))
        # Sort by order ascending, then updated_at descending
        results.sort(key=lambda p: (p.get("order", 0), -(self._parse_ts(p.get("updated_at", "")))))
        return results

    def create_project(self, name: str, description: str = "", icon: str = "") -> dict[str, Any]:
        pid = _new_project_id()
        now = _now_iso()
        project_dir = self.projects_root / pid
        project_dir.mkdir(parents=True)
        (project_dir / "conversations").mkdir()
        (project_dir / "runs").mkdir()
        (project_dir / "snapshots").mkdir()
        # 项目文件实际存储在 workspace/.files/{pid}/，此处 symlink 方便查找
        files_real = self.settings.userdata_root / "workspace" / ".files" / pid
        files_real.mkdir(parents=True, exist_ok=True)
        files_link = project_dir / "files"
        if not files_link.exists():
            files_link.symlink_to(files_real)

        # Compute order: max existing order + 1
        reg = self._read_registry()
        max_order = max((p.get("order", 0) for p in reg["projects"]), default=-1) + 1

        meta_raw: dict[str, Any] = {
            "id": pid,
            "name": name,
            "description": description,
            "icon": icon,
            "created_at": now,
            "updated_at": now,
            "order": max_order,
        }
        meta = self._build_meta(meta_raw, project_dir)
        (project_dir / "project.json").write_text(
            json.dumps(meta, indent=2, ensure_ascii=False)
        )
        self._update_registry_entry(meta)

        # Initialize empty canvas
        canvas = CanvasState()
        (project_dir / "canvas.json").write_text(
            canvas.model_dump_json(indent=2)
        )

        return meta

    def get_project(self, project_id: str) -> dict[str, Any] | None:
        project_dir = self.projects_root / project_id
        pj = project_dir / "project.json"
        if not pj.exists():
            return None
        try:
            raw = json.loads(pj.read_text())
        except (json.JSONDecodeError, OSError):
            return None
        return self._build_meta(raw, project_dir)

    def update_project(
        self, project_id: str, name: str | None = None, description: str | None = None,
        icon: str | None = None, order: int | None = None,
    ) -> dict[str, Any] | None:
        project_dir = self.projects_root / project_id
        pj = project_dir / "project.json"
        if not pj.exists():
            return None
        try:
            raw = json.loads(pj.read_text())
        except (json.JSONDecodeError, OSError):
            return None

        if name is not None:
            raw["name"] = name
        if description is not None:
            raw["description"] = description
        if icon is not None:
            raw["icon"] = icon
        if order is not None:
            raw["order"] = order
        raw["updated_at"] = _now_iso()

        meta = self._build_meta(raw, project_dir)
        pj.write_text(json.dumps(meta, indent=2, ensure_ascii=False))
        self._update_registry_entry(meta)
        return meta

    def delete_project(self, project_id: str) -> bool:
        project_dir = self.projects_root / project_id
        if not project_dir.is_dir():
            return False
        # 清理 workspace 文件目录
        files_dir = self.settings.userdata_root / "workspace" / ".files" / project_id
        if files_dir.is_dir():
            shutil.rmtree(files_dir)
        shutil.rmtree(project_dir)
        self._remove_registry_entry(project_id)
        return True

    def duplicate_project(self, project_id: str, new_name: str | None = None) -> dict[str, Any] | None:
        src_dir = self.projects_root / project_id
        if not src_dir.is_dir():
            return None

        new_pid = _new_project_id()
        dst_dir = self.projects_root / new_pid
        shutil.copytree(src_dir, dst_dir)

        # Read original meta
        pj = dst_dir / "project.json"
        try:
            raw = json.loads(pj.read_text())
        except (json.JSONDecodeError, OSError):
            raw = {"id": project_id, "name": project_id}

        now = _now_iso()
        raw["id"] = new_pid
        raw["name"] = new_name or f"{raw.get('name', 'Untitled')} (copy)"
        raw["created_at"] = now
        raw["updated_at"] = now

        meta = self._build_meta(raw, dst_dir)
        pj.write_text(json.dumps(meta, indent=2, ensure_ascii=False))
        self._update_registry_entry(meta)
        return meta

    def reorder_projects(self, ordered_ids: list[str]) -> None:
        """Update order field for each project based on position in list."""
        for idx, pid in enumerate(ordered_ids):
            project_dir = self.projects_root / pid
            pj = project_dir / "project.json"
            if not pj.exists():
                continue
            try:
                raw = json.loads(pj.read_text())
            except (json.JSONDecodeError, OSError):
                continue
            raw["order"] = idx
            pj.write_text(json.dumps(raw, indent=2, ensure_ascii=False))
            self._update_registry_entry(raw)

    def batch_delete_projects(self, project_ids: list[str]) -> list[str]:
        """Delete multiple projects. Returns list of successfully deleted IDs."""
        deleted: list[str] = []
        for pid in project_ids:
            if self.delete_project(pid):
                deleted.append(pid)
        return deleted

    # ── Canvas ─────────────────────────────────────────────────────────────

    def save_canvas(self, project_id: str, canvas: dict[str, Any]) -> bool:
        project_dir = self.projects_root / project_id
        if not project_dir.is_dir():
            return False
        (project_dir / "canvas.json").write_text(
            json.dumps(canvas, indent=2, ensure_ascii=False)
        )
        # Touch updated_at
        self.update_project(project_id)
        return True

    def load_canvas(self, project_id: str) -> dict[str, Any] | None:
        project_dir = self.projects_root / project_id
        f = project_dir / "canvas.json"
        if not f.exists():
            return None
        try:
            return json.loads(f.read_text())
        except (json.JSONDecodeError, OSError):
            return None

    # ── After-run Canvas ───────────────────────────────────────────────────

    def save_afterrun_canvas(self, project_id: str, run_name: str, canvas: dict[str, Any]) -> bool:
        run_dir = self.projects_root / project_id / "runs" / run_name
        if not run_dir.is_dir():
            run_dir.mkdir(parents=True, exist_ok=True)
        (run_dir / "afterrun_canvas.json").write_text(
            json.dumps(canvas, indent=2, ensure_ascii=False)
        )
        return True

    def load_afterrun_canvas(self, project_id: str, run_name: str) -> dict[str, Any] | None:
        f = self.projects_root / project_id / "runs" / run_name / "afterrun_canvas.json"
        if not f.exists():
            return None
        try:
            return json.loads(f.read_text())
        except (json.JSONDecodeError, OSError):
            return None

    # ── Conversations ──────────────────────────────────────────────────────

    def list_conversations(self, project_id: str) -> list[dict[str, Any]]:
        conv_dir = self.projects_root / project_id / "conversations"
        if not conv_dir.is_dir():
            return []
        results: list[dict[str, Any]] = []
        for child in sorted(conv_dir.iterdir()):
            if not child.is_dir():
                continue
            cf = child / "conversation.json"
            if cf.exists():
                try:
                    data = json.loads(cf.read_text())
                    results.append({
                        "id": data.get("id", child.name),
                        "title": data.get("title", child.name),
                        "created_at": data.get("created_at", ""),
                        "updated_at": data.get("updated_at", ""),
                        "message_count": len(data.get("messages", [])),
                    })
                except (json.JSONDecodeError, OSError):
                    pass
        return results

    def create_conversation(
        self, project_id: str, title: str = "New Chat"
    ) -> dict[str, Any] | None:
        conv_dir = self.projects_root / project_id / "conversations"
        if not conv_dir.is_dir():
            return None
        cid = _new_conversation_id()
        now = _now_iso()
        conv_path = conv_dir / cid
        conv_path.mkdir()
        detail: dict[str, Any] = {
            "id": cid,
            "title": title,
            "messages": [],
            "created_at": now,
            "updated_at": now,
        }
        (conv_path / "conversation.json").write_text(
            json.dumps(detail, indent=2, ensure_ascii=False)
        )
        (conv_path / "agent_logs").mkdir()
        return {
            "id": cid,
            "title": title,
            "created_at": now,
            "updated_at": now,
            "message_count": 0,
        }

    def load_conversation(self, project_id: str, conv_id: str) -> dict[str, Any] | None:
        f = self.projects_root / project_id / "conversations" / conv_id / "conversation.json"
        if not f.exists():
            return None
        try:
            return json.loads(f.read_text())
        except (json.JSONDecodeError, OSError):
            return None

    def save_conversation_messages(
        self, project_id: str, conv_id: str, messages: list[dict[str, Any]]
    ) -> bool:
        f = self.projects_root / project_id / "conversations" / conv_id / "conversation.json"
        if not f.exists():
            return False
        try:
            data = json.loads(f.read_text())
        except (json.JSONDecodeError, OSError):
            return False
        data["messages"] = messages
        data["updated_at"] = _now_iso()
        f.write_text(json.dumps(data, indent=2, ensure_ascii=False))
        return True

    def delete_conversation(self, project_id: str, conv_id: str) -> bool:
        conv_path = self.projects_root / project_id / "conversations" / conv_id
        if not conv_path.is_dir():
            return False
        shutil.rmtree(conv_path)
        return True

    # ── Snapshots ──────────────────────────────────────────────────────────

    def list_snapshots(self, project_id: str) -> list[dict[str, Any]]:
        snap_dir = self.projects_root / project_id / "snapshots"
        if not snap_dir.is_dir():
            return []
        results: list[dict[str, Any]] = []
        for child in sorted(snap_dir.iterdir()):
            if child.suffix != ".json":
                continue
            try:
                data = json.loads(child.read_text())
                results.append({
                    "id": data.get("id", child.stem),
                    "name": data.get("name", child.stem),
                    "created_at": data.get("created_at", ""),
                    "canvas_node_count": len(data.get("canvas", {}).get("nodes", [])),
                })
            except (json.JSONDecodeError, OSError):
                pass
        return results

    def create_snapshot(
        self, project_id: str, name: str, canvas: dict[str, Any]
    ) -> dict[str, Any] | None:
        snap_dir = self.projects_root / project_id / "snapshots"
        if not snap_dir.is_dir():
            return None

        # If a snapshot with the same name exists, overwrite it
        existing_id: str | None = None
        for child in snap_dir.iterdir():
            if child.suffix != ".json":
                continue
            try:
                data = json.loads(child.read_text())
                if data.get("name") == name:
                    existing_id = data.get("id", child.stem)
                    break
            except (json.JSONDecodeError, OSError):
                pass

        now = _now_iso()
        if existing_id:
            sid = existing_id
            # Remove old file in case the filename differs from the id
            for child in snap_dir.glob("*.json"):
                try:
                    data = json.loads(child.read_text())
                    if data.get("id") == existing_id:
                        child.unlink()
                        break
                except (json.JSONDecodeError, OSError):
                    pass
        else:
            sid = _new_snapshot_id()

        entry: dict[str, Any] = {
            "id": sid,
            "name": name,
            "created_at": now,
            "canvas": canvas,
        }
        (snap_dir / f"{sid}.json").write_text(
            json.dumps(entry, indent=2, ensure_ascii=False)
        )
        return {
            "id": sid,
            "name": name,
            "created_at": now,
            "canvas_node_count": len(canvas.get("nodes", [])),
        }

    def delete_snapshot(self, project_id: str, snapshot_id: str) -> bool:
        f = self.projects_root / project_id / "snapshots" / f"{snapshot_id}.json"
        if not f.exists():
            return False
        f.unlink()
        return True
