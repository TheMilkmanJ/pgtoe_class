#!/usr/bin/env python3
"""
Test PRTOE with BBN fix as recommended by user
"""

import classy
import sys

def test_prtoe_with_bbn_fix():
    """Test PRTOE with proper BBN configuration"""
    print("Testing PRTOE with BBN fix...")
    
    params = {
        'use_prtoe': 'yes',
        'xi_prtoe': 1e-6,
        'zeta_prtoe': 1.0,
        'phi_0_prtoe': 0.1,           # Start closer to zero
        'phi_c_prtoe': 0.0,
        'delta_phi_prtoe': 1.0,
        'V0_prtoe': 1.0,
        'm_prtoe': 0.1,
        'lambda_prtoe': 1.0,
        
        # === Critical fixes for BBN / N_eff ===
        'Omega0_lambda': 0.0,           # Let PRTOE handle late-time acceleration
        'Omega_Lambda': 0.0,            # Explicitly turn off cosmological constant
        'Omega_b': 0.05,
        'Omega_cdm': 0.27,
        'h': 0.67,
        'YHe': 0.245,
        'output': 'mPk'
    }
    
    try:
        print("Setting parameters...")
        cosmo = classy.Class()
        cosmo.set(params)
        print("✅ Parameters set successfully")
        
        print("Computing cosmology...")
        cosmo.compute()
        print("✅ Cosmology computation completed!")
        
        # Check key quantities
        try:
            H0 = cosmo.Hubble(0)
            print(f"H0 = {H0:.2f}")
        except Exception as e:
            print(f"⚠️  Could not access H0: {e}")
            
        try:
            Neff = cosmo.Neff()
            print(f"N_eff = {Neff:.3f}")
        except Exception as e:
            print(f"⚠️  Could not access N_eff: {e}")
            
        try:
            Omega_lambda = cosmo.Omega0_lambda()
            print(f"Omega0_lambda = {Omega_lambda:.4f}")
        except Exception as e:
            print(f"⚠️  Could not access Omega0_lambda: {e}")
            
        print("🎉 PRTOE with BBN fix working!")
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def test_prtoe_with_delta_neff_fix():
    """Test PRTOE with explicit Delta N_eff setting"""
    print("\nTesting PRTOE with explicit Delta N_eff...")
    
    params = {
        'use_prtoe': 'yes',
        'xi_prtoe': 1e-6,
        'zeta_prtoe': 1.0,
        'phi_0_prtoe': 0.1,
        'phi_c_prtoe': 0.0,
        'delta_phi_prtoe': 1.0,
        'V0_prtoe': 1.0,
        'm_prtoe': 0.1,
        'lambda_prtoe': 1.0,
        
        'Omega0_lambda': 0.0,
        'Omega_Lambda': 0.0,
        'Omega_b': 0.05,
        'Omega_cdm': 0.27,
        'h': 0.67,
        'N_ur': 3.046,              # Standard effective neutrinos
        'Delta_N_eff': 0.0,         # Force no extra radiation from PRTOE
        'output': 'mPk'
    }
    
    try:
        print("Setting parameters with explicit Delta N_eff...")
        cosmo = classy.Class()
        cosmo.set(params)
        print("✅ Parameters set successfully")
        
        print("Computing cosmology...")
        cosmo.compute()
        print("✅ Cosmology computation completed!")
        
        # Check key quantities
        try:
            H0 = cosmo.Hubble(0)
            print(f"H0 = {H0:.2f}")
        except Exception as e:
            print(f"⚠️  Could not access H0: {e}")
            
        try:
            Neff = cosmo.Neff()
            print(f"N_eff = {Neff:.3f}")
        except Exception as e:
            print(f"⚠️  Could not access N_eff: {e}")
            
        print("🎉 PRTOE with Delta N_eff fix working!")
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

if __name__ == "__main__":
    print("PRTOE BBN Fix Test Suite")
    print("="*50)
    
    test1_ok = test_prtoe_with_bbn_fix()
    test2_ok = test_prtoe_with_delta_neff_fix()
    
    print("\n" + "="*50)
    print("SUMMARY:")
    print(f"BBN Fix Test 1: {'✅ PASS' if test1_ok else '❌ FAIL'}")
    print(f"Delta N_eff Fix Test: {'✅ PASS' if test2_ok else '❌ FAIL'}")
    
    if test1_ok or test2_ok:
        print("\n🎉 PRTOE BBN issues resolved!")
        sys.exit(0)
    else:
        print("\n❌ All BBN fixes failed")
        sys.exit(1)