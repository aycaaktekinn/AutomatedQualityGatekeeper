"""Reliability rules and secret masking."""

from app.analyzers.base import Severity
from app.analyzers.reliability import js_error_handling_issues, python_error_handling_issues
from app.masking import MASK, mask_secrets


def rules(code):
    return [(rule, line, severity) for rule, line, severity, _ in python_error_handling_issues(code)]


def test_bare_except_that_passes_is_high():
    assert rules("try:\n    x()\nexcept:\n    pass\n") == [("bare-except", 3, Severity.HIGH)]


def test_bare_except_with_handling_is_medium():
    assert rules("try:\n    x()\nexcept:\n    log()\n    raise\n") == [("bare-except", 3, Severity.MEDIUM)]


def test_silent_broad_exception():
    assert rules("try:\n    x()\nexcept Exception:\n    ...\n") == [("swallowed-exception", 3, Severity.MEDIUM)]


def test_silent_specific_exception_is_low():
    assert rules("try:\n    x()\nexcept KeyError:\n    pass\n") == [("empty-except", 3, Severity.LOW)]


def test_handled_exception_is_not_flagged():
    assert rules("try:\n    x()\nexcept ValueError as e:\n    log(e)\n") == []


def test_js_empty_catch_reports_line():
    code = "function f() {\n  try { g(); }\n  catch (e) {}\n}\n"
    assert [(r, line) for r, line, _, _ in js_error_handling_issues(code)] == [("empty-catch", 3)]


def test_js_catch_with_body_not_flagged():
    assert js_error_handling_issues("try { g(); } catch (e) { console.error(e); }") == []


def test_password_assignment_is_masked():
    masked = mask_secrets('DB_PASSWORD = "hunter2secret"')
    assert "hunter2secret" not in masked and MASK in masked


def test_github_token_is_masked():
    assert "ghp_" not in mask_secrets("token ghp_abcdefghijklmnopqrstuvwxyz0123")


def test_normal_code_is_unchanged():
    code = "def add(a, b):\n    return a + b"
    assert mask_secrets(code) == code
