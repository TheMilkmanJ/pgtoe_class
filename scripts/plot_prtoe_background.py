#!/usr/bin/env python3
"""
PRTOE Background Evolution Plotter
===================================
Plots H(a), phi(a), F(a), and stability quantities for various PRTOE parameters.
"""

import sys
import os
import numpy as np
import matplotlib.pyplot as plt

# Add the prtoe_class directory to the path BEFORE importing classy
sys.path.insert(0, '/home/themilkmanj/prtoe_class/python')

import classy

# Create output directory
os.makedirs('output', exist_ok=True)


def run_prtoe_cosmology(params, name):
    """Run PRTOE cosmology with given parameters."""
    print(f"  Running {name}...")
    cosmo = classy.Class()
    
    # Base cosmology
    base_params = {
        'Omega_cdm': 0.27,
        'Omega_b': 0.05,
        'h': 0.67,
        'Omega_Lambda': 0.68,
        'tau_reio': 0.0544,
        'n_s': 0.965,
        'A_s': 2.1e-9,
    }
    
    # Add PRTOE parameters
    base_params.update({'use_prtoe': 'yes'})
    base_params.update(params)
    
    cosmo.set(base_params)
    try:
        cosmo.compute()
        bg = cosmo.get_background()
        print(f"  ✓ {name} successful")
        return bg
    except Exception as e:
        print(f"  ✗ {name} failed: {e}")
        return None


def extract_prtoe_quantities(bg):
    """Extract PRTOE-specific quantities from background."""
    return {
        'a': bg['a'],
        'H': bg['H [1/Mpc]'],
        'phi': bg.get('phi_prtoe', np.zeros_like(bg['a'])),
        'dphi': bg.get('dphi_prtoe', np.zeros_like(bg['a'])),
        'F': bg.get('F_prtoe', np.ones_like(bg['a'])),
        'F_phi': bg.get('F_phi_prtoe', np.zeros_like(bg['a'])),
        'F_phiphi': bg.get('F_phiphi_prtoe', np.zeros_like(bg['a'])),
        'meff2': bg.get('m_eff2_prtoe', np.zeros_like(bg['a'])),
        'K': bg.get('K_prtoe', np.ones_like(bg['a'])),
        'Q': bg.get('Q_prtoe', np.ones_like(bg['a'])),
        'cs2': bg.get('cs2_prtoe', np.ones_like(bg['a'])),
        'cT2': bg.get('cT2_prtoe', np.ones_like(bg['a'])),
        'rho_prtoe': bg.get('rho_prtoe', np.zeros_like(bg['a'])),
        'V': bg.get('V_scf', np.zeros_like(bg['a'])),
    }


def plot_parameter_variation():
    """Plot how varying each PRTOE parameter affects the evolution."""
    print("\n" + "="*60)
    print("Parameter Variation Study")
    print("="*60)
    
    # Base PRTOE parameters
    base_prtoe = {
        'xi_prtoe': 1e-5,
        'zeta_prtoe': 0.1,
        'V0_prtoe': 0.5,
        'lambda_prtoe': 0.05,
        'm_prtoe': 0.05,
        'phi_0_prtoe': 1.0,
        'phi_c_prtoe': 0.0,
        'delta_phi_prtoe': 0.1,
    }
    
    # Vary each parameter
    variations = {
        'xi': [
            {'name': 'xi=1e-6', 'params': {**base_prtoe, 'xi_prtoe': 1e-6}},
            {'name': 'xi=1e-5', 'params': {**base_prtoe, 'xi_prtoe': 1e-5}},
            {'name': 'xi=1e-4', 'params': {**base_prtoe, 'xi_prtoe': 1e-4}},
        ],
        'zeta': [
            {'name': 'zeta=0.01', 'params': {**base_prtoe, 'zeta_prtoe': 0.01}},
            {'name': 'zeta=0.1', 'params': {**base_prtoe, 'zeta_prtoe': 0.1}},
            {'name': 'zeta=1.0', 'params': {**base_prtoe, 'zeta_prtoe': 1.0}},
        ],
        'V0': [
            {'name': 'V0=0.1', 'params': {**base_prtoe, 'V0_prtoe': 0.1}},
            {'name': 'V0=0.5', 'params': {**base_prtoe, 'V0_prtoe': 0.5}},
            {'name': 'V0=1.0', 'params': {**base_prtoe, 'V0_prtoe': 1.0}},
        ],
        'lambda': [
            {'name': 'lambda=0.01', 'params': {**base_prtoe, 'lambda_prtoe': 0.01}},
            {'name': 'lambda=0.05', 'params': {**base_prtoe, 'lambda_prtoe': 0.05}},
            {'name': 'lambda=0.1', 'params': {**base_prtoe, 'lambda_prtoe': 0.1}},
        ],
    }
    
    for param_name, param_variations in variations.items():
        print(f"\nVarying {param_name}...")
        results = []
        
        for variation in param_variations:
            bg = run_prtoe_cosmology(variation['params'], variation['name'])
            if bg is not None:
                prtoe_qty = extract_prtoe_quantities(bg)
                results.append({'name': variation['name'], 'data': prtoe_qty})
        
        if len(results) > 0:
            # Plot phi(a) for this parameter variation
            plt.figure(figsize=(10, 6))
            for result in results:
                plt.plot(result['data']['a'], result['data']['phi'], label=result['name'])
            plt.xlabel('a')
            plt.ylabel('phi')
            plt.title(f'Scalar Field Evolution: Varying {param_name}')
            plt.legend()
            plt.grid(True, alpha=0.3)
            plt.tight_layout()
            plt.savefig(f'output/phi_vs_{param_name}.png', dpi=150)
            plt.close()
            print(f"  ✓ Saved phi_vs_{param_name}.png")
            
            # Plot F(a)
            plt.figure(figsize=(10, 6))
            for result in results:
                plt.plot(result['data']['a'], result['data']['F'], label=result['name'])
            plt.axhline(y=1.0, color='black', linestyle=':', label='F=1 (GR)')
            plt.xlabel('a')
            plt.ylabel('F')
            plt.title(f'F(a): Varying {param_name}')
            plt.legend()
            plt.grid(True, alpha=0.3)
            plt.tight_layout()
            plt.savefig(f'output/F_vs_{param_name}.png', dpi=150)
            plt.close()
            print(f"  ✓ Saved F_vs_{param_name}.png")
            
            # Plot H(a)
            plt.figure(figsize=(10, 6))
            for result in results:
                plt.plot(result['data']['a'], result['data']['H'], label=result['name'])
            plt.xlabel('a')
            plt.ylabel('H [1/Mpc]')
            plt.title(f'H(a): Varying {param_name}')
            plt.legend()
            plt.grid(True, alpha=0.3)
            plt.tight_layout()
            plt.savefig(f'output/H_vs_{param_name}.png', dpi=150)
            plt.close()
            print(f"  ✓ Saved H_vs_{param_name}.png")


def plot_stability_quantities():
    """Plot stability quantities for a single PRTOE configuration."""
    print("\n" + "="*60)
    print("Stability Quantities")
    print("="*60)
    
    base_prtoe = {
        'xi_prtoe': 1e-5,
        'zeta_prtoe': 0.1,
        'V0_prtoe': 0.5,
        'lambda_prtoe': 0.05,
        'm_prtoe': 0.05,
        'phi_0_prtoe': 1.0,
        'phi_c_prtoe': 0.0,
        'delta_phi_prtoe': 0.1,
    }
    
    bg = run_prtoe_cosmology(base_prtoe, 'PRTOE Stability')
    if bg is None:
        print("  ✗ Failed to run PRTOE")
        return
    
    prtoe_qty = extract_prtoe_quantities(bg)
    a = prtoe_qty['a']
    
    # Plot all stability quantities
    plt.figure(figsize=(14, 10))
    
    # meff^2
    plt.subplot(2, 2, 1)
    plt.plot(a, prtoe_qty['meff2'], label='m_eff^2')
    plt.axhline(y=0, color='red', linestyle='--', label='Stability threshold')
    plt.xlabel('a')
    plt.ylabel('m_eff^2')
    plt.title('Effective Mass Squared')
    plt.legend()
    plt.grid(True, alpha=0.3)
    
    # K
    plt.subplot(2, 2, 2)
    plt.plot(a, prtoe_qty['K'], label='K')
    plt.axhline(y=0, color='red', linestyle='--', label='Stability threshold')
    plt.xlabel('a')
    plt.ylabel('K')
    plt.title('Kinetic Coefficient')
    plt.legend()
    plt.grid(True, alpha=0.3)
    
    # Q
    plt.subplot(2, 2, 3)
    plt.plot(a, prtoe_qty['Q'], label='Q')
    plt.axhline(y=0, color='red', linestyle='--', label='Stability threshold')
    plt.xlabel('a')
    plt.ylabel('Q')
    plt.title('Gradient Stability Proxy')
    plt.legend()
    plt.grid(True, alpha=0.3)
    
    # c_s^2 and c_T^2
    plt.subplot(2, 2, 4)
    plt.plot(a, prtoe_qty['cs2'], label='c_s^2')
    plt.plot(a, prtoe_qty['cT2'], label='c_T^2')
    plt.axhline(y=0, color='red', linestyle='--', label='Stability threshold')
    plt.xlabel('a')
    plt.ylabel('Sound speeds squared')
    plt.title('Sound Speeds')
    plt.legend()
    plt.grid(True, alpha=0.3)
    
    plt.tight_layout()
    plt.savefig('output/prtoe_stability.png', dpi=150)
    plt.close()
    print("  ✓ Saved prtoe_stability.png")


def main():
    print("="*60)
    print("PRTOE Background Evolution Plotter")
    print("="*60)
    
    # Plot parameter variation
    plot_parameter_variation()
    
    # Plot stability quantities
    plot_stability_quantities()
    
    print("\n" + "="*60)
    print("Plotting Complete!")
    print("="*60)


if __name__ == '__main__':
    main()
