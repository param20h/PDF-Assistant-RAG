def test_profile_update_duplicate_username(client, auth_headers, other_user):
    response = client.put(
        "/profile/",
        json={"username": "other"},
        headers=auth_headers,
    )
    assert response.status_code == 400
    assert response.json()["error"]["message"] == "Username already exists"


def test_profile_update_keep_username(client, auth_headers, user):
    response = client.put(
        "/profile/",
        json={"username": "tester"},
        headers=auth_headers,
    )
    assert response.status_code == 200
    assert response.json()["username"] == "tester"


def test_profile_update_unique_username(client, auth_headers, user):
    response = client.put(
        "/profile/",
        json={"username": "tester_new"},
        headers=auth_headers,
    )
    assert response.status_code == 200
    assert response.json()["username"] == "tester_new"
