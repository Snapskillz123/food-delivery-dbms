from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_website_shell_is_served() -> None:
    response = client.get("/")

    assert response.status_code == 200
    assert "Fork &amp; Route" not in response.text
    assert "Fork & Route" in response.text
    assert 'id="restaurantGrid"' in response.text
    assert 'id="cartDrawer"' in response.text


def test_website_assets_are_served_with_expected_content_types() -> None:
    stylesheet = client.get("/site-assets/styles.css")
    script = client.get("/site-assets/app.js")

    assert stylesheet.status_code == 200
    assert stylesheet.headers["content-type"].startswith("text/css")
    assert "restaurant-grid" in stylesheet.text
    assert script.status_code == 200
    assert "javascript" in script.headers["content-type"]
    assert "async function checkout" in script.text
