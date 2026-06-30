# PRTOE Numerical Validation Results

**Date**: 2026-06-29  
**Status**: In Progress

## Summary

| Test | Status | Notes |
|------|--------|-------|
| Null Limit (ξ→0, ζ→0) | ⏳ Pending | Must recover ΛCDM to high precision |
| DHOST Consistency | ⏳ Pending | Using real CLASS background output |
| Stability Mapping | ⏳ Pending | Sweep over ξ, ζ, φ_c, Δφ |
| Background Equation Check | ⏳ Pending | Verify Ḟ and F̈ terms |
| Tensor Speed | ✅ Complete | c_T² = 1 confirmed by construction |

## Task 2.2 – Null Limit Test

**Goal**: Confirm that PRTOE reduces to ΛCDM when ξ → 0 and ζ → 0.

**Current Result**:  
- Test infrastructure ready  
- Awaiting real CLASS background output with very small ξ

## Task 2.3 – Stability Sweep

**Parameters Tested**:
- ξ ∈ {1e-7, 5e-6, 1e-5}
- ζ ∈ {0.1, 1.0, 3.0}

**Current Status**: Script created. Needs to be run with real background data.

## Task 3.1-3.4 – Stability Mapping

**Parameter Grid**:
- ξ ∈ [1e-7, 1.2e-5] (8 points, log-spaced)
- ζ ∈ [0.01, 5.0] (8 points)
- φ_c ∈ [-3.0, 3.0] (7 points)
- Δφ ∈ [0.05, 2.0] (6 points)
- Total combinations: 8 × 8 × 7 × 6 = 2,688 points

**Status**: Stability mapper script created with configurable grid and real-data loading capability.

## Task 4.1-4.4 – Tensor Sector

**Status**: ✅ Complete

- **4.1**: Reviewed tensor handling in CLASS - standard CLASS tensor module used
- **4.2**: Added `check_tensor_speed()` function to DHOST validation module
- **4.3**: Integrated tensor monitor into DHOST validation
- **4.4**: Documentation section completed

**Result**: Tensor speed c_T² = 1 confirmed by construction in DHOST Class Ia framework.

## Implementation Notes

### Background Equations Status
- ✅ Friedmann equation: Implemented with quadratic solver including F_dot terms
- ✅ Klein-Gordon equation: Full curvature coupling with proper conformal time conversion
- ✅ Acceleration equation: Includes F_ddot terms with circularity resolved
- ✅ F_dot and F_ddot: Computed and stored in background vector
- ✅ Stability quantities: K, Q, m_eff² computed and monitored

### Parameter Reading
- ✅ `use_prtoe` flag properly read from input
- ✅ All PRTOE parameters (ξ, ζ, φ_c, Δφ, V0, m, λ, φ₀) properly read
- ✅ Parameter validation with stability bounds (ξ ∈ [1e-7, 1.2e-5])

### Validation Scripts
- ✅ `prtoe_dhost_checks_v2.py`: Enhanced with tensor speed check
- ✅ `run_prtoe_validation.py`: Created with real CLASS data loading
- ✅ `stability_mapper.py`: Created with configurable grid and reporting
- ✅ Safe region documentation: Automatic generation

## How to Use This Package

1. **Run validation tests**:
   ```bash
   python scripts/run_prtoe_validation.py
   ```

2. **Run stability mapping (quick mode)**:
   ```bash
   python scripts/stability_mapper.py --quick
   ```

3. **Run stability mapping (full mode)**:
   ```bash
   python scripts/stability_mapper.py
   ```

4. **Check results**:
   - Validation results printed to console
   - Stability maps saved as PNG files
   - Safe region report saved to `docs/safe_region.md`

## Next Actions

1. ✅ Connect validation scripts to real CLASS output
2. ⏳ Run null limit test with ξ = 1e-10 using real CLASS background
3. ⏳ Expand stability sweep with real CLASS data
4. ⏳ Update this document with quantitative results
5. ⏳ Test with actual PRTOE runs and verify numerical stability

## Known Issues

- CLASS integration methods may need adjustment for PRTOE background
- Some background quantities may not be accessible through standard CLASS methods
- File locking issue between Real-Time Monitor and PolyChord (separate issue)

## Files Modified/Created

### C Files Modified:
- `source/background.c`: Cleaned PRTOE implementation, fixed circular dependencies
- `source/input.c`: Parameter reading already implemented

### Python Files Created/Modified:
- `cosmic_dashboard/templates/prtoe_dhost_checks_v2.py`: Added tensor speed check
- `scripts/run_prtoe_validation.py`: Created validation runner
- `scripts/stability_mapper.py`: Created stability mapping tool
- `docs/VALIDATION_RESULTS.md`: Created validation documentation

### New Background Indices:
- `index_bg_F_dot_prtoe`: dF/dt
- `index_bg_F_ddot_prtoe`: d²F/dt²
- `index_bg_K_prtoe`: Kinetic coefficient K
- `index_bg_cT2_prtoe`: Tensor speed squared

## Verification Checklist

- [x] PRTOE activation flag properly read
- [x] Background indices allocated
- [x] F_dot and F_ddot computed
- [x] Friedmann equation includes F_dot terms
- [x] KG equation uses full curvature coupling
- [x] H_dot equation includes F_ddot terms
- [x] Stability quantities computed
- [x] Tensor speed diagnostic implemented
- [x] Validation scripts created
- [x] Stability mapper created
- [ ] Real CLASS integration tested
- [ ] Null limit verified
- [ ] Full parameter sweep completed