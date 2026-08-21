from unittest.mock import MagicMock, patch

import paramiko

from src.ssh_manager import SSHConnection


TEST_CTF_FLAG = "fixture-value"


def _connection(verify_host_key: bool):
    notifications = []
    connection = SSHConnection(
        hostname="example.test",
        port=2222,
        username="bandit0",
        password=TEST_CTF_FLAG,
        notify_callback=lambda message, severity: notifications.append(
            (message, severity)
        ),
        verify_host_key=verify_host_key,
    )
    client = MagicMock(spec=paramiko.SSHClient)
    connection.client = client
    return connection, client, notifications


def _policy(client):
    return client.set_missing_host_key_policy.call_args.args[0]


def test_secure_mode_rejects_unknown_host_keys():
    connection, client, notifications = _connection(verify_host_key=True)
    with patch("src.ssh_manager.os.path.exists", return_value=False):
        connection._configure_host_key_policy()

    assert isinstance(_policy(client), paramiko.RejectPolicy)
    client.load_system_host_keys.assert_called_once_with()
    client.load_host_keys.assert_not_called()
    assert any("unknown SSH host keys will be rejected" in message for message, _ in notifications)


def test_secure_mode_loads_existing_known_hosts():
    connection, client, _ = _connection(verify_host_key=True)
    with patch("src.ssh_manager.os.path.exists", return_value=True), patch(
        "src.ssh_manager.os.path.expanduser", return_value="/tmp/test-known_hosts"
    ):
        connection._configure_host_key_policy()

    assert isinstance(_policy(client), paramiko.RejectPolicy)
    client.load_system_host_keys.assert_called_once_with()
    client.load_host_keys.assert_called_once_with("/tmp/test-known_hosts")


def test_secure_mode_warns_and_still_rejects_when_known_hosts_cannot_be_loaded():
    connection, client, notifications = _connection(verify_host_key=True)
    client.load_system_host_keys.side_effect = OSError("permission denied")

    connection._configure_host_key_policy()

    assert isinstance(_policy(client), paramiko.RejectPolicy)
    assert any("Could not load known hosts" in message for message, _ in notifications)
    assert any("will still be rejected" in message for message, _ in notifications)


def test_insecure_mode_is_explicit_and_does_not_load_known_hosts():
    connection, client, notifications = _connection(verify_host_key=False)

    connection._configure_host_key_policy()

    assert isinstance(_policy(client), paramiko.AutoAddPolicy)
    client.load_system_host_keys.assert_not_called()
    client.load_host_keys.assert_not_called()
    assert any("host-key verification is disabled" in message for message, _ in notifications)
