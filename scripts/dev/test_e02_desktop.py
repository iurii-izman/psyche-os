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
WINDOW_ROOT_PIDS: dict[int, int] = {}


def _window_hwnd(window: Any) -> int:
    try:
        return int(window.wrapper_object().handle)
    except Exception as error:
        raise AssertionError(f"UIA_TOP_LEVEL_HANDLE_UNAVAILABLE {error!r}") from error


def native_window_state(hwnd: int, root_pid: int) -> dict[str, Any]:
    """Use Win32, not UIA, as the authority for a top-level window's liveness."""
    user32 = ctypes.windll.user32
    is_window = bool(user32.IsWindow(hwnd))
    process_id = ctypes.c_ulong()
    title_buffer = ctypes.create_unicode_buffer(512)
    if is_window:
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(process_id))
        user32.GetWindowTextW(hwnd, title_buffer, len(title_buffer))
    owned_pids = _owned_pids(root_pid)
    return {
        "hwnd": hwnd,
        "is_window": is_window,
        "is_visible": bool(is_window and user32.IsWindowVisible(hwnd)),
        "native_title": title_buffer.value,
        "window_process_id": process_id.value,
        "root_pid": root_pid,
        "owned_process_ids": sorted(owned_pids),
        "owned": bool(is_window and process_id.value in owned_pids),
    }


def fresh_window(window: Any) -> Any:
    """Return a fresh UIA path for a live Win32 HWND; UIA readiness is semantic."""
    hwnd = _window_hwnd(window)
    root_pid = WINDOW_ROOT_PIDS.get(hwnd)
    if root_pid is None:
        raise AssertionError(f"UIA_TOP_LEVEL_ROOT_PID_UNKNOWN {json.dumps({'hwnd': hwnd}, sort_keys=True)}")
    state = native_window_state(hwnd, root_pid)
    if not state["is_window"]:
        raise AssertionError(f"UIA_TOP_LEVEL_WINDOW_GONE {json.dumps(state, ensure_ascii=False, sort_keys=True)}")
    if not state["owned"] or not state["is_visible"]:
        raise AssertionError(f"UIA_TOP_LEVEL_NATIVE_STATE_FAILED {json.dumps(state, ensure_ascii=False, sort_keys=True)}")
    return Desktop(backend="uia").window(handle=hwnd)


def _control_diagnostics(window: Any, request: dict[str, Any]) -> dict[str, Any]:
    """Bounded, content-free context for a failed descendant lookup."""
    fresh = fresh_window(window)
    wrapper = fresh.wrapper_object()
    markers = ("Локальный секрет сессии", "МОЁ ПРОСТРАНСТВО", "Сессия завершена", "ДИНАМИКА ПО СЕССИЯМ")
    try:
        descendants = fresh.descendants()
        text = "\n".join(control.window_text() for control in descendants)
        controls = [
            {
                "name": control.window_text(),
                "type": control.friendly_class_name(),
                "automation_id": control.element_info.automation_id,
            }
            for control in descendants[:30]
            if control.window_text()
        ]
    except Exception as error:
        text, controls = "", [{"enumeration_error": repr(error)}]
    return {
        "top_level_hwnd": int(wrapper.handle),
        "top_level_process_id": wrapper.element_info.process_id,
        "request": request,
        "visible_markers": {marker: marker in text for marker in markers},
        "matching_controls": controls,
    }


def _longitudinal_surface_diagnostics(window: Any, root_pid: int) -> dict[str, Any]:
    """Capture the bounded native surface needed to classify one navigation attempt."""
    fresh = fresh_window(window)
    wrapper = fresh.wrapper_object()
    descendants = fresh.descendants()
    text = "\n".join(control.window_text() for control in descendants)
    operation_status = next(
        (control.window_text() for control in descendants if control.element_info.automation_id == "operation-status"),
        "",
    )
    combo_boxes = [
        {"name": control.window_text(), "automation_id": control.element_info.automation_id}
        for control in descendants
        if control.element_info.control_type == "ComboBox"
    ]
    relevant_controls = [
        {"name": control.window_text(), "type": control.friendly_class_name(), "automation_id": control.element_info.automation_id}
        for control in descendants
        if control.element_info.control_type in {"Button", "ComboBox", "ListItem"} and control.window_text()
    ][:40]
    return {
        "top_level_hwnd": int(wrapper.handle),
        "top_level_process_id": wrapper.element_info.process_id,
        "hwnd_survives": bool(ctypes.windll.user32.IsWindow(int(wrapper.handle))),
        "owned_process_ids": sorted(_owned_pids(root_pid)),
        "session_a_visible": "V3BC-SESSION-A" in text,
        "session_b_visible": "V3BC-SESSION-B" in text,
        "longitudinal_markers": {
            marker: marker in text
            for marker in ("1. Обзор записей", "2. История рабочих формулировок", "7. Сравнить две сессии")
        },
        "operation_status": operation_status,
        "old_open_controls_present": any(
            control.element_info.control_type == "Button" and control.window_text() == "Открыть"
            for control in descendants
        ),
        "combo_boxes": combo_boxes,
        "relevant_controls": relevant_controls,
    }


def wait_for_longitudinal_transition(window: Any, root_pid: int, before: dict[str, Any]) -> dict[str, Any]:
    """Observe one invoked longitudinal navigation until its unique destination or error surface."""
    deadline = time.monotonic() + 20
    latest = before
    while time.monotonic() < deadline:
        latest = _longitudinal_surface_diagnostics(window, root_pid)
        if latest["longitudinal_markers"]["1. Обзор записей"]:
            return {"before": before, "after": latest, "outcome": "destination"}
        if latest["operation_status"] and latest["operation_status"] != before["operation_status"]:
            raise AssertionError(
                "LONGITUDINAL_TRANSITION_OPERATION_ERROR "
                f"{json.dumps({'before': before, 'after': latest}, ensure_ascii=False, sort_keys=True)}"
            )
        time.sleep(0.2)
    raise AssertionError(
        "LONGITUDINAL_TRANSITION_NO_DESTINATION_OR_ERROR "
        f"{json.dumps({'before': before, 'after': latest}, ensure_ascii=False, sort_keys=True)}"
    )


def _control_or_fail(window: Any, request: dict[str, Any], state: str = "ready") -> Any:
    criteria = dict(request)
    found_index = criteria.pop("found_index", 0)
    fallback_title = criteria.pop("fallback_title", None)
    deadline = time.monotonic() + 8
    last_error: Exception | None = None
    while time.monotonic() < deadline:
        fresh = fresh_window(window)
        try:
            matches = [
                control
                for control in fresh.descendants()
                if ("title" not in criteria or control.window_text() == criteria["title"])
                and (
                    "auto_id" not in criteria
                    or control.element_info.automation_id == criteria["auto_id"]
                    or (fallback_title is not None and control.window_text() == fallback_title)
                )
                and ("control_type" not in criteria or control.element_info.control_type == criteria["control_type"])
            ]
            if len(matches) > found_index:
                control = matches[found_index]
                if state == "exists" or (control.is_visible() and control.is_enabled()):
                    return control
        except Exception as error:
            last_error = error
        time.sleep(0.2)
    diagnostics = _control_diagnostics(window, request)
    raise AssertionError(
        f"UIA_CONTROL_LOOKUP_FAILED {json.dumps(diagnostics, ensure_ascii=False, sort_keys=True)}"
    ) from last_error


def wait_for_text(window: Any, needle: str, timeout: float = 20.0) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        fresh = fresh_window(window)
        text = "\n".join(control.window_text() for control in fresh.descendants())
        if needle in text:
            return
        time.sleep(0.2)
    raise AssertionError(
        "UIA_TEXT_LOOKUP_FAILED "
        f"{json.dumps(_control_diagnostics(window, {'text': needle}), ensure_ascii=False, sort_keys=True)}"
    )


def edit(window: Any, title: str, value: str) -> None:
    enter_editable(window, title, value)


def edit_id(window: Any, automation_id: str, value: str) -> None:
    control = _control_or_fail(window, {"auto_id": automation_id, "control_type": "Edit"})
    control.set_edit_text(value)


def find_editable(window: Any, accessible_name: str) -> Any:
    """Reacquire the native WebView2 Edit immediately before each write."""
    control = _control_or_fail(window, {"title": accessible_name, "control_type": "Edit"}, "exists")
    control.set_focus()
    ready = _control_or_fail(window, {"title": accessible_name, "control_type": "Edit"})
    ready.set_focus()
    return ready


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
    control = _control_or_fail(window, criteria, "exists")
    if not control.is_enabled():
        raise AssertionError(f"Native button is disabled: {title}")
    control.invoke()


def select_id(window: Any, automation_id: str, index: int, accessible_name: str | None = None) -> None:
    request: dict[str, Any] = {"auto_id": automation_id, "control_type": "ComboBox"}
    if accessible_name is not None:
        request["fallback_title"] = accessible_name
    control = _control_or_fail(window, request)
    control.expand()
    deadline = time.monotonic() + 8
    items: list[Any] = []
    while time.monotonic() < deadline:
        items = fresh_window(window).descendants(control_type="ListItem")
        if len(items) > index:
            items[index].click_input()
            return
        time.sleep(0.1)
    raise AssertionError(f"Native select option is unavailable: {automation_id} index={index}")


def choose_radio(window: Any, title: str) -> None:
    control = _control_or_fail(window, {"title": title, "control_type": "RadioButton"})
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
    request = {"title": title, "control_type": control_type}
    control = fresh_window(window).child_window(**request)
    if not control.exists(timeout=1):
        return
    if control.is_enabled():
        raise AssertionError(f"Closed session still exposes an enabled control: {title}")


def _owned_pids(root_pid: int) -> set[int]:
    try:
        root = psutil.Process(root_pid)
        return {root_pid, *(process.pid for process in root.children(recursive=True))}
    except psutil.Error:
        return set()


def acquire_owned_window(
    root_pid: int, timeout: float = 20.0, preferred_hwnd: int | None = None
) -> tuple[Any, dict[str, Any]]:
    """Acquire exactly one visible titled top-level window owned by the process tree."""
    desktop = Desktop(backend="uia")
    diagnostics: dict[str, Any] = {
        "root_pid": root_pid,
        "preferred_hwnd": preferred_hwnd,
        "titled_candidates": [],
    }
    if preferred_hwnd is not None:
        preferred_state = native_window_state(preferred_hwnd, root_pid)
        diagnostics["preferred_state"] = preferred_state
        if preferred_state["is_window"] and preferred_state["owned"] and preferred_state["is_visible"]:
            WINDOW_ROOT_PIDS[preferred_hwnd] = root_pid
            diagnostics["chosen_strategy"] = "preferred_live_hwnd"
            return desktop.window(handle=preferred_hwnd), diagnostics
        if preferred_state["is_window"]:
            raise AssertionError(f"UIA_WINDOW_ACQUISITION_FAILED {json.dumps(diagnostics, ensure_ascii=False, sort_keys=True)}")

    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        candidates: list[dict[str, Any]] = []
        for candidate in desktop.windows():
            state = native_window_state(int(candidate.handle), root_pid)
            if state["native_title"] == WINDOW_TITLE:
                candidates.append(state)
        diagnostics["owned_process_ids"] = sorted(_owned_pids(root_pid))
        diagnostics["titled_candidates"] = candidates
        owned = [candidate for candidate in candidates if candidate["owned"] and candidate["is_visible"]]
        if len(owned) == 1:
            hwnd = int(owned[0]["hwnd"])
            WINDOW_ROOT_PIDS[hwnd] = root_pid
            diagnostics["chosen_strategy"] = "owned_titled_candidate"
            diagnostics["chosen_hwnd"] = hwnd
            return desktop.window(handle=hwnd), diagnostics
        if len(owned) > 1:
            diagnostics["chosen_strategy"] = "ambiguous_owned_candidates"
            raise AssertionError(f"UIA_WINDOW_ACQUISITION_FAILED {json.dumps(diagnostics, ensure_ascii=False, sort_keys=True)}")
        time.sleep(0.2)
    diagnostics["chosen_strategy"] = "timed_out_without_owned_candidate"
    raise AssertionError(f"UIA_WINDOW_ACQUISITION_FAILED {json.dumps(diagnostics, ensure_ascii=False, sort_keys=True)}")


def refresh_window(window: Any, root_pid: int) -> tuple[Any, dict[str, Any]]:
    """Refresh a replaced WebView2 accessibility subtree through its stable HWND."""
    hwnd = _window_hwnd(window)
    state = native_window_state(hwnd, root_pid)
    if state["is_window"]:
        if not state["owned"] or not state["is_visible"]:
            raise AssertionError(f"UIA_WINDOW_LIFECYCLE_FAILED {json.dumps(state, ensure_ascii=False, sort_keys=True)}")
        WINDOW_ROOT_PIDS[hwnd] = root_pid
        return Desktop(backend="uia").window(handle=hwnd), {"chosen_strategy": "preferred_live_hwnd", "native_state": state}
    return acquire_owned_window(root_pid)


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
        window, _ = acquire_owned_window(first.pid)
        wait_for_text(window, "Локальный секрет сессии")
        edit_id(window, "unlock-secret", SECRET_CANARY)
        click(window, "Разблокировать локально")
        wait_for_text(window, "МОЁ ПРОСТРАНСТВО")
        window, _ = refresh_window(window, first.pid)
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
        window, _ = acquire_owned_window(second.pid)
        wait_for_text(window, "Локальный секрет сессии")
        edit_id(window, "unlock-secret", SECRET_CANARY)
        click(window, "Разблокировать локально")
        wait_for_text(window, title)
        window, _ = refresh_window(window, second.pid)
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
        wait_for_text(window, "МОЁ ПРОСТРАНСТВО")
        if title in "\n".join(control.window_text() for control in fresh_window(window).descendants()):
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


def _create_v3bc_session(
    window: Any,
    title: str,
    only_canary: str,
    formulation_canary: str,
    *,
    with_action: bool,
) -> None:
    """Create one complete synthetic longitudinal source through native UIA."""
    recurrence = "V3BC-EXACT-RECURRENCE"
    edit(window, "Название", title)
    click(window, "Новая сессия")
    wait_for_text(window, "Добавить в сессию")
    enter_editable(window, "Ваш текст", recurrence)
    click(window, "Добавить в сессию")
    wait_for_text(window, recurrence)
    wait_for_text(window, "Следующий вопрос")
    # The guided answer becomes a separately sourced KNOWN context record, so
    # comparison can honestly distinguish it from the shared first turn.
    enter_editable(window, "Ответ на следующий вопрос", only_canary)
    click(window, "Ответить на следующий вопрос")
    wait_for_text(window, only_canary)
    click(window, "Составить рабочую формулировку")
    wait_for_text(window, "Рабочее предложение, не диагноз")
    enter_editable(window, "Исправление формулировки", formulation_canary)
    click(window, "Исправить")
    wait_for_text(window, formulation_canary)
    click(window, "Принять как рабочую", found_index=0)
    wait_for_text(window, "CURRENT")
    for marker in ("АНАЛИТИКА СЕССИИ", "ИТОГ СЕССИИ"):
        wait_for_text(window, marker)
    if not with_action:
        return
    enter_editable(window, "Моя цель", "V3BC-GOAL-A")
    select_id(window, "action-anchor", 1)
    choose_radio(window, "Ничего не предпринимать сейчас и оставить вопрос открытым.")
    enter_editable(window, "Текст следующего шага", "V3BC-ACTION-A")
    click(window, "Сохранить мой следующий шаг")
    wait_for_text(window, "V3BC-ACTION-A")
    enter_editable(window, "Ваш комментарий о результате", "V3BC-OUTCOME-A")
    click(window, "Сохранить отметку")
    wait_for_text(window, "V3BC-OUTCOME-A")


def _assert_v3bc_workspace(window: Any, *, after_restart: bool) -> None:
    """Assert the read-only projection and its real UIA comparison controls."""
    required = (
        "ДИНАМИКА ПО СЕССИЯМ",
        "V3BC-SESSION-A",
        "V3BC-SESSION-B",
        "1. Обзор записей",
        "Сессий с guided exploration: 2",
        "V3BC-EXACT-RECURRENCE",
        "Одинаковая запись встречалась в 2 сессиях.",
        "2. История рабочих формулировок",
        "V3BC-FORMULATION-A",
        "V3BC-FORMULATION-B",
        "4. Рабочие альтернативы по сессиям",
        "SUPPORT (",
        "V3BC-EXACT-RECURRENCE",
        "5. Неизвестное и противоречия",
        "Неизвестное: Пока неизвестно, в каких ситуациях это заметнее или слабее.",
        "Состояние относится к записи внутри конкретной сессии.",
        "Открыто",
        "6. Мои следующие шаги и отметки",
        "V3BC-GOAL-A",
        "V3BC-ACTION-A",
        "V3BC-OUTCOME-A",
        "Отметка «Сделано» говорит только о выполнении шага, а не о его пользе или эффективности.",
        "7. Сравнить две сессии",
        "8. Хронология записанных событий продукта",
    )
    for marker in required:
        wait_for_text(window, marker)
    visible = "\n".join(control.window_text() for control in fresh_window(window).descendants())
    # A repeated UNKNOWN is an open question in each recorded session, not
    # negative evidence, resolution, persistence, or a contradiction.  This
    # deterministic flow creates none of the latter, so its contradiction
    # portion is honestly empty while UNKNOWN history remains populated.
    if "Противоречие:" in visible:
        raise AssertionError("Synthetic V3-B/C flow unexpectedly rendered a contradiction record")
    # Only-A/B are context records, not recurrence groups: neither may acquire
    # a false two-session recurrence presentation.
    for canary in ("V3BC-ONLY-A", "V3BC-ONLY-B"):
        if f"{canary} · user_report · Одинаковая запись" in visible:
            raise AssertionError(f"Single-session canary was falsely presented as recurrence: {canary}")
    # The workspace itself exposes selectors/navigation only; all source writes
    # are absent while the projection is shown.  The global new-session form is
    # intentionally outside this read-only surface and is not treated as one.
    for title, control_type in (
        ("Добавить в сессию", "Button"),
        ("Завершить сессию", "Button"),
        ("Удалить сессию", "Button"),
        ("Исправить", "Button"),
        ("Принять как рабочую", "Button"),
        ("Сохранить мой следующий шаг", "Button"),
        ("Сохранить отметку", "Button"),
    ):
        control = fresh_window(window).child_window(title=title, control_type=control_type)
        if control.exists(timeout=1):
            raise AssertionError(f"Longitudinal workspace exposes a mutation control: {title}")
    # UIA ComboBox/ListItem interaction, never renderer state injection.
    select_id(window, "longitudinal-session-a", 0, "Сессия A")
    select_id(window, "longitudinal-session-b", 1, "Сессия B")
    for marker in (
        "Общие точные записи: V3BC-EXACT-RECURRENCE",
        "Только в A: V3BC-ONLY-A",
        "Только в B: V3BC-ONLY-B",
        "Не записано в этой сессии",
        "V3BC-FORMULATION-A",
        "V3BC-FORMULATION-B",
        "CURRENT A:",
        "Гипотеза",
        "Действие A:",
    ):
        wait_for_text(window, marker)
    if after_restart:
        wait_for_text(window, "V3BC-SESSION-A")


def v3bc_longitudinal_proof(executable: Path, app_data: Path) -> dict[str, Any]:
    """Prove V3-B/C derives an honest two-session view after a full restart."""
    first = _launch(executable, app_data)
    try:
        window, _ = acquire_owned_window(first.pid)
        wait_for_text(window, "Локальный секрет сессии")
        edit_id(window, "unlock-secret", SECRET_CANARY)
        click(window, "Разблокировать локально")
        wait_for_text(window, "МОЁ ПРОСТРАНСТВО")
        window, _ = refresh_window(window, first.pid)
        _create_v3bc_session(window, "V3BC-SESSION-A", "V3BC-ONLY-A", "V3BC-FORMULATION-A", with_action=True)
        click(window, "Завершить сессию")
        wait_for_text(window, "Сессия завершена")
        window, closed_lifecycle = refresh_window(window, first.pid)
        wait_for_text(window, "V3BC-SESSION-A")
        click(window, "Назад к сессиям")
        _control_or_fail(window, {"title": "Открыть", "control_type": "Button"}, "exists")
        _create_v3bc_session(window, "V3BC-SESSION-B", "V3BC-ONLY-B", "V3BC-FORMULATION-B", with_action=False)
        click(window, "Назад к сессиям")
        _control_or_fail(window, {"title": "Открыть", "control_type": "Button"}, "exists")
        transition_before = _longitudinal_surface_diagnostics(window, first.pid)
        click(window, "ДИНАМИКА ПО СЕССИЯМ")
        transition = wait_for_longitudinal_transition(window, first.pid, transition_before)
        window, _ = refresh_window(window, first.pid)
        _assert_v3bc_workspace(window, after_restart=False)
        runtime = process_evidence(first.pid)
    finally:
        terminate_tree(first)
    if psutil.pid_exists(first.pid):
        raise AssertionError("First V3-B/C desktop process survived restart boundary")

    second = _launch(executable, app_data)
    try:
        window, _ = acquire_owned_window(second.pid)
        wait_for_text(window, "Локальный секрет сессии")
        edit_id(window, "unlock-secret", SECRET_CANARY)
        click(window, "Разблокировать локально")
        wait_for_text(window, "ДИНАМИКА ПО СЕССИЯМ")
        window, _ = refresh_window(window, second.pid)
        _control_or_fail(window, {"title": "Открыть", "control_type": "Button"}, "exists")
        transition_before = _longitudinal_surface_diagnostics(window, second.pid)
        click(window, "ДИНАМИКА ПО СЕССИЯМ")
        restart_transition = wait_for_longitudinal_transition(window, second.pid, transition_before)
        window, _ = refresh_window(window, second.pid)
        _assert_v3bc_workspace(window, after_restart=True)
        return {
            **runtime,
            "v3bc_first_pid": first.pid,
            "v3bc_second_pid": second.pid,
            "v3bc_closed_session_lifecycle": closed_lifecycle,
            "v3bc_transition": transition,
            "v3bc_restart_transition": restart_transition,
            "v3bc_restart_rebuild": True,
            "v3bc_two_session_comparison": True,
        }
    finally:
        terminate_tree(second)


def run(executable: Path, app_data: Path) -> dict[str, Any]:
    if not executable.is_file():
        raise SystemExit(f"Desktop executable does not exist: {executable}")
    process = _launch(executable, app_data)
    try:
        window, _ = acquire_owned_window(process.pid)
        wait_for_text(window, "Локальный секрет сессии")

        edit_id(window, "unlock-secret", SECRET_CANARY)
        click(window, "Разблокировать локально")
        wait_for_text(window, "Ваш локальный центр управления")
        window, _ = refresh_window(window, process.pid)
        visible_text = "\n".join(control.window_text() for control in fresh_window(window).descendants())
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
        acquire_owned_window(process.pid)

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
        fresh_window(window).set_focus()
        fresh_window(window).type_keys("{END}")
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
    parser.add_argument("--scenario", choices=("all", "restart"), default="all")
    args = parser.parse_args()
    with tempfile.TemporaryDirectory(prefix="psyche-os-v3a0-uia-") as temporary:
        app_data = Path(temporary)
        restart = restart_persistence_proof(args.executable.resolve(), app_data)
        if args.scenario == "restart":
            print(json.dumps(restart, indent=2, sort_keys=True))
            print("V3A0_NATIVE_RESTART_PERSISTENCE: PASS")
            return 0
        longitudinal = v3bc_longitudinal_proof(args.executable.resolve(), app_data)
        evidence = run(args.executable.resolve(), app_data)
        evidence.update(restart)
        evidence.update(longitudinal)
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
    print("V3BC_NATIVE_LONGITUDINAL_WORKSPACE: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
