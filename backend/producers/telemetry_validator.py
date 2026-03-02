# from decouple import config
# from apps.devices.tasks import CleanData
# TOPIC = config('KAFKA_TOPIC_TELEMETRY_CLEAN', default='telemetry.clean')

# producer = get_telemetry_clean_producer()
# clean_telemetry_data = CleanData()

# validated_items = clean_telemetry_data.validated_data

# for item in validated_items:
#     producer.produce(payload=item,key=str(item['device_metric_id']))

# producer.flush()
