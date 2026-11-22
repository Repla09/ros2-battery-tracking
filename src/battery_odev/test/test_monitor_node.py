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

"""Tests for monitor_node: printing, the low battery warning and auto recharge."""

import time

from battery_odev.battery_node import BatteryNode
from battery_odev.monitor_node import MonitorNode
import pytest
import rclpy
from rclpy.executors import SingleThreadedExecutor
from rclpy.parameter import Parameter
from std_msgs.msg import Float32


@pytest.fixture
def monitor():
    rclpy.init()
    node = MonitorNode()
    yield node
    node.destroy_node()
    rclpy.shutdown()


@pytest.fixture
def logs(monitor, monkeypatch):
    """Record (level, message) for everything the monitor logs."""
    records = []

    def recorder(level):
        def log(message, **kwargs):
            records.append((level, message))
            return True
        return log

    logger = monitor.get_logger()
    for level in ('info', 'warning', 'error'):
        monkeypatch.setattr(logger, level, recorder(level))
    return records


def feed(monitor, *values):
    for value in values:
        msg = Float32()
        msg.data = value
        monitor.on_battery_level(msg)


def test_prints_every_reading(monitor, logs):
    feed(monitor, 57.0, 56.0)
    assert logs == [('info', 'Battery level: 57.0%'), ('info', 'Battery level: 56.0%')]
    assert not monitor.low_battery


def test_warns_only_below_20_percent(monitor, logs):
    feed(monitor, 21.0, 20.0, 19.0, 18.0)
    assert [level for level, _ in logs] == ['info', 'info', 'warning', 'warning']
    assert 'LOW' in logs[2][1]
    assert monitor.low_battery


def test_warning_stops_when_level_rises(monitor, logs):
    feed(monitor, 12.0, 100.0, 99.0)
    assert [level for level, _ in logs] == ['warning', 'info', 'info']
    assert 'warning cleared' in logs[1][1]
    assert not monitor.low_battery


def test_no_recharge_at_5_percent_or_more(monitor, logs):
    feed(monitor, 6.0, 5.0)
    assert monitor.pending_recharge is None
    assert not any('/recharge' in message for _, message in logs)


def test_waits_when_recharge_service_is_missing(monitor, logs):
    feed(monitor, 4.0)
    assert monitor.pending_recharge is None
    assert logs[-1] == ('warning', '/recharge service is not available, will try again')


def test_sends_only_one_request_at_a_time(monitor, logs):
    battery = BatteryNode()
    assert monitor.recharge_client.wait_for_service(timeout_sec=5.0)
    feed(monitor, 4.0)
    first_request = monitor.pending_recharge
    feed(monitor, 3.0, 2.0)
    assert first_request is not None
    assert monitor.pending_recharge is first_request
    assert sum('calling /recharge' in message for _, message in logs) == 1
    battery.destroy_node()


def test_recharges_itself_below_5_percent(monitor, logs):
    battery = BatteryNode(parameter_overrides=[
        Parameter('initial_level', value=8.0),
        Parameter('update_period', value=0.05),
    ])
    executor = SingleThreadedExecutor()
    executor.add_node(battery)
    executor.add_node(monitor)

    deadline = time.monotonic() + 10.0
    while monitor.last_recharge_message is None and time.monotonic() < deadline:
        executor.spin_once(timeout_sec=0.1)

    assert monitor.last_recharge_message == 'Battery recharged'
    assert ('info', '/recharge replied: "Battery recharged"') in logs
    assert battery.level > 90.0
    executor.shutdown()
    battery.destroy_node()
