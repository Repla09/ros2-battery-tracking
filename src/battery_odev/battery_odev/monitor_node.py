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
Battery monitor of the underwater vehicle.

Listens to /battery_level and prints every reading. While the level is below
the low battery threshold (20 % by default) the readings are logged as
warnings; the warning stops as soon as the level is back above it.
"""

import rclpy
from rclpy.executors import ExternalShutdownException
from rclpy.node import Node
from std_msgs.msg import Float32


class MonitorNode(Node):
    """Prints the battery level and warns when it is low."""

    def __init__(self, **kwargs):
        super().__init__('monitor_node', **kwargs)
        self.declare_parameter('low_threshold', 20.0)
        self.low_threshold = self.get_parameter('low_threshold').value

        self.level = None
        self.low_battery = False

        self.level_subscription = self.create_subscription(
            Float32, 'battery_level', self.on_battery_level, 10)

    def on_battery_level(self, msg):
        """Print a new reading and update the low battery warning."""
        self.level = msg.data
        if self.level < self.low_threshold:
            self.low_battery = True
            self.get_logger().warning(
                f'Battery level: {self.level:.1f}% - LOW (below {self.low_threshold:g}%)')
        elif self.low_battery:
            self.low_battery = False
            self.get_logger().info(f'Battery level: {self.level:.1f}% - warning cleared')
        else:
            self.get_logger().info(f'Battery level: {self.level:.1f}%')


def main(args=None):
    """Run monitor_node until Ctrl+C."""
    # The outer try also catches a Ctrl+C that arrives while the node is
    # being cleaned up, so stopping the launch file prints no traceback.
    try:
        rclpy.init(args=args)
        node = MonitorNode()
        try:
            rclpy.spin(node)
        finally:
            node.destroy_node()
            rclpy.try_shutdown()
    except (KeyboardInterrupt, ExternalShutdownException):
        pass


if __name__ == '__main__':
    main()
