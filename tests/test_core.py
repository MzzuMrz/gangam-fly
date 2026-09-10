import numpy as np

from gangnamfly.plasticity import Plasticity
from gangnamfly.reference import DanceReference


# AC: AC-2
def test_plasticity_preserves_sign_topology_and_freezes():
    weights = np.array([1.0, -2.0, 0.5], np.float32)
    p = Plasticity(weights, np.array([0, 1]), np.array([0, 1]), np.array([1, 2]), eta=0.5)
    before = weights.copy()
    p.update(np.array([1, 2, 3]), 0.8, enabled=False)
    np.testing.assert_array_equal(weights, before)
    for _ in range(20):
        p.update(np.array([1, 2, 3]), 0.2, enabled=True)
        p.update(np.array([1, 2, 3]), 0.8, enabled=True)
    assert np.any(weights != before)
    np.testing.assert_array_equal(np.sign(weights), np.sign(before))
    assert weights[2] == before[2]
    assert np.all(np.abs(weights[:2]) >= np.abs(before[:2]) * 0.5)
    assert np.all(np.abs(weights[:2]) <= np.abs(before[:2]) * 1.5)


# AC: AC-3
def test_reference_is_periodic_bounded_and_scores_actual_pose():
    r = DanceReference(
        ["tibia_T1_left", "coxa_abduct_T1_right"],
        np.array([-1.0, 0.0]),
        np.array([[-1.35, 1.3], [-1.0, 0.7]]),
    )
    t = r.target(0.1)
    np.testing.assert_allclose(t, r.target(0.1 + r.period))
    assert r.error(t, 0.1) == 0
    assert r.error(t + 0.2, 0.1) > 0


# AC: AC-2, AC-6
def test_constant_reward_does_not_create_spurious_learning():
    weights = np.array([1.0, -2.0], np.float32)
    p = Plasticity(weights, np.array([0, 1]), np.array([0, 1]), np.array([1, 0]))
    for _ in range(50):
        p.update(np.array([2, 3]), 0.5, enabled=True)
    np.testing.assert_array_equal(weights, [1.0, -2.0])


# AC: AC-2, AC-6
def test_inverted_teaching_changes_update_direction():
    positive = np.array([1.0], np.float32)
    negative = np.array([1.0], np.float32)
    a = Plasticity(positive, np.array([0]), np.array([0]), np.array([1]), eta=0.1)
    b = Plasticity(negative, np.array([0]), np.array([0]), np.array([1]), eta=0.1)
    a.update(np.array([2, 2]), 0.5, True)
    b.update(np.array([2, 2]), 0.5, True)
    a.update(np.array([2, 2]), 0.8, True)
    b.update(np.array([2, 2]), 0.2, True)
    assert positive[0] > 1 and negative[0] < 1
