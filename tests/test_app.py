import pytest
from app import app
import json

@pytest.fixture
def client():
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client

def test_index_route(client):
    """Test that the main index page loads."""
    response = client.get('/')
    assert response.status_code == 200
    assert b"Binance Advanced Algorithmic Terminal" in response.data

def test_algo_toggle_on(client):
    """Test the algorithm toggle endpoint."""
    response = client.post('/api/algo/toggle', 
                           data=json.dumps({'active': True}),
                           content_type='application/json')
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data['status'] == 'success'
    assert 'Started' in data['message']

def test_algo_toggle_off(client):
    """Test stopping the algorithm."""
    response = client.post('/api/algo/toggle', 
                           data=json.dumps({'active': False}),
                           content_type='application/json')
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data['status'] == 'success'
    assert 'Stopped' in data['message']
