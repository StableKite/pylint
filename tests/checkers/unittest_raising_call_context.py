# Licensed under the GPL: https://www.gnu.org/licenses/old-licenses/gpl-2.0.html
# For details: https://github.com/pylint-dev/pylint/blob/main/LICENSE
# Copyright (c) https://github.com/pylint-dev/pylint/blob/main/CONTRIBUTORS.txt

"""A raising proof must retain the actual receiver and call arguments."""

import astroid
import pytest
from astroid import nodes

from pylint.checkers.typecheck import IterableChecker, _is_raising_call
from pylint.interfaces import UNDEFINED
from pylint.testutils import CheckerTestCase, MessageTest

INSTANCE_METHODS = """
class Parent:
    def helper(self):
        raise OSError()
    def result(self):
        self.helper()
class Child(Parent):
    def helper(self):
        return None
"""

CLASS_METHODS = """
class Parent:
    @classmethod
    def helper(cls):
        raise OSError()
    @classmethod
    def result(cls):
        cls.helper()
class Child(Parent):
    @classmethod
    def helper(cls):
        return None
"""

CALLBACK = """
def raise_error():
    raise OSError()
def return_none():
    return None
def result(callback):
    callback()
"""

ARGUMENT = INSTANCE_METHODS + """
def result(receiver):
    receiver.helper()
"""


@pytest.mark.parametrize(
    "source, expression, expected",
    [
        (INSTANCE_METHODS, "Parent().result()", True),
        (INSTANCE_METHODS, "Child().result()", False),
        (CLASS_METHODS, "Parent.result()", True),
        (CLASS_METHODS, "Child.result()", False),
        (ARGUMENT, "result(Parent())", True),
        (ARGUMENT, "result(Child())", False),
        (ARGUMENT, "result(receiver=Parent())", True),
        (ARGUMENT, "result(receiver=Child())", False),
        (CALLBACK, "result(raise_error)", True),
        (CALLBACK, "result(return_none)", False),
        (CALLBACK, "result(callback=raise_error)", True),
        (CALLBACK, "result(callback=return_none)", False),
    ],
)
def test_raising_proof_preserves_call_context(
    source: str, expression: str, expected: bool
) -> None:
    module = astroid.parse(source + "\n" + expression)
    statement = module.body[-1]
    assert isinstance(statement, nodes.Expr)
    assert isinstance(statement.value, nodes.Call)
    assert _is_raising_call(statement.value) is expected


class TestDynamicIterableIntegration(CheckerTestCase):
    """Returning overrides and callbacks retain the genuine E1133 diagnostic."""

    CHECKER_CLASS = IterableChecker

    @pytest.mark.parametrize(
        "source, expression",
        [
            (INSTANCE_METHODS, "Child().result()"),
            (CLASS_METHODS, "Child.result()"),
            (ARGUMENT, "result(Child())"),
            (ARGUMENT, "result(receiver=Child())"),
            (CALLBACK, "result(return_none)"),
            (CALLBACK, "result(callback=return_none)"),
        ],
    )
    def test_real_noniterable_dynamic_result(
        self, source: str, expression: str
    ) -> None:
        module = astroid.parse(source + f"\nfor value in {expression}:\n    pass\n")
        node = module.body[-1]
        assert isinstance(node, nodes.For)
        with self.assertAddsMessages(
            MessageTest(
                msg_id="not-an-iterable",
                line=node.iter.lineno,
                node=node.iter,
                args=expression,
                confidence=UNDEFINED,
                col_offset=node.iter.col_offset,
                end_line=node.iter.end_lineno,
                end_col_offset=node.iter.end_col_offset,
            )
        ):
            self.checker.visit_for(node)
