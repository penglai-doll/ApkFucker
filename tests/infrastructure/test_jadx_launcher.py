from apk_hacker.infrastructure.integrations.jadx_launcher import resolve_jadx_gui_path


def test_resolve_jadx_gui_path_prefers_explicit_value() -> None:
    result = resolve_jadx_gui_path(
        explicit_path="/opt/jadx/bin/jadx-gui",
        environ={"APKHACKER_JADX_GUI_PATH": "/env/jadx-gui"},
        which=lambda _: "/usr/local/bin/jadx-gui",
    )

    assert result == "/opt/jadx/bin/jadx-gui"


def test_resolve_jadx_gui_path_treats_blank_explicit_value_as_disabled() -> None:
    result = resolve_jadx_gui_path(
        explicit_path="",
        environ={"APKHACKER_JADX_GUI_PATH": "/env/jadx-gui"},
        which=lambda _: "/usr/local/bin/jadx-gui",
    )

    assert result is None


def test_resolve_jadx_gui_path_falls_back_to_environment_then_path() -> None:
    env_result = resolve_jadx_gui_path(
        explicit_path=None,
        environ={"APKHACKER_JADX_GUI_PATH": "/env/jadx-gui"},
        which=lambda _: "/usr/local/bin/jadx-gui",
    )
    path_result = resolve_jadx_gui_path(
        explicit_path=None,
        environ={},
        which=lambda _: "/usr/local/bin/jadx-gui",
    )

    assert env_result == "/env/jadx-gui"
    assert path_result == "/usr/local/bin/jadx-gui"
