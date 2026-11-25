import subprocess

from src.clean import add


def test_add():
    assert add(1, 2) == 3


def test_shell_in_test_code_is_not_counted():
    subprocess.call("echo test", shell=True)
