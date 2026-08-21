"""Exercise packaged E02 and E03 workflows through the native UIA boundary."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import subprocess
import tempfile
import time
from typing import Any

import psutil
from pywinauto import Desktop

WINDOW_TITLE = "PSYCHE OS — Управление локальным хранилищем"
SECRET_CANARY = "E02-SECRET-CANARY-8ca4c3"
MARKUP_CANARY = '<img src=x onerror="alert(1)"><script>bad()</script>'


def wait_for_text(window: Any, needle: str, timeout: float = 20.0) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        text = "\n".join(control.window_text() for control in window.descendants())
        if needle in text:
            return
        time.sleep(0.2)
    raise AssertionError(f"Timed out waiting for UI state: {needle}")


def edit(window: Any, title: str, value: str) -> None:
    control = window.child_window(title=title, control_type="Edit").wait("exists", 8)
    control.set_focus()
    control = window.child_window(title=title, control_type="Edit").wait("ready", 8)
    control.set_edit_text(value)


def edit_id(window: Any, automation_id: str, value: str) -> None:
    control = window.child_window(auto_id=automation_id, control_type="Edit").wait("ready", 8)
    control.set_edit_text(value)


def find_editable(window: Any, accessible_name: str) -> Any:
    """Focus the observed native WebView2 Edit and reacquire it after scrolling."""
    control = window.child_window(title=accessible_name, control_type="Edit").wait("exists", 8)
    control.set_focus()
    return window.child_window(title=accessible_name, control_type="Edit").wait("ready", 8)


def enter_editable(window: Any, accessible_name: str, value: str) -> None:
    control = find_editable(window, accessible_name)
    control.type_keys(value, with_spaces=True)
    deadline = time.monotonic() + 2.0
    actual = ""
    while time.monotonic() < deadline:
        actual = control.get_value()
        if actual == value:
            return
        time.sleep(0.05)
    raise AssertionError(
        f"Native editable control did not retain entered value: {accessible_name}; observed {actual!r}"
    )


def click(window: Any, title: str) -> None:
    control = window.child_window(title=title, control_type="Button").wait("exists", 8)
    control.invoke()


def process_evidence(root_pid: int) -> dict[str, Any]:
    root = psutil.Process(root_pid)
    descendants = root.children(recursive=True)
    names = sorted({process.name().lower() for process in descendants if process.is_running()})
    if not any("msedgewebview2" in name for name in names):
        raise AssertionError(f"WebView2 child process was not observed: {names}")
    if not any("psyche-os-sidecar" in name for name in names):
        raise AssertionError(f"Packaged fixed sidecar process was not observed: {names}")

    owned_pids = {root_pid, *(process.pid for process in descendants)}
    listeners: list[dict[str, Any]] = []
    application_connections: list[dict[str, Any]] = []
    webview_background_connections: list[dict[str, Any]] = []
    for connection in psutil.net_connections(kind="inet"):
        if connection.pid in owned_pids:
            try:
                process_name = psutil.Process(connection.pid).name().lower()
            except psutil.Error:
                process_name = "unavailable"
            detail = {
                "pid": connection.pid,
                "process_name": process_name,
                "local_address": str(connection.laddr),
                "remote_address": str(connection.raddr),
                "status": connection.status,
            }
            if connection.status == psutil.CONN_LISTEN:
                listeners.append(detail)
            elif "msedgewebview2" in process_name:
                webview_background_connections.append(detail)
            else:
                application_connections.append(detail)
    if listeners:
        raise AssertionError(f"Desktop process tree opened a listener: {listeners}")
    if application_connections:
        raise AssertionError(
            "Desktop or fixed sidecar used an INET connection: "
            f"{application_connections}"
        )
    return {
        "process_names": names,
        "listeners": listeners,
        "application_connections": application_connections,
        "webview_background_connections": webview_background_connections,
        "offline_workflows_completed": True,
    }


def terminate_tree(process: subprocess.Popen[bytes]) -> None:
    try:
        root = psutil.Process(process.pid)
        children = root.children(recursive=True)
        for child in children:
            child.terminate()
        root.terminate()
        _, alive = psutil.wait_procs([*children, root], timeout=5)
        for survivor in alive:
            survivor.kill()
    except psutil.Error:
        pass


def _launch(executable: Path, app_data: Path) -> subprocess.Popen[bytes]:
    environment = os.environ.copy()
    environment["PSYCHE_OS_APP_DATA"] = str(app_data)
    return subprocess.Popen([str(executable)], cwd=executable.parent, stdin=subprocess.DEVNULL,
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, env=environment)


def restart_persistence_proof(executable: Path, app_data: Path) -> dict[str, Any]:
    title = "UIA тестовая сессия"
    canary = "V3A0-UIA-RESTART-CANARY"
    first = _launch(executable, app_data)
    try:
        window = Desktop(backend="uia").window(process=first.pid, title=WINDOW_TITLE)
        window.wait("visible", timeout=20)
        edit(window, "Локальный секрет сессии", SECRET_CANARY)
        click(window, "Разблокировать локально")
        wait_for_text(window, "МОИ СЕССИИ")
        edit(window, "Название", title)
        click(window, "Новая сессия")
        wait_for_text(window, "Добавить в сессию")
        enter_editable(window, "Ваш текст", canary)
        click(window, "Добавить в сессию")
        wait_for_text(window, canary)
    finally:
        terminate_tree(first)
    if psutil.pid_exists(first.pid):
        raise AssertionError("First desktop process survived restart boundary")

    second = _launch(executable, app_data)
    try:
        window = Desktop(backend="uia").window(process=second.pid, title=WINDOW_TITLE)
        window.wait("visible", timeout=20)
        edit(window, "Локальный секрет сессии", SECRET_CANARY)
        click(window, "Разблокировать локально")
        wait_for_text(window, title)
        click(window, "Открыть")
        wait_for_text(window, canary)
        enter_editable(window, "Ваш текст", "V3A0-UIA-SECOND-TURN")
        click(window, "Добавить в сессию")
        wait_for_text(window, "V3A0-UIA-SECOND-TURN")
        click(window, "Завершить сессию")
        wait_for_text(window, "Сессия завершена")
        if window.child_window(title="Добавить в сессию", control_type="Button").is_enabled():
            raise AssertionError("Closed session still accepts turns")
        click(window, "Удалить сессию")
        wait_for_text(window, "МОИ СЕССИИ")
        if title in "\n".join(control.window_text() for control in window.descendants()):
            raise AssertionError("Deleted session remains in list")
        return {"first_pid": first.pid, "second_pid": second.pid,
                "persistence_canary": canary, "restart_persistence": True}
    finally:
        terminate_tree(second)


def run(executable: Path, app_data: Path) -> dict[str, Any]:
    if not executable.is_file():
        raise SystemExit(f"Desktop executable does not exist: {executable}")
    process = _launch(executable, app_data)
    try:
        window = Desktop(backend="uia").window(process=process.pid, title=WINDOW_TITLE)
        window.wait("visible", timeout=20)

        edit(window, "Локальный секрет сессии", SECRET_CANARY)
        click(window, "Разблокировать локально")
        wait_for_text(window, "Ваш локальный центр управления")
        visible_text = "\n".join(control.window_text() for control in window.descendants())
        if SECRET_CANARY in visible_text:
            raise AssertionError("Unlock secret leaked into the native accessibility surface")
        for required in ("Только синтетические данные", "Закрыт", "Без сети и слушателей", "Отключено"):
            if required not in visible_text:
                raise AssertionError(f"Missing privacy/runtime status: {required}")

        edit(window, "Исправленное синтетическое наблюдение", MARKUP_CANARY)
        edit(window, "Причина исправления", "Проверка безопасности синтетического UIA")
        click(window, "Сохранить историю и исправить")
        wait_for_text(window, "Исправление применено к этой синтетической сессии; предыдущая версия сессии сохранена.")
        if len(Desktop(backend="uia").windows(process=process.pid, title=WINDOW_TITLE)) != 1:
            raise AssertionError("Untrusted markup changed the native window surface")

        click(window, "Предпросмотр области удаления")
        wait_for_text(window, "Это только пробный запуск удаления; ничего не удалено.")
        click(window, "Подтвердить удаление")
        wait_for_text(window, "Удаление в синтетической сессии применено с указанными ограничениями; каноническая запись не изменена.")

        click(window, "Проверить резервную копию")
        wait_for_text(window, "Резервная копия проверена без раскрытия содержимого.")
        click(window, "Проверить изолированное восстановление")
        wait_for_text(window, "Кандидат проверен; активное хранилище не изменено.")
        click(window, "Активировать проверенного кандидата")
        wait_for_text(window, "Проверенный кандидат активирован отдельно.")

        edit(window, "Цель", "portability")
        edit(window, "Получатель", "owner")
        edit(window, "Область", "synthetic minimum")
        click(window, "Предпросмотр экспорта")
        wait_for_text(window, "Предпросмотр экспорта: пока ничего не записано.")
        click(window, "Подтвердить синтетический экспорт")
        wait_for_text(window, "Экспорт завершён. Это не резервная копия.")

        # E03-T1..T7: only fixed fictional operations are available.  Exercise
        # the canonical sequence through the packaged Rust/Python boundary.
        window.set_focus()
        window.type_keys("{END}")
        time.sleep(0.5)
        for label in (
            "Зафиксировать отчёт о лампе",
            "Зафиксировать наблюдение лампы",
            "Зафиксировать контротчёт",
            "Собрать эпистемический набор",
            "Создать исходный снимок",
            "Создать обновлённый снимок",
            "Исправить время отчёта канонически",
        ):
            click(window, label)
            wait_for_text(window, f"{label}. Операция выполнена для встроенного вымышленного набора.")
        click(window, "Загрузить выбранную шкалу")
        wait_for_text(window, "Шкала использует «Событие произошло»")
        click(window, "Открыть обозреватель доказательств")
        wait_for_text(window, "Предложение не является фактом или доказательством.")
        click(window, "Сравнить снимки модели")
        wait_for_text(window, "неразрешённое состояние остаётся видимым")
        click(window, "Предпросмотр канонического удаления")
        wait_for_text(window, "Это только пробный запуск канонического удаления; состояние не изменено.")
        click(window, "Подтвердить каноническое удаление")
        wait_for_text(window, "квитанция не содержит удалённых данных или стабильного хеша содержимого")

        evidence = process_evidence(process.pid)
        evidence.update(
            {
                "native_window": True,
                "uia_workflows": [
                    "unlock",
                    "correction",
                    "deletion",
                    "backup_verify",
                    "recovery_validate_activate",
                    "export_preview_execute",
                    "e03_fixed_capture",
                    "e03_explicit_timeline",
                    "e03_epistemic_explorer",
                    "e03_snapshot_diff",
                    "e03_canonical_correction_deletion",
                ],
                "secret_surface_clean": True,
                "malicious_markup_inert": True,
            }
        )
        return evidence
    finally:
        terminate_tree(process)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--executable", required=True, type=Path)
    args = parser.parse_args()
    with tempfile.TemporaryDirectory(prefix="psyche-os-v3a0-uia-") as temporary:
        app_data = Path(temporary)
        restart = restart_persistence_proof(args.executable.resolve(), app_data)
        evidence = run(args.executable.resolve(), app_data)
        evidence.update(restart)
    print(json.dumps(evidence, indent=2, sort_keys=True))
    print("E02_NATIVE_DESKTOP_UIA: PASS")
    print("E03_NATIVE_DESKTOP_UIA: PASS")
    print("V3A0_NATIVE_TURN_ENTRY: PASS")
    print("V3A0_NATIVE_RESTART_PERSISTENCE: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
