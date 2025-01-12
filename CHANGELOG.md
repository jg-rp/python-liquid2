# Python Liquid2 Change Log

## Version 0.2.0 (unreleased)

**Features**

- Added support for array literal syntax in `for` loop expressions. Previously array literals were only allowed in output statements and the `assign` tag. For example, `{% for x in some.thing, 42, true %}`.
- Add tokens for symbols `!` and `?`. These tokens are not used by any default Liquid expression, but can be used by custom tags.

## Version 0.1.0

Initial release. See [docs](https://jg-rp.github.io/python-liquid2/) and [migration guide](https://jg-rp.github.io/python-liquid2/migration/).
