from fastapi.testclient import TestClient
from app.main import app

def test_agent_endpoint_returns_provenance():
    client=TestClient(app)
    response=client.post('/api/v1/agent',json={'message':'सोनीपत मंडी में गेहूं का भाव क्या है?','language':'hi'})
    assert response.status_code == 200
    data=response.json()
    assert data['intent']=='farming'
    assert data['source']['name']=='Saathi Demo Mandi'
    assert data['demo'] is True
    assert data['tool_name'] == 'get_mandi_price'
    assert isinstance(data['latency_ms'], (int, float)) and data['latency_ms'] >= 0

def test_liveness():
    assert TestClient(app).get('/health/live').json()['status']=='alive'


def test_agent_endpoint_exposes_all_sources_for_combined_request():
    client=TestClient(app)
    response=client.post(
        '/api/v1/agent',
        json={
            'message':'सोनीपत में गेहूं का मंडी भाव और अगले 24 घंटे में बारिश का chance?',
            'language':'hi',
            'location':{'latitude':28.9931,'longitude':77.0151,'label':'Sonipat'},
        },
    )
    assert response.status_code == 200
    data=response.json()
    assert data['tool_name']=='get_mandi_price+get_weather'
    assert len(data['sources']) == 2
    assert data['source']['name'] in {item['name'] for item in data['sources']}

def test_voice_response_schema_keeps_telemetry_fields():
    from app.schemas import VoiceTurnResponse
    payload=VoiceTurnResponse(status='ok',tool_name='get_weather',latency_ms=12.5)
    assert payload.tool_name == 'get_weather'
    assert payload.latency_ms == 12.5



def test_api_responses_include_baseline_security_headers():
    response = TestClient(app).get('/health/live')
    assert response.headers['x-content-type-options'] == 'nosniff'
    assert response.headers['x-frame-options'] == 'DENY'
    assert response.headers['referrer-policy'] == 'no-referrer'
    assert response.headers['permissions-policy'] == 'camera=(), microphone=(), geolocation=()'



def test_outbound_call_demo_mode_does_not_bypass_auth_in_production(monkeypatch):
    import app.main as main

    monkeypatch.setattr(main.settings, "demo_mode", True)
    monkeypatch.setattr(main.settings, "app_env", "production")
    monkeypatch.setattr(main.settings, "call_api_token", None)
    response = TestClient(app).post(
        "/api/v1/calls",
        json={"to": "+911234567890", "callback_url": "https://example.test/callback", "consent": True},
    )
    assert response.status_code == 401
    assert response.json()["detail"] == "call_api_unauthorized"
