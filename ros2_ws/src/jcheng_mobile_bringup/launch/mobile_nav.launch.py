"""Contract-compliant mobile navigation bringup.

Inputs from the system/hardware layer:
  /scan   sensor_msgs/LaserScan, frame laser_link (LSLIDAR M10, 10 Hz)

Outputs (chassis intent, not motor commands):
  /odom   nav_msgs/Odometry (RTAB-Map ICP laser odometry)
  /map    nav_msgs/OccupancyGrid (slam_toolbox)
  /tf     map -> odom -> base_link, base_link -> laser_link
  /cmd_vel  geometry_msgs/Twist (Nav2 intent; consumed by the system layer)

This launch starts NO hardware driver and NO motor bridge. The M10 serial
driver, the motor controller and the e-stop belong to the system/hardware
layer; this repository declares hardware_access: none.
"""

import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
from launch.conditions import IfCondition
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


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
    publish_laser_tf = LaunchConfiguration('publish_laser_tf')

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

    nav2 = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(nav2_share, 'launch', 'navigation_launch.py')),
        launch_arguments={
            'use_sim_time': use_sim_time,
            'params_file': params_file,
            'autostart': autostart,
        }.items(),
        condition=IfCondition(start_nav2),
    )

    return LaunchDescription(
        declarations + [
            laser_tf,
            icp_odometry,
            slam,
            nav2,
        ])
