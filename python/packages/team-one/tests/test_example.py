import team_one


def test_about() -> None:
    about = team_one.ABOUT

    assert isinstance(about, str)
