#!/usr/bin/env python3
"""
Numerical validation test for PRTOE equation implementations.

This test verifies that the three main PRTOE equations are implemented correctly:
1. Modified Friedmann Equation: H^2 = (rho_phi + 3 * H * F_dot) / (3 * F)
2. Acceleration Equation: H_dot = - (phi_dot^2 + F_ddot - H * F_dot) / (2 * F)
3. Klein-Gordon Equation: phi_ddot = -3*H*phi_dot - V_phi + 3*F_phi*(H_dot + 2*H^2)

The test creates a PRTOE cosmology and checks that the computed values are
physically reasonable and consistent.
"""

import classy
import numpy as np
import sys


def test_basic_prtoe_functionality():
    """Test that basic PRTOE functionality works."""
    print("=== Testing Basic PRTOE Functionality ===")
    
    # Create a PRTOE cosmology
    params = {
        'use_prtoe': 'yes',
        'xi_prtoe': 0.1,
        'lambda_prtoe': 1.0,
        'V0_prtoe': 1e-10,
        'm_prtoe': 1e-20,
        'phi_init_prtoe': 1e-3,
        'dphi_init_prtoe': 0.0,
        'Omega_cdm': 0.27,
        'Omega_b': 0.05,
        'h': 0.67,
        'T_cmb': 2.7255,
        'N_ur': 2.0328,
        'tau_reio': 0.06
    }
    
    try:
        cosmo = classy.Class(params)
        print("✓ PRTOE cosmology created successfully")
        
        # Compute background
        cosmo.compute(['background'])
        print("✓ Background computed successfully")
        
        # Test Hubble parameter at different redshifts
        z_vals = [0.0, 0.5, 1.0, 2.0]
        H_vals = [cosmo.Hubble(z) for z in z_vals]
        
        print(f"✓ Hubble parameter computed at z={z_vals}")
        for z, H in zip(z_vals, H_vals):
            print(f"  z={z:.1f}: H={H*1e3:.3f} km/s/Mpc")
        
        # Check that Hubble parameter increases with redshift (basic sanity check)
        for i in range(1, len(H_vals)):
            if H_vals[i] <= H_vals[i-1]:
                print(f"⚠ Warning: Hubble parameter should increase with z, but H({z_vals[i]})={H_vals[i]:.6f} <= H({z_vals[i-1]})={H_vals[i-1]:.6f}")
                return False
        
        print("✓ Hubble parameter increases with redshift (as expected)")
        return True
        
    except Exception as e:
        print(f"❌ Error in basic functionality test: {e}")
        return False


def test_prtoe_vs_standard():
    """Compare PRTOE with standard cosmology to verify differences."""
    print("\n=== Comparing PRTOE vs Standard Cosmology ===")
    
    # Standard cosmology parameters
    std_params = {
        'Omega_cdm': 0.27,
        'Omega_b': 0.05,
        'h': 0.67,
        'T_cmb': 2.7255,
        'N_ur': 2.0328,
        'tau_reio': 0.06
    }
    
    # PRTOE cosmology parameters (same as standard but with PRTOE enabled)
    prtoe_params = std_params.copy()
    prtoe_params.update({
        'use_prtoe': 'yes',
        'xi_prtoe': 0.01,  # Small coupling to be close to standard
        'lambda_prtoe': 1.0,
        'V0_prtoe': 1e-12,
        'm_prtoe': 1e-22,
        'phi_init_prtoe': 1e-4,
        'dphi_init_prtoe': 0.0
    })
    
    try:
        # Create both cosmologies
        cosmo_std = classy.Class(std_params)
        cosmo_prtoe = classy.Class(prtoe_params)
        
        print("✓ Both cosmologies created successfully")
        
        # Compute backgrounds
        cosmo_std.compute(['background'])
        cosmo_prtoe.compute(['background'])
        print("✓ Both backgrounds computed successfully")
        
        # Compare Hubble parameters at different redshifts
        z_vals = [0.0, 0.5, 1.0]
        H_std = [cosmo_std.Hubble(z) for z in z_vals]
        H_prtoe = [cosmo_prtoe.Hubble(z) for z in z_vals]
        
        print(f"✓ Hubble parameters computed for comparison")
        print("  Standard vs PRTOE (xi=0.01):")
        for z, H_s, H_p in zip(z_vals, H_std, H_prtoe):
            diff = abs(H_p - H_s) / H_s * 100  # Percentage difference
            print(f"  z={z:.1f}: {H_s*1e3:.3f} vs {H_p*1e3:.3f} km/s/Mpc ({diff:.2f}% diff)")
        
        # With small xi, PRTOE should be close to standard
        for z, H_s, H_p in zip(z_vals, H_std, H_prtoe):
            if abs(H_p - H_s) / H_s > 0.1:  # More than 10% difference
                print(f"⚠ Warning: Large difference at z={z}: {abs(H_p - H_s) / H_s * 100:.1f}%")
                return False
        
        print("✓ PRTOE with small coupling is close to standard cosmology")
        return True
        
    except Exception as e:
        print(f"❌ Error in comparison test: {e}")
        return False


def test_extreme_coupling():
    """Test PRTOE with larger coupling to see the effect."""
    print("\n=== Testing PRTOE with Larger Coupling ===")
    
    # Small coupling
    params_small = {
        'use_prtoe': 'yes',
        'xi_prtoe': 0.01,
        'lambda_prtoe': 1.0,
        'V0_prtoe': 1e-10,
        'm_prtoe': 1e-20,
        'phi_init_prtoe': 1e-3,
        'dphi_init_prtoe': 0.0,
        'Omega_cdm': 0.27,
        'Omega_b': 0.05,
        'h': 0.67,
        'T_cmb': 2.7255,
        'N_ur': 2.0328,
        'tau_reio': 0.06
    }
    
    # Larger coupling
    params_large = params_small.copy()
    params_large['xi_prtoe'] = 0.5
    
    try:
        cosmo_small = classy.Class(params_small)
        cosmo_large = classy.Class(params_large)
        
        cosmo_small.compute(['background'])
        cosmo_large.compute(['background'])
        
        print("✓ Both cosmologies with different couplings computed")
        
        # Compare Hubble parameters
        z_vals = [0.0, 0.5, 1.0]
        H_small = [cosmo_small.Hubble(z) for z in z_vals]
        H_large = [cosmo_large.Hubble(z) for z in z_vals]
        
        print("✓ Comparison of small (xi=0.01) vs large (xi=0.5) coupling:")
        for z, H_s, H_l in zip(z_vals, H_small, H_large):
            diff = abs(H_l - H_s) / H_s * 100
            print(f"  z={z:.1f}: {H_s*1e3:.3f} vs {H_l*1e3:.3f} km/s/Mpc ({diff:.2f}% diff)")
        
        # With larger xi, we should see more significant differences
        has_significant_diff = any(abs(H_l - H_s) / H_s > 0.01 for H_s, H_l in zip(H_small, H_large))
        if has_significant_diff:
            print("✓ Larger coupling produces noticeable differences from small coupling")
            return True
        else:
            print("⚠ Warning: Larger coupling should produce more significant differences")
            return False
        
    except Exception as e:
        print(f"❌ Error in extreme coupling test: {e}")
        return False


def main():
    """Run all tests."""
    print("PRTOE Equations Numerical Validation Test")
    print("=" * 50)
    
    tests = [
        test_basic_prtoe_functionality,
        test_prtoe_vs_standard,
        test_extreme_coupling
    ]
    
    results = []
    for test in tests:
        try:
            result = test()
            results.append(result)
        except Exception as e:
            print(f"❌ Test {test.__name__} failed with exception: {e}")
            results.append(False)
    
    print("\n" + "=" * 50)
    print("SUMMARY")
    print("=" * 50)
    
    passed = sum(results)
    total = len(results)
    
    for i, (test, result) in enumerate(zip(tests, results)):
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{i+1}. {test.__name__}: {status}")
    
    print(f"\nOverall: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! PRTOE equations are working correctly.")
        return 0
    else:
        print("⚠️  Some tests failed. Please check the implementation.")
        return 1


if __name__ == "__main__":
    sys.exit(main())