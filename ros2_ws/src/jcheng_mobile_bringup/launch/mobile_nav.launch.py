"""Contract-compliant mobile navigation bringup.

Inputs from the system/hardware layer:
  /scan   sensor_msgs/LaserScan, frame laser_link (LSLIDAR M10, 10 Hz)

Outputs (chassis intent, not motor commands):
  /jcheng/intent/base  std_msgs/String, provisional jcheng.mobile.base_intent.v1
                       JSON envelope (lease-gated, <=20 Hz, domain 42)
  /odom   nav_msgs/Odometry (RTAB-Map ICP laser odometry)
  /map    nav_msgs/OccupancyGrid (slam_toolbox)
  /tf     map -> odom -> base_link, base_link -> laser_link

Nav2's velocity never reaches `/cmd_vel`:

  controller_server -> cmd_vel_nav -> velocity_smoother
                    -> /jcheng/nav2/cmd_vel -> jcheng_base_intent
                    -> /jcheng/intent/base

The Nav2 include is wrapped in a remap group. `/cmd_vel` and
`cmd_vel_smoothed` are both redirected, and the internal controller/smoother
hops keep their Nav2 1.1.20 remapping so the smoother chain is not bypassed.
The intent node is the only publisher of `/jcheng/intent/base`.

The ROS domain is fixed to 42. `ROS_DOMAIN_ID` is set for every child process
and a launch guard aborts on any other `domain:=` value. Domain isolation is
necessary but is not a safety proof: the system layer must still validate the
lease, sequence, freshness, limits and duty of every intent envelope.

This launch starts NO hardware driver and NO motor bridge. The M10 serial
driver, the motor controller and the e-stop belong to the system/hardware
layer; this repository declares hardware_access: none.
"""

import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import (
    DeclareLaunchArgument,
    GroupAction,
    IncludeLaunchDescription,
    OpaqueFunction,
    SetEnvironmentVariable,
)
from launch.conditions import IfCondition
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node, SetRemap
from launch_ros.parameter_descriptions import ParameterValue

FIXED_DOMAIN = 42
NAV2_CMD_VEL = '/jcheng/nav2/cmd_vel'
INTENT_TOPIC = '/jcheng/intent/base'


def _require_fixed_domain(context, *args, **kwargs):
    """Abort unless domain:=42; the capability contract fixes the domain."""
    value = LaunchConfiguration('domain').perform(context).strip()
    try:
        domain = int(value)
    except ValueError:
        raise RuntimeError(
            f'domain must be an integer, got {value!r}; jcheng-mobile is '
            f'fixed to ROS domain {FIXED_DOMAIN}')
    if domain != FIXED_DOMAIN:
        raise RuntimeError(
            f'jcheng-mobile is fixed to ROS domain {FIXED_DOMAIN}; '
            f'got domain:={domain}. The domain is part of the capability '
            'contract, not a tuning knob. Domain isolation alone is not a '
            'safety mechanism.')
    return []


def generate_launch_description():
    pkg_share = get_package_share_directory('jcheng_mobile_bringup')
    nav2_share = get_package_share_directory('nav2_bringup')
    slam_share = get_package_share_directory('slam_toolbox')

    params_file = LaunchConfiguration('params_file')
    slam_params_file = LaunchConfiguration('slam_params_file')
    odom_params_file = LaunchConfiguration('odom_params_file')
    use_sim_time = LaunchConfiguration('use_sim_time')
    autostart = LaunchConfiguration('autostart')
    start_slam = LaunchConfiguration('start_slam')
    start_nav2 = LaunchConfiguration('start_nav2')
    start_intent = LaunchConfiguration('start_intent')
    publish_laser_tf = LaunchConfiguration('publish_laser_tf')
    lease_id = LaunchConfiguration('lease_id')
    holder = LaunchConfiguration('holder')
    intent_rate = LaunchConfiguration('intent_rate')
    duty_limit = LaunchConfiguration('duty_limit')

    base_frame = LaunchConfiguration('base_frame')
    odom_frame = LaunchConfiguration('odom_frame')
    laser_frame = LaunchConfiguration('laser_frame')
    laser_x = LaunchConfiguration('laser_x')
    laser_y = LaunchConfiguration('laser_y')
    laser_z = LaunchConfiguration('laser_z')
    laser_yaw = LaunchConfiguration('laser_yaw')
    laser_pitch = LaunchConfiguration('laser_pitch')
    laser_roll = LaunchConfiguration('laser_roll')

    declarations = [
        DeclareLaunchArgument(
            'domain',
            default_value=str(FIXED_DOMAIN),
            description=f'ROS domain; must be {FIXED_DOMAIN} (asserted)'),
        DeclareLaunchArgument(
            'params_file',
            default_value=os.path.join(pkg_share, 'config', 'nav2_params.yaml'),
            description='Nav2 params file'),
        DeclareLaunchArgument(
            'slam_params_file',
            default_value=os.path.join(pkg_share, 'config', 'slam_toolbox.yaml'),
            description='slam_toolbox params file'),
        DeclareLaunchArgument(
            'odom_params_file',
            default_value=os.path.join(pkg_share, 'config', 'icp_odometry.yaml'),
            description='RTAB-Map ICP odometry params file'),
        DeclareLaunchArgument('use_sim_time', default_value='false'),
        DeclareLaunchArgument('autostart', default_value='true'),
        DeclareLaunchArgument('start_slam', default_value='true'),
        DeclareLaunchArgument('start_nav2', default_value='true'),
        DeclareLaunchArgument(
            'start_intent', default_value='true',
            description='Start the base intent node; it publishes nothing '
                        'without lease_id and holder'),
        DeclareLaunchArgument(
            'lease_id', default_value='',
            description='Control lease id granted by the system layer '
                        '(required for any intent)'),
        DeclareLaunchArgument(
            'holder', default_value='',
            description='Lease holder name (required for any intent)'),
        DeclareLaunchArgument(
            'intent_rate', default_value='20.0',
            description='Intent publish rate in Hz; must be <= 20'),
        DeclareLaunchArgument(
            'duty_limit', default_value='0.60',
            description='Normalized duty cap carried in the intent; the '
                        'system layer still clamps'),
        DeclareLaunchArgument(
            'publish_laser_tf', default_value='true',
            description='Publish base_link -> laser_link; disable if the '
                        'system layer already publishes it'),
        DeclareLaunchArgument('base_frame', default_value='base_link'),
        DeclareLaunchArgument('odom_frame', default_value='odom'),
        DeclareLaunchArgument('laser_frame', default_value='laser_link'),
        # Relative to base_link, not to the floor.
        DeclareLaunchArgument(
            'laser_x', default_value='0.12',
            description='LiDAR x relative to base_link (PROVISIONAL)'),
        DeclareLaunchArgument(
            'laser_y', default_value='0.0',
            description='LiDAR y relative to base_link (PROVISIONAL)'),
        DeclareLaunchArgument(
            'laser_z', default_value='0.03',
            description='LiDAR z relative to base_link (PROVISIONAL)'),
        DeclareLaunchArgument(
            'laser_yaw', default_value='0.0',
            description='LiDAR yaw relative to base_link (+x forward)'),
        DeclareLaunchArgument(
            'laser_pitch', default_value='0.0',
            description='LiDAR pitch relative to base_link'),
        DeclareLaunchArgument(
            'laser_roll', default_value='0.0',
            description='LiDAR roll relative to base_link'),
    ]

    # Humble positional form: x y z yaw pitch roll parent child.
    laser_tf = Node(
        package='tf2_ros',
        executable='static_transform_publisher',
        name='base_link_to_laser_tf',
        output='screen',
        arguments=[
            laser_x, laser_y, laser_z,
            laser_yaw, laser_pitch, laser_roll,
            base_frame, laser_frame,
        ],
        condition=IfCondition(publish_laser_tf),
    )

    # Real laser odometry: consumes /scan, publishes /odom and odom -> base.
    icp_odometry = Node(
        package='rtabmap_odom',
        executable='icp_odometry',
        name='icp_odometry',
        output='screen',
        parameters=[
            odom_params_file,
            {
                'frame_id': base_frame,
                'odom_frame_id': odom_frame,
                'use_sim_time': use_sim_time,
            },
        ],
        remappings=[('scan', '/scan'), ('odom', '/odom')],
    )

    slam = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(slam_share, 'launch', 'online_async_launch.py')),
        launch_arguments={
            'use_sim_time': use_sim_time,
            'slam_params_file': slam_params_file,
        }.items(),
        condition=IfCondition(start_slam),
    )

    # Nav2 1.1.20 navigation_launch.py remaps:
    #   controller_server:  cmd_vel -> cmd_vel_nav
    #   velocity_smoother:  cmd_vel -> cmd_vel_nav, cmd_vel_smoothed -> cmd_vel
    #   behavior_server:    no cmd_vel remap (it publishes /cmd_vel directly)
    # rcl applies the first matching rule, and SetRemap rules are passed before
    # the node's own rules. The scoped rules keep the controller -> smoother
    # chain intact; the final blanket rule catches the smoother output and the
    # behavior server, so Nav2 never publishes /cmd_vel.
    nav2 = GroupAction(
        condition=IfCondition(start_nav2),
        actions=[
            SetRemap('controller_server:cmd_vel', 'cmd_vel_nav'),
            SetRemap('velocity_smoother:cmd_vel', 'cmd_vel_nav'),
            SetRemap('velocity_smoother:cmd_vel_smoothed',
                    '/jcheng/nav2/cmd_vel'),
            SetRemap('/cmd_vel', '/jcheng/nav2/cmd_vel'),
            IncludeLaunchDescription(
                PythonLaunchDescriptionSource(
                    os.path.join(nav2_share, 'launch', 'navigation_launch.py')),
                launch_arguments={
                    'use_sim_time': use_sim_time,
                    'params_file': params_file,
                    'autostart': autostart,
                }.items(),
            ),
        ],
    )

    # Thin intent source: validates Nav2 velocity and publishes the envelope.
    # No lease_id/holder -> no publish; the defaults are empty on purpose.
    intent_node = Node(
        package='jcheng_mobile_bringup',
        executable='intent_node',
        name='jcheng_base_intent',
        output='screen',
        parameters=[{
            # Lease strings stay strings; launch_ros would otherwise apply
            # YAML rules and turn a numeric lease id into an int.
            'lease_id': ParameterValue(lease_id, value_type=str),
            'holder': ParameterValue(holder, value_type=str),
            'intent_topic': INTENT_TOPIC,
            'input_topic': NAV2_CMD_VEL,
            'rate': intent_rate,
            'duty_limit': duty_limit,
        }],
        condition=IfCondition(start_intent),
    )

    return LaunchDescription(
        declarations + [
            # Fixed capability domain for every child process. The guard runs
            # before any node is launched.
            SetEnvironmentVariable('ROS_DOMAIN_ID', str(FIXED_DOMAIN)),
            OpaqueFunction(function=_require_fixed_domain),
            laser_tf,
            icp_odometry,
            slam,
            nav2,
            intent_node,
        ])
