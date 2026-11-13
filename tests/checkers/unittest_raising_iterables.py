# Licensed under the GPL: https://www.gnu.org/licenses/old-licenses/gpl-2.0.html
# For details: https://github.com/pylint-dev/pylint/blob/main/LICENSE
# Copyright (c) https://github.com/pylint-dev/pylint/blob/main/CONTRIBUTORS.txt

"""A call that never produces a value cannot supply a non-iterable value."""

from __future__ import annotations

import astroid
import pytest
from astroid import nodes

from pylint.checkers.typecheck import IterableChecker, _is_raising_call
from pylint.interfaces import UNDEFINED
from pylint.testutils import CheckerTestCase, MessageTest


@pytest.mark.parametrize(
    "source, expected",
    [
        ("def call():\n    raise OSError()\ncall()", True),
        (
            "from typing import Never\n"
            "def fail() -> Never:\n    raise OSError()\n"
            "def call() -> list[int]:\n    fail()\ncall()",
            True,
        ),
        (
            "def fail():\n    raise OSError()\n"
            "def middle():\n    fail()\n"
            "def call():\n    middle()\ncall()",
            True,
        ),
        (
            "def fail():\n    raise OSError()\n"
            "def call():\n    return fail()\ncall()",
            True,
        ),
        (
            "def fail():\n    raise OSError()\n"
            "def call(flag):\n"
            "    if flag:\n        fail()\n"
            "    else:\n        raise ValueError()\ncall(True)",
            True,
        ),
        (
            "def fail():\n    raise OSError()\n"
            "def call():\n"
            "    def nested():\n        return None\n"
            "    class Nested:\n        def method(self):\n            return None\n"
            "    fail()\ncall()",
            True,
        ),
        ("def fail():\n    raise OSError()\ncall = lambda: fail()\ncall()", True),
        ("def call():\n    return None\ncall()", False),
        ("def call() -> list[int]:\n    return None\ncall()", False),
        (
            "from typing import Never\ndef call() -> Never:\n    return None\ncall()",
            False,
        ),
        ("from typing import Never\ndef call() -> Never:\n    pass\ncall()", False),
        (
            "def fail():\n    raise OSError()\n"
            "def call(flag):\n"
            "    if flag:\n        return None\n"
            "    fail()\ncall(True)",
            False,
        ),
        (
            "def fail():\n    raise OSError()\n"
            "def call():\n"
            "    try:\n        fail()\n"
            "    except OSError:\n        pass\ncall()",
            False,
        ),
        (
            "def fail():\n    raise OSError()\n"
            "def call():\n"
            "    try:\n        fail()\n"
            "    finally:\n        return None\ncall()",
            False,
        ),
        (
            "from contextlib import suppress\n"
            "def fail():\n    raise OSError()\n"
            "def call():\n"
            "    with suppress(OSError):\n        fail()\ncall()",
            False,
        ),
        ("async def call():\n    raise OSError()\ncall()", False),
        ("def call():\n    yield 1\n    raise OSError()\ncall()", False),
        (
            "def fail(value):\n    raise OSError()\n"
            "call = lambda: fail((yield 1))\ncall()",
            False,
        ),
        ("def call():\n    call()\ncall()", False),
    ],
)
def test_actual_body_raising_proof(source: str, expected: bool) -> None:
    """Keep genuine values, async objects and caught exceptions distinguishable."""
    module = astroid.parse(source)
    statement = module.body[-1]
    assert isinstance(statement, nodes.Expr)
    assert isinstance(statement.value, nodes.Call)
    assert _is_raising_call(statement.value) is expected


class TestRaisingIterableIntegration(CheckerTestCase):
    """Exercise the actual E1133 visitor, not just the body proof."""

    CHECKER_CLASS = IterableChecker

    def test_cold_raise_wrapper_does_not_produce_none(self) -> None:
        node = astroid.extract_node("""
            from typing import Never
            def fail(error: BaseException) -> Never:
                raise error
            class Unsupported:
                @staticmethod
                def poll(timeout: float) -> list[tuple[int, int]]:
                    fail(OSError(str(timeout)))
            for value in Unsupported.poll(0):
                pass
            """)
        assert isinstance(node, nodes.For)
        with self.assertNoMessages():
            self.checker.visit_for(node)

    @pytest.mark.parametrize(
        "body",
        [
            "return None",
            "return 0",
            "if flag:\n        return None\n    raise OSError()",
            "try:\n        fail()\n    except OSError:\n        pass",
            "try:\n        fail()\n    finally:\n        return None",
        ],
    )
    def test_real_noniterable_values_remain_errors(self, body: str) -> None:
        module = astroid.parse(
            "from typing import Never\n"
            "def fail() -> Never:\n    raise OSError()\n"
            f"def call(flag: bool) -> list[int]:\n    {body}\n"
            "for value in call(True):\n    pass\n"
        )
        node = module.body[-1]
        assert isinstance(node, nodes.For)
        with self.assertAddsMessages(
            MessageTest(
                msg_id="not-an-iterable",
                line=node.iter.lineno,
                node=node.iter,
                args="call(True)",
                confidence=UNDEFINED,
                col_offset=node.iter.col_offset,
                end_line=node.iter.end_lineno,
                end_col_offset=node.iter.end_col_offset,
            )
        ):
            self.checker.visit_for(node)
