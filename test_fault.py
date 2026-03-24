import requests

for i in range(10):
    try:
        r = requests.post(
            'http://localhost:8001/graphql/',
            json={'query': '{ shop { name } }'},
            headers={'X-Target-URL': 'http://localhost:8000/graphql/'},
            timeout=10
        )
        print(f"{i+1}. Status: {r.status_code}")
    except Exception as e:
        print(f"{i+1}. ERROR: {e}")
