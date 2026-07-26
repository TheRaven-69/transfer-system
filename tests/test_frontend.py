def test_root_serves_frontend(client):
    response = client.get("/")

    assert response.status_code == 200
    assert "Transfer System Frontend" in response.text
    assert "/static/app.js" in response.text


def test_static_assets_are_served(client):
    response = client.get("/static/app.js")

    assert response.status_code == 200
    assert "refreshHealth" in response.text


def test_users_frontend_page_is_served(client):
    response = client.get("/ui/users")

    assert response.status_code == 200
    assert "Users workspace" in response.text


def test_wallets_frontend_page_is_served(client):
    response = client.get("/ui/wallets")

    assert response.status_code == 200
    assert "Wallets workspace" in response.text


def test_transfers_frontend_page_is_served(client):
    response = client.get("/ui/transfers")

    assert response.status_code == 200
    assert "Transfers workspace" in response.text
