"""
MCP Weather Client — PoC Test Harness
======================================
1. weather_api.py (mock REST API) arka planda başlatılır
2. server.py (MCP Server) stdio üzerinden çalıştırılır ve API'ye bağlanır
3. Testler koşulur:
   - list_tools  → Handshake doğrulama
   - get_weather → Başarılı çağrı & şema doğrulama
   - get_weather → Geçersiz girdi ile hata doğrulama (Schema Validation)
   - Type Safety  → temperature her zaman float mı?
"""

from __future__ import annotations

import asyncio
import json
import subprocess
import sys
import time
from datetime import datetime

import httpx
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

SERVER_SCRIPT = "server.py"
API_SCRIPT = "weather_api.py"
API_HOST = "127.0.0.1"
API_PORT = 8000
API_BASE_URL = f"http://{API_HOST}:{API_PORT}"

# ── Helpers ───────────────────────────────────────────────────────────────────
VALID_CONDITIONS = {"Sunny", "Cloudy", "Rainy", "Snowy"}


def _validate_weather_response(data: dict) -> list[str]:
    """Spec §3 şemasına göre yanıtı doğrula. Hata mesajları listesi döner."""
    errors: list[str] = []

    # temperature → float
    temp = data.get("temperature")
    if not isinstance(temp, (float, int)):
        errors.append(f"temperature float olmalı, gelen: {type(temp).__name__}")
    elif not isinstance(temp, float):
        errors.append(f"temperature int değil float olmalı, gelen: {temp}")

    # condition → enum
    cond = data.get("condition")
    if cond not in VALID_CONDITIONS:
        errors.append(f"condition geçersiz: '{cond}'. Beklenen: {VALID_CONDITIONS}")

    # timestamp → ISO8601
    ts = data.get("timestamp")
    if ts:
        try:
            datetime.strptime(ts, "%Y-%m-%dT%H:%M:%SZ")
        except ValueError:
            errors.append(f"timestamp ISO8601 formatında değil: '{ts}'")
    else:
        errors.append("timestamp alanı eksik")

    return errors


def _print_result(label: str, passed: bool, detail: str = ""):
    status = "✅ PASS" if passed else "❌ FAIL"
    print(f"  {status} | {label}")
    if detail:
        print(f"         {detail}")


# ── Main test flow ────────────────────────────────────────────────────────────
async def _wait_for_api(timeout: float = 10.0) -> bool:
    """API sunucusunun hazır olmasını bekle."""
    deadline = time.monotonic() + timeout
    async with httpx.AsyncClient() as client:
        while time.monotonic() < deadline:
            try:
                resp = await client.get(f"{API_BASE_URL}/health")
                if resp.status_code == 200:
                    return True
            except httpx.ConnectError:
                pass
            await asyncio.sleep(0.3)
    return False


async def main() -> None:
    # ── 1. Mock REST API'yi arka planda başlat ────────────────────────────
    print("▶ Mock Weather API başlatılıyor...")
    api_process = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "weather_api:app",
         "--host", API_HOST, "--port", str(API_PORT)],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

    try:
        if not await _wait_for_api():
            print("❌ Mock API başlatılamadı!")
            api_process.kill()
            return
        print(f"✅ Mock API hazır: {API_BASE_URL}\n")

        # ── 2. MCP Server'ı başlat (API URL'yi env ile geçir) ────────────
        server_params = StdioServerParameters(
            command=sys.executable,
            args=[SERVER_SCRIPT],
            env={**dict(__import__("os").environ), "WEATHER_API_BASE_URL": API_BASE_URL},
        )

        print("=" * 60)
        print("  MCP Weather PoC — Test Suite")
        print("=" * 60)

        async with stdio_client(server_params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()

                # ── Test 1: Handshake / list_tools ────────────────────────
                print("\n[Test 1] Handshake — list_tools")
                tools_result = await session.list_tools()
                tools = tools_result.tools
                tool_names = [t.name for t in tools]
                has_get_weather = "get_weather" in tool_names
                _print_result(
                    "get_weather tool sunucuda tanımlı",
                    has_get_weather,
                    f"Bulunan tool'lar: {tool_names}",
                )

                if has_get_weather:
                    tool_def = next(t for t in tools if t.name == "get_weather")
                    schema = tool_def.inputSchema
                    has_city = "city" in schema.get("properties", {})
                    has_unit = "unit" in schema.get("properties", {})
                    _print_result("Input schema 'city' alanı var", has_city)
                    _print_result("Input schema 'unit' alanı var", has_unit)

                # ── Test 2: Başarılı çağrı (Istanbul, celsius) ────────────
                print("\n[Test 2] get_weather(city='Istanbul') — Başarılı çağrı")
                result = await session.call_tool("get_weather", {"city": "Istanbul"})
                # MCP tool sonucu content listesi olarak döner
                raw_text = result.content[0].text
                data = json.loads(raw_text)
                print(f"         Yanıt: {json.dumps(data, ensure_ascii=False, indent=2)}")

                schema_errors = _validate_weather_response(data)
                _print_result(
                    "Şema doğrulama (§3)",
                    len(schema_errors) == 0,
                    "; ".join(schema_errors) if schema_errors else "",
                )
                _print_result(
                    "Type Safety: temperature is float",
                    isinstance(data.get("temperature"), float),
                    f"type={type(data.get('temperature')).__name__}, value={data.get('temperature')}",
                )

                # ── Test 3: Fahrenheit birimi ─────────────────────────────
                print("\n[Test 3] get_weather(city='Ankara', unit='fahrenheit')")
                result_f = await session.call_tool(
                    "get_weather", {"city": "Ankara", "unit": "fahrenheit"}
                )
                data_f = json.loads(result_f.content[0].text)
                print(f"         Yanıt: {json.dumps(data_f, ensure_ascii=False, indent=2)}")
                _print_result(
                    "unit='fahrenheit' doğru dönüyor",
                    data_f.get("unit") == "fahrenheit",
                )
                _print_result(
                    "Type Safety: temperature is float",
                    isinstance(data_f.get("temperature"), float),
                )

                # ── Test 4: Schema Validation — geçersiz şehir adı ───────
                print("\n[Test 4] Schema Validation — geçersiz şehir adı (rakam içeren)")
                result_err = await session.call_tool(
                    "get_weather", {"city": "123Invalid!"}
                )
                is_error = result_err.isError
                error_text = result_err.content[0].text if result_err.content else ""
                _print_result(
                    "Geçersiz girdi hata döndürüyor",
                    is_error or "Geçersiz" in error_text or "Error" in error_text,
                    f"isError={is_error}, mesaj={error_text[:120]}",
                )

                # ── Test 5: Schema Validation — boş şehir ────────────────
                print("\n[Test 5] Schema Validation — boş şehir adı")
                result_empty = await session.call_tool("get_weather", {"city": ""})
                is_error_empty = result_empty.isError
                error_text_empty = (
                    result_empty.content[0].text if result_empty.content else ""
                )
                _print_result(
                    "Boş şehir adı hata döndürüyor",
                    is_error_empty or "boş" in error_text_empty.lower(),
                    f"isError={is_error_empty}, mesaj={error_text_empty[:120]}",
                )

                # ── Summary ──────────────────────────────────────────────
                print("\n" + "=" * 60)
                print("  Tüm testler tamamlandı.")
                print("=" * 60)

    finally:
        # ── Mock API sürecini temizle ─────────────────────────────────────
        api_process.terminate()
        api_process.wait(timeout=5)
        print("\n▶ Mock API kapatıldı.")


if __name__ == "__main__":
    asyncio.run(main())
