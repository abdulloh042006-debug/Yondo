def test_liveness_endpoint(client):
    response = client.get('/health', headers={'X-Request-ID': 'test-request-id'})

    assert response.status_code == 200
    assert response.json() == {'status': 'ok', 'service': 'Yondo API', 'version': '0.1.0'}
    assert response.headers['X-Request-ID'] == 'test-request-id'


def test_versioned_readiness_endpoint_reports_dependencies(client, app):
    async def healthy():
        return True

    app.state.readiness_checks = {'database': healthy, 'redis': healthy}
    response = client.get('/api/v1/health/ready')

    assert response.status_code == 200
    assert response.json() == {
        'status': 'ok',
        'checks': {'database': 'ok', 'redis': 'ok'},
    }


def test_readiness_is_unavailable_when_dependency_fails(client, app):
    async def healthy():
        return True

    async def unhealthy():
        raise ConnectionError('not exposed to clients')

    app.state.readiness_checks = {'database': healthy, 'redis': unhealthy}
    response = client.get('/api/v1/health/ready')

    assert response.status_code == 503
    assert response.json() == {
        'status': 'unavailable',
        'checks': {'database': 'ok', 'redis': 'unavailable'},
    }

