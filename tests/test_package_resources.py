from importlib.resources import files


def test_runtime_resources_are_packaged():
    package = files("src")
    for resource_name in ("ai_mentor_data.json", "bandit_levels.json", "app.tcss"):
        resource = package.joinpath(resource_name)
        assert resource.is_file(), f"missing package resource: {resource_name}"
