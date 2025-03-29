def test_index_redirect(client):
    """Test that the index page redirects to the create_notification page"""
    response = client.get('/')
    assert response.status_code == 302  # Код перенаправления
    assert '/create_notification' in response.location

def test_create_notification_page(client):
    """Test that the create_notification page loads correctly"""
    response = client.get('/create_notification')
    assert response.status_code == 200
    assert b'create_notification' in response.data

def test_api_get_schedule_times(client):
    """Test the API endpoint for getting schedule times"""
    response = client.get('/api/get_schedule_times')
    assert response.status_code == 200
    assert response.is_json
    data = response.get_json()
    assert isinstance(data, list)
    assert len(data) > 0
    assert 'id' in data[0]
    assert 'name' in data[0]
    assert 'start' in data[0]
    assert 'end' in data[0]