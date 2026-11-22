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

"""Start battery_node and monitor_node together."""

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue


def generate_launch_description():
    """Describe the two battery nodes."""
    initial_level = LaunchConfiguration('initial_level')

    return LaunchDescription([
        DeclareLaunchArgument(
            'initial_level',
            default_value='100.0',
            description='Battery level in percent when the battery node starts'),
        Node(
            package='battery_odev',
            executable='battery_node',
            name='battery_node',
            output='screen',
            parameters=[{'initial_level': ParameterValue(initial_level, value_type=float)}],
        ),
        Node(
            package='battery_odev',
            executable='monitor_node',
            name='monitor_node',
            output='screen',
        ),
    ])
