import sys
import os
from pathlib import Path

# Dynamic search for classy build directory
classy_build_root = os.environ.get("CLASSY_BUILD_ROOT")
if classy_build_root:
    import glob
    build_dirs = sorted(glob.glob(os.path.join(classy_build_root, "build", "lib.*")))
    if build_dirs:
        sys.path.insert(0, build_dirs[-1])
else:
    # Fallback to repo-relative build directory
    repo_root = Path(__file__).resolve().parent
    import glob
    build_dirs = sorted(glob.glob(os.path.join(repo_root, "build", "lib.*")))
    if build_dirs:
        sys.path.insert(0, build_dirs[-1])

from classy import Class

c = Class()
c.set({
    "H0": 67.4,
    "omega_b": 0.0224,
    "omega_cdm": 0.12,
    "A_s": 2.11e-9,
    "n_s": 0.965,
    "z_reio": 8.0,
    "use_prtoe": "yes",
    "xi_prtoe": 1e-7,
    "zeta_prtoe": 0.1,
    "V0_prtoe": 0.6865,
    "lambda_prtoe": 0.05,
    "m_prtoe": 0.05,
    "phi_0_prtoe": 0.0,
    "N_ncdm": 1,
    "T_ncdm": 0.71611,
    "m_ncdm": 0.06,
    "beta_prtoe": 1e-6,
    "M_prtoe": 100.0,
    "alpha_prtoe": 0.1,
    "M_ew_prtoe": 100.0,
    "H_vac_floor": 64.1218,
    "delta_prtoe": 0.0,
    "output": "tCl"
})
c.compute()

bg = c.get_background()
z_today = bg['z'][-1]
rho_lambda = bg.get('(.)rho_lambda', [0.0])[-1]
rho_tot = bg['(.)rho_tot'][-1]

print(f"z today: {z_today}")
print(f"rho_lambda today: {rho_lambda}")
print(f"rho_tot today: {rho_tot}")
print(f"Fraction of lambda: {rho_lambda / rho_tot:.4f}")

# Let us print all keys and their values today
for key in bg.keys():
    print(f"  {key:<25} : {bg[key][-1]:.6e}")

c.struct_cleanup()
c.empty()
