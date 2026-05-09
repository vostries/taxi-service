import os
import sys
import time
import uuid
import unittest
from concurrent.futures import ThreadPoolExecutor, as_completed

import requests
from requests import RequestException


USER_BASE_URL = os.getenv("USER_BASE_URL", "http://localhost:8081")
TRIP_BASE_URL = os.getenv("TRIP_BASE_URL", "http://localhost:8082")
NOTIFICATION_BASE_URL = os.getenv("NOTIFICATION_BASE_URL", "http://localhost:8083")
RABBIT_API_URL = os.getenv("RABBIT_API_URL", "http://localhost:15672/api")
RABBIT_USER = os.getenv("RABBIT_USER", "guest")
RABBIT_PASSWORD = os.getenv("RABBIT_PASSWORD", "guest")

LOG_FILE = "log.txt"


class DetailedLogger:
    def __init__(self, log_file):
        self.log_file = log_file
        
    def log(self, message):
        with open(self.log_file, 'a', encoding='utf-8') as f:
            f.write(message + '\n')
    
    def log_step(self, step_num, title):
        self.log(f"\n{'='*80}")
        self.log(f"STEP {step_num:02d}: {title}")
        self.log(f"{'='*80}")
    
    def log_request(self, method, url, headers=None, params=None, json_data=None):
        self.log(f"  -> REQUEST: {method} {url}")
        if headers:
            safe_headers = dict(headers)
            if "Authorization" in safe_headers:
                safe_headers["Authorization"] = "Bearer ***"
            self.log(f"     headers: {self._pretty(safe_headers)}")
        if params:
            self.log(f"     params:  {self._pretty(params)}")
        if json_data:
            self.log(f"     json:    {self._pretty(json_data)}")
    
    def log_response(self, status_code, body):
        self.log(f"  <- RESPONSE STATUS: {status_code}")
        if body:
            try:
                self.log(f"     json: {self._pretty(body)}")
            except:
                self.log(f"     body: {body}")
    
    def _pretty(self, value):
        try:
            return requests.models.complexjson.dumps(value, ensure_ascii=False, indent=2)
        except Exception:
            return str(value)


detailed_logger = DetailedLogger(LOG_FILE)


class TaxiServiceE2ETest(unittest.TestCase):
    passenger_id = None
    driver_id = None
    trip_id = None
    token = None
    step_counter = 0

    @classmethod
    def setUpClass(cls):
        if os.path.exists(LOG_FILE):
            os.remove(LOG_FILE)

    def log_step(self, title):
        TaxiServiceE2ETest.step_counter += 1
        detailed_logger.log_step(self.step_counter, title)

    def pretty(self, value):
        return detailed_logger._pretty(value)

    def require_trip(self):
        if self.trip_id is None:
            self.skipTest("Trip was not created in test_04_create_trip")

    def request_json(self, method, url, expected_status, **kwargs):
        request_json_payload = kwargs.get("json")
        request_params = kwargs.get("params")
        request_headers = kwargs.get("headers") or {}
        
        detailed_logger.log_request(method, url, request_headers, request_params, request_json_payload)

        response = requests.request(method, url, timeout=15, **kwargs)
        
        response_json = None
        if response.text.strip():
            try:
                response_json = response.json()
            except Exception:
                pass
        
        detailed_logger.log_response(response.status_code, response_json)

        self.assertEqual(
            expected_status,
            response.status_code,
            msg=f"{method} {url} -> {response.status_code}, body: {response.text}",
        )
        
        return response_json

    def create_trip_with_retry(self, headers, payload, attempts=3, delay_seconds=1.5):
        last_error = None
        for i in range(attempts):
            try:
                return self.request_json(
                    "POST",
                    f"{TRIP_BASE_URL}/trips",
                    201,
                    headers=headers,
                    json=payload,
                )
            except AssertionError as exc:
                last_error = exc
                if i < attempts - 1:
                    time.sleep(delay_seconds)
                    continue
                raise
            except RequestException as exc:
                last_error = exc
                if i < attempts - 1:
                    time.sleep(delay_seconds)
                    continue
                raise
        raise AssertionError(f"Failed to create trip after retries: {last_error}")

    def get_rabbit_trip_events_publish_count(self):
        try:
            response = requests.get(
                f"{RABBIT_API_URL}/queues/%2F/trip.events.queue",
                auth=(RABBIT_USER, RABBIT_PASSWORD),
                timeout=5,
            )
            if response.status_code != 200:
                return None
            data = response.json()
            stats = data.get("message_stats") or {}
            return int(stats.get("publish", 0))
        except Exception:
            return None

    def test_01_register_passenger(self):
        self.log_step("Register passenger")
        suffix = uuid.uuid4().hex[:8]
        payload = {
            "email": f"passenger_{suffix}@test.com",
            "password": "123456",
            "name": f"[TEST test_01_register_passenger] Passenger Demo",
            "phone": f"+7900{int(time.time()) % 10_000_000:07d}",
            "userType": "PASSENGER",
        }
        data = self.request_json(
            "POST",
            f"{USER_BASE_URL}/auth/register",
            201,
            json=payload,
        )
        self.assertIn("token", data)
        self.assertIn("userId", data)
        TaxiServiceE2ETest.token = data["token"]
        TaxiServiceE2ETest.passenger_id = data["userId"]

    def test_02_register_driver(self):
        self.log_step("Register driver and set AVAILABLE")
        suffix = uuid.uuid4().hex[:8]
        payload = {
            "email": f"driver_{suffix}@test.com",
            "password": "123456",
            "name": f"[TEST test_02_register_driver] Driver Demo",
            "phone": f"+7911{int(time.time()) % 10_000_000:07d}",
            "userType": "DRIVER",
            "licenseNumber": f"LIC-{suffix.upper()}",
        }
        data = self.request_json(
            "POST",
            f"{USER_BASE_URL}/auth/register",
            201,
            json=payload,
        )
        self.assertIn("userId", data)
        TaxiServiceE2ETest.driver_id = data["userId"]

        self.assertIsNotNone(self.token, "Passenger token must be created first")
        headers = {"Authorization": f"Bearer {self.token}"}
        updated = self.request_json(
            "PATCH",
            f"{USER_BASE_URL}/drivers/{self.driver_id}/status",
            200,
            headers=headers,
            json={"status": "AVAILABLE"},
        )
        self.assertEqual("AVAILABLE", updated["status"])

    def test_03_check_user_profiles(self):
        self.log_step("Get passenger and driver profiles")
        self.assertIsNotNone(self.passenger_id, "Passenger must be created first")
        self.assertIsNotNone(self.driver_id, "Driver must be created first")
        self.assertIsNotNone(self.token, "Token must be received first")
        headers = {"Authorization": f"Bearer {self.token}"}

        passenger = self.request_json(
            "GET",
            f"{USER_BASE_URL}/passengers/{self.passenger_id}",
            200,
            headers=headers,
        )
        self.assertEqual(self.passenger_id, passenger["id"])

        driver = self.request_json(
            "GET",
            f"{USER_BASE_URL}/drivers/{self.driver_id}",
            200,
            headers=headers,
        )
        self.assertEqual(self.driver_id, driver["id"])

    def test_04_create_trip(self):
        self.log_step("Create trip")
        self.assertIsNotNone(self.passenger_id, "Passenger must be created first")
        self.assertIsNotNone(self.token, "Token must be received first")

        headers = {"Authorization": f"Bearer {self.token}"}
        payload = {
            "passengerId": self.passenger_id,
            "origin": "Moscow, Lenina 1",
            "destination": "Moscow, Pushkina 10",
        }
        trip = self.create_trip_with_retry(headers, payload)
        self.assertIn("id", trip)
        self.assertIsNotNone(trip.get("driverId"))
        self.assertEqual("DRIVER_ASSIGNED", trip["status"])
        self.assertGreater(trip.get("price", 0), 0)
        TaxiServiceE2ETest.trip_id = trip["id"]

    def test_05_get_trip_and_passenger_history(self):
        self.log_step("Get trip by id and passenger history")
        self.require_trip()
        headers = {"Authorization": f"Bearer {self.token}"}

        trip = self.request_json(
            "GET",
            f"{TRIP_BASE_URL}/trips/{self.trip_id}",
            200,
            headers=headers,
        )
        self.assertEqual(self.trip_id, trip["id"])

        trips = self.request_json(
            "GET",
            f"{TRIP_BASE_URL}/trips",
            200,
            headers=headers,
            params={"passenger_id": self.passenger_id},
        )
        self.assertTrue(any(t["id"] == self.trip_id for t in trips))

    def test_06_update_trip_statuses(self):
        self.log_step("Update trip statuses to IN_PROGRESS and COMPLETED")
        self.require_trip()
        headers = {"Authorization": f"Bearer {self.token}"}

        in_progress = self.request_json(
            "PATCH",
            f"{TRIP_BASE_URL}/trips/{self.trip_id}/status",
            200,
            headers=headers,
            json={"status": "IN_PROGRESS"},
        )
        self.assertEqual("IN_PROGRESS", in_progress["status"])

        completed = self.request_json(
            "PATCH",
            f"{TRIP_BASE_URL}/trips/{self.trip_id}/status",
            200,
            headers=headers,
            json={"status": "COMPLETED"},
        )
        self.assertEqual("COMPLETED", completed["status"])

    def test_07_rate_trip(self):
        self.log_step("Rate completed trip")
        self.require_trip()
        headers = {"Authorization": f"Bearer {self.token}"}

        rated = self.request_json(
            "POST",
            f"{TRIP_BASE_URL}/trips/{self.trip_id}/rate",
            200,
            headers=headers,
            json={"rating": 5},
        )
        self.assertEqual(5, rated["rating"])

    def test_08_get_stats(self):
        self.log_step("Get trip statistics")
        headers = {"Authorization": f"Bearer {self.token}"}
        stats = self.request_json(
            "GET",
            f"{TRIP_BASE_URL}/trips/stats",
            200,
            headers=headers,
        )
        self.assertGreaterEqual(stats.get("tripsToday", 0), 1)
        self.assertGreaterEqual(stats.get("averagePrice", 0), 0)

    def test_09_notifications_created_by_event(self):
        self.log_step("Check notifications created from trip event")
        self.require_trip()

        notifications = []
        for _ in range(10):
            notifications = self.request_json(
                "GET",
                f"{NOTIFICATION_BASE_URL}/notifications",
                200,
                params={"trip_id": self.trip_id},
            )
            if notifications:
                break
            time.sleep(1)

        self.assertGreaterEqual(
            len(notifications),
            1,
            msg="No notifications found for trip, check RabbitMQ/worker service",
        )
        statuses = {n["status"] for n in notifications}
        self.assertTrue(
            statuses & {"PENDING", "IN_PROGRESS", "SENT", "FAILED"},
            msg=f"Unexpected notification statuses: {statuses}",
        )

    def test_10_manual_notification_endpoint(self):
        self.log_step("Create notification via API")
        self.require_trip()
        payload = {
            "tripId": self.trip_id,
            "recipientType": "PASSENGER",
            "recipientId": self.passenger_id,
            "message": f"[TEST test_10_manual_notification_endpoint] Manual API notification test",
        }
        created = self.request_json(
            "POST",
            f"{NOTIFICATION_BASE_URL}/notifications",
            201,
            json=payload,
        )
        self.assertEqual(self.trip_id, created["tripId"])

    def test_11_driver_not_assigned_to_two_trips_concurrently(self):
        self.log_step("Concurrent trips: verify unique driver assignment")
        users = []
        for _ in range(4):
            suffix = uuid.uuid4().hex[:8]
            reg = self.request_json(
                "POST",
                f"{USER_BASE_URL}/auth/register",
                201,
                json={
                    "email": f"p_conc_{suffix}@test.com",
                    "password": "123456",
                    "name": f"[TEST test_11_driver_not_assigned_to_two_trips_concurrently] Passenger Concurrency",
                    "phone": f"+7922{int(time.time() * 1000) % 10_000_000:07d}",
                    "userType": "PASSENGER",
                },
            )
            users.append((reg["userId"], reg["token"]))

        for _ in range(4):
            suffix = uuid.uuid4().hex[:8]
            reg = self.request_json(
                "POST",
                f"{USER_BASE_URL}/auth/register",
                201,
                json={
                    "email": f"d_conc_{suffix}@test.com",
                    "password": "123456",
                    "name": f"[TEST test_11_driver_not_assigned_to_two_trips_concurrently] Driver Concurrency",
                    "phone": f"+7933{int(time.time() * 1000) % 10_000_000:07d}",
                    "userType": "DRIVER",
                    "licenseNumber": f"LIC-C-{suffix.upper()}",
                },
            )
            driver_id = reg["userId"]
            self.request_json(
                "PATCH",
                f"{USER_BASE_URL}/drivers/{driver_id}/status",
                200,
                headers={"Authorization": f"Bearer {users[0][1]}"},
                json={"status": "AVAILABLE"},
            )

        def create_trip_for_user(user):
            passenger_id, token = user
            headers = {"Authorization": f"Bearer {token}"}
            payload = {
                "passengerId": passenger_id,
                "origin": "Moscow, Parallel A",
                "destination": "Moscow, Parallel B",
            }
            response = requests.post(
                f"{TRIP_BASE_URL}/trips", headers=headers, json=payload, timeout=15
            )
            return response.status_code, response.text

        successful_driver_ids = []
        with ThreadPoolExecutor(max_workers=4) as pool:
            futures = [pool.submit(create_trip_for_user, user) for user in users]
            for future in as_completed(futures):
                status_code, body = future.result()
                if status_code == 201:
                    data = requests.models.complexjson.loads(body)
                    successful_driver_ids.append(data.get("driverId"))

        self.assertGreaterEqual(
            len(successful_driver_ids),
            2,
            msg="Expected at least 2 successful concurrent assignments",
        )
        self.assertEqual(
            len(successful_driver_ids),
            len(set(successful_driver_ids)),
            msg=f"Same driver assigned concurrently: {successful_driver_ids}",
        )

    def test_12_trip_event_published_to_rabbit_queue(self):
        self.log_step("RabbitMQ queue publish counter check")
        publish_before = self.get_rabbit_trip_events_publish_count()
        if publish_before is None:
            self.skipTest("RabbitMQ management API is unavailable on localhost:15672")

        suffix = uuid.uuid4().hex[:8]
        passenger = self.request_json(
            "POST",
            f"{USER_BASE_URL}/auth/register",
            201,
            json={
                "email": f"p_queue_{suffix}@test.com",
                "password": "123456",
                "name": f"[TEST test_12_trip_event_published_to_rabbit_queue] Passenger Queue",
                "phone": f"+7944{int(time.time() * 1000) % 10_000_000:07d}",
                "userType": "PASSENGER",
            },
        )
        driver = self.request_json(
            "POST",
            f"{USER_BASE_URL}/auth/register",
            201,
            json={
                "email": f"d_queue_{suffix}@test.com",
                "password": "123456",
                "name": f"[TEST test_12_trip_event_published_to_rabbit_queue] Driver Queue",
                "phone": f"+7955{int(time.time() * 1000) % 10_000_000:07d}",
                "userType": "DRIVER",
                "licenseNumber": f"LIC-Q-{suffix.upper()}",
            },
        )

        token = passenger["token"]
        self.request_json(
            "PATCH",
            f"{USER_BASE_URL}/drivers/{driver['userId']}/status",
            200,
            headers={"Authorization": f"Bearer {token}"},
            json={"status": "AVAILABLE"},
        )

        self.request_json(
            "POST",
            f"{TRIP_BASE_URL}/trips",
            201,
            headers={"Authorization": f"Bearer {token}"},
            json={
                "passengerId": passenger["userId"],
                "origin": "Moscow, Lenina 1",
                "destination": "Moscow, kreml",
            },
        )

        publish_after = publish_before
        for _ in range(5):
            time.sleep(1)
            current = self.get_rabbit_trip_events_publish_count()
            if current is not None:
                publish_after = current
            if publish_after > publish_before:
                break

        self.assertGreater(
            publish_after,
            publish_before,
            msg=f"Queue publish counter did not increase: before={publish_before}, after={publish_after}",
        )


if __name__ == "__main__":
    if os.path.exists(LOG_FILE):
        os.remove(LOG_FILE)
    
    suite = unittest.TestLoader().loadTestsFromTestCase(TaxiServiceE2ETest)
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    print(f"\nDetailed logs saved to: {LOG_FILE}")
    
    sys.exit(0 if result.wasSuccessful() else 1)