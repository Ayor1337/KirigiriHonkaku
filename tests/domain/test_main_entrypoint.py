from app import main


def test_main_entrypoint_invokes_uvicorn(monkeypatch):
    captured = {}

    def fake_run(app_target, host, port, reload):
        captured["app_target"] = app_target
        captured["host"] = host
        captured["port"] = port
        captured["reload"] = reload

    monkeypatch.setattr(main.uvicorn, "run", fake_run)

    main.main()

    assert captured == {
        "app_target": "app.main:app",
        "host": "127.0.0.1",
        "port": 8000,
        "reload": False,
    }
