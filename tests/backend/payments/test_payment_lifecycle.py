from fastapi.testclient import TestClient


def test_app_shutdown_closes_payment_provider_registry(
    monkeypatch,
) -> None:
    from app import main as main_module

    calls: list[str] = []

    def close_registry() -> None:
        calls.append("closed")

    monkeypatch.setattr(
        main_module,
        "close_payment_provider_registry",
        close_registry,
    )

    with TestClient(main_module.app):
        assert calls == []

    assert calls == ["closed"]
