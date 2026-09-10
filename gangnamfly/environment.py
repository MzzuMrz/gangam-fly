"""Unchanged Flybody MJCF in its native cm/gram/second units."""

import mujoco
import numpy as np

from .config import BODY, DT
from .mapping import PAIRS


class FlybodyEnvironment:
    def __init__(self):
        self.model = mujoco.MjModel.from_xml_path(str(BODY / "floor.xml"))
        self.data = mujoco.MjData(self.model)
        self.names = [
            f"{joint}_{segment}_{side}"
            for segment in ["T1", "T2", "T3"]
            for side in ["left", "right"]
            for joint in PAIRS
        ]
        self.actuators = np.asarray([self.model.actuator(n).id for n in self.names])
        self.qadr = np.asarray([self.model.joint(n).qposadr[0] for n in self.names])
        self.rest = self.model.qpos_spring[self.qadr].copy()
        self.limits = self.model.actuator_ctrlrange[self.actuators].copy()
        self.rest = np.clip(self.rest, self.limits[:, 0], self.limits[:, 1])
        self.mesh_geoms = [
            i for i in range(self.model.ngeom) if self.model.geom_type[i] == mujoco.mjtGeom.mjGEOM_MESH
        ]
        self.reset()

    def reset(self, seed=64, jitter=0.0):
        mujoco.mj_resetData(self.model, self.data)
        self.data.qpos[:] = self.model.qpos_spring
        if jitter:
            self.data.qpos[self.qadr] = np.clip(
                self.data.qpos[self.qadr] + np.random.default_rng(seed).normal(0, jitter, len(self.qadr)),
                self.limits[:, 0],
                self.limits[:, 1],
            )
        # qpos_spring carries the model's reference free-root orientation.
        for i in range(self.model.nu):
            if self.model.actuator_trntype[i] == mujoco.mjtTrn.mjTRN_JOINT:
                j = self.model.actuator_trnid[i, 0]
                if self.model.jnt_type[j] == mujoco.mjtJoint.mjJNT_HINGE:
                    self.data.ctrl[i] = self.data.qpos[self.model.jnt_qposadr[j]]
        np.clip(
            self.data.ctrl,
            self.model.actuator_ctrlrange[:, 0],
            self.model.actuator_ctrlrange[:, 1],
            out=self.data.ctrl,
        )
        # Wings/adhesion controls not learned or used as balance assistance.
        for i in range(self.model.nu):
            if "wing" in self.model.actuator(i).name or "adhere" in self.model.actuator(i).name:
                self.data.ctrl[i] = 0
        mujoco.mj_forward(self.model, self.data)

    def step(self, command):
        if np.shape(command) != self.rest.shape or not np.isfinite(command).all():
            raise ValueError("Invalid motor command")
        self.data.ctrl[self.actuators] = np.clip(command, self.limits[:, 0], self.limits[:, 1])
        mujoco.mj_step(self.model, self.data, nstep=round(DT / self.model.opt.timestep))
        if not np.isfinite(self.data.qpos).all() or any(w.number for w in self.data.warning):
            raise RuntimeError("MuJoCo produced a nonfinite state or solver warning")
        mujoco.mj_forward(self.model, self.data)

    def support_loads(self):
        """Floor normal forces normalized by body weight; self contacts are excluded."""
        floor = self.model.geom("floor").id
        force = np.zeros(6)
        foot, other_load = 0.0, 0.0
        for index, contact in enumerate(self.data.contact):
            if floor not in (contact.geom1, contact.geom2):
                continue
            other = int(contact.geom2 if contact.geom1 == floor else contact.geom1)
            name = self.model.geom(other).name or ""
            mujoco.mj_contactForce(self.model, self.data, index, force)
            normal = max(0.0, float(force[0]))
            if name.startswith(("tarsus", "tarsal_claw")) and name.endswith("_collision"):
                foot += normal
            else:
                other_load += normal
        weight = float(self.model.body_mass.sum() * np.linalg.norm(self.model.opt.gravity))
        return {"foot_load_fraction": foot / weight, "other_load_fraction": other_load / weight}

    def transforms(self):
        result = []
        for i in self.mesh_geoms:
            q = np.empty(4)
            mujoco.mju_mat2Quat(q, self.data.geom_xmat[i])
            result.append({"id": i, "pos": self.data.geom_xpos[i].tolist(), "quat": q.tolist()})
        return result

    def geometry(self):
        m = self.model
        meshes = []
        for i in range(m.nmesh):
            va, vn = m.mesh_vertadr[i], m.mesh_vertnum[i]
            fa, fn = m.mesh_faceadr[i], m.mesh_facenum[i]
            meshes.append(
                {
                    "id": i,
                    "vertices": m.mesh_vert[va : va + vn].ravel().tolist(),
                    "faces": m.mesh_face[fa : fa + fn].ravel().tolist(),
                }
            )
        geoms = []
        for i in self.mesh_geoms:
            mat = m.geom_matid[i]
            rgba = m.mat_rgba[mat] if mat >= 0 else m.geom_rgba[i]
            geoms.append({"id": i, "mesh": int(m.geom_dataid[i]), "rgba": rgba.tolist()})
        return {"meshes": meshes, "geoms": geoms, "label": "Flybody · DeepMind + HHMI Janelia", "units": "cm"}
