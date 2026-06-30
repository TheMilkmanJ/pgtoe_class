# Local Gravity Test for PRTOE

## What is it?

A **validation test** to ensure PRTOE satisfies local gravity constraints:
- Solar system tests (perihelion precession of Mercury, etc.)
- Chameleon/Vainshtein screening effectiveness
- Constraint on fifth-force coupling in dense environments
- Ensures PRTOE doesn't predict "fifth-force" effects ruled out by experiments

## Why PRTOE Needs It

PRTOE has:
- **Non-minimal coupling**: F(φ) = 1 + ξ_eff * A(φ)
- **Screening**: S(φ) = φ²/(1 + ζ*φ²) (Vainshtein-like)
- **Modified gravity effects**: Changes to gravitational strength with scalar field

**Must verify**: These effects don't violate local tests where they're tightly constrained.

## Current PRTOE Implementation

✅ **Has screening** (Vainshtein parameter `zeta_prtoe`)
- Suppresses coupling at high field values
- Should keep local gravity safe

❓ **No explicit test** to validate this

## Test Design

### Test 1: Solar System Scale
**Concept**: Evaluate effective gravitational coupling `G_eff` at solar system density/scale

```
At solar system densities:
- Matter density: ρ ~ 1000 kg/m³ (typical star interior)
- Field value φ should be screened to small value
- G_eff ≈ G (General Relativity) ± tiny correction
- Constraint: |ΔG/G| < 10⁻⁵ (from experiments)
```

**Implementation**:
1. Evaluate field φ at solar system density
2. Compute xi_eff = xi * S(φ) where S = φ²/(1 + ζ*φ²)
3. Compute F(φ) = 1 + xi_eff * A(φ)
4. Compute G_eff/G from F value
5. Check: |ΔG/G| < 10⁻⁵?

### Test 2: Chameleon Mechanism
**Concept**: Field responds to local density

```
Low density (space):   φ_large → big coupling
High density (matter): φ_small → weak coupling (screening)
```

**Implementation**:
1. Run PRTOE with varying background matter densities
2. Track field value φ(ρ) as function of density
3. Verify: dφ/dρ < 0 (field suppressed in high density)
4. Verify screening effectiveness: S(φ_dense) < S(φ_vacuum)

### Test 3: Vainshtein Screening
**Concept**: High field gradient suppresses coupling

```
|∇φ| large → coupling suppressed even if φ not small
```

**Already implemented** via:
```c
double xi_screened = xi_eff * trans;  // trans depends on field derivatives
```

**Test**: Verify that beta-term (high-k coupling) is indeed screened at small scales.

## Quick Implementation Plan

### Phase 1: Simple validation (1-2 hrs)
```python
# test_local_gravity.py
import classy
from scipy.optimize import fsolve

params_prtoe = {..., 'xi_prtoe': 5e-6, 'zeta_prtoe': 1.0}
params_lcdm = {...}

M = classy.Class()
M.set(params_prtoe)
M.compute()

# Evaluate at solar system scale
rho_ss = 1e3  # kg/m³
phi_ss = compute_phi_at_density(rho_ss)  # Need helper
G_eff = compute_G_eff(phi_ss)

# Check: |G_eff - G| / G < 1e-5
deviation = abs(G_eff - 1.0)  # normalized
assert deviation < 1e-4, f"Solar system test failed: ΔG/G = {deviation}"
```

### Phase 2: Comprehensive validation (4-6 hrs)
- Multi-density scan
- Chameleon mechanism verification
- Vainshtein gradient effects
- Comparison with known solar system limits

## Expected Outcomes

### If PRTOE Passes ✓
- Strong publication support
- Shows PRTOE is observationally viable
- Strengthens credibility vs. other modified gravity theories

### If PRTOE Fails ✗
- Need to adjust screening parameters (ζ, β)
- Or modify activation function A(φ)
- Provides guidance for parameter tuning

## Status

**NOT YET IMPLEMENTED**

This should be added to Phase 5 Step 4 (guard consolidation) or Phase 5 Step 5 (full validation).

---

**Priority**: **MEDIUM** (publication requirement, but not critical for current ODE fix)
**Effort**: **~2-3 hours** for basic test


---

## Additional Constraint: Laboratory Tests (Future)

### Atomic-Scale Validation
PRTOE should also pass **lab tests** at atomic scales:
- **Fifth-force searches** (torsion balances, neutron interferometry)
- **Equivalence principle tests** (laser interferometry)
- **Gravitational inverse-square-law tests** (precision pendulums)

### Scaling Hierarchy
```
✓ Phase 1 (Now):       Local gravity (solar system) ~ 10^8 m
  Phase 2 (Next):      Bayesian evidence (cosmology fit)
  Phase 3 (Future):    Laboratory tests (atomic scales) ~ 10^-10 m
```

### Why Defer Laboratory Tests?
1. **Cosmological fit is primary goal** - PRTOE's strength is fitting cosmic data
2. **Screening should handle both scales** - Same Vainshtein mechanism works at all distances
3. **Sequential validation** - Prove cosmological viability first, then validate screening across scales

### If Lab Tests Fail (Later)
Would indicate:
- Screening parameters (ζ, β) need adjustment
- Possible need for additional short-range suppression
- Screening function S(φ) may need refinement

**But not a blocker** - PRTOE could still be viable as a cosmological model even if it requires additional mechanisms at atomic scales.

---

## Validation Roadmap (Recommended)

```
✓ Step 1: Code Structure       (DONE - Phase 5)
  Step 2: Local Gravity Test   (IN PROGRESS)
  Step 3: Bayesian Evidence    (NEXT - full inference run)
  Step 4: Lab Scale Tests      (FUTURE - if Bayesian evidence positive)
  Step 5: Publication          (Final - with all validations)
```

