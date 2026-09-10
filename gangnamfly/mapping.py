"""Dataset-resolved motor muscle labels and explicitly provisional sensory tuning."""

import json
from typing import Any

import numpy as np
from pyarrow import feather

from .config import ANNOTATIONS

PAIRS = {
    "coxa_abduct": ("Pleural remotor/abductor MN", "Sternal adductor MN"),
    "coxa_twist": ("Sternal anterior rotator MN", "Sternal posterior rotator MN"),
    "coxa": ("Sternotrochanter MN", "Tergotr. MN"),
    "femur": ("Tr extensor MN", "Tr flexor MN"),
    "tibia": ("Ti extensor MN", "Ti flexor MN"),
}


class Mapping:
    def __init__(self, ids):
        a = feather.read_table(ANNOTATIONS).to_pandas().set_index("bodyId").loc[ids]
        self.ids = ids
        self.motor: list[dict[str, Any]] = []
        self.sensory: list[dict[str, Any]] = []
        self.dn: list[dict[str, Any]] = []
        for segment, subclass, nerves in [
            ("T1", "fl", ["ProCN", "ProLN"]),
            ("T2", "ml", ["MesoLN"]),
            ("T3", "hl", ["MetaLN"]),
        ]:
            for side, word in [("L", "left"), ("R", "right")]:
                base = a.superclass.eq("vnc_motor") & a.subclass.eq(subclass) & a.somaSide.eq(side)
                for joint, pair in PAIRS.items():
                    pools = [np.flatnonzero((base & a.type.eq(t)).to_numpy()).astype(np.int32) for t in pair]
                    if any(len(p) == 0 for p in pools):
                        raise ValueError(f"Missing motor population: {segment} {side} {pair}")
                    self.motor.append({"name": f"{joint}_{segment}_{word}", "pools": pools, "types": pair})
                mask = (
                    a.superclass.eq("vnc_sensory")
                    & a.subclass.eq("chordotonal organ")
                    & a.entryNerve.isin(nerves)
                    & a.rootSide.eq(side)
                )
                pool = np.flatnonzero(mask.to_numpy()).astype(np.int32)
                if len(pool) < 2:
                    raise ValueError("Missing chordotonal pool")
                # No receptor direction tuning is supplied by these annotations.
                for sign, part in zip([-1, 1], np.array_split(pool, 2)):
                    self.sensory.append(
                        {
                            "name": f"{segment}_{word}_{sign}",
                            "indices": part,
                            "kind": "leg",
                            "segment": segment,
                            "side": word,
                            "sign": sign,
                        }
                    )
        for side in ["L", "R"]:
            for kind, superclass, subclass in [
                ("angular", "sensory_ascending", "haltere"),
                ("beat", "cb_sensory", "auditory"),
            ]:
                mask = a.superclass.eq(superclass) & a.subclass.eq(subclass) & a.rootSide.eq(side)
                ix = np.flatnonzero(mask.to_numpy()).astype(np.int32)
                if not len(ix):
                    raise ValueError(f"Missing {kind} sensory input")
                self.sensory.append(
                    {"name": f"{kind}_{side}", "indices": ix, "kind": kind, "sign": -1 if side == "L" else 1}
                )
        for typ in ["DNg100", "DNa02", "DNg13"]:
            for side in ["L", "R"]:
                ix = np.flatnonzero((a.type.eq(typ) & a.somaSide.eq(side)).to_numpy())
                if not len(ix):
                    raise ValueError("Missing descending neuron observer")
                self.dn.append({"name": f"{typ}_{side}", "indices": ix})
        self.motor_indices = np.unique(np.concatenate([p for m in self.motor for p in m["pools"]]))
        self.sensory_indices = np.unique(np.concatenate([s["indices"] for s in self.sensory]))
        if np.intersect1d(self.motor_indices, self.sensory_indices).size:
            raise ValueError("Sensory and motor pools overlap")
        self.annotations = a

    def document(self):
        def neurons(ix):
            return [
                {"id": str(self.ids[i]), "index": int(i), "type": str(self.annotations.type.iloc[i])}
                for i in ix
            ]

        return {
            "motor_interpretation": "Muscle names are anatomical annotations. MJCF joint axes/signs/gains and antagonistic pairing are provisional; not a measured neuromuscular mapping.",
            "sensory_interpretation": "Anatomical sensory cells; artificial opponent tuning by sorted ID and engineered current gains.",
            "motor": [
                {
                    "actuator": m["name"],
                    "positive": neurons(m["pools"][0]),
                    "negative": neurons(m["pools"][1]),
                }
                for m in self.motor
            ],
            "sensory": [
                {"name": s["name"], "kind": s["kind"], "neurons": neurons(s["indices"])} for s in self.sensory
            ],
            "descending_observers": [{"name": s["name"], "neurons": neurons(s["indices"])} for s in self.dn],
        }

    def save(self, path):
        path.write_text(json.dumps(self.document(), indent=2) + "\n")
