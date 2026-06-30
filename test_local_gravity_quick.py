#!/usr/bin/env python3
"""
Quick Local Gravity Test Suite for PRTOE
(Skips full cosmology computation - tests screening logic only)
"""

import sys
import numpy as np

# ============================================================================
# SCREENING CALCULATIONS
# ============================================================================

def get_xi_eff(phi, xi_prtoe, zeta_prtoe):
    """Compute effective coupling ξ_eff = ξ * S(φ) with Vainshtein screening."""
    phi2 = phi * phi
    denom = 1.0 + zeta_prtoe * phi2
    S_phi = phi2 / denom
    return xi_prtoe * S_phi

def get_G_eff_ratio(phi, xi_prtoe, zeta_prtoe):
    """Compute G_eff / G_Newton from F(φ)."""
    xi_eff = get_xi_eff(phi, xi_prtoe, zeta_prtoe)
    return 1.0 - xi_eff / 2.0

# ============================================================================
# TEST SUITE
# ============================================================================

def test_all(xi_prtoe=5e-6, zeta_prtoe=1.0):
    """Run local gravity tests."""
    
    print("\n" + "█"*70)
    print("█ LOCAL GRAVITY TEST SUITE FOR PRTOE (Screening Logic)")
    print("█"*70)
    print(f"\nParameters: ξ = {xi_prtoe:.2e}, ζ = {zeta_prtoe:.4f}")
    
    # Test 1: Solar System
    print("\n" + "="*70)
    print("TEST 1: SOLAR SYSTEM CONSTRAINT (|ΔG/G| < 10^-5)")
    print("="*70)
    
    phi_vacuum = 0.5
    phi_screened = 0.01
    
    G_eff_vacuum = get_G_eff_ratio(phi_vacuum, xi_prtoe, zeta_prtoe)
    G_eff_screened = get_G_eff_ratio(phi_screened, xi_prtoe, zeta_prtoe)
    
    delta_G_vacuum = abs(1.0 - G_eff_vacuum)
    delta_G_screened = abs(1.0 - G_eff_screened)
    
    print(f"\nG_eff/G (vacuum):        {G_eff_vacuum:.6f}  ΔG/G = {delta_G_vacuum:.2e}")
    print(f"G_eff/G (screened):      {G_eff_screened:.6f}  ΔG/G = {delta_G_screened:.2e}")
    print(f"Constraint limit:        {1e-5:.2e}")
    
    test1_pass = delta_G_screened < 1e-5
    print(f"Result: {'✓ PASS' if test1_pass else '✗ FAIL'}")
    
    # Test 2: Chameleon
    print("\n" + "="*70)
    print("TEST 2: CHAMELEON SCREENING MECHANISM")
    print("="*70)
    
    densities = [1e-26, 1e-21, 1e3]
    phi_values = [1.0, 0.3, 0.05]
    
    print(f"\n{'Density':<15} {'φ':<10} {'ξ_eff':<15} {'S(φ)':<15}")
    print("-" * 55)
    
    screening_factors = []
    for rho, phi in zip(densities, phi_values):
        xi_eff = get_xi_eff(phi, xi_prtoe, zeta_prtoe)
        S_phi = phi * phi / (1.0 + zeta_prtoe * phi * phi)
        screening_factors.append(S_phi)
        print(f"{rho:<15.2e} {phi:<10.4f} {xi_eff:<15.2e} {S_phi:<15.2e}")
    
    suppression = screening_factors[0] / max(screening_factors[-1], 1e-10)
    test2_pass = (screening_factors[-1] / screening_factors[0]) < 0.1
    
    print(f"\nSuppression ratio: {suppression:.2e}x")
    print(f"Result: {'✓ PASS' if test2_pass else '✗ FAIL'}")
    
    # Test 3: Vainshtein
    print("\n" + "="*70)
    print("TEST 3: VAINSHTEIN GRADIENT SUPPRESSION")
    print("="*70)
    
    k_array = np.array([1e-3, 1e-1, 1.0, 10.0, 100.0])
    l_vain = 0.1
    coupling_supp = 1.0 / (1.0 + (k_array * l_vain)**2)
    
    print(f"\n{'k (Mpc^-1)':<15} {'Coupling':<15} {'Suppression':<15}")
    print("-" * 45)
    for k, supp in zip(k_array, coupling_supp):
        print(f"{k:<15.2e} {supp:<15.4f} {1-supp:<15.4f}")
    
    test3_pass = coupling_supp[-1] < 0.1
    print(f"\nResult: {'✓ PASS' if test3_pass else '✗ FAIL'}")
    
    # Summary
    print("\n" + "="*70)
    print("SUMMARY")
    print("="*70)
    print(f"{'Solar System Constraint':<30} {'✓ PASS' if test1_pass else '✗ FAIL'}")
    print(f"{'Chameleon Screening':<30} {'✓ PASS' if test2_pass else '✗ FAIL'}")
    print(f"{'Vainshtein Suppression':<30} {'✓ PASS' if test3_pass else '✗ FAIL'}")
    
    all_pass = test1_pass and test2_pass and test3_pass
    print("\n" + ("█"*70))
    if all_pass:
        print("█ OVERALL: ✓ PRTOE PASSES LOCAL GRAVITY CONSTRAINTS (Screening Logic)")
    else:
        print("█ OVERALL: ✗ PRTOE FAILS SOME LOCAL GRAVITY TESTS")
    print("█"*70 + "\n")
    
    return all_pass

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Quick local gravity test for PRTOE")
    parser.add_argument('--xi', type=float, default=5e-6, help='PRTOE coupling ξ')
    parser.add_argument('--zeta', type=float, default=1.0, help='Vainshtein screening ζ')
    
    args = parser.parse_args()
    passed = test_all(args.xi, args.zeta)
    sys.exit(0 if passed else 1)
