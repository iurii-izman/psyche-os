"""Exercise packaged E02 and E03 workflows through the native UIA boundary."""
# ruff: noqa: RUF001

from __future__ import annotations

import argparse
import ctypes
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
    enter_editable(window, title, value)


def edit_id(window: Any, automation_id: str, value: str) -> None:
    control = window.child_window(auto_id=automation_id, control_type="Edit").wait("ready", 8)
    control.set_edit_text(value)


def find_editable(window: Any, accessible_name: str) -> Any:
    """Reacquire the native WebView2 Edit immediately before each write."""
    control = window.child_window(title=accessible_name, control_type="Edit").wait("exists", 8)
    control.set_focus()
    return window.child_window(title=accessible_name, control_type="Edit").wait("ready", 8)


def enter_editable(window: Any, accessible_name: str, value: str) -> None:
    """Set and read back the whole value with a bounded WebView2 fallback."""
    observed = ""
    automation_id = ""
    value_pattern = False
    enabled = False
    for attempt in range(1, 4):
        control = find_editable(window, accessible_name)
        automation_id = control.element_info.automation_id
        enabled = control.is_enabled()
        if not enabled:
            raise AssertionError(f"Native editable control is disabled: {accessible_name}")
        control.set_focus()
        try:
            value_pattern = bool(control.iface_value)
        except Exception:
            value_pattern = False
        if value_pattern and attempt == 1:
            control.set_edit_text(value)
        else:
            control.type_keys("^a{BACKSPACE}" + value, with_spaces=True)
        control = find_editable(window, accessible_name)
        observed = control.get_value()
        if observed == value:
            return
        # A ValuePattern write can be accepted by UIA while WebView2 drops it.
        # Remaining attempts replace the complete value via keyboard; they never
        # append a missing suffix.
    raise AssertionError(
        "Native editable control did not retain full value: "
        f"name={accessible_name!r} automation_id={automation_id!r} attempts=3 "
        f"expected_length={len(value)} observed_length={len(observed)} "
        f"observed={observed!r} enabled={enabled} value_pattern={value_pattern}"
    )


def click(window: Any, title: str, found_index: int | None = None) -> None:
    criteria: dict[str, Any] = {"title": title, "control_type": "Button"}
    if found_index is not None:
        criteria["found_index"] = found_index
    control = window.child_window(**criteria).wait("exists", 8)
    if not control.is_enabled():
        raise AssertionError(f"Native button is disabled: {title}")
    control.invoke()


def select_id(window: Any, automation_id: str, index: int) -> None:
    control = window.child_window(auto_id=automation_id, control_type="ComboBox").wait("ready", 8)
    control.expand()
    deadline = time.monotonic() + 8
    items: list[Any] = []
    while time.monotonic() < deadline:
        items = window.descendants(control_type="ListItem")
        if len(items) > index:
            items[index].click_input()
            return
        time.sleep(0.1)
    raise AssertionError(f"Native select option is unavailable: {automation_id} index={index}")


def choose_radio(window: Any, title: str) -> None:
    control = window.child_window(title=title, control_type="RadioButton").wait("ready", 8)
    control.select()


def assert_edit_values(window: Any, expected: dict[str, str]) -> None:
    observed = {title: find_editable(window, title).get_value() for title in expected}
    if observed != expected:
        raise AssertionError(
            "UIA_INPUT_RELIABILITY before export preview: "
            f"expected={expected!r} observed={observed!r}"
        )


def assert_absent_or_disabled(window: Any, title: str, control_type: str) -> None:
    """Accept an intentionally removed control, but reject an enabled write path."""
    control = window.child_window(title=title, control_type=control_type)
    if not control.exists(timeout=1):
        return
    if control.is_enabled():
        raise AssertionError(f"Closed session still exposes an enabled control: {title}")


def _owned_pids(root_pid: int) -> set[int]:
    root = psutil.Process(root_pid)
    return {root_pid, *(process.pid for process in root.children(recursive=True))}


def refresh_window(window: Any, root_pid: int) -> tuple[Any, dict[str, Any]]:
    """Refresh a replaced WebView2 accessibility subtree through its stable HWND."""
    wrapper = window.wrapper_object()
    hwnd = int(wrapper.handle)
    markers = ("Сессия завершена", "АНАЛИТИКА СЕССИИ", "ИСТОРИЯ МОИХ СЛЕДУЮЩИХ ШАГОВ")
    text = "\n".join(control.window_text() for control in window.descendants())
    owned_pids = _owned_pids(root_pid)
    desktop = Desktop(backend="uia")
    diagnostics: dict[str, Any] = {
        "old_hwnd": hwnd,
        "old_process_id": wrapper.element_info.process_id,
        "old_title": wrapper.window_text(),
        "old_visible": wrapper.is_visible(),
        "old_enabled": wrapper.is_enabled(),
        "old_descendants_available": bool(window.descendants()),
        "old_markers": {marker: marker in text for marker in markers},
        "owned_process_ids": sorted(owned_pids),
    }
    hwnd_survives = bool(ctypes.windll.user32.IsWindow(hwnd))
    diagnostics["hwnd_survives"] = hwnd_survives
    if hwnd_survives:
        refreshed = desktop.window(handle=hwnd)
        refreshed.wait("visible", timeout=8)
        diagnostics["refresh_strategy"] = "existing_hwnd"
        diagnostics["new_process_id"] = refreshed.wrapper_object().element_info.process_id
        return refreshed, diagnostics
    candidates = []
    for candidate in desktop.windows():
        if candidate.window_text() == WINDOW_TITLE:
            candidates.append(
                {
                    "hwnd": int(candidate.handle),
                    "process_id": candidate.element_info.process_id,
                    "visible": candidate.is_visible(),
                }
            )
    diagnostics["titled_candidates"] = candidates
    owned = [
        candidate
        for candidate in candidates
        if candidate["process_id"] in owned_pids and candidate["visible"]
    ]
    if len(owned) != 1:
        raise AssertionError(
            f"UIA_WINDOW_LIFECYCLE_FAILED {json.dumps(diagnostics, sort_keys=True)}"
        )
    refreshed = desktop.window(handle=owned[0]["hwnd"])
    refreshed.wait("visible", timeout=8)
    diagnostics["refresh_strategy"] = "owned_title_fallback"
    diagnostics["new_process_id"] = refreshed.wrapper_object().element_info.process_id
    return refreshed, diagnostics


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
            f"Desktop or fixed sidecar used an INET connection: {application_connections}"
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
    return subprocess.Popen(
        [str(executable)],
        cwd=executable.parent,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        env=environment,
    )


def restart_persistence_proof(executable: Path, app_data: Path) -> dict[str, Any]:
    title = "UIA тестовая сессия"
    canary = "V3A0-UIA-RESTART-CANARY"
    first = _launch(executable, app_data)
    try:
        window = Desktop(backend="uia").window(process=first.pid, title=WINDOW_TITLE)
        window.wait("visible", timeout=20)
        wait_for_text(window, "Локальный секрет сессии")
        edit_id(window, "unlock-secret", SECRET_CANARY)
        click(window, "Разблокировать локально")
        wait_for_text(window, "МОИ СЕССИИ")
        edit(window, "Название", title)
        click(window, "Новая сессия")
        wait_for_text(window, "Добавить в сессию")
        enter_editable(window, "Ваш текст", canary)
        click(window, "Добавить в сессию")
        wait_for_text(window, canary)
        wait_for_text(window, "Рабочие гипотезы")
        wait_for_text(window, "Следующий вопрос")
        enter_editable(window, "Ответ на следующий вопрос", "SYNTHETIC-V3A1-ANSWER")
        click(window, "Ответить на следующий вопрос")
        wait_for_text(window, "SYNTHETIC-V3A1-ANSWER")
        click(window, "Составить рабочую формулировку")
        wait_for_text(window, "Рабочее предложение, не диагноз")
        enter_editable(window, "Исправление формулировки", "SYNTHETIC-V3A1-CORRECTION")
        click(window, "Исправить")
        wait_for_text(window, "SYNTHETIC-V3A1-CORRECTION")
        # Formulation history remains visible. The UI renders newest version first,
        # so select its action rather than assuming a text label is globally unique.
        click(window, "Принять как рабочую", found_index=0)
        wait_for_text(window, "CURRENT")
        # V3-A2: the projection is read-only and derives only the persisted
        # V3-A1 session state; its headings are native accessibility evidence.
        for marker in (
            "АНАЛИТИКА СЕССИИ",
            "Текущая рабочая формулировка",
            "Как менялась формулировка",
            "Матрица контекста",
            "Рабочие гипотезы и основания",
            "Противоречия / разные ответы",
            "Что остаётся неизвестным",
            "Хронология сессии",
        ):
            wait_for_text(window, marker)
        wait_for_text(window, "ИТОГ СЕССИИ")
        enter_editable(window, "Моя цель", "V3A3-SYNTHETIC-USER-GOAL")
        select_id(window, "action-anchor", 1)
        # PAUSE remains an equal safe option regardless of the selected anchor.
        wait_for_text(window, "Ничего не предпринимать сейчас и оставить вопрос открытым.")
        choose_radio(window, "Ничего не предпринимать сейчас и оставить вопрос открытым.")
        enter_editable(window, "Текст следующего шага", "V3A3-SYNTHETIC-EDITED-ACTION")
        click(window, "Сохранить мой следующий шаг")
        wait_for_text(window, "V3A3-SYNTHETIC-EDITED-ACTION")
        wait_for_text(window, "КАК ЗАКОНЧИЛОСЬ?")
    finally:
        terminate_tree(first)
    if psutil.pid_exists(first.pid):
        raise AssertionError("First desktop process survived restart boundary")

    second = _launch(executable, app_data)
    try:
        window = Desktop(backend="uia").window(process=second.pid, title=WINDOW_TITLE)
        window.wait("visible", timeout=20)
        wait_for_text(window, "Локальный секрет сессии")
        edit_id(window, "unlock-secret", SECRET_CANARY)
        click(window, "Разблокировать локально")
        wait_for_text(window, title)
        click(window, "Открыть")
        wait_for_text(window, canary)
        wait_for_text(window, "SYNTHETIC-V3A1-CORRECTION")
        wait_for_text(window, "АНАЛИТИКА СЕССИИ")
        wait_for_text(window, "Текущая рабочая формулировка")
        wait_for_text(window, "Хронология сессии")
        wait_for_text(window, "ИТОГ СЕССИИ")
        wait_for_text(window, "V3A3-SYNTHETIC-EDITED-ACTION")
        enter_editable(window, "Ваш комментарий о результате", "V3A3-SYNTHETIC-OUTCOME-NOTE")
        click(window, "Сохранить отметку")
        wait_for_text(window, "V3A3-SYNTHETIC-OUTCOME-NOTE")
        enter_editable(window, "Ваш текст", "V3A0-UIA-SECOND-TURN")
        click(window, "Добавить в сессию")
        wait_for_text(window, "V3A0-UIA-SECOND-TURN")
        click(window, "Завершить сессию")
        wait_for_text(window, "Сессия завершена")
        # `showSession` replaces the renderer subtree; keep the native HWND and
        # refresh only its UIA view rather than rediscovering by root PID.
        window, lifecycle = refresh_window(window, second.pid)
        assert_absent_or_disabled(window, "Ваш текст", "Edit")
        assert_absent_or_disabled(window, "Добавить в сессию", "Button")
        wait_for_text(window, "АНАЛИТИКА СЕССИИ")
        wait_for_text(window, "Хронология сессии")
        wait_for_text(window, "ИСТОРИЯ МОИХ СЛЕДУЮЩИХ ШАГОВ")
        assert_absent_or_disabled(window, "Моя цель", "Edit")
        assert_absent_or_disabled(window, "Сохранить мой следующий шаг", "Button")
        assert_absent_or_disabled(window, "Сохранить отметку", "Button")
        click(window, "Удалить сессию")
        wait_for_text(window, "МОИ СЕССИИ")
        if title in "\n".join(control.window_text() for control in window.descendants()):
            raise AssertionError("Deleted session remains in list")
        return {
            "first_pid": first.pid,
            "second_pid": second.pid,
            "persistence_canary": canary,
            "restart_persistence": True,
            "closed_window_lifecycle": lifecycle,
        }
    finally:
        terminate_tree(second)


def run(executable: Path, app_data: Path) -> dict[str, Any]:
    if not executable.is_file():
        raise SystemExit(f"Desktop executable does not exist: {executable}")
    process = _launch(executable, app_data)
    try:
        window = Desktop(backend="uia").window(process=process.pid, title=WINDOW_TITLE)
        window.wait("visible", timeout=20)
        wait_for_text(window, "Локальный секрет сессии")

        edit_id(window, "unlock-secret", SECRET_CANARY)
        click(window, "Разблокировать локально")
        wait_for_text(window, "Ваш локальный центр управления")
        visible_text = "\n".join(control.window_text() for control in window.descendants())
        if SECRET_CANARY in visible_text:
            raise AssertionError("Unlock secret leaked into the native accessibility surface")
        for required in (
            "Только синтетические данные",
            "Закрыт",
            "Без сети и слушателей",
            "Отключено",
        ):
            if required not in visible_text:
                raise AssertionError(f"Missing privacy/runtime status: {required}")

        edit(window, "Исправленное синтетическое наблюдение", MARKUP_CANARY)
        edit(window, "Причина исправления", "Проверка безопасности синтетического UIA")
        click(window, "Сохранить историю и исправить")
        wait_for_text(
            window,
            "Исправление применено к этой синтетической сессии; предыдущая версия сессии сохранена.",
        )
        if len(Desktop(backend="uia").windows(process=process.pid, title=WINDOW_TITLE)) != 1:
            raise AssertionError("Untrusted markup changed the native window surface")

        click(window, "Предпросмотр области удаления")
        wait_for_text(window, "Это только пробный запуск удаления; ничего не удалено.")
        click(window, "Подтвердить удаление")
        wait_for_text(
            window,
            "Удаление в синтетической сессии применено с указанными ограничениями; каноническая запись не изменена.",
        )

        click(window, "Проверить резервную копию")
        wait_for_text(window, "Резервная копия проверена без раскрытия содержимого.")
        click(window, "Проверить изолированное восстановление")
        wait_for_text(window, "Кандидат проверен; активное хранилище не изменено.")
        click(window, "Активировать проверенного кандидата")
        wait_for_text(window, "Проверенный кандидат активирован отдельно.")

        edit(window, "Цель", "portability")
        edit(window, "Получатель", "owner")
        edit(window, "Область", "synthetic minimum")
        assert_edit_values(
            window,
            {
                "Цель": "portability",
                "Получатель": "owner",
                "Область": "synthetic minimum",
            },
        )
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
            wait_for_text(
                window, f"{label}. Операция выполнена для встроенного вымышленного набора."
            )
        click(window, "Загрузить выбранную шкалу")
        wait_for_text(window, "Шкала использует «Событие произошло»")
        click(window, "Открыть обозреватель доказательств")
        wait_for_text(window, "Предложение не является фактом или доказательством.")
        click(window, "Сравнить снимки модели")
        wait_for_text(window, "неразрешённое состояние остаётся видимым")
        click(window, "Предпросмотр канонического удаления")
        wait_for_text(
            window, "Это только пробный запуск канонического удаления; состояние не изменено."
        )
        click(window, "Подтвердить каноническое удаление")
        wait_for_text(
            window, "квитанция не содержит удалённых данных или стабильного хеша содержимого"
        )

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
    print("V3A1_NATIVE_GUIDED_EXPLORATION: PASS")
    print("V3A1_NATIVE_FORMULATION_VERSIONING: PASS")
    print("V3A1_NATIVE_RESTART_PERSISTENCE: PASS")
    print("V3A2_NATIVE_ANALYTICAL_WORKSPACE: PASS")
    print("V3A3_NATIVE_SYNTHESIS_ACTION_WORKSPACE: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
