"""Plain-assert tests for build_site. Run: python3 test_build_site.py"""
import build_site


def test_parse_attaches_current_theme():
    text = (
        "## Taste is the human edge\n"
        "\n"
        "> \"a first quote\"\n"
        "> — [[Jane Doe - A Talk]]\n"
        "\n"
        "## The last mile is ours\n"
        "\n"
        "> \"a second quote\"\n"
        "> — [[John Roe - An Essay]]\n"
    )
    quotes = build_site.parse(text)
    assert len(quotes) == 2, quotes
    assert quotes[0]["theme"] == "Taste is the human edge", quotes[0]
    assert quotes[1]["theme"] == "The last mile is ours", quotes[1]


def test_parse_theme_empty_before_any_heading():
    text = '> "orphan quote"\n> — [[Jane Doe - A Talk]]\n'
    quotes = build_site.parse(text)
    assert quotes[0]["theme"] == "", quotes[0]


def _run():
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
            print(f"  ok {name}")
    print("OK")


if __name__ == "__main__":
    _run()
