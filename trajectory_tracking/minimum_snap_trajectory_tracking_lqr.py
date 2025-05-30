# TODO track the trajectory (a_des - a) + kd(v_des - v) + kp(p_des - p) = 0

import time

import numpy as np
import pybullet as p
import matplotlib.pyplot as plt
import pybullet_data

from gym_pybullet_drones.utils.enums import DroneModel, Physics
from gym_pybullet_drones.envs.CtrlAviary import CtrlAviary
from controllers.lqr import LQRControl
from gym_pybullet_drones.utils.Logger import Logger
from gym_pybullet_drones.utils.utils import sync, str2bool
from trajectory_tracking.trajGen3D import get_helix_waypoints, get_MST_coefficients, generate_trajectory

DEFAULT_DRONES = DroneModel("racer")
DEFAULT_NUM_DRONES = 1
DEFAULT_PHYSICS = Physics("pyb")
DEFAULT_GUI = True
DEFAULT_RECORD_VISION = False
DEFAULT_PLOT = True
DEFAULT_USER_DEBUG_GUI = False
DEFAULT_OBSTACLES = False
DEFAULT_SIMULATION_FREQ_HZ = 240
DEFAULT_CONTROL_FREQ_HZ = 48
DEFAULT_DURATION_SEC = 30
DEFAULT_OUTPUT_FOLDER = 'results'
DEFAULT_COLAB = False

def run(
        drone=DEFAULT_DRONES,
        num_drones=DEFAULT_NUM_DRONES,
        physics=DEFAULT_PHYSICS,
        gui=DEFAULT_GUI,
        record_video=DEFAULT_RECORD_VISION,
        plot=DEFAULT_PLOT,
        user_debug_gui=DEFAULT_USER_DEBUG_GUI,
        obstacles=DEFAULT_OBSTACLES,
        simulation_freq_hz=DEFAULT_SIMULATION_FREQ_HZ,
        control_freq_hz=DEFAULT_CONTROL_FREQ_HZ,
        duration_sec=DEFAULT_DURATION_SEC,
        output_folder=DEFAULT_OUTPUT_FOLDER,
        colab=DEFAULT_COLAB
        ):

    INIT_XYZS = np.array([[0, 0, 1]])
    INIT_RPYS = np.array([[0, 0, 0]])

    TARGET_WAYPOINTS = np.array([[1.8, 1.2, 0.9], [1.5, -1.7, 0.5], [0.3, 1.9, 1.2], [-2, 0.8, 1.7], [1.8, 1.2, 0.9]])
    TARGET_WAYPOINTS = np.array([[-1, 0, 1], [1, 0, 1], [-1, 0, 1], [1, 0, 1],
                                [-1, 0, 1], [1, 0, 1], [-1, 0, 1], [1, 0, 1], 
                                [-1, 0, 1], [1, 0, 1], [-1, 0, 1], [1, 0, 1]])
    TARGET_RPY = np.array([[0, 0, 0]])

    coeff_x, coeff_y, coeff_z = get_MST_coefficients(TARGET_WAYPOINTS)
    v = 1.0

    env = CtrlAviary(drone_model=drone,
                        num_drones=num_drones,
                        initial_xyzs=INIT_XYZS,
                        initial_rpys=INIT_RPYS,
                        physics=physics,
                        neighbourhood_radius=10,
                        pyb_freq=simulation_freq_hz,
                        ctrl_freq=control_freq_hz,
                        gui=gui,
                        record=record_video,
                        obstacles=obstacles,
                        user_debug_gui=user_debug_gui
                        )
    
    #### Obtain the PyBullet Client ID from the environment ####
    PYB_CLIENT = env.getPyBulletClient()

    #### Initialize the logger ################################# TODO Make Logger update in realtime
    logger = Logger(logging_freq_hz=control_freq_hz,
                    num_drones=num_drones,
                    output_folder=output_folder,
                    colab=colab
                    )
    
    #### Initialize the controllers ############################
    if drone in [DroneModel.CF2X, DroneModel.CF2P, DroneModel.RACE]:
        ctrl = [LQRControl(drone_model=drone) for i in range(num_drones)]

    
    #### Run the simulation ####################################
    action = np.zeros((num_drones, 4))
    START = time.time()
    for i in range(0, int(duration_sec*env.CTRL_FREQ)):
        obs, reward, terminated, truncated, info = env.step(action)

        t = i/env.CTRL_FREQ
        state = generate_trajectory(t, v, TARGET_WAYPOINTS, coeff_x, coeff_y, coeff_z)

        for j in range(num_drones):
            action[j,:], _, _ = ctrl[j].computeControlFromState(control_timestep=env.CTRL_TIMESTEP,
                                                                state=obs[j],
                                                                target_pos=state.pos,
                                                                target_vel=state.vel,
                                                                target_rpy=TARGET_RPY[j, :])
            
        #### Log the simulation ####################################
        for j in range(num_drones):
            logger.log(drone=j,
                    timestamp=i/env.CTRL_FREQ,
                    state=obs[j],
                    control=np.hstack([state.pos, TARGET_RPY[j, :], np.zeros(6)])
                    )
            
        env.render()

        if gui:
            sync(i, START, env.CTRL_TIMESTEP)

    env.close()

    logger.save()
    logger.save_as_csv("min_snap")

    if plot:
        logger.plot()


if __name__ == "__main__":
    run()