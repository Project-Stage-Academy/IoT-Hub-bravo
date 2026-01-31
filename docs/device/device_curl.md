## Device cURL commands

### Authentication and Authorization
- Authenticate as Client:
    `curl -X POST http://localhost:8000/api/auth/login/ -H "Content-Type: application/json" -d "{ \"username\": \"testuser\", \"password\": \"testpassword\"}"`

- Authenticate as Admin:
    `curl -X POST http://localhost:8000/api/auth/login/ -H "Content-Type: application/json" -d "{ \"username\": \"adminuser\", \"password\": \"adminpassword\"}"`

### /api/devices/:
- GET (default pagination parameters: limit=5, offset=0):
    `curl -X GET http://localhost:8000/api/devices/ -H "Content-Type: application/json" -H "Authorization: Bearer <client/admin-token>"`
- GET (pagination parameters: limit=5, offset=5):
    `curl -X GET "http://localhost:8000/api/devices/?limit=5&offset=5" -H "Content-Type: application/json" -H "Authorization: Bearer <client/admin-token>"`
- POST:
    `curl -X POST http://localhost:8000/api/devices/ -H "Content-Type: application/json" -H "Authorization: Bearer <admin-token>" -d "{ \"serial_id\": \"ABC123456\", \"name\": \"Testing Device\", \"description\": \"Testing description\", \"user_id\": 2, \"is_active\": false }"`

### /api/devices/{device_id}/:
- GET:
    `curl -X GET http://localhost:8000/api/devices/1/ -H "Content-Type: application/json" -H "Authorization: Bearer <client/admin-token>"`

- PUT:
    `curl -X PUT http://localhost:8000/api/devices/1/ -H "Content-Type: application/json" -H "Authorization: Bearer <admin-token>" -d "{ \"serial_id\": \"ABC123456\", \"name\": \"Update Device\", \"description\": \"Update description\", \"user_id\": 2, \"is_active\": false }"`
    
- PATCH:
    `curl -X PATCH http://localhost:8000/api/devices/1/ -H "Content-Type: application/json" -H "Authorization: Bearer <admin-token>" -d "{ \"name\": \"Second Update Device\", \"is_active\": true }"`

- DELETE:
    `curl -X DELETE http://localhost:8000/api/devices/1/ -H "Content-Type: application/json" -H "Authorization: Bearer <admin-token>"`