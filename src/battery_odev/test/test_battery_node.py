# Copyright 2026 Repla09
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Tests for battery_node: draining, the /battery_level topic and /recharge."""

import time

from battery_odev.battery_node import BatteryNode
import pytest
import rclpy
from rclpy.executors import SingleThreadedExecutor
from rclpy.parameter import Parameter
from std_msgs.msg import Float32
from std_srvs.srv import Trigger


@pytest.fixture
def ros():
    rclpy.init()
    yield
    rclpy.shutdown()


def make_battery(**params):
    overrides = [Parameter(name, value=value) for name, value in params.items()]
    return BatteryNode(parameter_overrides=overrides)


def test_starts_at_100_percent(ros):
    battery = make_battery()
    assert battery.level == 100.0
    battery.destroy_node()


def test_drains_one_percent_per_step(ros):
    battery = make_battery()
    for _ in range(3):
        battery.on_drain_timer()
    assert battery.level == 97.0
    battery.destroy_node()


def test_never_goes_below_zero(ros):
    battery = make_battery(initial_level=1.5)
    for _ in range(5):
        battery.on_drain_timer()
    assert battery.level == 0.0
    battery.destroy_node()


def test_publishes_level_on_battery_level_topic(ros):
    battery = make_battery(update_period=0.05)
    listener = rclpy.create_node('test_listener')
    received = []
    listener.create_subscription(
        Float32, 'battery_level', lambda msg: received.append(msg.data), 10)
    executor = SingleThreadedExecutor()
    executor.add_node(battery)
    executor.add_node(listener)

    deadline = time.monotonic() + 5.0
    while len(received) < 5 and time.monotonic() < deadline:
        executor.spin_once(timeout_sec=0.1)

    assert len(received) >= 5
    assert all(a - b == 1.0 for a, b in zip(received, received[1:]))
    executor.shutdown()
    listener.destroy_node()
    battery.destroy_node()


def test_recharge_service_fills_battery(ros):
    battery = make_battery(initial_level=42.0)
    caller = rclpy.create_node('test_caller')
    client = caller.create_client(Trigger, 'recharge')
    executor = SingleThreadedExecutor()
    executor.add_node(battery)
    executor.add_node(caller)

    assert client.wait_for_service(timeout_sec=5.0)
    future = client.call_async(Trigger.Request())
    executor.spin_until_future_complete(future, timeout_sec=5.0)

    response = future.result()
    assert response is not None
    assert response.success
    assert response.message == 'Battery recharged'
    assert battery.level == 100.0
    executor.shutdown()
    caller.destroy_node()
    battery.destroy_node()
