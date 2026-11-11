# Declared slot storage and attribute-defined-outside-init

Pylint 4.1.3+stablekite.2 recognizes statically known slot descriptors as
declarations of instance fields for W0201. The existing checker already
recognizes ordinary class attributes and annotation-only fields. A slot is
also a class declaration of storage, even when its first value is assigned
outside the constructor.

The change reads actual Astroid class and expression nodes. It accepts known
slot names in tuples, lists, sets, dictionary keys and single strings, including
inferred constant declarations. It intersects alternative declarations so an
unknown or missing alternative cannot establish an arbitrary field.

Known descriptors are collected from each declaring class in the MRO. This
also handles inheritance from a class with a normal instance dictionary, where
Astroid's aggregate slots() result is None even though slot descriptors exist.

Private names use the declaring class's compiler mangling rules. A child's
private field differs from a parent's private slot. Attribute assignment syntax
is mangled in its lexical class, while string arguments to setattr retain their
literal value. These assignments remain distinct even when Astroid groups them
under the same source spelling.

Only the proven declared-slot assignments leave the W0201 candidate list.
Undeclared attributes, extra attributes and uninferred dynamic names retain
their diagnostics. Other slot checks and all other checker rules remain intact.
The patch introduces no ignore, cast, Any annotation, project-specific path,
class-name exception or runtime placeholder.

Existing tests and expected results remain unchanged. Separate regression
tests cover mixed dictionary inheritance, inherited storage, ordinary and
private fields, ambiguous declarations, unknown names and setattr. Native
qualification additionally exercises actual ctypes.byref values and real
MemberDescriptorType storage under free-threaded CPython 3.15.
