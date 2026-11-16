"""Environment smoke test: the package installs and the data files exist."""

from twin.config import DATA_DIR, MAX_ATTEMPTS


def test_package_imports():
    import twin  # noqa: F401

    assert MAX_ATTEMPTS == 3


def test_background_files_exist():
    assert (DATA_DIR / "linkedin.txt").is_file()
    assert (DATA_DIR / "summary.txt").is_file()
