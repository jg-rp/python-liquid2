# Python Liquid2 Change Log

## Version 0.3.0 (unreleased)

**Breaking changes**

- Most built-in expression parsing functions/methods now expect the current `Environment` instance to be passed as the first argument.

**Fixes**

- Fixed `{% for %}` tag expressions with a comma between the iterable and `limit`, `offset` or `reversed`. Previously we were assuming a comma immediately following the iterable would mean we are iterating an array literal. We're also explicitly disallowing `limit`, `offset` and `reversed` arguments after an array literal.

**Features**

- Added optional filter argument validation at template parse time. ([docs](https://jg-rp.github.io/python-liquid2/custom_filters/#filter-argument-validation))
- Added lambda expressions as filter arguments. Both custom and built-in filters can accept arguments of the form `<identifier> => <boolean expression>` or `(<identifier>, <identifier>) => <boolean expression>`.
- Updated filters `map`, `where`, `sort`, `sort_natural`, `uniq`, `compact` and `sum` to accept lambda expression or string arguments.
- Added filters `reject`, `has`, `find` and `find_index`.

**Documentation**

- Added documentation for the `json` filter's optional `indent` argument.

## Version 0.2.0

**Features**

- Added support for array literal syntax in `for` loop expressions. Previously array literals were only allowed in output statements and the `assign` tag. For example, `{% for x in some.thing, 42, true %}`.
- Add tokens for symbols `!` and `?`. These tokens are not used by any default Liquid expression, but can be used by custom tags.

## Version 0.1.0

Initial release. See [docs](https://jg-rp.github.io/python-liquid2/) and [migration guide](https://jg-rp.github.io/python-liquid2/migration/).
