from pathlib import Path
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


def test_secure_mode_rejects_unknown_host_keys():
    connection, client, notifications = _connection(verify_host_key=True)
    with patch("src.ssh_manager.os.path.exists", return_value=False):
        connection._configure_host_key_policy()

    policy = client.set_missing_host_key_policy.call_args.args[0]
    assert isinstance(policy, paramiko.RejectPolicy)
    assert any("unknown SSH host keys will be rejected" in message for message, _ in notifications)


def test_insecure_mode_requires_explicit_opt_out_and_warns():
    connection, client, notifications = _connection(verify_host_key=False)
    connection._configure_host_key_policy()

    policy = client.set_missing_host_key_policy.call_args.args[0]
    assert isinstance(policy, paramiko.AutoAddPolicy)
    assert any("host-key verification is disabled" in message for message, _ in notifications)
