#!/usr/bin/env python3
"""
PRTOE Basic Cosmology Test Script
==================================
Runs CLASS with PRTOE and compares basic background evolution to LambdaCDM.
"""

import sys
import os
import numpy as np

# Add the prtoe_class directory to the path BEFORE importing classy
sys.path.insert(0, '/home/themilkmanj/prtoe_class/python')

import classy
import matplotlib.pyplot as plt

# Create output directory
os.makedirs('output', exist_ok=True)

def run_cosmology(name, params):
    """Run CLASS with given parameters and return cosmology object."""
    print(f"  Running {name}...")
    cosmo = classy.Class()
    cosmo.set(params)
    try:
        cosmo.compute()
        print(f"  ✓ {name} computation successful")
        return cosmo
    except Exception as e:
        print(f"  ✗ {name} computation failed: {e}")
        return None

def get_background(cosmo):
    """Extract background quantities from cosmology object."""
    bg = cosmo.get_background()
    return {
        'a': bg['a'],
        'H': bg['H [1/Mpc]'],
        'rho_crit': bg['rho_crit [1/Mpc^2]'],
        'rho_m': bg.get('rho_cdm', np.zeros_like(bg['a'])) + bg.get('rho_b', np.zeros_like(bg['a'])),
        'rho_r': bg.get('rho_g', np.zeros_like(bg['a'])),
        'phi_prtoe': bg.get('phi_prtoe', np.zeros_like(bg['a'])),
        'F_prtoe': bg.get('F_prtoe', np.ones_like(bg['a'])),
        'rho_prtoe': bg.get('rho_prtoe', np.zeros_like(bg['a'])),
    }

def plot_comparison(lcdm_bg, prtoe_bg, output_prefix='prtoe_vs_lcdm'):
    """Plot comparison between LambdaCDM and PRTOE background evolution."""
    plt.figure(figsize=(12, 10))
    
    # Plot 1: H(a)
    plt.subplot(2, 2, 1)
    plt.plot(lcdm_bg['a'], lcdm_bg['H'], label='LambdaCDM', color='blue')
    plt.plot(prtoe_bg['a'], prtoe_bg['H'], label='PRTOE', color='red', linestyle='--')
    plt.xlabel('a')
    plt.ylabel('H [1/Mpc]')
    plt.title('Hubble Parameter')
    plt.legend()
    plt.grid(True, alpha=0.3)
    
    # Plot 2: phi(a)
    plt.subplot(2, 2, 2)
    plt.plot(prtoe_bg['a'], prtoe_bg['phi_prtoe'], label='PRTOE phi', color='green')
    plt.xlabel('a')
    plt.ylabel('phi')
    plt.title('Scalar Field Evolution')
    plt.grid(True, alpha=0.3)
    
    # Plot 3: F(a)
    plt.subplot(2, 2, 3)
    plt.plot(prtoe_bg['a'], prtoe_bg['F_prtoe'], label='PRTOE F', color='purple')
    plt.axhline(y=1.0, color='black', linestyle=':', label='F=1 (GR)')
    plt.xlabel('a')
    plt.ylabel('F')
    plt.title('Non-Minimal Coupling F(phi)')
    plt.legend()
    plt.grid(True, alpha=0.3)
    
    # Plot 4: Energy densities
    plt.subplot(2, 2, 4)
    plt.plot(lcdm_bg['a'], lcdm_bg['rho_m'], label='LambdaCDM Matter', color='orange')
    plt.plot(prtoe_bg['a'], prtoe_bg['rho_m'], label='PRTOE Matter', color='cyan', linestyle='--')
    plt.plot(prtoe_bg['a'], prtoe_bg['rho_prtoe'], label='PRTOE Field', color='magenta', linestyle='-.')
    plt.xlabel('a')
    plt.ylabel('Energy Density')
    plt.title('Energy Densities')
    plt.legend()
    plt.grid(True, alpha=0.3)
    
    plt.tight_layout()
    plt.savefig(f'output/{output_prefix}.png', dpi=150)
    plt.close()
    print(f"  ✓ Saved plots to output/{output_prefix}.png")


def main():
    print("="*60)
    print("PRTOE Basic Cosmology Test")
    print("="*60)
    
    # LambdaCDM parameters
    lcdm_params = {
        'Omega_cdm': 0.27,
        'Omega_b': 0.05,
        'h': 0.67,
        'Omega_Lambda': 0.68,
        'tau_reio': 0.0544,
        'n_s': 0.965,
        'A_s': 2.1e-9,
    }
    
    # PRTOE parameters (active)
    prtoe_params = lcdm_params.copy()
    prtoe_params.update({
        'use_prtoe': 'yes',
        'xi_prtoe': 1e-5,
        'zeta_prtoe': 0.1,
        'V0_prtoe': 0.5,
        'lambda_prtoe': 0.05,
        'm_prtoe': 0.05,
        'phi_0_prtoe': 1.0,
        'phi_c_prtoe': 0.0,
        'delta_phi_prtoe': 0.1,
    })
    
    # Run both cosmologies
    lcdm_cosmo = run_cosmology("LambdaCDM", lcdm_params)
    if lcdm_cosmo is None:
        print("  ✗ Aborting - LambdaCDM failed")
        return
    
    prtoe_cosmo = run_cosmology("PRTOE", prtoe_params)
    if prtoe_cosmo is None:
        print("  ✗ Aborting - PRTOE failed")
        return
    
    # Extract background quantities
    lcdm_bg = get_background(lcdm_cosmo)
    prtoe_bg = get_background(prtoe_cosmo)
    
    # Generate plots
    plot_comparison(lcdm_bg, prtoe_bg, 'prtoe_vs_lcdm')
    
    # Print some summary statistics
    print("\n" + "="*60)
    print("Summary Statistics")
    print("="*60)
    
    # H at a=1
    h_lcdm = lcdm_bg['H'][-1]
    h_prtoe = prtoe_bg['H'][-1]
    print(f"H0 (LambdaCDM): {h_lcdm:.4f}")
    print(f"H0 (PRTOE): {h_prtoe:.4f}")
    print(f"H0 difference: {abs(h_prtoe - h_lcdm):.4f} ({(abs(h_prtoe - h_lcdm)/h_lcdm*100):.2f}%)")
    
    # phi at a=1
    phi_final = prtoe_bg['phi_prtoe'][-1]
    print(f"\nphi (a=1): {phi_final:.6f}")
    
    # F at a=1
    F_final = prtoe_bg['F_prtoe'][-1]
    print(f"F (a=1): {F_final:.6f}")
    print(f"F - 1: {F_final - 1:.6f}")
    
    # PRTOE energy density at a=1
    rho_prtoe_final = prtoe_bg['rho_prtoe'][-1]
    rho_crit_final = prtoe_bg['rho_crit'][-1]
    omega_prtoe = rho_prtoe_final / rho_crit_final
    print(f"\nOmega_PRTOE (a=1): {omega_prtoe:.6f}")
    
    print("\n" + "="*60)
    print("Test Complete!")
    print("="*60)


if __name__ == '__main__':
    main()
