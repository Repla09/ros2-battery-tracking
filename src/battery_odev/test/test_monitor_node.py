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

"""Tests for monitor_node: printing and the low battery warning."""

from battery_odev.monitor_node import MonitorNode
import pytest
import rclpy
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
