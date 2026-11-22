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

When the level drops below the recharge threshold (5 % by default) the node
calls the /recharge service itself and prints the reply.
"""

import rclpy
from rclpy.executors import ExternalShutdownException
from rclpy.node import Node
from std_msgs.msg import Float32
from std_srvs.srv import Trigger


class MonitorNode(Node):
    """Prints the battery level, warns when it is low and recharges it."""

    def __init__(self, **kwargs):
        super().__init__('monitor_node', **kwargs)
        self.declare_parameter('low_threshold', 20.0)
        self.declare_parameter('recharge_threshold', 5.0)
        self.low_threshold = self.get_parameter('low_threshold').value
        self.recharge_threshold = self.get_parameter('recharge_threshold').value

        self.level = None
        self.low_battery = False
        self.pending_recharge = None
        self.last_recharge_message = None

        self.level_subscription = self.create_subscription(
            Float32, 'battery_level', self.on_battery_level, 10)
        self.recharge_client = self.create_client(Trigger, 'recharge')

    def on_battery_level(self, msg):
        """Print a new reading, update the warning and recharge if needed."""
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

        if self.level < self.recharge_threshold:
            self.request_recharge()

    def request_recharge(self):
        """Call /recharge asynchronously, unless a call is already pending."""
        if self.pending_recharge is not None:
            return
        if not self.recharge_client.service_is_ready():
            self.get_logger().warning(
                '/recharge service is not available, will try again',
                throttle_duration_sec=5.0)
            return
        self.get_logger().info(
            f'Battery below {self.recharge_threshold:g}%, calling /recharge')
        self.pending_recharge = self.recharge_client.call_async(Trigger.Request())
        self.pending_recharge.add_done_callback(self.on_recharge_response)

    def on_recharge_response(self, future):
        """Print the reply of the /recharge service."""
        self.pending_recharge = None
        error = future.exception()
        if error is not None:
            self.get_logger().error(f'/recharge call failed: {error}')
            return
        response = future.result()
        if response is None:
            self.get_logger().error('/recharge call was cancelled')
            return
        self.last_recharge_message = response.message
        if response.success:
            self.get_logger().info(f'/recharge replied: "{response.message}"')
        else:
            self.get_logger().error(f'/recharge refused: "{response.message}"')


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
