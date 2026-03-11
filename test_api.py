"""Test API endpoints."""
import requests
import json

# Test stats API
print("Testing /api/v1/dashboard/stats...")
resp = requests.get("http://localhost:8000/api/v1/dashboard/stats")
print(f"Status: {resp.status_code}")
print(f"Response: {resp.text[:500]}")

# Test items API
print("\nTesting /api/v1/dashboard/items...")
resp = requests.get("http://localhost:8000/api/v1/dashboard/items")
print(f"Status: {resp.status_code}")
print(f"Response: {resp.text[:200]}")

# Test departments API
print("\nTesting /api/v1/organization/departments...")
resp = requests.get("http://localhost:8000/api/v1/organization/departments")
print(f"Status: {resp.status_code}")
print(f"Response: {resp.text[:500]}")

# Test employees API
print("\nTesting /api/v1/organization/employees...")
resp = requests.get("http://localhost:8000/api/v1/organization/employees")
print(f"Status: {resp.status_code}")
print(f"Response: {resp.text[:500]}")
