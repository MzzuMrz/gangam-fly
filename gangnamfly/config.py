from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOOM = ROOT / "vendor/doomfly"
BODY = ROOT / "vendor/flybody/flybody/fruitfly/assets"
GRAPH = DOOM / "outputs/doom/malecns_v1/graph.npz"
ANNOTATIONS = DOOM / "connectome_data/malecns_v1/annotations.feather"
EPISODES = ROOT / "episodes"
DT = 0.02
SEED = 64
