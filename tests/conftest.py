import pytest
from pathlib import Path

dir = Path("tests/results/")


def pytest_addoption(parser):
    parser.addoption("--abs", action="store", default=None)


def pytest_runtest_logreport(report):
    if report.failed and report.when in ('setup', 'teardown'):
        raise pytest.UsageError("Errors during collection, aborting")


@pytest.fixture(scope="session")
def abspath(pytestconfig):
    return pytestconfig.getoption("abs")


def get_au_op(i):
    new_op = i.__dict__.copy()
    new_op.pop("_element")
    new_op["activity"] = new_op["_activity"].name if new_op["_activity"] is not None else None
    new_op.pop("_activity")
    new_op["lang"] = new_op["_lang"]
    new_op.pop("_lang")
    new_op["first_name"] = new_op["_first_name"]
    new_op.pop("_first_name")
    new_op["last_name"] = new_op["_last_name"]
    new_op.pop("_last_name")
    return new_op
