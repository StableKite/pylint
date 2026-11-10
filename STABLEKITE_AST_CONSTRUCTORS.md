# StableKite AST constructor correction

This fork is the actual Pylint 4.1.3 release plus the local version
`4.1.3+stablekite.1`. It distinguishes valid AST type use from constructing an
abstract AST base, which Python 3.15 deprecates. W4904 remains enabled.

`from ast import expr` is valid for annotations, type aliases, `isinstance`, and
subclassing. Calls such as `ast.expr()`, imported constructor aliases and module
aliases still report W4904 at the call. Other deprecated class imports and
shadowed/concrete constructors retain their behavior. Older target versions
skip the added constructor inference when their deprecation map is empty.

Install the default of this fork using ordinary pip:

```sh
python -m pip install git+https://github.com/StableKite/pylint.git
```

The change includes fourteen regressions with valid uses and real constructor
controls. On native Windows CPython 3.15.2t with astroid 4.3.4, the original full
checker/functional selection has 1392 passes and six failures. This version has
1406 passes and the same six failures; all 1465 shared case outcomes match.
The 67 skipped outcomes include four expected failures. The six inherited
failures are `invalid_all_format_valid_5`, `invalid_all_format_valid_6`,
`regression_4680`, `regression_9497`, `undefined_variable_typing`, and
`unused_import_assigned_to`. They remain open. This is not a claim that the
complete upstream Pylint suite passes on Python 3.15.

On native Linux CPython 3.15.2t, the same original selection has 1389 passes
and sixteen inherited failures before this patch, and 1403 passes with the
same sixteen failures afterwards. All 1465 shared case outcomes match and
the fourteen new regressions pass. Fresh ordinary wheel consumers on both
Windows and Linux validate the full project configuration: the real parsed
expression and annotation have no W4904; four real constructor forms keep
their W4904 at call lines 5, 6, 7, and 8.
