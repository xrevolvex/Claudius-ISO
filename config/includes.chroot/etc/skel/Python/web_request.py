#!/usr/bin/env python3
"""Talk to a web API with the requests library (needs internet)."""
import requests

r = requests.get("https://api.github.com/repos/python/cpython", timeout=10)
r.raise_for_status()
repo = r.json()
print(f"{repo['full_name']}: {repo['description']}")
print(f"⭐ {repo['stargazers_count']:,} stars, {repo['forks_count']:,} forks")
