#!/usr/bin/env python3
"""
PRTOE Stability Mapper
======================
Systematically scans parameter space and maps stable vs unstable regions.
"""

import numpy as np
import sys
import os
import itertools
import matplotlib.pyplot as plt
import argparse

# Robust path handling
try:
    script_dir = os.path.dirname(os.path.abspath(__file__))
except NameError:
    script_dir = os.getcwd()

sys.path.append(os.path.join(script_dir, '..', 'cosmic_dashboard', 'templates'))
from prtoe_dhost_checks_v2 import prtoe_dhost_consistency_check_v2


def generate_parameter_grid(quick_mode=False):
    """Task 3.1: Define parameter grid"""
    if quick_mode:
        # Reduced grid for quick testing
        xi_vals = np.logspace(-7, -5, 4)
        zeta_vals = np.linspace(0.01, 5.0, 4)
        phi_c_vals = np.linspace(-3.0, 3.0, 3)
        delta_phi_vals = np.linspace(0.05, 2.0, 3)
    else:
        # Full grid for proper mapping
        xi_vals = np.logspace(-7, -5, 8)
        zeta_vals = np.linspace(0.01, 5.0, 8)
        phi_c_vals = np.linspace(-3.0, 3.0, 7)
        delta_phi_vals = np.linspace(0.05, 2.0, 6)

    grid = list(itertools.product(xi_vals, zeta_vals, phi_c_vals, delta_phi_vals))
    print(f"Generated parameter grid with {len(grid)} combinations")
    return grid


def load_class_background_for_params(params):
    """
    Load background data from CLASS for given PRTOE parameters.
    """
    try:
        import classy
        
        # Set up parameters
        cosmo_params = {
            'use_prtoe': 'yes',
            'xi_prtoe': params['xi'],
            'zeta_prtoe': params['zeta'],
            'phi_0_prtoe': 0.0,
            'V0_prtoe': 1.0,
            'm_prtoe': 0.1,
            'lambda_prtoe': 1.0,
            'phi_c_prtoe': params['phi_c'],
            'delta_phi_prtoe': params['delta_phi'],
            'Omega_cdm': 0.27,
            'Omega_b': 0.05,
            'h': 0.67,
            'Omega_k': 0.0,
            'YHe': 0.245,   # Primordial helium fraction
            'output': 'mPk',
            'lensing': 'yes'
        }
        
        cosmo = classy.Class()
        cosmo.set(cosmo_params)
        cosmo.compute()
        
        # Extract background
        background = {}
        tau_array = np.linspace(0, cosmo.tau_max(), 1000)
        
        # Try to get PRTOE-specific quantities
        if hasattr(cosmo, 'phi_prtoe_of_tau'):
            background['phi'] = cosmo.phi_prtoe_of_tau(tau_array)
        else:
            background['phi'] = np.zeros(1000)
            
        if hasattr(cosmo, 'F_prtoe_of_tau'):
            background['F'] = cosmo.F_prtoe_of_tau(tau_array)
        else:
            background['F'] = np.ones(1000)
            
        if hasattr(cosmo, 'F_phi_prtoe_of_tau'):
            background['F_phi'] = cosmo.F_phi_prtoe_of_tau(tau_array)
        else:
            background['F_phi'] = np.zeros(1000)
            
        if hasattr(cosmo, 'F_phiphi_prtoe_of_tau'):
            background['F_phiphi'] = cosmo.F_phiphi_prtoe_of_tau(tau_array)
        else:
            background['F_phiphi'] = np.zeros(1000)
            
        if hasattr(cosmo, 'dphi_prtoe_of_tau'):
            background['phi_prime'] = cosmo.dphi_prtoe_of_tau(tau_array)
        else:
            background['phi_prime'] = np.zeros(1000)
            
        if hasattr(cosmo, 'ddphi_prtoe_of_tau'):
            background['ddphi'] = cosmo.ddphi_prtoe_of_tau(tau_array)
        else:
            background['ddphi'] = np.zeros(1000)
            
        background['a'] = cosmo.a_of_tau(tau_array)
        background['H'] = cosmo.Hubble_of_tau(tau_array)
        
        return background
        
    except ImportError:
        print("⚠️  CLASS module not available, using dummy background")
        return None


def create_dummy_background(phi_c, delta_phi):
    """Create a realistic dummy background for testing"""
    phi_vals = np.linspace(-4, 4, 600)
    
    # Create a smooth transition around phi_c
    u = (phi_vals - phi_c) / delta_phi
    activation = 0.5 * (1.0 + np.tanh(u))
    
    background = {
        'phi': phi_vals,
        'F': 1.0 + 0.05 * activation,
        'F_phi': 0.05 * (1.0 - np.tanh(u)**2) / delta_phi,
        'F_phiphi': -0.1 * np.tanh(u) * (1.0 - np.tanh(u)**2) / (delta_phi**2),
        'phi_prime': np.ones(600) * 0.005,
        'ddphi': np.zeros(600),
    }
    
    return background


def run_stability_sweep(grid, background_template=None, use_class=True):
    """Task 3.2: Run stability sweep across the grid"""
    results = []

    for i, (xi, zeta, phi_c, delta_phi) in enumerate(grid):
        params = {'xi': xi, 'zeta': zeta, 'phi_c': phi_c, 'delta_phi': delta_phi}
        
        # Try to load real CLASS background
        if background_template is None and use_class:
            background = load_class_background_for_params(params)
        else:
            background = None
            
        # If CLASS failed or not available, use dummy background
        if background is None:
            background = create_dummy_background(phi_c, delta_phi)
        
        result = prtoe_dhost_consistency_check_v2(
            background=background,
            xi=xi,
            zeta=zeta,
            verbose=False
        )

        results.append({
            'xi': xi,
            'zeta': zeta,
            'phi_c': phi_c,
            'delta_phi': delta_phi,
            'healthy': result.healthy,
            'min_K': result.min_K,
            'min_c_s2': result.min_c_s2,
            'distance_to_ghost': result.distance_to_ghost,
            'distance_to_gradient_instability': result.distance_to_gradient_instability
        })

        if (i + 1) % 200 == 0:
            print(f"  Processed {i+1}/{len(grid)} combinations...")

    return results


def plot_stability_maps(results, save_prefix="stability_map"):
    """Task 3.3: Generate stability plots"""
    # Convert to list of dicts for easier access
    results_list = results

    # Plot 1: Stability in (xi, zeta) plane (averaged over other parameters)
    plt.figure(figsize=(10, 8))
    
    # Simple 2D projection: fraction of healthy points
    xi_vals = [r['xi'] for r in results_list]
    zeta_vals = [r['zeta'] for r in results_list]
    xi_unique = sorted(set(xi_vals))
    zeta_unique = sorted(set(zeta_vals))
    
    stability_grid = np.zeros((len(zeta_unique), len(xi_unique)))
    
    for i, xi in enumerate(xi_unique):
        for j, zeta in enumerate(zeta_unique):
            mask = [r['xi'] == xi and r['zeta'] == zeta for r in results_list]
            if any(mask):
                healthy_points = [r['healthy'] for r, m in zip(results_list, mask) if m]
                stability_grid[j, i] = np.mean(healthy_points)
            else:
                stability_grid[j, i] = 0.0
    
    plt.imshow(stability_grid, extent=[min(xi_unique), max(xi_unique), 
                                       min(zeta_unique), max(zeta_unique)],
               aspect='auto', origin='lower', cmap='RdYlGn', vmin=0, vmax=1)
    plt.colorbar(label='Fraction of Stable Points')
    plt.xlabel(r'$\xi$')
    plt.ylabel(r'$\zeta$')
    plt.title(r'PRTOE Stability Map ($\xi$ vs $\zeta$)')
    plt.xscale('log')
    plt.savefig(f'{save_prefix}_xi_zeta.png', dpi=150, bbox_inches='tight')
    print(f"Saved: {save_prefix}_xi_zeta.png")
    plt.close()

    # Plot 2: Stability in (phi_c, delta_phi) plane (averaged over xi, zeta)
    plt.figure(figsize=(10, 8))
    
    phi_c_vals = [r['phi_c'] for r in results_list]
    delta_phi_vals = [r['delta_phi'] for r in results_list]
    phi_c_unique = sorted(set(phi_c_vals))
    delta_phi_unique = sorted(set(delta_phi_vals))
    
    stability_grid2 = np.zeros((len(delta_phi_unique), len(phi_c_unique)))
    
    for i, phi_c in enumerate(phi_c_unique):
        for j, delta_phi in enumerate(delta_phi_unique):
            mask = [r['phi_c'] == phi_c and r['delta_phi'] == delta_phi for r in results_list]
            if any(mask):
                healthy_points = [r['healthy'] for r, m in zip(results_list, mask) if m]
                stability_grid2[j, i] = np.mean(healthy_points)
            else:
                stability_grid2[j, i] = 0.0
    
    plt.imshow(stability_grid2, extent=[min(phi_c_unique), max(phi_c_unique), 
                                       min(delta_phi_unique), max(delta_phi_unique)],
               aspect='auto', origin='lower', cmap='RdYlGn', vmin=0, vmax=1)
    plt.colorbar(label='Fraction of Stable Points')
    plt.xlabel(r'$\phi_c$')
    plt.ylabel(r'$\Delta\phi$')
    plt.title(r'PRTOE Stability Map ($\phi_c$ vs $\Delta\phi$)')
    plt.savefig(f'{save_prefix}_phi_c_delta_phi.png', dpi=150, bbox_inches='tight')
    print(f"Saved: {save_prefix}_phi_c_delta_phi.png")
    plt.close()


def generate_safe_region_report(results, filename="docs/safe_region.md"):
    """Task 3.4: Generate safe region documentation"""
    results_list = results
    
    # Find the stable parameter ranges
    stable_results = [r for r in results_list if r['healthy']]
    
    if len(stable_results) > 0:
        xi_stable = [r['xi'] for r in stable_results]
        zeta_stable = [r['zeta'] for r in stable_results]
        phi_c_stable = [r['phi_c'] for r in stable_results]
        delta_phi_stable = [r['delta_phi'] for r in stable_results]
        
        xi_min, xi_max = min(xi_stable), max(xi_stable)
        zeta_min, zeta_max = min(zeta_stable), max(zeta_stable)
        phi_c_min, phi_c_max = min(phi_c_stable), max(phi_c_stable)
        delta_phi_min, delta_phi_max = min(delta_phi_stable), max(delta_phi_stable)
        
        # Also compute the fraction of stable points
        total_points = len(results)
        stable_fraction = len(stable_results) / total_points * 100
        
        report = f"""# PRTOE Safe Parameter Region

**Date**: 2026-06-29  
**Status**: Preliminary Analysis

## Summary
- Total parameter combinations tested: {total_points}
- Stable points: {len(stable_results)} ({stable_fraction:.1f}%)
- Unstable points: {total_points - len(stable_results)} ({100 - stable_fraction:.1f}%)

## Safe Parameter Region (Preliminary)

Based on the stability sweep, the following region appears physically viable:

- `xi_prtoe`     : {xi_min:.2e} to {xi_max:.2e}
- `zeta_prtoe`   : {zeta_min:.2f} to {zeta_max:.2f}
- `phi_c_prtoe`  : {phi_c_min:.2f} to {phi_c_max:.2f}
- `delta_phi_prtoe`: {delta_phi_min:.2f} to {delta_phi_max:.2f}

**Warning**: These boundaries are preliminary and based on the current sweep.  
They must be re-evaluated with full CLASS + PRTOE background output.

## Stability Metrics

The safe region is defined by:
- K (kinetic coefficient) > 0 (no ghost instability)
- c_s² (sound speed squared) > 0 (no gradient instability)
- c_T² = 1 (tensor speed preserved)

## Next Steps

1. Run with real CLASS background output for more accurate results
2. Expand the parameter grid for higher resolution
3. Validate with observational constraints
4. Update this document with quantitative results from real runs
"""
        
        # Ensure docs directory exists
        os.makedirs(os.path.dirname(filename), exist_ok=True)
        
        with open(filename, 'w') as f:
            f.write(report)
        
        print(f"Saved safe region report to {filename}")
        return report
    else:
        print("⚠️  No stable points found in the parameter sweep!")
        return "No stable points found."


def print_summary_statistics(results):
    """Print summary statistics for the stability sweep"""
    results_list = results
    
    total_points = len(results)
    stable_points = sum(1 for r in results_list if r['healthy'])
    stable_fraction = stable_points / total_points * 100
    
    print("\n" + "="*60)
    print(" STABILITY SWEEP SUMMARY")
    print("="*60)
    print(f"Total parameter combinations: {total_points}")
    print(f"Stable points: {stable_points} ({stable_fraction:.1f}%)")
    print(f"Unstable points: {total_points - stable_points} ({100 - stable_fraction:.1f}%)")
    
    if stable_points > 0:
        stable_results = [r for r in results_list if r['healthy']]
        print(f"\nStable parameter ranges:")
        print(f"  ξ: {min(r['xi'] for r in stable_results):.2e} to {max(r['xi'] for r in stable_results):.2e}")
        print(f"  ζ: {min(r['zeta'] for r in stable_results):.2f} to {max(r['zeta'] for r in stable_results):.2f}")
        print(f"  φ_c: {min(r['phi_c'] for r in stable_results):.2f} to {max(r['phi_c'] for r in stable_results):.2f}")
        print(f"  Δφ: {min(r['delta_phi'] for r in stable_results):.2f} to {max(r['delta_phi'] for r in stable_results):.2f}")
    
    # Find most stable and least stable points
    min_K_values = [r['min_K'] for r in results_list]
    min_c_s2_values = [r['min_c_s2'] for r in results_list]
    
    worst_K = min(min_K_values)
    worst_c_s2 = min(min_c_s2_values)
    
    print(f"\nWorst stability metrics:")
    print(f"  Minimum K: {worst_K:.4f}")
    print(f"  Minimum c_s²: {worst_c_s2:.4f}")


if __name__ == "__main__":
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='PRTOE Stability Mapper')
    parser.add_argument('--quick', action='store_true', help='Use reduced grid for fast testing')
    parser.add_argument('--output', type=str, default='stability_map', help='Output prefix for plots')
    parser.add_argument('--dummy', action='store_true', help='Use dummy background data instead of CLASS')
    args = parser.parse_args()
    
    print("Starting PRTOE Stability Mapping...")
    print(f"Mode: {'QUICK' if args.quick else 'FULL'}")

    grid = generate_parameter_grid(quick_mode=args.quick)
    results = run_stability_sweep(grid, use_class=not args.dummy)
    
    plot_stability_maps(results, save_prefix=args.output)
    
    print_summary_statistics(results)
    
    # Generate safe region report
    report = generate_safe_region_report(results)
    
    print("\nStability mapping complete.")
    print(f"Total points evaluated: {len(results)}")
    print("Plots and reports generated.")