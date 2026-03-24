import requests
import json
import time
import random
import threading

# Saleor GraphQL Endpoint (assumed local via Docker)
SALEOR_URL = "http://localhost:8000/graphql/"

# GraphQL Queries
QUERIES = [
    """
    query {
      products(first: 5, channel: "default-channel") {
        edges {
          node {
            id
            name
          }
        }
      }
    }
    """,
    """
    query {
      categories(first: 5) {
        edges {
          node {
            id
            name
          }
        }
      }
    }
    """,
    """
    query {
      me {
        id
        email
      }
    }
    """
]

def generate_load(rps=2):
    """Generate continuous load on the Saleor API."""
    print(f"[LoadGenerator] Starting load generation at ~{rps} requests/sec")
    while True:
        query = random.choice(QUERIES)
        try:
            # We don't actually need real data, just to trigger Saleor core code
            start = time.time()
            response = requests.post(SALEOR_URL, json={'query': query})
            duration = time.time() - start
            # print(f"[LoadGenerator] Request took {duration:.3f}s, Status: {response.status_code}")
        except Exception as e:
            print(f"[LoadGenerator] Request failed: {e}")
        
        time.sleep(1.0 / rps)

if __name__ == "__main__":
    generate_load()
