# PRTOE Physics for Code Review

Compact math/physics reference for static review of the CLASS PRTOE core.
**Not an implementation guide** — auditors cite this document and `CONTEXT.md`;
implementers choose the code.

Full derivations and dispute resolution: `PRTOE_Working_Formulation.md` (Sections 2, 10).

Auditable code contracts (PASS/FAIL checklist): `CONTEXT.md`.

---

## 1. Scalar-tensor background (Section 2)

### Coupling and potential

```
F(φ) = 1 + ξ_eff(φ) · A(φ)
A(φ) = ½(1 + tanh((φ − φ_c)/δφ))     with δφ = delta_phi_prtoe > 0
ξ_eff(φ) = ξ · φ²/(1 + ζ·φ²)          (chameleon screening; same ξ_eff everywhere)
V(φ) = V₀·exp(−λφ) + ½m²φ²
```

### Friedmann (PRTOE active)

```
3 F H² + 3 H Ḟ = ρ_tot − 3 F K/a²
Ḟ = F_φ · φ̇   (same definition in solver and stored index_bg_F_dot_prtoe)
```

When PRTOE is inactive (null limit): F → 1, Ḟ → 0, standard ΛCDM Friedmann.

### Covariant activation (within an active run)

Activation is **not** a function of scale factor alone. It is a density ratio:

```
ρ_φ = ½φ̇² + V(φ)
ρ_r = photons + ultra-relativistic + dark radiation + IDR + relativistic NCDM (3p contribution)
trans = ½(1 + tanh((log(ρ_φ/ρ_r) − log(0.01)) / 0.1))
ρ_prtoe = trans · (½φ̇² + V)
p_prtoe   = trans · (½φ̇² − V)
```

Field stress-energy is gated by `trans`; coupling outputs F, F_φ may still be stored when inactive.

### Mode / allocation gates (parameter time)

Single predicate family — do not mix threshold variants:

```
prtoe_is_physically_active ≡ use_prtoe AND NOT prtoe_explicit_null_de
                             AND (Ω₀_prtoe > 0 OR ξ ≥ 1e−7 OR β > 1e−8)

prtoe_coupling_dynamical ≡ ξ ≥ 1e−7 OR β > 1e−8  →  de_mode = prtoe_active
else if Ω₀_prtoe > 0                              →  de_mode = prtoe_frozen
else                                              →  de_mode = lambda_limit
```

Lambda budget: add Ω₀_Λ to ρ_tot only when PRTOE is not physically active, or `de_mode == lambda_limit`.

---

## 2. Perturbations — variables and gauges (Section 10.2–10.3)

Newtonian gauge: evolve scalar field perturbation δφ with metric potentials Φ (Bardeen) and slip η = Ψ − Φ.

**Slip driver (anisotropic stress):** PRTOE contributes Π_PRTOE through δF and field derivatives:

```
(k² + 2aH ∂_τ) η = 4πG a² Π_total

Π_PRTOE ∝ (F_φ/F)(δφ'' + ℋδφ' − (k²/3)δφ) + (F_φφφ'/F)(δφ' + ℋδφ)   (+ higher-order δF terms)
```

**Newtonian ψ relation (must match Einstein assembly):**

```
ψ = Φ − (9/2)(a/k)² · (ρ_plus_p_shear / F)     when PRTOE covariantly active (G_eff/F)
```

`rho_plus_p_shear` holds unscaled stress (photon: 4/3 ρ σ; PRTOE δF: a² × Π terms).
Apply **1/F only once** in `perturbations_einstein` / `prtoe_newtonian_psi` — not inside the δF accumulator.

Any term entering ψ at a given stage must already be in `rho_plus_p_shear` at that stage.

**Gauge consistency:** If the Newtonian path changes, the synchronous-gauge equivalent must be updated (e.g. synchronous → current-gauge transforms on source variables).

---

## 3. Initial conditions — superhorizon adiabatic (Section 10.4)

Radiation era, k ≪ aH:

```
Φ = −(2/3) ζ
δφ = −(F_φ/F) Φ     when metric IC active (covariant PRTOE on)
η  = ζ               seed synchronous curvature once — never derive η from δφ
δφ' = 0, Φ' = 0, η' = 0 at IC
```

**Constraint solve ordering:** Before solving the synchronous Newtonian constraint for α/φ, the shear budget `rho_plus_p_shear` must include every anisotropic-stress contribution that will enter ψ at that time — including neutrino shear **and** PRTOE δF shear if metric IC is active.

**Covariant perturbation gate (runtime):**

```
prtoe_is_covariantly_active_at_tau ≡ de_mode == prtoe_active AND ρ_prtoe > 1e−30
```

---

## 4. Unified dark sector (Section 10.4.1)

When `unify_dark_sector`: single PRTOE field carries clustered DM + DE budget.

```
prtoe_unified_dark_sector_active → no separate CDM indices; cluster weight = 1.0
partial unify → prtoe_clustering_weight_cdm(g_c_prtoe) on PRTOE stress-energy in matter sources
```

Adiabatic ICs in full unification: δ_prtoe seeded CDM-like (3/4 δ_g convention in formulation).

---

## 5. Null-limit recovery (Section 10.5)

```
ξ → 0, β → 0, Ω₀_prtoe → 0  ⇒  F → 1, Ḟ → 0, trans → 0, Π_PRTOE → 0, η → 0
```

Background and perturbation equations must reduce to ΛCDM; no spurious PRTOE stress or modified Poisson terms.

---

## 6. Stability guards (Section 10.6 — review flags)

| Condition | Requirement |
|-----------|-------------|
| Ghost | F(φ) > 0 |
| Gradient | c_s² > 0 (watch V_φφ and k/a) |
| Tachyonic | m_eff² > 0 |
| Activation | trans transition smooth in log(ρ_φ/ρ_r) |
| Fifth force | \|G_eff/G − 1\| ≲ 1e−5 at solar-system densities |

---

## 7. Source-term normalization

P(k) / CMB source assembly divides by ρ_prtoe only when ρ_prtoe > PRTOE_RHO_ACTIVATION_THRESHOLD (1e−30).
θ sources use |ρ_prtoe + p_prtoe| > same scale.

Synchronous-gauge dump: PRTOE-backed `delta_scf` / `theta_scf` receive the same α transform as canonical SCF when `get_perturbations_in_current_gauge == false`.

---

## 8. How reviewers should use this document

For each finding, report in this order:

1. **Physics** — invariant or equation violated; cite `PRTOE_PHYSICS_FOR_REVIEW.md` §N or `CONTEXT.md` contract name.
2. **Code** — file:line where implementation diverges (no patch, no diff).
3. **Impact** — symbols, gates, and other sites that must stay consistent (background_functions vs background_derivs, IC vs evolution, sync vs Newtonian).

Do **not** propose implementation or paste code unless the team explicitly asks.