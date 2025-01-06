## base64_decode

<!-- md:version 0.1.0 -->
<!-- md:shopify -->

`<string> | base64_decode`

Decode a base64 encoded string. The decoded value is assumed to be UTF-8 and will be decoded as UTF-8.

!!! warning

    While Python Liquid assumes UTF-8 character encoding, Ruby Liquid does not seem to do so, potentially introducing byte strings into the render context.

```liquid2
{{ 'SGVsbG8sIFdvcmxkIQ==' | base64_decode }}
```

```plain title="output"
Hello, World!
```

If the input value is not a valid base64 encoded string, an exception will be raised.

```liquid2
{{ 'notbase64' | base64_decode }}
```

```plain title="output"
FilterError: invalid base64-encoded string, on line 1
```

## base64_encode

<!-- md:version 0.1.0 -->
<!-- md:shopify -->

`<string> | base64_encode`

Encode a string using base64.

!!! note

    Python Liquid returns a `str` from `base64_encode`, not `bytes`.

```liquid2
{{ 'Hello, World!' | base64_encode }}
```

```plain title="output"
SGVsbG8sIFdvcmxkIQ==
```

If the input value is not a string, it will be converted to a string before base64 encoding.

```liquid2
{{ 5 | base64_encode }}
```

```plain title="output"
NQ==
```

## base64_url_safe_decode

<!-- md:version 0.1.0 -->
<!-- md:shopify -->

`<string> | base64_url_safe_decode`

Decode a URL safe base64 encoded string. Substitutes `-` instead of `+` and `_` instead of `/` in
the standard base64 alphabet. The decoded value is assumed to be UTF-8 and will be decoded as UTF-8.

!!! warning

    While Python Liquid assumes UTF-8 character encoding, Ruby Liquid does not seem to do so, potentially introducing byte strings into the render context.

```liquid2
{{ 'SGVsbG8sIFdvcmxkIQ==' | base64_url_safe_decode }}
```

```plain title="output"
Hello, World!
```

If the input value is not a valid base64 encoded string, an exception will be raised.

```liquid2
{{ 'notbase64' | base64_url_safe_decode }}
```

```plain title="output"
FilterError: invalid base64-encoded string, on line 1
```

## base64_url_safe_encode

<!-- md:version 0.1.0 -->
<!-- md:shopify -->

`<string> | base64_url_safe_encode`

Encode a string using URL safe base64. Substitutes `-` instead of `+` and `_` instead of `/` in
the standard base64 alphabet.

!!! note

    Python Liquid returns a `str` from `base64_url_safe_encode`, not `bytes`.

```liquid2
{{ 'Hello, World!' | base64_url_safe_encode }}
```

```plain title="output"
SGVsbG8sIFdvcmxkIQ==
```

If the input value is not a string, it will be converted to a string before base64 encoding.

```liquid2
{{ 5 | base64_url_safe_encode }}
```

```plain title="output"
NQ==
```
