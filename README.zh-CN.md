# jcheng-mobile

> **状态：实验性 / 静态接入部分验证（2026-11-25）；运动未验证。** 本仓库是 JCHENG 生态的 L3 移动底盘能力。
> 它消费 2D 激光扫描，估计真实激光里程计、建图并发布底盘意图。它**不**打开设备、
> 不驱动电机、不伪造里程计。
> 本文为英文主文档的中文对照；如有歧义，以 [README.md](README.md) 为准。

## 范围与边界

| 项 | 本仓库 |
|---|---|
| 层 | L3 能力（`capability.yaml`：`hardware_access: none`） |
| 输入 | `/scan`（LSLIDAR M10，10 Hz，frame `laser_link`），来自系统/硬件层 |
| 输出 | `/odom`（RTAB-Map ICP 激光里程计）、`/map`（slam_toolbox）、`/tf`、`/cmd_vel` 底盘意图 |
| 运动授权 | `motion_source`，scope `base`，需要租约，500 ms deadman |
| 不在范围 | M10 串口/设备驱动、电机桥、急停、轮式里程计（底盘没有编码器） |
| 禁止 | 电机驱动话题、伪造里程计、`/dev/*`、串口/CAN/GPIO 访问 |

系统/硬件层拥有 M10 驱动与电机桥。本仓库消费 `/scan` 并产生意图；它绝不发布
`/ros_robot_controller/*`，也不打开串口。`tests/test_no_hardware.py` 的静态扫描
强制执行这条边界。

## 目录

```text
jcheng-mobile/
├── capability.yaml                 # 准入清单
├── docs/INTEGRATION.md             # 发现、租约、话题、失败语义
├── tests/test_contract.py          # 清单契约检查
├── tests/test_no_hardware.py       # 静态无硬件扫描
├── VERSION
├── CHANGELOG.md
├── LICENSE
└── ros2_ws/src/jcheng_mobile_bringup/
    ├── launch/mobile_nav.launch.py # ICP odom + SLAM + Nav2；无硬件驱动
    ├── config/nav2_params.yaml     # MPPI Omni、代价地图、速度平滑
    ├── config/slam_toolbox.yaml    # online-async 建图
    ├── config/icp_odometry.yaml    # 真实激光里程计，/scan -> /odom
    └── urdf/jcheng_mobile.urdf.xacro
```

## 依赖

- ROS 2 Humble。
- 目标环境安装 `ros-humble-nav2-bringup`、`ros-humble-nav2-mppi-controller`、
  `ros-humble-slam-toolbox`、`ros-humble-rtabmap-odom`。
- 由系统/硬件层拥有的 `/scan` 发布者。M10 驱动不属于本仓库。
- 真实导航前必须实测 LiDAR 安装位姿与底盘轮廓。URDF/launch/Nav2 配置中的
  数值是**暂定值**。

## 构建与运行

```bash
colcon build --base-paths ros2_ws/src --packages-select jcheng_mobile_bringup
source install/setup.bash

ros2 launch jcheng_mobile_bringup mobile_nav.launch.py \
  laser_x:=0.12 laser_y:=0.0 laser_z:=0.03 laser_yaw:=0.0
```

如果系统层已经发布 `base_link -> laser_link`，传入 `publish_laser_tf:=false`
以避免重复 TF。分阶段检查可用 `start_slam:=false` 或 `start_nav2:=false`。

launch 不启动电机桥。`/cmd_vel` 是底盘意图；系统层必须先应用租约、deadman、
急停与底盘限幅，电机才会动作。

## 测试

```bash
python3 -m pytest -q tests
```

- `test_contract.py` 校验能力清单字段、契约哈希形状、scope/lease/deadman、
  域 42 与话题表面。
- `test_no_hardware.py` 拒绝设备路径、串口/CAN/GPIO 访问、电机驱动话题、
  厂商麦克纳姆节点与台架开环里程计。

## 验证状态

- 离线：YAML 解析、`py_compile`、`colcon build`、`xacro` 展开、launch 描述生成，
  以及 M10 驱动参数交叉检查（在前身台架包中），于 2026-11-24 通过。
- **静态接入部分验证（2026-11-25，Pi 5 Humble，无运动）：** M10 `/scan` 10 Hz、
  RTAB-Map ICP `/odom` 10 Hz、slam_toolbox `/map` 1 Hz、`map -> odom`，Nav2
  `controller_server` / `planner_server` / `bt_navigator` 均为 active；
  `/cmd_vel` 有发布者但没有底盘订阅者，未启动电机桥。
- **运动未验证。** 没有底盘/机械臂运动，也没有精度结论；LiDAR 安装位与底盘
  轮廓仍是占位值，驱动/Nav2 包只存在于有状态的机器人容器中。
- 证据：[evidence/20261125_static_bringup/README.md](evidence/20261125_static_bringup/README.md)。

完整报告：[ACCEPTANCE.md](ACCEPTANCE.md)。

## 相关

- `JCHENG-Robotics/jcheng-interfaces` — 契约 Schema 与哈希。
- `JCHENG-Robotics/jcheng-system` — 安全、控制权、运动、硬件桥。
- `JCHENG-Robotics/jcheng-ops` — 运维与看门狗。
- `docs/INTEGRATION.md` — 发现、租约与失败语义。

## 许可

本仓库在初始化时已包含一份 MIT `LICENSE`。这早于组织的许可证审查策略：其余新仓库
（`jcheng-interfaces`、`jcheng-system`、`jcheng-perception`、`jcheng-ops`、
`.github`）都没有 `LICENSE`，审查仍在进行。该文件**保留待审查**；见
[LICENSE-REVIEW.md](LICENSE-REVIEW.md)。该差异记录在
[`JCHENG-Robotics/.github/ACCEPTANCE.md`](https://github.com/JCHENG-Robotics/.github/blob/main/ACCEPTANCE.md)。
不要把这份文件当作组织级许可决定。
