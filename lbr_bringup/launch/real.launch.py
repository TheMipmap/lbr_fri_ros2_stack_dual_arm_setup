from typing import List

from launch import LaunchContext, LaunchDescription, LaunchDescriptionEntity
from launch.actions import DeclareLaunchArgument, OpaqueFunction, RegisterEventHandler
from launch.conditions import IfCondition, UnlessCondition
from launch.event_handlers import OnProcessExit, OnProcessStart
from launch.substitutions import (
    AndSubstitution,
    LaunchConfiguration,
    NotSubstitution,
    PathJoinSubstitution,
)

from lbr_bringup import LBRMoveGroupMixin
from lbr_description import LBRDescriptionMixin, RVizMixin
from lbr_ros2_control import LBRSystemInterfaceMixin


def launch_setup(context: LaunchContext) -> List[LaunchDescriptionEntity]:
    ld = LaunchDescription()

    robot_description = LBRDescriptionMixin.param_robot_description(sim=False)
    ros2_control_node = LBRSystemInterfaceMixin.node_ros2_control(
        robot_description=robot_description
    )
    ld.add_action(ros2_control_node)

    # joint state broad caster and controller on ros2 control node start
    joint_state_broadcaster = LBRSystemInterfaceMixin.node_joint_state_broadcaster()
    controller = LBRSystemInterfaceMixin.node_controller()

    controller_event_handler = RegisterEventHandler(
        OnProcessStart(
            target_action=ros2_control_node,
            on_start=[joint_state_broadcaster, controller],
        )
    )
    ld.add_action(controller_event_handler)

    # robot state publisher on joint state broadcaster spawn exit
    robot_state_publisher = LBRSystemInterfaceMixin.node_robot_state_publisher(
        robot_description=robot_description, use_sim_time=False
    )
    robot_state_publisher_event_handler = RegisterEventHandler(
        OnProcessExit(
            target_action=joint_state_broadcaster, on_exit=[robot_state_publisher]
        )
    )
    ld.add_action(robot_state_publisher_event_handler)

    # MoveIt 2
    ld.add_action(LBRMoveGroupMixin.arg_allow_trajectory_execution())
    ld.add_action(LBRMoveGroupMixin.arg_capabilities())
    ld.add_action(LBRMoveGroupMixin.arg_disable_capabilities())
    ld.add_action(LBRMoveGroupMixin.arg_monitor_dynamics())
    ld.add_action(LBRMoveGroupMixin.args_publish_monitored_planning_scene())

    # MoveGroup:
    # - requires world frame
    # - maps link robot_name/base_frame -> base_frame
    # These two transform need publishing
    robot_name = LaunchConfiguration("robot_name").perform(context)
    ld.add_action(
        LBRDescriptionMixin.node_static_tf(
            tf=[0, 0, 0, 0, 0, 0],
            parent="world",
            child=LaunchConfiguration("base_frame"),
            condition=IfCondition(LaunchConfiguration("moveit")),
        ),
    )
    ld.add_action(
        LBRDescriptionMixin.node_static_tf(
            tf=[0, 0, 0, 0, 0, 0],  # keep zero
            parent=LaunchConfiguration("base_frame"),
            child=PathJoinSubstitution(
                [
                    LaunchConfiguration("robot_name"),
                    LaunchConfiguration("base_frame"),
                ]  # results in robot_name/base_frame
            ),
            condition=IfCondition(LaunchConfiguration("moveit")),
        )
    )

    model = LaunchConfiguration("model").perform(context)
    moveit_configs_builder = LBRMoveGroupMixin.moveit_configs_builder(
        robot_name=model,
        base_frame=LaunchConfiguration("base_frame"),
        package_name=f"{model}_moveit_config",
    )
    movegroup_params = LBRMoveGroupMixin.params_move_group()

    ld.add_action(
        LBRMoveGroupMixin.node_move_group(
            parameters=[
                moveit_configs_builder.to_dict(),
                movegroup_params,
                {"use_sim_time": False},
            ],
            condition=IfCondition(LaunchConfiguration("moveit")),
            namespace=robot_name,
        )
    )

    # unless MoveIt: add world -> robot_name/base_frame transform
    ld.add_action(
        LBRDescriptionMixin.node_static_tf(
            tf=[0, 0, 0, 0, 0, 0],  # keep zero
            parent="world",
            child=PathJoinSubstitution(
                [
                    LaunchConfiguration("robot_name"),
                    LaunchConfiguration("base_frame"),
                ]  # results in robot_name/base_frame
            ),
            condition=UnlessCondition(LaunchConfiguration("moveit")),
        )
    )

    # RViz and MoveIt
    rviz_moveit = RVizMixin.node_rviz(
        rviz_config_pkg=f"{model}_moveit_config",
        rviz_config="config/moveit.rviz",
        parameters=LBRMoveGroupMixin.params_rviz(
            moveit_configs=moveit_configs_builder.to_moveit_configs()
        ),
        condition=IfCondition(
            AndSubstitution(LaunchConfiguration("moveit"), LaunchConfiguration("rviz"))
        ),
        remappings=[
            ("robot_description", robot_name + "/robot_description"),
            ("robot_description_semantic", robot_name + "/robot_description_semantic"),
            ("display_planned_path", robot_name + "/display_planned_path"),
            ("monitored_planning_scene", robot_name + "/monitored_planning_scene"),
        ],
    )

    # RViz no MoveIt
    rviz = RVizMixin.node_rviz(
        rviz_config_pkg="lbr_bringup",
        rviz_config="config/config.rviz",
        condition=IfCondition(
            AndSubstitution(
                LaunchConfiguration("rviz"),
                NotSubstitution(LaunchConfiguration("moveit")),
            )
        ),
    )

    # RViz event handler
    rviz_event_handler = RegisterEventHandler(
        OnProcessStart(
            target_action=robot_state_publisher, on_start=[rviz_moveit, rviz]
        )
    )
    ld.add_action(rviz_event_handler)

    return ld.entities


def generate_launch_description() -> LaunchDescription:
    ld = LaunchDescription()
    ld.add_action(LBRDescriptionMixin.arg_model())
    ld.add_action(LBRDescriptionMixin.arg_robot_name())
    ld.add_action(LBRDescriptionMixin.arg_base_frame())
    ld.add_action(LBRDescriptionMixin.arg_port_id())
    ld.add_action(
        DeclareLaunchArgument(
            name="moveit",
            default_value="false",
            description="Whether to launch MoveIt 2.",
        )
    )
    ld.add_action(
        DeclareLaunchArgument(
            name="rviz", default_value="true", description="Whether to launch RViz."
        )
    )
    ld.add_action(LBRSystemInterfaceMixin.arg_ctrl_cfg_pkg())
    ld.add_action(LBRSystemInterfaceMixin.arg_ctrl_cfg())
    ld.add_action(LBRSystemInterfaceMixin.arg_ctrl())
    ld.add_action(OpaqueFunction(function=launch_setup))
    return ld
