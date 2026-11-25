"""FR-03 / SR-03: only https://github.com/<owner>/<repo> is accepted (TC-03, TC-04)."""

import pytest

from app.repo_url import InvalidRepoUrl, parse_repo_url


@pytest.mark.parametrize("url, owner, name", [
    ("https://github.com/pallets/flask", "pallets", "flask"),
    ("https://github.com/pallets/flask/", "pallets", "flask"),
    ("https://github.com/pallets/flask.git", "pallets", "flask"),
    ("  https://github.com/a-b/c.d_e  ", "a-b", "c.d_e"),
])
def test_valid_urls(url, owner, name):
    ref = parse_repo_url(url)
    assert (ref.owner, ref.name) == (owner, name)
    assert ref.clone_url == f"https://github.com/{owner}/{name}.git"


@pytest.mark.parametrize("url", [
    "https://gitlab.com/a/b",                       # TC-04: other host
    "http://github.com/a/b",                        # not https
    "https://github.com.evil.com/a/b",              # host spoofing
    "https://github.com/a/b;rm -rf /",              # TC-03: shell characters
    "https://github.com/a/b/../../etc",             # path traversal
    "https://github.com/a",                         # missing repo
    "https://github.com/a/b/tree/main",             # not a repository root
    "https://github.com/-a/b",                      # invalid owner
    "https://github.com/a/..",                      # invalid repo name
    "https://github.com/a/b?x=1",                   # query string
    "file:///etc/passwd",
    "",
])
def test_invalid_urls_are_rejected(url):
    with pytest.raises(InvalidRepoUrl):
        parse_repo_url(url)


def test_rejection_message_explains_the_fix():
    with pytest.raises(InvalidRepoUrl, match="https://github.com/<owner>/<repo>"):
        parse_repo_url("https://gitlab.com/a/b")


def test_too_long_url_rejected():
    with pytest.raises(InvalidRepoUrl, match="too long"):
        parse_repo_url("https://github.com/a/" + "b" * 300)
