# Sources and notices

- DOOMFLY by nftechie and contributors, revision
  `71ecf53d78eaffaf1a57ed7b0ccf5d458abc9f33`, MIT. Its importer, prepared CSR,
  NativeBrain state and compiled kernel are used without changing source.
  https://github.com/nftechie/doomfly
- Flybody by the Google DeepMind / HHMI Janelia collaboration, revision
  `d015e9bfe441bd90ae431bac24c55cb74bdbce26`, Apache-2.0. The unchanged MJCF
  and anatomical meshes are loaded directly. Browser geometry is exported from
  MuJoCo's compiled mesh coordinates, not a substitute body.
  https://github.com/TuragaLab/flybody
  Vaxenburg et al., Whole-body physics simulation of fruit fly locomotion,
  Nature 643, 1312–1320 (2025), https://doi.org/10.1038/s41586-025-09029-4
- MaleCNS v1.0, FlyEM / HHMI Janelia, University of Cambridge, MRC Laboratory
  of Molecular Biology and Google Research collaboration; CC BY 4.0 per the
  pinned DOOMFLY data provenance. Source https://male-cns.janelia.org/download/,
  publication https://doi.org/10.1016/j.cell.2026.08.015. Modifications: DOOMFLY's
  retained-node filtering, compact indexing and modeled signed weights;
  GangnamFly's provisional sensory/motor assignments and experimental efficacy
  updates. Anatomical synapse counts are not learned functional weights.
- Fly64, https://github.com/ornata/fly at
  `f2f4114e53eaa326e54129f27a5383f93c6957af`, inspected for context only.
  No source, game bridge, ROM or learning policy is imported.
- Three.js, MIT, installed separately through web/package-lock.json.
  Python/JS dependencies retain their distributed licenses.
- Xsens, "Motion Capture files for PSY - Gangnam Style", published December 14,
  2015, offered by Xsens as a free animation download:
  https://www.xsens.com/resources/news/motion-capture-files-for-psy-gangnam-style
  ZIP: https://www.xsens.com/hubfs/Downloads/Data/Gangnam%20Style.zip
  SHA-256: `a9f8b4f97e23db799055464ccd705ed448f6dc712aa1f775aa34f3ac2d2a85de`.
  The MVNX contains 23 human segments and 7,451 normal frames, timestamps
  0..31,070 ms, nominally 240 Hz. Neutral/T-pose calibration frames are excluded.
  Source and derived data remain local under ignored vendor/xsens, fetched from
  the provider during preparation. No open-source license is inferred for this
  asset. Modifications: timestamp interpolation, scale/orientation alignment and
  bounded inverse kinematics onto Flybody plus authored stand-up/ending and
  middle-leg adaptation. This motion is used exclusively in the labeled DEMO.

Full principal notices are under licenses/. Public source checkouts, datasets
and generated anatomical model payload are local dependencies, excluded from
this repository's source distribution. No song audio or performance footage is
included. The neural target remains an authored fly-joint exercise inspired by
the dance; the DEMO now uses the separately attributed continuous capture.
