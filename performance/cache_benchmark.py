"""Crude benchmark for our LRU cache."""

import timeit
from typing import Any
from typing import MutableMapping

# from liquid2.utils.cache import LRUCache as LegacyLRUCache
from liquid2.utils.lru_cache import LRUCache
from liquid2.utils.lru_cache import ThreadSafeLRUCache

# ruff: noqa: D103, T201


def benchmark_get_miss(_cache: Any, *, label: str) -> None:
    cache: MutableMapping[str, str] = _cache(10)
    t = timeit.repeat("cache.get('nosuchthing')", globals={"cache": cache})
    print(f"Get miss ({label}): {min(t):.2}")


def benchmark_get_hit(_cache: Any, *, label: str) -> None:
    cache: MutableMapping[str, str] = _cache(10)
    cache["a"] = "b"
    t = timeit.repeat("cache.get('a')", globals={"cache": cache})
    print(f"Get hit ({label}): {min(t):.2}")


def benchmark_getitem_hit(_cache: Any, *, label: str) -> None:
    cache: MutableMapping[str, str] = _cache(10)
    cache["a"] = "b"
    t = timeit.repeat("cache['a']", globals={"cache": cache})
    print(f"Get item hit ({label}): {min(t):.2}")


def benchmark_move_to_end(_cache: Any, *, label: str) -> None:
    cache: MutableMapping[str, str] = _cache(10)
    cache["a"] = "1"
    cache["b"] = "2"
    cache["c"] = "3"
    t = timeit.repeat(
        "cache['a'] = '1'; cache['b'] = '2'; cache['c'] = '3'; cache['a']",
        globals={"cache": cache},
    )
    print(f"Move to end ({label}): {min(t):.2}")


def main() -> None:
    benchmark_get_miss(LRUCache, label="defaultdict")
    benchmark_get_miss(ThreadSafeLRUCache, label="thread safe defaultdict")
    # benchmark_get_miss(LegacyLRUCache, label="legacy")
    print()
    benchmark_get_hit(LRUCache, label="defaultdict")
    benchmark_get_hit(ThreadSafeLRUCache, label="thread safe defaultdict")
    # benchmark_get_hit(LegacyLRUCache, label="legacy")
    print()
    benchmark_getitem_hit(LRUCache, label="defaultdict")
    benchmark_getitem_hit(ThreadSafeLRUCache, label="thread safe defaultdict")
    # benchmark_getitem_hit(LegacyLRUCache, label="legacy")
    print()
    benchmark_move_to_end(LRUCache, label="defaultdict")
    benchmark_move_to_end(ThreadSafeLRUCache, label="thread safe defaultdict")
    # benchmark_move_to_end(LegacyLRUCache, label="legacy")


if __name__ == "__main__":
    main()
