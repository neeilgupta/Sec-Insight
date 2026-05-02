from pathlib import Path


def test_dockerfile_exists():
    assert Path("backend/Dockerfile").exists()


def test_dockerfile_has_uvicorn_cmd():
    content = Path("backend/Dockerfile").read_text()
    assert "uvicorn" in content
    assert "8000" in content


def test_docker_compose_exists():
    assert Path("docker-compose.yml").exists()


def test_env_example_exists():
    assert Path(".env.example").exists()
