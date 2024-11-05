import cProfile
import sys
import timeit
from pathlib import Path

from liquid2 import Environment
from liquid2.lexer import tokenize


def fixture(path_to_templates: Path) -> dict[str, str]:
    loader_dict: dict[str, str] = {}

    for input_file in path_to_templates.glob("*html"):
        loader_dict[input_file.name] = input_file.read_text()

    return loader_dict


def print_result(
    name: str, times: list[float], n_iterations: int, n_templates: int
) -> None:
    best = min(times)
    n_calls = n_iterations * n_templates
    per_sec = round(n_calls / best, 2)

    per_i = best / n_iterations
    i_per_s = 1 / per_i

    print(f"{name:>31}: {best:.2}s ({per_sec:.2f} ops/s, {i_per_s:.2f} i/s)")


def benchmark(search_path: str, number: int = 1000, repeat: int = 5) -> None:
    templates = fixture(Path(search_path))
    template = templates["main.html"]

    print(len(template))

    print((f"Best of {repeat} rounds with {number} iterations per round."))

    print_result(
        "scan template",
        timeit.repeat(
            "tokenize(template)",
            globals={
                "template": template,
                "tokenize": tokenize,
            },
            number=number,
            repeat=repeat,
        ),
        number,
        1,
    )

    print_result(
        "parse template",
        timeit.repeat(
            "env.from_string(template)",
            globals={
                "template": template,
                "env": Environment(),
            },
            number=number,
            repeat=repeat,
        ),
        number,
        1,
    )


def profile_parse(search_path: str) -> None:
    templates = fixture(Path(search_path))
    template = templates["main.html"]
    env = Environment()

    for _ in range(10000):
        env.from_string(template)


def main() -> None:
    search_path = "performance/fixtures/001/templates/"

    args = sys.argv
    n_args = len(args)

    if n_args == 1:
        benchmark(search_path)
    elif n_args == 2 and args[1] == "--profile":
        profile_parse(search_path)
    else:
        sys.stderr.write(f"usage: python {args[0]} [--profile]\n")
        sys.exit(1)


if __name__ == "__main__":
    main()
