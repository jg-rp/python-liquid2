import timeit
from pathlib import Path

# from liquid2 import DictLoader
from liquid2 import Environment

# from liquid2 import Template
from liquid2.lexer import tokenize


def fixture(path_to_templates: Path) -> dict[str, str]:
    loader_dict: dict[str, str] = {}

    for input_file in path_to_templates.glob("*html"):
        loader_dict[input_file.name] = input_file.read_text()

    return loader_dict


def lex(env: Environment, templates: dict[str, str]) -> None:
    for source in templates.values():
        tokenize(env, source)


def parse(env: Environment, templates: dict[str, str]) -> None:
    for source in templates.values():
        env.from_string(source)


# def render(root: Template, data: dict[str, object]) -> None:
#     root.render(**data)


# def parse_and_render(
#     env: Environment,
#     templates: dict[str, str],
#     data: dict[str, object],
# ) -> None:
#     for source in templates.values():
#         template = env.from_string(source)
#         template.render(**data)


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
    n_templates = len(templates)
    n_calls = number * n_templates

    print(
        (
            f"Best of {repeat} rounds with {number} iterations per round "
            f"and {n_templates} ops per iteration ({n_calls} ops per round)."
        )
    )

    print_result(
        "lex template (not expressions)",
        timeit.repeat(
            "lex(env, templates)",
            globals={
                "lex": lex,
                "env": Environment(),
                "search_path": search_path,
                "templates": templates,
                "tokenize": tokenize,
            },
            number=number,
            repeat=repeat,
        ),
        number,
        n_templates,
    )

    print_result(
        "lex and parse",
        timeit.repeat(
            "parse(env, templates)",
            globals={
                "parse": parse,
                "search_path": search_path,
                "env": Environment(),
                "templates": templates,
            },
            number=number,
            repeat=repeat,
        ),
        number,
        n_templates,
    )

    # print_result(
    #     "render",
    #     timeit.repeat(
    #         "render(templates)",
    #         setup="templates = setup_render(search_path)",
    #         globals={**globals(), "search_path": search_path},
    #         number=number,
    #         repeat=repeat,
    #     ),
    #     number,
    #     n_templates,
    # )

    # print_result(
    #     "lex, parse and render",
    #     timeit.repeat(
    #         "parse_and_render(env, templates)",
    #         setup="env, templates = setup_parse(search_path)",
    #         globals={**globals(), "search_path": search_path},
    #         number=number,
    #         repeat=repeat,
    #     ),
    #     number,
    #     n_templates,
    # )


def main() -> None:
    search_path = "performance/fixtures/001/templates/"
    benchmark(search_path)


if __name__ == "__main__":
    main()
