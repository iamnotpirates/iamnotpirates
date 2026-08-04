"""Environment and dependency import tests."""


def test_imports():
    """Verify that all required libraries can be imported successfully."""
    import bs4
    import curl_cffi
    import questionary
    import rich

    assert curl_cffi is not None
    assert bs4 is not None
    assert rich is not None
    assert questionary is not None
