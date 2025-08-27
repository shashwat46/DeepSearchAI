import asyncio
import os
import sys
import re
import time
from typing import Dict, Any, List, Optional, Tuple

import phonenumbers

from .base import BaseTool
from services.service_ids import canonicalize_service


_LINE_RE = re.compile(r'^\[(\+|\-|x)\]\s+(.+)$')


def _extract_marker(line: str) -> Optional[Tuple[str, str]]:
    s = line.strip()
    if not s.startswith("["):
        return None
    m = _LINE_RE.match(s)
    if not m:
        return None
    return m.group(1), m.group(2).strip()


def _split_phone(e164: str) -> Optional[Tuple[str, str]]:
    try:
        parsed = phonenumbers.parse(e164)
        cc = str(parsed.country_code)
        nn = str(parsed.national_number)
        return cc, nn
    except Exception:
        return None


class IgnorantCliTool(BaseTool):
    @property
    def name(self) -> str:
        return "ignorant_cli"

    @property
    def stage(self) -> str:
        return "shallow"

    def can_handle(self, params: Dict[str, Any]) -> bool:
        return bool(params.get("phone"))

    async def execute(self, params: Dict[str, Any]) -> Dict[str, Any]:
        raw_phone = (params.get("phone") or "").strip()
        try:
            parsed = phonenumbers.parse(raw_phone, "US")
            e164 = phonenumbers.format_number(parsed, phonenumbers.PhoneNumberFormat.E164)
        except Exception:
            e164 = raw_phone
        split = _split_phone(e164)
        if not split:
            return {"source": "Ignorant", "raw_data": {"schema_version": "1.0", "phone": e164, "error": "invalid_phone"}}
        country_code, national_number = split

        timeout = int(os.getenv("IGNORANT_CLI_TIMEOUT", "60"))
        started_at = time.time()

        cmds: List[List[str]] = [
            ["ignorant", country_code, national_number],
            [sys.executable, "-m", "ignorant", country_code, national_number],
        ]

        stdout_text = ""
        stderr_text = ""
        rc = 1
        cmd_used = None

        for cmd in cmds:
            try:
                cmd_used = " ".join(cmd)
                proc = await asyncio.create_subprocess_exec(
                    *cmd,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                    env=dict(os.environ, PYTHONIOENCODING="utf-8"),
                )
                try:
                    stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout)
                except asyncio.TimeoutError:
                    proc.kill()
                    await proc.wait()
                    return {"source": "Ignorant", "raw_data": {"schema_version": "1.0", "phone": e164, "country_code": country_code, "national_number": national_number, "error": "timeout", "command_used": cmd_used}}
                rc = proc.returncode
                stdout_text = stdout.decode("utf-8", errors="ignore")
                stderr_text = stderr.decode("utf-8", errors="ignore")
                if rc == 0 or stdout_text:
                    break
            except FileNotFoundError:
                continue
            except Exception as e:
                return {"source": "Ignorant", "raw_data": {"schema_version": "1.0", "phone": e164, "country_code": country_code, "national_number": national_number, "error": f"execution failed: {e}"}}

        used_ids: List[str] = []
        used_labels: List[str] = []
        rate_limited_ids: List[str] = []
        checked = 0

        for raw_line in stdout_text.splitlines():
            mark = _extract_marker(raw_line)
            if not mark:
                continue
            status, label = mark
            canon = canonicalize_service(label)
            if not canon:
                continue
            service_id, host_label = canon
            checked += 1
            if status == "+":
                if service_id not in used_ids:
                    used_ids.append(service_id)
                    used_labels.append(host_label)
            elif status == "x":
                if service_id not in rate_limited_ids:
                    rate_limited_ids.append(service_id)

        finished_at = time.time()
        raw = {
            "schema_version": "1.0",
            "phone": e164,
            "country_code": country_code,
            "national_number": national_number,
            "used_services": used_labels,
            "used_service_ids": used_ids,
            "rate_limited_service_ids": rate_limited_ids,
            "checked_count": checked,
            "command_used": cmd_used,
            "started_at": started_at,
            "finished_at": finished_at,
        }
        if rc != 0 and not used_ids and not rate_limited_ids:
            raw["warning"] = "ignorant exited non-zero"
            if stderr_text:
                raw["stderr"] = stderr_text.strip()[:2000]

        return {"source": "Ignorant", "raw_data": raw}



