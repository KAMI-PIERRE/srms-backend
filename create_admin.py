import requests

# Register an admin user
url = "http://localhost:5000/register"
admin_data = {
    "username": "admin",
    "password": "admin123",
    "role": "admin"
}

try:
    response = requests.post(url, json=admin_data)
    print(f"Status Code: {response.status_code}")
    print(f"Response: {response.text}")
    if response.status_code == 201:
        print("Admin user created successfully!")
    else:
        print("Failed to create admin user")
except Exception as e:
    print(f"Error: {e}")