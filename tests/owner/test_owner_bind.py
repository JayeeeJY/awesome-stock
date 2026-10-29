"""Native startup stays on loopback. A container must opt in to 0.0.0.0."""
import pytest


def test_native_start_stays_on_loopback_and_container_host_is_opt_in(monkeypatch, tmp_path, capsys):
    from awesome_stock.runtime import owner
    calls = []

    class Server:
        def __enter__(self):
            return self

        def __exit__(self, *exc):
            return False

        def serve_forever(self):
            calls.append('served')

    def make_server(host, port, app, **kwargs):
        calls.append((host, port))
        return Server()

    monkeypatch.setattr(owner, 'make_server', make_server)
    monkeypatch.setattr('sys.argv', ['start_owner.py', '--data-dir', str(tmp_path / 'ledger'), '--port', '4322'])
    owner.main()
    native = capsys.readouterr().out
    assert calls == [('127.0.0.1', 4322), 'served']
    assert 'http://127.0.0.1:4322/' in native and '0.0.0.0' not in native

    monkeypatch.setattr('sys.argv', ['start_owner.py', '--host', '0.0.0.0', '--data-dir', str(tmp_path / 'container'), '--port', '4322'])
    owner.main()
    assert calls == [('127.0.0.1', 4322), 'served', ('0.0.0.0', 4322), 'served']
    published = capsys.readouterr().out
    assert 'http://127.0.0.1:4322/' in published and '0.0.0.0' in published

    monkeypatch.setattr('sys.argv', ['start_owner.py', '--host', '10.1.2.3', '--data-dir', str(tmp_path / 'nope')])
    with pytest.raises(SystemExit):
        owner.main()
    assert calls == [('127.0.0.1', 4322), 'served', ('0.0.0.0', 4322), 'served']
    assert not (tmp_path / 'nope').exists()
