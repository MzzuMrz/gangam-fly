import numpy as np
import pytest
from flybike.brain.motor import MotorAdapter
from flybike.brain.sensory import ProvisionalMechanosensoryAdapter
from flybike.sim.environment import BicycleEnvironment
from flybike.sim.scheduler import Scheduler


def test_motor_has_no_world_input_and_zero_activity_means_zero_command():
    motor = MotorAdapter()
    np.testing.assert_array_equal(motor.decode(np.zeros(6), 0.02), [0, 0])
    command = motor.decode(np.array([0, 100, 0, 100, 100, 100]), 0.02)
    assert 0 < command[0] <= 0.6 and 0 < command[1] <= 8
    with pytest.raises(ValueError):
        motor.decode(np.full(6, np.nan), 0.02)


def test_sensory_sign_and_saturation():
    sensory = ProvisionalMechanosensoryAdapter()
    output = sensory.encode(
        {"roll": 0.3, "angular_velocity_body": np.array([2.0, 0, 0]), "forward_velocity": 3.0}
    )
    assert output.shape == (6,)
    assert output[1] > output[0] and output[3] > output[2] and output[5] > output[4]
    assert np.all((output >= 0) & (output <= 30))


def test_scheduler_never_drops_ticks():
    schedule = Scheduler(100, 50, 60, 10)
    due = [schedule.due(i) for i in range(100)]
    assert sum(x["brain"] for x in due) == 50
    assert sum(x["vision"] for x in due) == 10
    assert sum(x["render"] for x in due) == 60


def test_bicycle_falls_and_actuators_change_physics():
    env = BicycleEnvironment(seed=64)
    assert env.model.nq == 10 and env.model.nu == 2
    assert env.model.opt.gravity[2] < 0
    initial = env.observe()["roll"]
    contact = False
    for _ in range(300):
        env.step(np.zeros(2))
        contact |= env.data.ncon > 0
    assert contact and abs(env.observe()["roll"]) > abs(initial) + 0.3
    assert np.isfinite(env.data.qpos).all()
    driven = BicycleEnvironment(seed=64)
    for _ in range(20):
        driven.step(np.array([0.3, 4.0]))
    assert driven.observe()["steering"] > 0.05
    assert abs(driven.data.qvel[-2]) > 0.01
