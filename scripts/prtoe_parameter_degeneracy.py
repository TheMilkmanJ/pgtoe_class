#!/usr/bin/env python3
"""
PRTOE Parameter Degeneracy Analysis
=====================================
Systematically varies PRTOE parameters and tracks effects on cosmological observables.
Identifies parameter degeneracies and constraints.
"""

import sys
import os
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from itertools import product

# Add the prtoe_class directory to the path BEFORE importing classy
sys.path.insert(0, '/home/themilkmanj/prtoe_class/python')

import classy

# Create output directory
os.makedirs('output', exist_ok=True)


def run_cosmology(params, name=None):
    """Run CLASS with given parameters and return background data."""
    cosmo = classy.Class()
    
    # Base LambdaCDM parameters
    base_params = {
        'Omega_cdm': 0.27,
        'Omega_b': 0.05,
        'h': 0.67,
        'Omega_Lambda': 0.68,
        'tau_reio': 0.0544,
        'n_s': 0.965,
        'A_s': 2.1e-9,
        'l_max_scalars': 2500,
        'P_k_max_h/Mpc': 10.0,
    }
    
    # Add PRTOE parameters
    base_params.update({'use_prtoe': 'yes'})
    base_params.update(params)
    
    cosmo.set(base_params)
    
    try:
        cosmo.compute()
        bg = cosmo.get_background()
        
        # Extract cosmological observables
        result = {
            'a': bg['a'],
            'H0': bg['H [1/Mpc]'][-1],  # H at a=1
            'H': bg['H [1/Mpc]'],
            'phi_final': bg.get('phi_prtoe', np.zeros_like(bg['a']))[-1],
            'F_final': bg.get('F_prtoe', np.ones_like(bg['a']))[-1],
            'rho_prtoe_final': bg.get('rho_prtoe', np.zeros_like(bg['a']))[-1],
            'rho_crit_final': bg['rho_crit [1/Mpc^2]'][-1],
            'Omega_prtoe': bg.get('rho_prtoe', np.zeros_like(bg['a']))[-1] / bg['rho_crit [1/Mpc^2]'][-1] if bg['rho_crit [1/Mpc^2]'][-1] > 0 else 0,
        }
        
        # Compute derived quantities
        result['Omega_m'] = base_params['Omega_cdm'] + base_params['Omega_b']
        result['Omega_Lambda'] = base_params['Omega_Lambda']
        
        return result
        
    except Exception as e:
        print(f"  ✗ {name if name else 'Run'} failed: {e}")
        return None


def compute_observables(result, params):
    """Compute derived cosmological observables from results."""
    observable_dict = {
        'H0': result['H0'],
        'Omega_prtoe': result['Omega_prtoe'],
        'phi_final': result['phi_final'],
        'F_final': result['F_final'],
        'rho_prtoe_frac': result['rho_prtoe_final'] / result['rho_crit_final'] if result['rho_crit_final'] > 0 else 0,
    }
    
    # Add parameter values
    for key, value in params.items():
        observable_dict[f'param_{key}'] = value
    
    return observable_dict


def parameter_scan():
    """Perform systematic parameter scan."""
    print("\n" + "="*60)
    print("PRTOE Parameter Degeneracy Analysis")
    print("="*60)
    
    # Define parameter grid
    param_grid = {
        'xi_prtoe': [1e-6, 5e-6, 1e-5, 5e-5],
        'zeta_prtoe': [0.01, 0.1, 0.5, 1.0],
        'V0_prtoe': [0.1, 0.5, 1.0],
        'lambda_prtoe': [0.01, 0.05, 0.1],
        'm_prtoe': [0.01, 0.05, 0.1],
    }
    
    # Create parameter combinations (single-parameter variation)
    base_params = {
        'xi_prtoe': 1e-5,
        'zeta_prtoe': 0.1,
        'V0_prtoe': 0.5,
        'lambda_prtoe': 0.05,
        'm_prtoe': 0.05,
        'phi_0_prtoe': 1.0,
        'phi_c_prtoe': 0.0,
        'delta_phi_prtoe': 0.1,
    }
    
    results = []
    
    # LambdaCDM reference
    print("\n1. Running LambdaCDM reference...")
    lcdm_result = run_cosmology({}, 'LambdaCDM')
    if lcdm_result:
        lcdm_obs = compute_observables(lcdm_result, {})
        lcdm_obs['name'] = 'LambdaCDM'
        results.append(lcdm_obs)
        print(f"  ✓ LambdaCDM: H0={lcdm_obs['H0']:.4f}")
    
    # Single parameter variations
    for param_name, param_values in param_grid.items():
        print(f"\n2. Varying {param_name}...")
        for value in param_values:
            params = base_params.copy()
            params[param_name] = value
            
            result = run_cosmology(params, f'{param_name}={value}')
            if result:
                obs = compute_observables(result, params)
                obs['name'] = f'{param_name}={value}'
                results.append(obs)
                print(f"  ✓ {param_name}={value}: H0={obs['H0']:.4f}, Omega_prtoe={obs['Omega_prtoe']:.6f}")
    
    # Create DataFrame for analysis
    df = pd.DataFrame(results)
    
    # Save to CSV
    df.to_csv('output/prtoe_parameter_scan.csv', index=False)
    print(f"\n✓ Saved parameter scan to output/prtoe_parameter_scan.csv")
    
    # Compute correlations
    print("\n3. Computing parameter correlations...")
    
    # Correlation matrix
    observable_cols = ['H0', 'Omega_prtoe', 'phi_final', 'F_final', 'rho_prtoe_frac']
    param_cols = [col for col in df.columns if col.startswith('param_')]
    
    # Create correlation matrix
    corr_df = df[observable_cols + param_cols]
    corr_matrix = corr_df.corr()
    
    # Save correlation matrix
    corr_matrix.to_csv('output/prtoe_correlation_matrix.csv')
    print(f"✓ Saved correlation matrix to output/prtoe_correlation_matrix.csv")
    
    # Plot correlation heatmap
    plt.figure(figsize=(12, 8))
    plt.matshow(corr_matrix, fignum=1)
    plt.xticks(range(len(corr_matrix.columns)), corr_matrix.columns, rotation=90)
    plt.yticks(range(len(corr_matrix.columns)), corr_matrix.columns)
    plt.colorbar()
    plt.title('PRTOE Parameter-Observable Correlation Matrix')
    plt.tight_layout()
    plt.savefig('output/prtoe_correlation_heatmap.png', dpi=150)
    plt.close()
    print(f"✓ Saved correlation heatmap to output/prtoe_correlation_heatmap.png")
    
    # Identify strong correlations
    print("\n4. Strong Correlations (|r| > 0.7):")
    for obs in observable_cols:
        for param in param_cols:
            corr_val = corr_matrix.loc[obs, param]
            if abs(corr_val) > 0.7:
                param_name = param.replace('param_', '')
                print(f"  {obs:20s} <-> {param_name:15s}: r = {corr_val:8.4f}")
    
    # Plot H0 vs each parameter
    print("\n5. Generating parameter-effect plots...")
    for obs in observable_cols:
        plt.figure(figsize=(10, 6))
        for param_name in param_grid.keys():
            subset = df[df['name'].str.startswith(param_name)]
            if len(subset) > 0:
                param_vals = subset[f'param_{param_name}']
                obs_vals = subset[obs]
                plt.plot(param_vals, obs_vals, 'o-', label=param_name)
        
        # Add LambdaCDM reference
        lcdm_val = df[df['name'] == 'LambdaCDM'][obs].values[0]
        plt.axhline(y=lcdm_val, color='black', linestyle='--', label='LambdaCDM')
        
        plt.xlabel('Parameter Value')
        plt.ylabel(obs)
        plt.title(f'{obs} vs PRTOE Parameters')
        plt.legend()
        plt.grid(True, alpha=0.3)
        plt.tight_layout()
        plt.savefig(f'output/prtoe_degeneracy_{obs}.png', dpi=150)
        plt.close()
        print(f"  ✓ Saved {obs} degeneracy plot")
    
    return df, corr_matrix


def two_parameter_scan():
    """Perform 2D parameter scan for selected parameter pairs."""
    print("\n" + "="*60)
    print("2D Parameter Scan (Identifying Degeneracies)")
    print("="*60)
    
    # Select parameter pairs to scan
    param_pairs = [
        ('xi_prtoe', 'zeta_prtoe'),
        ('xi_prtoe', 'V0_prtoe'),
        ('V0_prtoe', 'lambda_prtoe'),
        ('zeta_prtoe', 'V0_prtoe'),
    ]
    
    base_params = {
        'xi_prtoe': 1e-5,
        'zeta_prtoe': 0.1,
        'V0_prtoe': 0.5,
        'lambda_prtoe': 0.05,
        'm_prtoe': 0.05,
        'phi_0_prtoe': 1.0,
        'phi_c_prtoe': 0.0,
        'delta_phi_prtoe': 0.1,
    }
    
    for param1, param2 in param_pairs:
        print(f"\nScanning {param1} vs {param2}...")
        
        # Define scan ranges
        param1_values = np.logspace(
            np.log10(base_params[param1]) - 1, 
            np.log10(base_params[param1]) + 1, 
            5
        )
        param2_values = np.logspace(
            np.log10(base_params[param2]) - 1, 
            np.log10(base_params[param2]) + 1, 
            5
        )
        
        H0_grid = np.zeros((len(param1_values), len(param2_values)))
        Omega_prtoe_grid = np.zeros((len(param1_values), len(param2_values)))
        
        for i, p1_val in enumerate(param1_values):
            for j, p2_val in enumerate(param2_values):
                params = base_params.copy()
                params[param1] = p1_val
                params[param2] = p2_val
                
                result = run_cosmology(params, f'{param1}={p1_val:.2e}, {param2}={p2_val:.2e}')
                if result:
                    H0_grid[i, j] = result['H0']
                    Omega_prtoe_grid[i, j] = result['Omega_prtoe']
                    print(f"  {param1}={p1_val:.2e}, {param2}={p2_val:.2e}: H0={H0_grid[i,j]:.4f}")
        
        # Plot H0 contour
        plt.figure(figsize=(12, 5))
        
        plt.subplot(1, 2, 1)
        X, Y = np.meshgrid(param1_values, param2_values, indexing='ij')
        CS = plt.contourf(X, Y, H0_grid.T, levels=20, cmap='viridis')
        plt.colorbar(CS, label='H0 [1/Mpc]')
        plt.xscale('log')
        plt.yscale('log')
        plt.xlabel(param1)
        plt.ylabel(param2)
        plt.title(f'H0: {param1} vs {param2}')
        
        plt.subplot(1, 2, 2)
        CS = plt.contourf(X, Y, Omega_prtoe_grid.T, levels=20, cmap='viridis')
        plt.colorbar(CS, label='Omega_PRTOE')
        plt.xscale('log')
        plt.yscale('log')
        plt.xlabel(param1)
        plt.ylabel(param2)
        plt.title(f'Omega_PRTOE: {param1} vs {param2}')
        
        plt.tight_layout()
        plt.savefig(f'output/prtoe_2d_scan_{param1}_vs_{param2}.png', dpi=150)
        plt.close()
        print(f"  ✓ Saved 2D scan plot for {param1} vs {param2}")


def sensitivity_analysis():
    """Compute sensitivity of observables to parameter changes."""
    print("\n" + "="*60)
    print("Sensitivity Analysis")
    print("="*60)
    
    # Use results from parameter_scan
    try:
        df = pd.read_csv('output/prtoe_parameter_scan.csv')
    except FileNotFoundError:
        print("  ✗ Parameter scan not found. Run parameter_scan() first.")
        return
    
    # LambdaCDM reference
    lcdm = df[df['name'] == 'LambdaCDM'].iloc[0]
    
    # Compute percentage changes
    observables = ['H0', 'Omega_prtoe', 'phi_final', 'F_final']
    parameters = ['param_xi_prtoe', 'param_zeta_prtoe', 'param_V0_prtoe', 
                  'param_lambda_prtoe', 'param_m_prtoe']
    
    sensitivity = {}
    
    for obs in observables:
        lcdm_val = lcdm[obs]
        sensitivity[obs] = {}
        
        for param in parameters:
            param_name = param.replace('param_', '')
            # Find rows where this parameter is varied
            param_cols = [col for col in df.columns if col.startswith(f'param_{param_name}')]
            if param_cols:
                subset = df[df[param_cols[0]].notna()]
                if len(subset) > 1:
                    # Compute percentage change
                    pct_changes = []
                    for _, row in subset.iterrows():
                        if lcdm_val != 0:
                            pct_change = (row[obs] - lcdm_val) / lcdm_val * 100
                        else:
                            pct_change = 0
                        pct_changes.append(abs(pct_change))
                    
                    avg_pct_change = np.mean(pct_changes)
                    sensitivity[obs][param_name] = avg_pct_change
    
    # Create sensitivity matrix
    sensitivity_df = pd.DataFrame(sensitivity).T
    sensitivity_df.to_csv('output/prtoe_sensitivity.csv')
    print(f"✓ Saved sensitivity analysis to output/prtoe_sensitivity.csv")
    
    # Plot sensitivity heatmap
    plt.figure(figsize=(10, 6))
    plt.matshow(sensitivity_df, fignum=1, cmap='YlOrRd')
    plt.xticks(range(len(sensitivity_df.columns)), sensitivity_df.columns, rotation=45)
    plt.yticks(range(len(sensitivity_df.index)), sensitivity_df.index)
    plt.colorbar(label='Avg % Change')
    plt.title('PRTOE Observable Sensitivity to Parameters')
    plt.tight_layout()
    plt.savefig('output/prtoe_sensitivity_heatmap.png', dpi=150)
    plt.close()
    print(f"✓ Saved sensitivity heatmap to output/prtoe_sensitivity_heatmap.png")
    
    # Print sensitivity summary
    print("\nSensitivity Summary (Avg % Change from LambdaCDM):")
    print(sensitivity_df.round(2))
    
    # Identify most sensitive parameters
    print("\nMost Sensitive Parameters:")
    for obs in sensitivity_df.index:
        max_param = sensitivity_df.loc[obs].idxmax()
        max_val = sensitivity_df.loc[obs].max()
        print(f"  {obs:20s}: Most affected by {max_param:15s} ({max_val:6.2f}% avg change)")


def main():
    print("="*60)
    print("PRTOE Parameter Degeneracy Analysis")
    print("="*60)
    
    # Perform parameter scan
    df, corr_matrix = parameter_scan()
    
    # Perform 2D parameter scan
    two_parameter_scan()
    
    # Perform sensitivity analysis
    sensitivity_analysis()
    
    print("\n" + "="*60)
    print("Parameter Degeneracy Analysis Complete!")
    print("="*60)
    print("\nResults saved to output/ directory:")
    print("  - prtoe_parameter_scan.csv")
    print("  - prtoe_correlation_matrix.csv")
    print("  - prtoe_correlation_heatmap.png")
    print("  - prtoe_degeneracy_*.png (one per observable)")
    print("  - prtoe_2d_scan_*.png (parameter pair plots)")
    print("  - prtoe_sensitivity.csv")
    print("  - prtoe_sensitivity_heatmap.png")


if __name__ == '__main__':
    main()
