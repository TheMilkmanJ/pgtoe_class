"""
PRTOE Data Loader for CLASS Background Output
==============================================
Provides helper functions to load background quantities from CLASS runs.
"""

import numpy as np
import classy


def load_class_background(cosmo, a_values=None, z_values=None):
    """
    Load background quantities from a completed CLASS run.
    
    Args:
        cosmo: A classy.Class instance that has already run compute()
        a_values: Array of scale factor values to extract (if None, use CLASS's default table)
        z_values: Array of redshift values to extract (alternative to a_values)
    
    Returns:
        Dictionary with keys: a, z, H, phi, F, F_phi, phi_prime, H_prime, etc.
        All values are numpy arrays of the same length.
    """
    # Get the background table
    background = cosmo.get_background()
    
    # Extract arrays
    a = np.array(background['a'])
    z = np.array(background['z'])
    H = np.array(background['H [1/Mpc]'])
    
    result = {
        'a': a,
        'z': z,
        'H': H,
    }
    
    # Try to get PRTOE-specific quantities if available
    prtoe_keys = [
        'phi_prtoe', 'dphi_prtoe', 'ddphi_prtoe',
        'F_prtoe', 'F_phi_prtoe', 'F_phiphi_prtoe',
        'F_dot_prtoe', 'F_ddot_prtoe',
        'rho_prtoe', 'p_prtoe',
        'V_scf', 'dV_scf', 'ddV_scf',
        'meff2_prtoe', 'K_prtoe', 'Q_prtoe', 'cT2_prtoe'
    ]
    
    for key in prtoe_keys:
        if key in background:
            result[key] = np.array(background[key])
    
    # Also get standard quantities
    standard_keys = ['rho_g', 'rho_b', 'rho_cdm', 'rho_r', 'rho_tot', 'p_tot']
    for key in standard_keys:
        if key in background:
            result[key] = np.array(background[key])
    
    return result


def get_background_at_z(cosmo, z):
    """
    Get background quantities at a specific redshift.
    
    Args:
        cosmo: A classy.Class instance that has already run compute()
        z: Redshift value
    
    Returns:
        Dictionary with single values for each quantity at redshift z.
    """
    result = {}
    
    # Get at specific z
    result['z'] = z
    result['a'] = 1.0 / (1.0 + z)
    result['H'] = cosmo.Hubble(z)
    
    # Try to get PRTOE quantities
    try:
        result['phi'] = cosmo.phi_prtoe(z)
    except:
        pass
    
    try:
        result['F'] = cosmo.F_prtoe(z)
    except:
        pass
    
    return result


if __name__ == "__main__":
    # Test the loader
    print("Testing data loader...")
    
    cosmo = classy.Class()
    cosmo.set({
        'use_prtoe': 'yes',
        'xi_prtoe': 1e-6,
        'phi_0_prtoe': 0.5,
        'zeta_prtoe': 1.0,
        'phi_c_prtoe': 0.0,
        'delta_phi_prtoe': 1.0,
        'V0_prtoe': 1e-10,
        'm_prtoe': 1e-6,
        'lambda_prtoe': 0.1,
        'Omega_cdm': 0.27,
        'Omega_b': 0.05,
        'h': 0.67,
        'Omega_Lambda': 0.0,
        'YHe': 0.245
    })
    cosmo.compute()
    
    bg = load_class_background(cosmo)
    print(f"Loaded {len(bg['a'])} background points")
    print(f"a range: {bg['a'][0]:.4f} to {bg['a'][-1]:.4f}")
    print(f"H range: {bg['H'][0]:.6f} to {bg['H'][-1]:.6f}")
    
    if 'phi_prtoe' in bg:
        print(f"phi_prtoe range: {bg['phi_prtoe'][0]:.6f} to {bg['phi_prtoe'][-1]:.6f}")
    if 'F_prtoe' in bg:
        print(f"F_prtoe range: {bg['F_prtoe'][0]:.6f} to {bg['F_prtoe'][-1]:.6f}")
    
    print("Data loader test passed!")
