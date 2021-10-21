import asyncio

from environmental_sensing.env_sensor import EnvironmentalSensor
from environmental_sensing.mqtt_client import MqttClient

BT_ADDRESS = "98:4F:EE:0F:50:00"
MQTT_ADDRESS = "raspberrypi.lan"

async def main(bt_address: str, mqtt_address: str):
    queue = asyncio.Queue()
    sensor = EnvironmentalSensor(BT_ADDRESS, 0, queue)
    mqtt = MqttClient(MQTT_ADDRESS, queue)
    
    mqtt_task = mqtt.run()
    sensor_task = sensor.run()

    try:
        await asyncio.gather(mqtt_task, sensor_task)
    except KeyboardInterrupt:
        print("Caught signal, exiting")
    except Exception as e:
        print("Fatal error: ", end="")
        print(e)
    for task in asyncio.all_tasks():
        task.cancel()

if __name__ == "__main__":
    try:
        asyncio.run(main(BT_ADDRESS,MQTT_ADDRESS))
    except asyncio.CancelledError:
        pass