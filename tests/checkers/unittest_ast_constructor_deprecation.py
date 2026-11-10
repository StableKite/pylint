# Licensed under the GPL: https://www.gnu.org/licenses/old-licenses/gpl-2.0.html
"""Abstract AST bases remain valid types; only construction is deprecated."""
from __future__ import annotations

import astroid
import pytest

from pylint.checkers.stdlib import StdlibChecker
from pylint.interfaces import UNDEFINED
from pylint.testutils import CheckerTestCase, MessageTest


class TestASTConstructorDeprecation(CheckerTestCase):
    CHECKER_CLASS = StdlibChecker

    def setup_method(self) -> None:
        super().setup_method()
        # Exercise the 3.15 contract even when Pylint's tests run on older Python.
        self.checker._deprecated_classes["ast"] = {"AST", "expr"}

    @pytest.mark.parametrize("source", [
        'from ast import expr, parse\nvalue: expr = parse("value", mode="eval").body',
        'from ast import expr\nvalue: type[expr] = expr',
        'from ast import expr, parse\nassert isinstance(parse("value", mode="eval").body, expr)',
        'from ast import expr\nclass Expression(expr):\n    pass',
        'import ast\nvalue: type[ast.expr] = ast.expr',
    ])
    def test_valid_type_uses(self, source: str) -> None:
        with self.assertNoMessages():
            self.walk(astroid.parse(source))

    @pytest.mark.parametrize("source", [
        'import ast\nast.expr()',
        'import ast as tree\ntree.expr()',
        'from ast import expr\nexpr()',
        'from ast import expr as Expression\nExpression()',
        'import ast\nalias = ast\nalias.expr()',
    ])
    def test_actual_constructor_calls(self, source: str) -> None:
        node = astroid.extract_node(source)
        with self.assertAddsMessages(MessageTest(
            msg_id="deprecated-class", node=node, args=("expr", "ast"),
            confidence=UNDEFINED,
        ), ignore_position=True):
            self.checker.visit_call(node)

    @pytest.mark.parametrize("source", [
        'from ast import expr\nexpr = lambda: 73\nexpr()',
        'import ast\nclass Custom:\n    def expr(self):\n        return 73\nast = Custom()\nast.expr()',
        'import ast\nast.Name(id="value")',
    ])
    def test_unrelated_or_shadowed_constructors(self, source: str) -> None:
        with self.assertNoMessages():
            self.walk(astroid.parse(source))

    def test_other_deprecated_class_import_still_warns(self) -> None:
        self.checker._deprecated_classes["obsolete"] = {"Old"}
        node = astroid.extract_node('from obsolete import Old')
        with self.assertAddsMessages(MessageTest(
            msg_id="deprecated-class", node=node, args=("Old", "obsolete"),
            confidence=UNDEFINED,
        ), ignore_position=True):
            self.checker.visit_importfrom(node)
