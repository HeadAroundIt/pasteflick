from app.helper_main import main


def test_helper_main_update_uses_updater(monkeypatch) -> None:
    called = {}

    class Result:
        ok = True

    def fake_apply() -> Result:
        called["update"] = True
        return Result()

    monkeypatch.setattr("app.update.check_and_apply", fake_apply)
    assert main(["--update"]) == 0
    assert called["update"] is True
