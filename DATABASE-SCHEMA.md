Table "users" {

  "id" SERIAL [pk, increment]

  "username" VARCHAR(150) [unique, not null]

  "email" VARCHAR(255) [unique, not null]

  "password" VARCHAR(255) [not null]

  "role" ENUM('admin', 'client') [default: 'client']

  "created_at" TIMESTAMP [default: `CURRENT_TIMESTAMP`]

  "updated_at" TIMESTAMP [default: `CURRENT_TIMESTAMP`]

  Indexes {

    (role) [name: "idx_users_role"]

  }

}

Table "devices" {

  "id" SERIAL [pk, increment]

  "serial_id" VARCHAR(255) [unique, not null]

  "name" VARCHAR(255) [not null]

  "description" TEXT

  "user_id" INTEGER

  "is_active" BOOLEAN [default: TRUE]

  "created_at" TIMESTAMP [default: `CURRENT_TIMESTAMP`]

  Indexes {

    (user_id) [name: "idx_devices_user_id"]

    (is_active) [name: "idx_devices_is_active"]

  }

}

Table "rules" {

  "id" SERIAL [pk, increment]

  "name" VARCHAR(255) [not null]

  "description" TEXT

  "condition" JSONB [not null]

  "action" JSONB [not null]

  "is_active" BOOLEAN [default: TRUE]

  "device_metric_id" INTEGER

  Indexes {

    (device_metric_id) [name: "idx_rules_device_metric"]

    (is_active) [name: "idx_rules_is_active"]

  }

}

Table "events" {

  "id" BIGSERIAL [pk, increment]

  "timestamp" TIMESTAMP [not null]

  "rule_id" INTEGER

  "created_at" TIMESTAMP [default: `CURRENT_TIMESTAMP`]

  Indexes {

    (timestamp) [name: "idx_events_timestamp"]

    (rule_id) [name: "idx_events_rule"]

  }

}

// Table "notifications" {

//   "id" SERIAL [pk, increment]

//   "event_id" BIGINT

//   "type" ENUM('email','webhook','sms') [not null]

//   "target" TEXT [not null]

//   "status" ENUM('pending','sent','failed') [default: 'pending']

//   "message" TEXT

//   "sent_at" TIMESTAMP

//   "created_at" TIMESTAMP [default: `CURRENT_TIMESTAMP`]

// }

Table "metrics" {

  "id" SERIAL [pk, increment]

  "metric_type" CITEXT [unique, not null]

  "data_type" ENUM('numeric', 'str', 'boolean') [not null]

}

Table telemetries {

  id bigserial [pk, increment]

  device_metric_id int [not null]

  value_jsonb jsonb [not null]

  // Generated columns — заповнюються тільки для правильного типу

  value_numeric NUMERIC [note: 'GENERATED ALWAYS AS (CASE WHEN value_jsonb->>\'t\' = \'numeric\' THEN (value_jsonb->>\'v\')::numeric ELSE NULL END) STORED']

  value_bool BOOLEAN [note: 'GENERATED ALWAYS AS (CASE WHEN value_jsonb->>\'t\' = \'bool\' THEN (value_jsonb->>\'v\')::boolean ELSE NULL END) STORED']

  value_str TEXT [note: 'GENERATED ALWAYS AS (CASE WHEN value_jsonb->>\'t\' = \'str\' THEN value_jsonb->>\'v\' ELSE NULL END) STORED']

  ts timestamptz [not null, default: `now()`]

  created_at timestamptz [default: `now()`]

  Indexes {

    (device_metric_id, ts) [unique, name: 'unique_telemetry_per_metric_time']

    (device_metric_id, ts) [name: 'idx_telemetries_metric_time']

    ts [name: 'idx_telemetries_timestamp']

  }

}

Table "device_metrics" {

  "id" SERIAL [pk, increment]

  "device_id" INTEGER [not null]

  "metric_id" INTEGER [not null]

  Indexes {

    (device_id, metric_id) [unique, name: "uq_device_metric"]

    (device_id) [name: "idx_device_metrics_device"]

    (metric_id) [name: "idx_device_metrics_metric"]

  }

} 

Ref: "users"."id" < "devices"."user_id" [delete: cascade]

Ref:"devices"."id" < "device_metrics"."device_id" [delete: cascade]

Ref:"metrics"."id" < "device_metrics"."metric_id" [delete: restrict]

Ref:"device_metrics"."id" < "telemetries"."device_metric_id" [delete: cascade]

Ref:"device_metrics"."id" < "rules"."device_metric_id" [delete: cascade]

Ref:"rules"."id" < "events"."rule_id" [delete: cascade]
