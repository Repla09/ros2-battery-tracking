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

"""
Battery of the underwater vehicle.

Publishes the battery level in percent (std_msgs/Float32) on /battery_level.
The level starts at 100, drops by 1 every second and never goes below 0.
"""

import rclpy
from rclpy.executors import ExternalShutdownException
from rclpy.node import Node
from std_msgs.msg import Float32

FULL_LEVEL = 100.0
EMPTY_LEVEL = 0.0


class BatteryNode(Node):
    """Simulated battery that drains at a fixed rate."""

    def __init__(self, **kwargs):
        super().__init__('battery_node', **kwargs)
        self.declare_parameter('initial_level', FULL_LEVEL)
        self.declare_parameter('drain_step', 1.0)
        self.declare_parameter('update_period', 1.0)

        initial_level = self.get_parameter('initial_level').value
        self.level = min(max(initial_level, EMPTY_LEVEL), FULL_LEVEL)
        self.drain_step = self.get_parameter('drain_step').value
        update_period = self.get_parameter('update_period').value

        self.level_publisher = self.create_publisher(Float32, 'battery_level', 10)
        self.drain_timer = self.create_timer(update_period, self.on_drain_timer)

        self.get_logger().info(
            f'Battery at {self.level:.1f}%, draining {self.drain_step:g}% '
            f'every {update_period:g} s')
        self.publish_level()

    def publish_level(self):
        """Publish the current battery level on /battery_level."""
        msg = Float32()
        msg.data = self.level
        self.level_publisher.publish(msg)

    def on_drain_timer(self):
        """Drain the battery by one step and publish the new level."""
        if self.level > EMPTY_LEVEL:
            self.level = max(self.level - self.drain_step, EMPTY_LEVEL)
            if self.level == EMPTY_LEVEL:
                self.get_logger().warning('Battery is empty')
        self.publish_level()


def main(args=None):
    """Run battery_node until Ctrl+C."""
    # The outer try also catches a Ctrl+C that arrives while the node is
    # being cleaned up, so stopping the launch file prints no traceback.
    try:
        rclpy.init(args=args)
        node = BatteryNode()
        try:
            rclpy.spin(node)
        finally:
            node.destroy_node()
            rclpy.try_shutdown()
    except (KeyboardInterrupt, ExternalShutdownException):
        pass


if __name__ == '__main__':
    main()
