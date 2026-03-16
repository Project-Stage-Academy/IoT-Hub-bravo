# Usage Examples for IoT Hub Bravo APIs

## 1. Authentication

### **Login to get a bearer token**

```
curl --location 'http://localhost:8000/api/auth/login/' \
--header 'Content-Type: application/json' \
--header 'Accept: application/json' \
--data '{
  "username": "testuser",
  "password": "testpassword"
}'
```

### **Response Example:**
```
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "Bearer"
}
```
## 2. Device Management
### **List devices**
```
curl --location 'http://localhost:8000/api/devices/?limit=5&offset=0' \
--header 'Accept: application/json' \
--header 'Authorization: Bearer {{bearerToken}}'
```
### **Create a new device**
```
curl --location 'http://localhost:8000/api/devices/' \
--header 'Content-Type: application/json' \
--header 'Accept: application/json' \
--header 'Authorization: Bearer {{bearerToken}}' \
--data '{
  "schema_version": "v1",
  "device": {
    "serial_id": "DEF12345",
    "name": "Digital thermometer",
    "description": "Monitors indoor temperature",
    "user_id": 1,
    "is_active": false
  }
}'
```
### **Retrieve a device by ID**
```
curl --location 'http://localhost:8000/api/devices/1/' \
--header 'Accept: application/json' \
--header 'Authorization: Bearer {{bearerToken}}'
```
### **Update device (PUT)**
```
curl --location --request PUT 'http://localhost:8000/api/devices/1/' \
--header 'Content-Type: application/json' \
--header 'Accept: application/json' \
--header 'Authorization: Bearer {{bearerToken}}' \
--data '{
  "schema_version": "v1",
  "device": {
    "serial_id": "DEF12345",
    "name": "Digital thermometer",
    "description": "Monitors indoor temperature",
    "user_id": 1,
    "is_active": false
  }
}'
```
### **Partial update (PATCH)**
```
curl --location --request PATCH 'http://localhost:8000/api/devices/1/' \
--header 'Content-Type: application/json' \
--header 'Accept: application/json' \
--header 'Authorization: Bearer {{bearerToken}}' \
--data '{
  "schema_version": "v1",
  "device": {
    "name": "Updated smoke detector name",
    "description": "Updated description",
    "is_active": true
  }
}'
```
### **Delete a device**
```
curl --location --request DELETE 'http://localhost:8000/api/devices/1/' \
--header 'Accept: application/json' \
--header 'Authorization: Bearer {{bearerToken}}'
```
## 3. Telemetry Management
### **List telemetry for a device**
```
curl --location 'http://localhost:8000/api/telemetry/?device_id=1&limit=5&offset=0' \
--header 'Accept: application/json' \
--header 'Authorization: Bearer {{bearerToken}}'
```
### **Submit telemetry (async ingestion)**
```
curl --location 'http://localhost:8000/api/telemetry/' \
--header 'Ingest-Async: 1' \
--header 'Content-Type: application/json' \
--header 'Accept: application/json' \
--header 'Authorization: Bearer {{bearerToken}}' \
--data '{
  "schema_version": 1,
  "device": "DEV-001",
  "ts": "2026-02-04T12:00:00Z",
  "metric": {
    "temperature": {
      "value": 21.5,
      "unit": "celsius"
    },
    "door_open": {
      "value": false,
      "unit": "closed"
    },
    "status": {
      "value": "ok",
      "unit": "Online"
    }
  }
}'
```
## 4. Rules Management
### **List rules**
```
curl --location 'http://localhost:8000/api/rules/?limit=20&offset=0&is_active=false' \
--header 'Accept: application/json' \
--header 'Authorization: Bearer {{bearerToken}}'
```
### **Create a rule**
```
curl --location 'http://localhost:8000/api/rules/' \
--header 'Content-Type: application/json' \
--header 'Accept: application/json' \
--header 'Authorization: Bearer {{bearerToken}}' \
--data '{
  "schema_version": 1,
  "name": "High Temperature Alert",
  "description": "Alert when temperature exceeds 30°C",
  "is_active": true,
  "condition": {
    "type": "threshold",
    "operator": ">",
    "value": 30
  },
  "action": {
    "webhook": {
      "url": "https://webhook.site/your-webhook",
      "enabled": true
    },
    "notification": {
      "channel": "email",
      "enabled": true,
      "message": "High temperature in {device_name}: {value}°C"
    }
  },
  "device_metric_id": 1
}'
```
### **Evaluate a rule**
```
curl --location 'http://localhost:8000/api/rules/evaluate/' \
--header 'Content-Type: application/json' \
--header 'Accept: application/json' \
--header 'Authorization: Bearer {{bearerToken}}' \
--data '{
  "rule_id": 12,
  "device_id": 5
}'
```
### **Update a rule (PUT)**
```
curl --location --request PUT 'http://localhost:8000/api/rules/3400/' \
--header 'Content-Type: application/json' \
--header 'Accept: application/json' \
--header 'Authorization: Bearer {{bearerToken}}' \
--data '{
  "schema_version": 1,
  "name": "High Temperature Alert",
  "description": "Alert when temperature exceeds 30°C",
  "is_active": true,
  "condition": {
    "type": "threshold",
    "operator": ">",
    "value": 30
  },
  "action": {
    "webhook": {
      "url": "https://webhook.site/your-webhook",
      "enabled": true
    },
    "notification": {
      "channel": "email",
      "enabled": true,
      "message": "High temperature in {device_name}: {value}°C"
    }
  },
  "device_metric_id": 1
}'
```
### **Partial update (PATCH)**
```
curl --location --request PATCH 'http://localhost:8000/api/rules/3400/' \
--header 'Content-Type: application/json' \
--header 'Accept: application/json' \
--header 'Authorization: Bearer {{bearerToken}}' \
--data '{
  "is_active": false
}'
```
### **Delete a rule**
```
curl --location --request DELETE 'http://localhost:8000/api/rules/3400/' \
--header 'Accept: application/json' \
--header 'Authorization: Bearer {{bearerToken}}'
```
## 5. Event Management
### **List events with filters**
```
curl --location 'http://localhost:8000/api/events/?rule_id=2933&device_id=2933&acknowledged=true&severity=string&limit=50&offset=0' \
--header 'Accept: application/json' \
--header 'Authorization: Bearer {{bearerToken}}'
```
### **Acknowledge an event**
```
curl --location --request POST 'http://localhost:8000/api/events/2933/ack/' \
--header 'Accept: application/json' \
--header 'Authorization: Bearer {{bearerToken}}'
Retrieve an event by ID
curl --location 'http://localhost:8000/api/events/2933/' \
--header 'Accept: application/json' \
--header 'Authorization: Bearer {{bearerToken}}'
```
---
✅ **This collection of usage examples covers common devices, telemetry scenarios, rules, and event handling, providing a full integration guide for developers.**