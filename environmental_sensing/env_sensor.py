import asyncio
import datetime
import struct

from bleak import BleakClient, BleakScanner
from bleak.uuids import uuid16_dict

class EnvironmentalSensor:

    _ENV_SENSING_SERVICE_UUID = "0000181a-0000-1000-8000-00805f9b34fb"
    _ENV_SENSING_MEASUREMENT_DESCRIPTOR_UUID = "0000290c-0000-1000-8000-00805f9b34fb"

    _RELAY_SERVICE_UUID = "8dc27700-8a2f-11eb-b538-0800200c9a66"
    _RELAY_CHAR_UUID = "8dc27701-8a2f-11eb-b538-0800200c9a66"

    _characteristic_specs = {
        "Temperature": { "format": "<h", "M": 1, "d": -2, "b": 0},
        "Pressure": { "format": "<L", "M": 1, "d": -1, "b": 0},
        "Humidity": { "format": "<H", "M": 1, "d": -2, "b": 0}
    }

    _applications = {
        0x00: "Unspecified",
        0x01: "Air",
        0x02: "Water",
        0x03: "Barometric",
        0x04: "Soil",
        0x05: "Infrared",
        0x06: "Map Database",
        0x07: "Barometric Elevation Source",
        0x08: "GPS only Elevation Source",
        0x09: "GPS and Map database Elevation Source",
        0x0A: "Vertical datum Elevation Source",
        0x0B: "Onshore",
        0x0C: "Onboard vessel or vehicle",
        0x0D: "Front",
        0x0E: "Back/Rear",
        0x0F: "Upper",
        0x10: "Lower",
        0x11: "Primary",
        0x12: "Secondary",
        0x13: "Outdoor",
        0x14: "Indoor",
        0x15: "Top",
        0x16: "Bottom",
        0x17: "Main",
        0x18: "Backup",
        0x19: "Auxiliary",
        0x1A: "Supplementary",
        0x1B: "Inside",
        0x1C: "Outside",
        0x1D: "Left",
        0x1E: "Right",
        0x1F: "Internal",
        0x20: "External",
        0x21: "Solar"
    }

    def __init__(self, address, secret, queue):
        
        self.address = address
        self.secret = secret
        self.queue = queue

        self.disconnected_event = asyncio.Event()
        self.disconnected_event.set()

        self.client = None
        self.characteristics = {}
        self.descriptions = {}

    def handle_disconnect(self, _):
        print(f"Disconnected from {self.address}")
        self.disconnected_event.set()

    def notification_handler(self, sender, data):
        measurement = self.descriptions[sender][0]
        application = self.descriptions[sender][1]
        try:
            specs = EnvironmentalSensor._characteristic_specs[measurement]
            raw_value = struct.unpack(specs["format"], data)[0]
            value = specs["M"] * raw_value * 10**specs["d"] * 2**specs["b"]
            self.queue.put_nowait((datetime.datetime.now(datetime.timezone.utc), self.address, f"{measurement}_{application}", value))
        except KeyError:
            self.queue.put_nowait((datetime.datetime.now(datetime.timezone.utc), self.address, f"{measurement}_{application}", None))

    async def _subscribe(self):
        if not self.characteristics:
            services = await self.client.get_services()
            ess_service = services.get_service(EnvironmentalSensor._ENV_SENSING_SERVICE_UUID)
            self.characteristics = ess_service.characteristics
        if not self.descriptions:
            for c in self.characteristics:
                d = c.get_descriptor(EnvironmentalSensor._ENV_SENSING_MEASUREMENT_DESCRIPTOR_UUID)
                data = await self.client.read_gatt_descriptor(d.handle)
                app_id = struct.unpack("<H9B", data)[8]
                try:
                    application = EnvironmentalSensor._applications[app_id]
                except KeyError:
                    application = app_id
                self.descriptions[c.handle] = (c.description, application)
        for c in self.characteristics:
            await self.client.start_notify(c, self.notification_handler)

    async def run(self):
        while True:
            await self.disconnected_event.wait()
            device = await BleakScanner.find_device_by_address(self.address, timeout=30)
            if device:
                self.client = BleakClient(device, disconnected_callback=self.handle_disconnect)
                try:
                    await self.client.connect()
                    self.disconnected_event.clear()
                    print(f"Connected to {self.address}")
                except Exception as e:
                    print("Failed to connect: ", end="")
                    print(e)
                    continue
                try:
                    await self._subscribe()
                except Exception as e:
                    print("Failed to subscribe: ", end="")
                    print(e)
            else:
                print(f"Device {self.address} could not be found")

    async def set_fan_speed(self, speed):
        if self.client:
            speed_data = self.secret + speed
            await self.client.write_gatt_char(EnvironmentalSensor._RELAY_CHAR_UUID, speed_data)

    async def set_fan_manual(self):
        if self.client:
            await self.client.write_gatt_char(EnvironmentalSensor._RELAY_CHAR_UUID, 0)
        
