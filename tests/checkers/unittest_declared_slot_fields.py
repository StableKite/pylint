# Licensed under the GPL: https://www.gnu.org/licenses/old-licenses/gpl-2.0.html
# For details: https://github.com/pylint-dev/pylint/blob/main/LICENSE
# Copyright (c) https://github.com/pylint-dev/pylint/blob/main/CONTRIBUTORS.txt

"""Known slot descriptors declare fields independently of their first value."""

import textwrap

import astroid
import pytest
from astroid import nodes

from pylint.checkers.classes.class_checker import ClassChecker
from pylint.lint import PyLinter


def _assert_outside_init_messages(linter: PyLinter, attributes: list[str]) -> None:
    assert [(message.msg_id, message.msg) for message in linter.reporter.messages] == [
        ("W0201", f"Attribute '{attribute}' defined outside __init__")
        for attribute in attributes
    ]


@pytest.mark.parametrize(
    "declaration",
    [
        '__slots__ = ("reference",)',
        '__slots__ = ["reference"]',
        '__slots__ = {"reference"}',
        '__slots__ = {"reference": "Native argument storage"}',
        '__slots__ = "reference"',
        'SLOTS = ("reference",)\n__slots__ = SLOTS',
    ],
)
def test_known_slots_declare_fields_with_dictionary_base(
    linter: PyLinter, declaration: str
) -> None:
    module = astroid.parse(
        "class DictionaryBase: pass\nclass Owner(DictionaryBase):\n"
        + textwrap.indent(declaration, "    ")
        + "\n    def initialize(self):\n        self.reference = 1\n"
        + "        self.extra = 2\n"
    )
    owner = module.body[-1]
    assert isinstance(owner, nodes.ClassDef)
    assert owner.slots() is None  # A dictionary base does not remove descriptors.
    checker = ClassChecker(linter)
    checker.open()
    linter.set_current_module("slots_control")

    checker._check_attribute_defined_outside_init(owner)

    _assert_outside_init_messages(linter, ["extra"])


@pytest.mark.parametrize("child_slots", ["", "__slots__ = ()", '__slots__ = ("own",)'])
def test_known_parent_slot_is_declared_in_child(
    linter: PyLinter, child_slots: str
) -> None:
    module = astroid.parse(
        "class DictionaryBase: pass\n"
        + 'class Parent(DictionaryBase):\n    __slots__ = {"reference": "Storage"}\n'
        + "class Owner(Parent):\n"
        + textwrap.indent(child_slots, "    ")
        + "\n    def initialize(self):\n        self.reference = 1\n"
        + "        self.extra = 2\n"
    )
    owner = module.body[-1]
    assert isinstance(owner, nodes.ClassDef)
    checker = ClassChecker(linter)
    checker.open()
    linter.set_current_module("inherited_slots_control")

    checker._check_attribute_defined_outside_init(owner)

    _assert_outside_init_messages(linter, ["extra"])


@pytest.mark.parametrize(
    ("declaration", "expected"),
    [
        ("", ["reference"]),
        ("__slots__ = ()", ["reference"]),
        ('__slots__ = ("unrelated",)', ["reference"]),
        ("__slots__ = unknown_slots()", ["reference"]),
        ("__slots__: tuple[str, ...]", ["reference"]),
        ('__slots__ = ("unrelated", unknown_name)', ["reference"]),
        ('__slots__ = ("reference", unknown_name)', []),
        ('__slots__ = ("reference",) if condition else ("other",)', ["reference"]),
        ('__slots__ = ("reference",) if condition else ("reference", "other")', []),
    ],
)
def test_missing_or_unknown_slots_do_not_declare_arbitrary_fields(
    linter: PyLinter, declaration: str, expected: list[str]
) -> None:
    module = astroid.parse(
        "class DictionaryBase: pass\nclass Owner(DictionaryBase):\n"
        + textwrap.indent(declaration, "    ")
        + "\n    def initialize(self):\n        self.reference = 1\n"
    )
    owner = module.body[-1]
    assert isinstance(owner, nodes.ClassDef)
    checker = ClassChecker(linter)
    checker.open()
    linter.set_current_module("unknown_slots_control")

    checker._check_attribute_defined_outside_init(owner)

    _assert_outside_init_messages(linter, expected)


@pytest.mark.parametrize("class_name", ["Owner", "_Owner", "___"])
def test_private_slot_uses_its_declaring_class_name(
    linter: PyLinter, class_name: str
) -> None:
    module = astroid.parse(
        f'class {class_name}:\n    __slots__ = ("__reference",)\n'
        + "    def initialize(self):\n        self.__reference = 1\n"
    )
    owner = module.body[0]
    assert isinstance(owner, nodes.ClassDef)
    checker = ClassChecker(linter)
    checker.open()
    linter.set_current_module("private_slots_control")

    checker._check_attribute_defined_outside_init(owner)

    assert not linter.reporter.messages


def test_child_private_name_is_distinct_from_parent_slot(linter: PyLinter) -> None:
    module = astroid.parse(
        'class Parent:\n    __slots__ = ("__reference",)\n'
        "class Owner(Parent):\n"
        "    def initialize(self):\n"
        "        self._Parent__reference = 1\n"
        "        self.__reference = 2\n"
    )
    owner = module.body[-1]
    assert isinstance(owner, nodes.ClassDef)
    checker = ClassChecker(linter)
    checker.open()
    linter.set_current_module("distinct_private_slots_control")

    checker._check_attribute_defined_outside_init(owner)

    _assert_outside_init_messages(linter, ["__reference"])


def test_setattr_string_does_not_apply_private_name_mangling(linter: PyLinter) -> None:
    module = astroid.parse(
        'class Owner:\n    __slots__ = ("__reference",)\n'
        "    def initialize(self):\n"
        '        setattr(self, "_Owner__reference", 1)\n'
        '        setattr(self, "__reference", 2)\n'
    )
    owner = module.body[0]
    assert isinstance(owner, nodes.ClassDef)
    checker = ClassChecker(linter)
    checker.open()
    linter.set_current_module("setattr_private_slots_control")
    for call in owner.nodes_of_class(nodes.Call):
        checker.visit_call(call)

    checker._check_attribute_defined_outside_init(owner)

    _assert_outside_init_messages(linter, ["__reference"])


def test_private_assignment_and_unmangled_setattr_are_distinct_fields(
    linter: PyLinter,
) -> None:
    module = astroid.parse(
        "class DictionaryBase: pass\n"
        'class Owner(DictionaryBase):\n    __slots__ = ("__reference",)\n'
        "    def initialize(self):\n"
        "        self.__reference = 1\n"
        '        setattr(self, "__reference", 2)\n'
    )
    owner = module.body[-1]
    assert isinstance(owner, nodes.ClassDef)
    checker = ClassChecker(linter)
    checker.open()
    linter.set_current_module("distinct_assignment_slots_control")
    for call in owner.nodes_of_class(nodes.Call):
        checker.visit_call(call)

    checker._check_attribute_defined_outside_init(owner)

    _assert_outside_init_messages(linter, ["__reference"])
    assert linter.reporter.messages[0].line == 6


def test_known_slot_without_dictionary_base_declares_field(linter: PyLinter) -> None:
    module = astroid.parse(
        'class Owner:\n    __slots__ = ("reference",)\n'
        "    def initialize(self):\n        self.reference = 1\n"
    )
    owner = module.body[0]
    assert isinstance(owner, nodes.ClassDef)
    checker = ClassChecker(linter)
    checker.open()
    linter.set_current_module("pure_slots_control")

    checker._check_attribute_defined_outside_init(owner)

    assert not linter.reporter.messages
