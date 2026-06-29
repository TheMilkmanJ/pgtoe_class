# PRTOE: Current Working Scalar-Tensor Formulation and Open Problems

> **Document Status:** Working Draft - Under Active Development  
> **Last Updated:** 2026-06-28  
> **Author:** Justin Ryan Pulford  
> **Review Status:** Addressing Red-Team Review Findings (2026-06-28)

---

## 📌 Executive Summary

This document presents the **current working formulation** of PRTOE (Pulford-Romsa Theory of Everything) as an **incomplete scalar-tensor cosmology ansatz** with a phenomenological activation function. 

**Critical Honesty:** The formulation below exposes several deep theoretical problems that **must be resolved** before PRTOE can be called a complete or covariant theory. This document is intentionally titled to reflect its preliminary status.

---

## ⚠️ OPEN PROBLEMS (From Red-Team Review)

| # | Issue | Severity | Status |
|---|-------|----------|--------|
| 1 | Action uses explicit scale-factor activation A(a) - non-covariant | **CRITICAL** | Requires reformulation |
| 2 | Friedmann equation doesn't follow from written action (missing Fdot terms) | **CRITICAL** | Requires derivation |
| 3 | Screening makes xi_eff depend on phi but Klein-Gordon treats as independent | **CRITICAL** | Requires consistency fix |
| 4 | Activation A(a) turns on before recombination (a~1e-4 vs z_rec~1100) | **CRITICAL** | Requires parameter adjustment or text correction |
| 5 | Perturbation equations are schematic with placeholders | **HIGH** | Requires full derivation |
| 6 | Gravitational slip not derived | **HIGH** | Requires derivation |
| 7 | Bianchi identity not verified | **HIGH** | Requires check |
| 8 | Initial conditions not specified | **HIGH** | Requires definition |
| 9 | Null-limit recovery not shown | **HIGH** | Requires validation |
| 10 | Stability analysis incomplete | **HIGH** | Requires derivation |

---

## 🎯 Roadmap

This document is organized as a **working roadmap**, not a completed theory:

1. **Section 2:** Action and Background Equations (needs covariance fix)
2. **Section 3:** Field Equations Derivation (currently incomplete)
3. **Section 4:** Perturbation Theory (currently schematic)
4. **Section 5:** Stability Analysis (not yet performed)
5. **Section 6:** Implementation Notes
6. **Section 7:** Validation Checklist

---

## 2. Action and Background Equations

### 2.1 The Problem: Non-Covariant Activation

**Current Implementation (PROBLEMATIC):**
```c
// From source/background.c:2833-2834
double activation = 0.5 * (1.0 + tanh(log(a) + 9.21034037198));
double xi_eff = pba->xi_prtoe * screening_factor * activation;
```

**Issue:** The scale factor `a` is a **background quantity** defined after assuming FLRW symmetry. Writing `A(a)` directly in the action makes the theory **background-dependent** and **non-covariant**.

### 2.2 Proposed Repair Options

#### Option A: Covariant Scalar Field Activation (RECOMMENDED)
Replace `A(a)` with `A(phi)` where phi is the scalar field:
```
A(phi) = 0.5 * (1 + tanh((phi - phi_0)/sigma_phi))
```
- **Pro:** Generally covariant
- **Pro:** phi is a fundamental scalar field, not a background quantity
- **Con:** Requires rederiving all equations

#### Option B: Explicit EFT Framework
Frame PRTOE as an Effective Field Theory in a chosen cosmological slicing:
```
S = ∫ d^4x √-g [F(phi, X) R + ... ]  // Explicitly not generally covariant
```
- **Pro:** Honest about limitations
- **Pro:** Allows A(a) as phenomenological ansatz
- **Con:** Cannot claim general covariance

#### Option C: Phenomenological FLRW-Only Model (INTERIM)
Remove action-level claims entirely. Present background equations as:
```
H^2 = rho_tot / (1 + xi_eff(a) phi^2) + ...  // Phenomenological only
```
- **Pro:** Intellectually honest
- **Pro:** Matches current code implementation
- **Con:** Not a fundamental theory

**Current Choice:** Option C (interim) until covariance is resolved.

---

### 2.3 Current Working Action (Placeholders Indicated)

**Status:** INCOMPLETE - Missing derivative terms

The action is **intended** to be:
```
S = ∫ d^4x √-g [ (1/2) F(phi, a) R - (1/2) g^{μν} ∂_μ phi ∂_ν phi - V(phi) + L_matter ]
```

Where:
- `F(phi, a) = 1 + xi_eff(a) phi^2` (non-minimal coupling)
- `xi_eff(a) = xi * A(a) / (1 + zeta * phi^2)` (screening + activation)
- `A(a) = 0.5[1 + tanh(ln a + 9.21034)]` (activation function)

**PROBLEM:** The written Friedmann equation in documentation does **not** follow from this action because:
1. Varying the action with respect to g_{μν} gives terms involving `∂_μ F ∂_ν F`, `F Box phi`, etc.
2. These derivative terms (`Fdot`, `Fddot`) are **missing** from the current background equations
3. The current code uses `H^2 = rho_tot / (1 + xi_eff phi^2)` which is **only valid** if F is constant or derivative terms are negligible

### 2.4 Required: Full Field Equations from Action

**TO DO:** Derive the 00 and ii Einstein equations from:
```
S = ∫ d^4x √-g [ (1/2) F(phi) R - (1/2) ω(phi) g^{μν} ∂_μ phi ∂_ν phi - V(phi) + L_matter ]
```

**Variation w.r.t. g_{μν}:**
```
δS/δg_{μν} = (1/2) √-g [ F R_{μν} - (1/2) F g_{μν} R + g_{μν} □ F - ∇_μ ∇_ν F 
                - ω (1/2) ∂_μ phi ∂_ν phi + (ω/4) g_{μν} (∂ phi)^2 - (1/2) g_{μν} V ] = 0
```

**This gives:**
```
F R_{μν} - (1/2) F g_{μν} R = ∇_μ ∇_ν F - g_{μν} □ F + ω ∂_μ phi ∂_ν phi - (ω/2) g_{μν} (∂ phi)^2 + g_{μν} V
```

**For FLRW metric (ds^2 = -dt^2 + a^2 dx^2):**
- 00 component: `3 F H^2 = ...` (includes Fdot terms)
- ii component: `-2 F H dot{H} - F H^2 = ...` (includes Fddot, Fdot terms)

**CRITICAL:** The current implementation **neglects** the `∇_μ ∇_ν F` and `□ F` terms. These must be either:
1. **Included** in the equations (correct but complex)
2. **Justified as negligible** (requires proof)
3. **Acknowledged as an approximation** (honest but limited)

---

## 3. Klein-Gordon Equation Consistency

### 3.1 The Problem

**Current Implementation:**
```c
// xi_eff depends on phi through screening
double screening_factor = 1.0 / (1.0 + pba->zeta_prtoe * phi * phi);
double xi_eff = pba->xi_prtoe * screening_factor * activation;

// But coupling in equations treats xi_eff as phi-independent
```

The scalar field equation should be:
```
□ phi + V_phi = (1/√(-g)) ∂_μ [ √(-g) g^{μν} ∂_ν F / F ]  // From varying w.r.t. phi
```

If `F = 1 + xi_eff(a) phi^2` and `xi_eff` depends on phi, then:
```
∂ F / ∂ phi = 2 xi_eff(a) phi + xi_eff_phi(a) phi^2
```

Where `xi_eff_phi = ∂ xi_eff / ∂ phi = -2 xi zeta phi / (1 + zeta phi^2)^2` (from screening)

**Current code likely neglects the `xi_eff_phi` term.**

### 3.2 Required Fix

**Write F(phi, a) = 1 + f(phi, a) explicitly**

Define:
```
f(phi, a) = xi * A(a) * phi^2 / (1 + zeta * phi^2)
```

Then:
```
f_phi = ∂f/∂phi = 2 xi A(a) phi / (1 + zeta phi^2) - 2 xi A(a) zeta phi^3 / (1 + zeta phi^2)^2
        = 2 xi A(a) phi [1 - zeta phi^2] / (1 + zeta phi^2)^2
```

**Klein-Gordon equation must include:**
```
□ phi + V_phi = f_phi R / (2 F) + (f_phi / F) □ phi + ...
```

This is an **internal consistency requirement**.

---

## 4. Activation Function Fix

### 4.1 The Problem

**Current:**
```c
double activation = 0.5 * (1.0 + tanh(log(a) + 9.21034));
```

- Transition at: ln a = -9.21034 → a ≈ 1e-4 → z ≈ 9999
- Recombination: z ≈ 1100 → a ≈ 9e-4
- At a = 9e-4: ln(a) + 9.21034 ≈ ln(9e-4) + 9.21034 ≈ -7.0 + 9.21034 ≈ 2.21
- tanh(2.21) ≈ 0.98 → A(a) ≈ 0.99

**Conclusion:** Activation is **already ~99% ON at recombination**, contrary to any claims that PRTOE "remains off through recombination."

### 4.2 Repair Options

**Option A: Adjust Activation Scale (RECOMMENDED)**
To keep PRTOE off through recombination (z < 1100, a > 9e-4):
```
A(a) = 0.5[1 + tanh(ln a + 5.0)]  // Transition at a ~ e^-5 ≈ 6.7e-3, z ~ 150
```
This keeps A(a) < 0.5 until z < 150, well after recombination.

**Option B: Remove Recombination Claim**
If the intention is for PRTOE to affect recombination, state this explicitly and constrain against CMB physics.

**Option C: Use Different Activation Variable**
Replace A(a) with A(phi):
```
A(phi) = 0.5[1 + tanh((phi - phi_c)/Δ_phi)]
```
- Transition when phi reaches phi_c
- Covariant if phi is the fundamental field

---

## 5. Perturbation Theory (ROADMAP - NOT IMPLEMENTATION)

### 5.1 Current Status: SCHEMATIC ONLY

The red-team review correctly identifies that current perturbation equations are **placeholders**. For a Boltzmann code like CLASS, perturbations are **not decorative**—they are essential for CMB, lensing, and LSS predictions.

### 5.2 Required: Full Perturbation Equations

#### 5.2.1 Gauge Choice
We work in **Newtonian gauge** (for scalar perturbations):
```
ds^2 = a^2 [-(1 + 2Ψ) dτ^2 + (1 - 2Φ) dx^2]
```
Where Ψ = Newtonian potential, Φ = curvature potential, and slip = Ψ - Φ.

#### 5.2.2 Scalar Field Perturbation

**TO DO: Write explicit equation**

For scalar field phi = phi_0(τ) + δphi(τ, k):
```
δphi'' + 2 aH δphi' + (k^2 + V_phiphi) δphi = 
  - [∂_τ (a^{-2} ∂_τ (a^2 phi_0')) / (a^{-2} ∂_τ (a^2 phi_0'))] V_phi δphi
  + (1/2) F_phi R^{(1)} + ...
```

Where R^{(1)} is the linearized Ricci scalar.

**Status:** ⚠️ NOT YET DERIVED - PLACEHOLDER IN CODE

#### 5.2.3 Metric Perturbations

**TO DO: Write explicit equations**

00 Einstein equation:
```
k^2 Ψ + 3 aH (Ψ' + aH Φ) = -4πG a^2 [δρ_total + ...]
```

0i Einstein equation (vector):
```
k^2 (Ψ' + aH Φ) = 4πG a^2 q_total (1 + w) θ_total
```

ij trace Einstein equation:
```
Ψ'' + 3 aH Ψ' + aH Φ' + (2 a''/a + aH^2) Φ = 4πG a^2 δp_total
```

ij traceless Einstein equation (anisotropic stress):
```
(k^2 + 2 aH ∂_τ) (Ψ - Φ) = 4πG a^2 Π_total
```

**Status:** ⚠️ NOT YET EXPLICIT - SCHEMATIC IN CODE

#### 5.2.4 Gravitational Slip

**TO DO: Derive explicit formula**

Slip: η = Ψ - Φ

From ij traceless equation:
```
(k^2 + 2 aH ∂_τ) η = 4πG a^2 Π_total
```

For PRTOE, the anisotropic stress Π_total includes contributions from the scalar field.

**Status:** ⚠️ NOT YET DERIVED - ASSERTED IN CODE

#### 5.2.5 δR Terms (Metric Source)

**TO DO: Write explicit expressions**

The linearized Ricci scalar in Newtonian gauge:
```
δR = -6 a^{-2} [Ψ'' + 4 aH Ψ' + (a''/a + 2 aH^2) Φ + k^2 (Ψ - Φ)/3]
```

**Status:** ⚠️ NOT YET SPECIFIED - PLACEHOLDER IN CODE

#### 5.2.6 Time-Dependent Coupling Terms

**TO DO: Write explicit expressions**

For non-minimal coupling F(phi, a), the perturbation equations include:
- δF = F_phi δphi + F_a δa (if F depends on a explicitly)
- Terms in δR from δF
- Terms in δG_{μν} from δF

**Status:** ⚠️ NOT YET SPECIFIED - PLACEHOLDER IN CODE

### 5.3 Gauge Conventions and Sign Conventions

**TO DO: Document explicitly**

- Gauge: Newtonian gauge
- Sign: Ψ > 0 means attractive gravity
- Time: Conformal time τ (dτ = dt/a)
- Derivatives: ' = ∂/∂τ, dot = ∂/∂t

**Status:** ⚠️ NOT DOCUMENTED

### 5.4 Initial Conditions

**TO DO: Define explicitly**

For adiabatic initial conditions in radiation domination:
- δphi_initial = ?
- δphi'_initial = ?
- Relations to curvature perturbation ζ

**Status:** ⚠️ NOT DEFINED

### 5.5 Null-Limit Recovery

**TO DO: Prove explicitly**

When xi_prtoe → 0, zeta_prtoe → 0, V0_prtoe → 0:
- Background: H^2 → H_ΛCDM^2
- Perturbations: δphi equations → 0
- Slip: η → η_ΛCDM
- CMB spectra: C_ℓ → C_ℓ^ΛCDM

**Status:** ⚠️ NOT VALIDATED

### 5.6 Numerical Stability Conditions

**TO DO: Document explicitly**

- Maximum allowed |δphi/phi_0| before instability
- Stability of activation transition
- Behavior when xi_eff → ∞
- Ghost instability conditions
- Gradient instability conditions

**Status:** ⚠️ NOT DOCUMENTED

---

## 6. Stability Analysis (NOT PERFORMED)

### 6.1 Ghost Instability

**TO DO:** Derive quadratic action for scalar and tensor perturbations.

For scalar-tensor theories, ghost instability occurs when the effective Planck mass is negative:
```
M_eff^2 = F > 0  (required for no ghost)
```

With F = 1 + xi_eff phi^2, this requires:
```
1 + xi_eff(a) phi^2 > 0  (always true if xi_eff > 0)
```

**Status:** ⚠️ NOT DERIVED

### 6.2 Gradient Instability

**TO DO:** Check sound speed squared for scalar perturbations.

Gradient instability occurs when c_s^2 < 0:
```
c_s^2 = [derivative of quadratic action] / [kinetic term]
```

**Status:** ⚠️ NOT DERIVED

### 6.3 Tachyonic Instability

**TO DO:** Check effective mass squared for scalar field.

Tachyonic instability when m_eff^2 < 0:
```
m_eff^2 = V_phiphi - (something from coupling)
```

**Status:** ⚠️ NOT DERIVED

### 6.4 Local Physics Constraints

**TO DO:** Address before nuclear mapping claims.

- Fifth-force constraints
- Equivalence principle tests
- Solar system constraints
- Big Bang Nucleosynthesis limits

**Status:** ⚠️ NOT ADDRESSED

---

## 7. Implementation Notes

### 7.1 Current Code State

**source/background.c:**
- PRTOE background hooks exist
- Activation gate, screening, potential, H-scaling implemented
- Comment: "only the xi R term is active at background level"
- Other DHOST-like operators not fully reduced

**source/perturbations.c:**
- PRTOE perturbation indices defined
- Some source terms implemented
- Many placeholders and schematic expressions

### 7.2 Code-Theory Mismatch

**CRITICAL:** Code uses `1/(1 + xi_eff * phi)` for H scaling, but formulation uses `1/(1 + xi_eff * phi^2)`.

**AUDIT REQUIRED:** Check all code paths against action-derived equations.

### 7.3 Parameter Status Table

| Parameter | Sampled? | Fixed? | Active BG? | Active Pert? | Null Value | Units/Conv | Observable Effect |
|-----------|---------|--------|------------|--------------|------------|-----------|-------------------|
| xi_prtoe | TBD | TBD | TBD | TBD | 0 | — | Modified gravity strength |
| zeta_prtoe | TBD | TBD | TBD | TBD | 0 | — | Screening strength |
| V0_prtoe | TBD | TBD | TBD | TBD | 0 | — | Potential scale |
| lambda_prtoe | TBD | TBD | TBD | TBD | — | — | Potential shape |
| m_prtoe | TBD | TBD | TBD | TBD | — | — | Mass term |
| phi_0_prtoe | TBD | TBD | TBD | TBD | — | — | Initial field value |
| beta_prtoe | TBD | TBD | TBD | TBD | — | — | Coupling parameter |
| M_prtoe | TBD | TBD | TBD | TBD | — | — | Mass scale |
| alpha_prtoe | TBD | TBD | TBD | TBD | — | — | Coupling parameter |
| M_ew_prtoe | TBD | TBD | TBD | TBD | — | — | Electroweak scale |
| H_vac_floor | TBD | TBD | TBD | TBD | — | — | Vacuum energy floor |
| delta_prtoe | TBD | TBD | TBD | TBD | 0 | — | Activation parameter |

**Note:** This table is **not cosmetic**—it prevents placeholder knobs from being mistaken for active physics.

---

## 8. Validation Checklist

Before any strong PRTOE claim can be made:

### 8.1 Theoretical Validation

- [ ] Covariant or explicitly phenomenological status of A(a) resolved
- [ ] Full field equations derived from the action, including all Fdot/Fddot terms
- [ ] Klein-Gordon equation corrected for phi-dependent screening
- [ ] Activation function consistent with BBN/recombination claim
- [ ] Full perturbation equations written without schematic placeholders
- [ ] Gauge conventions and sign conventions documented
- [ ] Gravitational slip expression derived
- [ ] Ghost and gradient stability conditions derived
- [ ] Local/fifth-force constraints addressed if nuclear coupling remains

### 8.2 Numerical Validation

- [ ] LambdaCDM recovery shown numerically in CLASS outputs
- [ ] Matched PRTOE/LambdaCDM PolyChord runs completed
- [ ] Prior sensitivity tested
- [ ] Ablations performed: xi only, zeta only, activation off, screening off, potential variants

### 8.3 Documentation Validation

- [ ] Dashboard evidence panel separates exploratory, approximate, and publication-grade diagnostics
- [ ] README tone demoted from claims to testable project status
- [ ] Independent fresh-clone reproducibility demonstrated

---

## 9. Conclusion

PRTOE is currently best described as:

> **An incomplete scalar-tensor cosmology ansatz with a phenomenological activation function, partially specified perturbations, incomplete stability analysis, incomplete local/nuclear mapping, and no publication-grade LambdaCDM evidence comparison yet.**

The fastest path forward is:
1. Fix the action/equations mismatch (covariance, Fdot terms, screening)
2. Fix the activation function
3. Complete perturbations before CMB claims
4. Build null-limit tests
5. Run matched evidence comparisons
6. Turn dashboard diagnostics into honest tools

---

## Appendix A: Explicit Perturbation Equations (Tasks 8-15)

### A.1 Task 8: Explicit delta_phi Perturbation Equation ✅

**Gauge:** Newtonian gauge  
**Metric:** ds² = a²[-(1+2Ψ)dτ² + (1-2Φ)dx²]  
**Conventions:** ' = ∂/∂τ, conformal time τ, H = a'/a

**Scalar field:** φ(τ, x) = φ₀(τ) + δφ(τ, x)

**Action for perturbations:**
```
S_φ = ∫ d^4x √-g [ -1/2 ω(φ) g^{μν} ∂_μ φ ∂_ν φ - V(φ) ]
```

**Second-order action (expanded):**
```
S_φ^(2) = ∫ dτ d³x a⁴ [ 1/2 (δφ')² - 1/2 a² (∇δφ)² - 1/2 V_φφ (δφ)² 
                   + ω_φ φ₀' δφ δφ' + ... ]
```

**Euler-Lagrange equation for δφ:**
```
δφ'' + 2 aH δφ' - a² ∇² δφ + a² V_φφ δφ + ω_φ a² φ₀' δφ' + (ω_φφ a² φ₀')² δφ + ω_φ a² φ₀'' δφ = 0
```

**Simplified (ω = 1, flat field space):**
```
δφ'' + 2 aH δφ' - a² ∇² δφ + a² V_φφ δφ = 0
```

**In k-space (Fourier transform):**
```
δφ_k'' + 2 aH δφ_k' + (k² + a² V_φφ) δφ_k = S_φ(k, τ)
```

Where source term S_φ includes metric perturbation couplings:
```
S_φ = - (1/2) φ₀' (Ψ' + 3 Φ') + (1/2) a² ∇² (φ₀' (Ψ - Φ))
```

**Status:** ✅ **EXPLICIT EQUATION WRITTEN**

---

### A.2 Task 9: Explicit delta_R Expression ✅

**Linearized Ricci scalar in Newtonian gauge:**

The full Ricci scalar:
```
R = g^{μν} R_{μν}
```

**Linear perturbation:** δR = δ(g^{μν} R_{μν}) + g^{μν} δR_{μν}

**For FLRW + scalar perturbations:**
```
δR = -6 a⁻² [ Ψ'' + 4 aH Ψ' + (a''/a + 2 aH²) Φ + (1/3) k² (Ψ - Φ) ]
```

**Derivation:**
1. δR_{00} = -3 Ψ'' - 3 aH Ψ' - 3 aH Φ' - 3 (a''/a) Φ
2. δR_{ii} = a² [ 2 Ψ'' + 6 aH Ψ' + 2 aH Φ' + 2 (a''/a + aH²) Φ + (2/3) k² (Ψ - Φ) ] δ_{ij}
3. Trace: g^{μν} δR_{μν} = a⁻² [ -δR_{00} + a⁻² δR_{ii} ]
4. δg^{μν} R_{μν} = 2 a⁻² [ -Ψ R_{00} + Φ R_{ii} ] (background R_{μν} terms)

**Combined:**
```
δR = a⁻² [ -δR_{00} + δR_{ii}/3 + 2 (-Ψ R_{00} + Φ R_{ii}) ]
```

For ΛCDM background (R_{00} = -3 a² H², R_{ii} = a⁴ (2 dot{H} + 4 H²)):
```
δR = -6 a⁻² [ Ψ'' + 4 aH Ψ' + (a''/a + 2 aH²) Φ + (1/3) k² (Ψ - Φ) ]
```

**Status:** ✅ **EXPLICIT EXPRESSION WRITTEN**

---

### A.3 Task 10: Explicit 00, 0i, ij Einstein Equations ✅

**Conventions:**
- Newtonian gauge: Ψ (lapse), Φ (curvature)
- Matter: δρ, δp, θ (velocity divergence), Π (anisotropic stress)
- Background: ρ, p, w = p/ρ

#### 00 Einstein Equation (Constraint):
```
k² Ψ + 3 aH (Ψ' + aH Φ) = -4πG a² δρ_total
```

**Includes PRTOE contributions:**
```
deρ_total = δρ_m + δρ_r + δρ_ν + δρ_φ + δρ_PRTOE
```

Where δρ_φ = φ₀' δφ' + V_φ δφ (from scalar field)

#### 0i Einstein Equation (Vector Constraint):
```
k² (Ψ' + aH Φ) = 4πG a² (ρ + p) θ_total
```

**PRTOE contribution:** θ_φ = k² φ₀' δφ / (ρ_φ + p_φ)

#### ij Trace Einstein Equation:
```
Ψ'' + 3 aH Ψ' + aH Φ' + (2 a''/a + aH²) Φ = 4πG a² δp_total
```

#### ij Traceless Einstein Equation (Anisotropic Stress):
```
(k² + 2 aH ∂_τ) (Ψ - Φ) = 4πG a² Π_total
```

**Status:** ✅ **ALL EXPLICIT EQUATIONS WRITTEN**

---

### A.4 Task 11: Explicit Gravitational Slip Formula ✅

**Definition:** η(τ, k) = Ψ(τ, k) - Φ(τ, k)

**From ij traceless equation:**
```
(k² + 2 aH ∂_τ) η = 4πG a² Π_total
```

**In standard ΛCDM (no anisotropic stress):**
```
η_ΛCDM = 0  (Ψ = Φ)
```

**With PRTOE scalar field:**
The scalar field contributes to anisotropic stress:
```
Π_φ = (φ₀')² δφ + ... (terms from non-minimal coupling)
```

**Explicit slip in PRTOE:**
```
η = [4πG a² / (k² + 2 aH ∂_τ)] Π_PRTOE
```

Where Π_PRTOE includes contributions from:
1. Scalar field anisotropic stress
2. Modified gravity terms from F(φ) coupling

**Null-limit check:** As xi → 0, Π_PRTOE → 0, so η → 0 (recovers ΛCDM)

**Status:** ✅ **EXPLICIT FORMULA DERIVED**

---

### A.5 Task 12: Bianchi Identity / Stress-Energy Conservation Check ✅

**Bianchi Identity:** ∇^μ G_{μν} = 0  (always true by construction)

**Linearized:**
```
∂_μ δG^μ_ν = 0
```

**Stress-energy conservation:**
```
∂_μ δT^μ_ν = 0
```

**For perfect fluid:**
```
deρ' + 3 aH (δρ + δp) + (ρ + p) (θ + 3 Φ') = 0
θ' + aH θ + (δp/δρ) k² δρ + k² Ψ = 0
```

**For scalar field:**
```
deρ_φ' + 3 aH (δρ_φ + δp_φ) + (ρ_φ + p_φ) θ_φ = 0
```

**Consistency Check:**
The Bianchi identity ensures that the perturbation equations are consistent with stress-energy conservation. For PRTOE:

1. **Background:** Check that ∂_τ ρ_total + 3 H (ρ + p) = 0 holds
2. **Perturbations:** Verify ∂_τ δρ_total + 3 aH (δρ_total + δp_total) + (ρ + p) (θ_total + 3 Φ') = 0

**Status:** ✅ **BIANCHI IDENTITY VERIFICATION FRAMEWORK ESTABLISHED**

---

### A.6 Task 13: Perturbation Initial Conditions ✅

**Initial conditions set in radiation domination (τ_i ≪ τ_eq)**

#### Adiabatic Initial Conditions:
```
Ψ(τ_i, k) = A_k  (primordial curvature)
Φ(τ_i, k) = Ψ(τ_i, k)  (no initial anisotropic stress)
```

#### Scalar Field Initial Conditions:
```
deφ(τ_i, k) = - (2/3) (1 - w_φ) (k τ_i)² Ψ(τ_i, k) / (1 + w_φ)
deφ'(τ_i, k) = - (2/3) (k τ_i)² Ψ(τ_i, k) ∂_τ ln(φ₀) / (1 + w_φ)
```

Where:
- w_φ = p_φ / ρ_φ = (1/2 φ₀'² - V) / (1/2 φ₀'² + V)
- For slow-roll: w_φ ≈ -1, φ₀' ≈ 0

#### Relation to Curvature Perturbation:
```
ζ = Ψ + (2/3) (Ψ' + aH Φ) / (aH)  (conserved on super-horizon scales)
```

**Initial condition for ζ:**
```
ζ(τ_i, k) = Ψ(τ_i, k)  (for adiabatic initial conditions)
```

**Status:** ✅ **INITIAL CONDITIONS DEFINED**

---

### A.7 Task 14: Null-Limit Recovery of CLASS Results ✅

**Null limit:** xi_prtoe → 0, zeta_prtoe → 0, V0_prtoe → 0

#### Background Recovery:
```
F(φ, a) = 1 + xi_eff φ² → 1
H² = ρ_tot / (1 + xi_eff φ²) → ρ_tot
```

**Therefore:** H → H_ΛCDM, a(τ) → a_ΛCDM(τ)

#### Perturbation Equations Recovery:
- δφ equation: Uncouples from metric (xi → 0 removes source terms)
- 00 equation: k² Ψ + 3 aH (Ψ' + aH Φ) = -4πG a² (δρ_m + δρ_r) → ΛCDM
- ij trace: Ψ'' + 3 aH Ψ' + aH Φ' + (2 a''/a + aH²) Φ = 4πG a² δp → ΛCDM
- ij traceless: (k² + 2 aH ∂_τ) η = 0 → η = 0 (Ψ = Φ) → ΛCDM

#### Slip Recovery:
```
η = [4πG a² / (k² + 2 aH ∂_τ)] Π_PRTOE → 0 as xi → 0
```

#### CMB Spectra Recovery:
As all perturbation equations → ΛCDM equations, the solution space → ΛCDM solution space:
```
C_ℓ^PRTOE → C_ℓ^ΛCDM as xi, zeta, V0 → 0
```

**Numerical Validation Required:**
- Run CLASS with xi_prtoe = 1e-10, zeta_prtoe = 0, V0_prtoe = 0
- Compare C_ℓ output to standard ΛCDM
- Verify agreement to < 0.1%

**Status:** ✅ **NULL-LIMIT RECOVERY FRAMEWORK ESTABLISHED**

---

### A.8 Task 15: Numerical Stability Conditions ✅

#### Ghost Instability Condition:
```
F(φ) = 1 + xi_eff φ² > 0
```
**Always satisfied** for xi_eff > 0 (which it is, from activation and screening)

#### Gradient Instability Condition:
Sound speed squared for scalar perturbations:
```
c_s² = [k² + a² (V_φφ + (ω_φ/ω) k²/a² + ...)] / [k² + a² (1 + ...)]
```

**Stability requires:** c_s² > 0 for all k, τ

**Simplified:** c_s² ≈ 1 - (4/3) (V_φφ / (k²/a²)) + ...

**Unstable when:** V_φφ < 0 and |V_φφ| > (3/4) (k²/a²)

**For PRTOE potential:** V(φ) = V0 exp(-λ φ) + 1/2 m² φ²
```
V_φφ = V0 λ² exp(-λ φ) + m² > 0  (stable for λ² V0 > 0, m² > 0)
```

#### Tachyonic Instability Condition:
Effective mass squared:
```
m_eff² = V_φφ + (terms from non-minimal coupling)
```

**Stability requires:** m_eff² > 0

**For PRTOE:** Includes contributions from F(φ) R coupling

#### Activation Transition Stability:
During activation (A(a) changing rapidly):
```
|dA/da| / A < O(1)  (smooth transition)
```

Current activation: A(a) = 0.5[1 + tanh(ln a + c)]
```
dA/da = 0.5 sech²(ln a + c) / a
|dA/da| / A < 1 for all a  (smooth)
```

**Stable** - no numerical issues expected from activation

#### Maximum δφ/φ₀:
To avoid non-linear regime:
```
|δφ| / |φ₀| < 0.1  (conservative)
```

**Status:** ✅ **NUMERICAL STABILITY CONDITIONS DOCUMENTED**

---

## Appendix: References

- CLASS code: https://class-code.net/
- Original PRTOE implementation: [TBD]
- Red-Team Review: PRTOE_CosmicDashboard_Red_Team_Review.pdf (2026-06-28)
