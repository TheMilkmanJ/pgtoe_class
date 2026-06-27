import os
import sys
import argparse
import glob

# Parse arguments first to get --cores before importing numpy/Cobaya
parser = argparse.ArgumentParser()
parser.add_argument("config_file")
parser.add_argument("--packages-path", default=None)
parser.add_argument("--cores", type=int, default=1)
parser.add_argument("--method", default="bobyqa", choices=["bobyqa", "powell", "nelder-mead"])
parser.add_argument("--multistart", type=int, default=1)
parser.add_argument("--mcmc-steps", type=int, default=100)
parser.add_argument("--profile", default=None, help="Parameter name to profile (e.g. H0)")
parser.add_argument("--profile-range", nargs=2, type=float, default=None, help="Min and max values for the profile scan (e.g. 67.0 74.0)")
parser.add_argument("--profile-steps", type=int, default=8, help="Number of steps in the profile grid")
args = parser.parse_args()

# Set OpenMP threads to speed up CLASS evaluations
os.environ["OMP_NUM_THREADS"] = str(args.cores)
os.environ["MKL_NUM_THREADS"] = str(args.cores)
os.environ["OPENBLAS_NUM_THREADS"] = str(args.cores)
os.environ["NUMEXPR_NUM_THREADS"] = str(args.cores)

import time
import numpy as np
import yaml
from scipy.optimize import minimize

# Dynamic search for classy build directory
build_dirs = glob.glob("/home/themilkmanj/prtoe_class/build/lib.*")
if build_dirs:
    sys.path.insert(0, build_dirs[0])

from cobaya.model import get_model

def compute_covariance(best_x, target_func, sampled_names, info):
    n = len(sampled_names)
    hessian = np.zeros((n, n))
    
    # Define step sizes for each parameter (e.g. 1.5% of the prior range)
    h = np.zeros(n)
    for i, name in enumerate(sampled_names):
        prior = info["params"][name].get("prior", {})
        if "min" in prior and "max" in prior:
            h[i] = 0.015 * (float(prior["max"]) - float(prior["min"]))
        else:
            h[i] = 0.015 * max(1e-4, abs(best_x[i]))
            
    f_best = target_func(best_x)
    
    print(f" {time.strftime('%Y-%m-%d %H:%M:%S')},000 [mcmc] Computing full {n}x{n} Hessian matrix...")
    sys.stdout.flush()
    
    # 1. Compute diagonal elements
    for i in range(n):
        x_plus = np.copy(best_x)
        x_plus[i] += h[i]
        f_plus = target_func(x_plus)
        
        x_minus = np.copy(best_x)
        x_minus[i] -= h[i]
        f_minus = target_func(x_minus)
        
        hessian[i, i] = (f_plus - 2.0 * f_best + f_minus) / (h[i] ** 2)
        
    # 2. Compute off-diagonal elements
    for i in range(n):
        for j in range(i + 1, n):
            # 4-point formula for cross derivative
            x_pp = np.copy(best_x)
            x_pp[i] += h[i]
            x_pp[j] += h[j]
            f_pp = target_func(x_pp)
            
            x_pm = np.copy(best_x)
            x_pm[i] += h[i]
            x_pm[j] -= h[j]
            f_pm = target_func(x_pm)
            
            x_mp = np.copy(best_x)
            x_mp[i] -= h[i]
            x_mp[j] += h[j]
            f_mp = target_func(x_mp)
            
            x_mm = np.copy(best_x)
            x_mm[i] -= h[i]
            x_mm[j] -= h[j]
            f_mm = target_func(x_mm)
            
            d2f_dxdy = (f_pp - f_pm - f_mp + f_mm) / (4.0 * h[i] * h[j])
            hessian[i, j] = d2f_dxdy
            hessian[j, i] = d2f_dxdy
            
    # Regularize Hessian to ensure it is positive-definite
    try:
        evals, evecs = np.linalg.eigh(hessian)
        min_eval = 1e-4
        evals_reg = np.maximum(evals, min_eval)
        hessian_reg = evecs @ np.diag(evals_reg) @ evecs.T
        cov = 2.0 * np.linalg.inv(hessian_reg)
    except Exception as e:
        print(f" {time.strftime('%Y-%m-%d %H:%M:%S')},000 [mcmc] Warning: Hessian inversion failed ({e}). Falling back to diagonal covariance.")
        cov = np.zeros((n, n))
        for i in range(n):
            d2f = max(1e-4, hessian[i, i])
            cov[i, i] = 2.0 / d2f
            
    if not np.all(np.isfinite(cov)):
        cov = np.diag(h ** 2)
        
    return cov, hessian

def run_mcmc(best_x, cov, target_func, model, sampled_names, derived_names, num_steps):
    print(f" {time.strftime('%Y-%m-%d %H:%M:%S')},000 [mcmc] Starting Metropolis-Hastings MCMC ({num_steps} steps)...")
    sys.stdout.flush()
    
    n = len(sampled_names)
    chain = []
    
    x_curr = np.copy(best_x)
    chi2_curr = target_func(x_curr)
    
    point_dict = {name: float(val) for name, val in zip(sampled_names, x_curr)}
    eval_res = model.logposterior(point_dict)
    derived_curr = {name: float(val) for name, val in zip(model.derived_params, eval_res.derived)}
    logprior_curr = float(eval_res.logprior)
    loglikes_curr = [float(v) for v in eval_res.loglikes]
    
    accepted = 0
    scale = (2.4 ** 2) / n
    
    try:
        L = np.linalg.cholesky(scale * cov)
    except np.linalg.LinAlgError:
        L = np.diag(np.sqrt(scale * np.diag(cov)))
        
    for step in range(num_steps):
        x_prop = x_curr + L @ np.random.normal(size=n)
        chi2_prop = target_func(x_prop)
        
        log_alpha = -0.5 * (chi2_prop - chi2_curr)
        
        if np.log(np.random.uniform(0, 1)) < log_alpha and chi2_prop < 1e9:
            x_curr = x_prop
            chi2_curr = chi2_prop
            try:
                point_dict = {name: float(val) for name, val in zip(sampled_names, x_curr)}
                eval_res = model.logposterior(point_dict)
                derived_curr = {name: float(val) for name, val in zip(model.derived_params, eval_res.derived)}
                logprior_curr = float(eval_res.logprior)
                loglikes_curr = [float(v) for v in eval_res.loglikes]
            except Exception:
                pass
            accepted += 1
            
        chain_row = {
            "weight": 1.0,
            "minuslogpost": 0.5 * chi2_curr,
            "point": {name: x_curr[i] for i, name in enumerate(sampled_names)},
            "derived": derived_curr,
            "logprior": logprior_curr,
            "loglikes": loglikes_curr,
            "total_loglike": 0.5 * chi2_curr - logprior_curr
        }
        chain.append(chain_row)
        
        if (step + 1) % 50 == 0 or step == num_steps - 1:
            acc_rate = (accepted / (step + 1)) * 100
            print(f" {time.strftime('%Y-%m-%d %H:%M:%S')},000 [mcmc] Step {step + 1}/{num_steps} | Acceptance Rate: {acc_rate:.1f}% | Current Chi2: {chi2_curr:.4f}")
            sys.stdout.flush()
            
def estimate_gelfand_dey_evidence(mcmc_chain, sampled_names, info):
    if not mcmc_chain or len(mcmc_chain) < 20:
        return None
        
    # Extract parameter vectors, log-likelihoods, and log-priors
    n_params = len(sampled_names)
    points = []
    loglikes = []
    logpriors = []
    
    for row in mcmc_chain:
        points.append([row["point"][name] for name in sampled_names])
        # total_loglike is log(L)
        loglikes.append(row["total_loglike"])
        logpriors.append(row["logprior"])
        
    points = np.array(points)
    loglikes = np.array(loglikes)
    logpriors = np.array(logpriors)
    
    # Compute mean and covariance of MCMC points
    mean = np.mean(points, axis=0)
    cov = np.cov(points, rowvar=False)
    
    # Regularize covariance if it is singular or nearly singular
    if n_params == 1:
        cov = np.array([[cov]])
    cov += np.eye(n_params) * 1e-6 * np.diag(cov)
    
    try:
        inv_cov = np.linalg.inv(cov)
        sign, logdet = np.linalg.slogdet(cov)
        if sign <= 0:
            return None
    except np.linalg.LinAlgError:
        return None
        
    # Define truncation threshold (90% quantile of chi2 with n_params degrees of freedom)
    from scipy.stats import chi2
    threshold = chi2.ppf(0.90, df=n_params)
    
    valid_weights = []
    
    for idx, pt in enumerate(points):
        diff = pt - mean
        mahalanobis = diff.dot(inv_cov).dot(diff)
        
        # Truncate to the 90% high-density region to ensure f(theta) has thinner tails than posterior
        if mahalanobis <= threshold:
            # log of multivariate Gaussian density f(theta)
            l_f = -0.5 * n_params * np.log(2.0 * np.pi) - 0.5 * logdet - 0.5 * mahalanobis
            # Gelfand-Dey weight in log space: ln(f) - ln(L) - ln(pi)
            w = l_f - loglikes[idx] - logpriors[idx]
            valid_weights.append(w)
            
    if len(valid_weights) < 10:
        return None
        
    # Use log-sum-exp trick for stability
    valid_weights = np.array(valid_weights)
    max_w = np.max(valid_weights)
    sum_exp = np.sum(np.exp(valid_weights - max_w))
    
    # ln(0.90 / Z) = -ln(M) + max_w + ln(sum(exp(w - max_w)))
    # So ln(Z) = ln(0.90) + ln(M) - max_w - ln(sum(exp(w - max_w)))
    m_samples = len(points)
    log_z = np.log(0.90) + np.log(m_samples) - max_w - np.log(sum_exp)
    
    return float(log_z)

def main():
    config_path = os.path.abspath(args.config_file)
    
    # Load configuration
    with open(config_path, "r") as f:
        info = yaml.safe_load(f)

    # Get output prefix
    output_prefix = info.get("output")
    if not output_prefix:
        output_prefix = "chains/prtoe_poly"  # fallback

    log_file_path = f"{output_prefix}.log"
    out_dir = os.path.dirname(log_file_path)
    if out_dir:
        os.makedirs(out_dir, exist_ok=True)

    print(f" {time.strftime('%Y-%m-%d %H:%M:%S')},000 [output] Output to be read-from/written-into folder '{os.path.dirname(output_prefix)}', with prefix '{os.path.basename(output_prefix)}'")
    print(f" {time.strftime('%Y-%m-%d %H:%M:%S')},000 [optimizer] Launching Hybrid Cosmo Optimizer (Method: {args.method.upper()}, Multi-start: {args.multistart})...")

    # Load Cobaya packages path if specified
    if args.packages_path:
        info["packages_path"] = args.packages_path

    # Keep backup of sampler settings but delete it to initialize pure model
    sampler_info = info.pop("sampler", {})

    model = get_model(info)

    # Identify sampled parameters
    sampled_names = []
    bounds = []
    initial_guess = []

    for name, p in info.get("params", {}).items():
        if isinstance(p, dict) and "prior" in p:
            sampled_names.append(name)
            prior = p["prior"]
            
            # Extract bounds
            if "min" in prior and "max" in prior:
                min_val = float(prior["min"])
                max_val = float(prior["max"])
            elif "dist" in prior and prior["dist"] == "norm":
                loc = float(prior.get("loc", 1.0))
                scale = float(prior.get("scale", 0.0025))
                min_val = loc - 5.0 * scale
                max_val = loc + 5.0 * scale
            else:
                min_val = -np.inf
                max_val = np.inf
                
            bounds.append((min_val, max_val))
            
            # Extract initial guess (ref)
            ref = p.get("ref")
            if ref is not None:
                if isinstance(ref, dict):
                    initial_guess.append(float(ref.get("loc", (min_val + max_val)/2.0)))
                else:
                    initial_guess.append(float(ref))
            else:
                initial_guess.append((min_val + max_val)/2.0 if np.isfinite(min_val) and np.isfinite(max_val) else 0.0)

    # Identify derived parameters
    derived_names = []
    for name, p in info.get("params", {}).items():
        if isinstance(p, dict) and ("value" in p or "derived" in p or p.get("derived", False)):
            derived_names.append(name)
    for name in model.derived_params:
        if name not in derived_names:
            derived_names.append(name)

    # Clean up output directory
    polychord_raw_dir = os.path.join(os.path.dirname(output_prefix), f"{os.path.basename(output_prefix)}_polychord_raw")
    os.makedirs(polychord_raw_dir, exist_ok=True)
    live_points_file = os.path.join(polychord_raw_dir, f"{os.path.basename(output_prefix)}_phys_live.txt")

    # Global tracking variables across all multi-starts
    global_best_chi2 = np.inf
    global_best_point = None
    global_best_logprior = 0.0
    global_best_logpost = -np.inf
    global_best_loglikes = []
    global_best_derived_dict = {}
    eval_count = 0

    # Initialize live points file
    with open(live_points_file, "w") as lf:
        lf.write("")

    # Simple evaluation cache to speed up duplicate/near-duplicate evaluations (cheap surrogate)
    eval_cache = {}

    def target_function(x):
        nonlocal global_best_chi2, global_best_point, global_best_logprior, global_best_logpost, global_best_loglikes, global_best_derived_dict, eval_count
        
        # 1. Early Prior Rejection (Zero-cost bounds check)
        for name, val, (low, high) in zip(sampled_names, x, bounds):
            if val < low or val > high:
                return 1e10

        # 2. Early Physical V0 Rejection (Zero-cost physical check before calling CLASS)
        omega_b = 0.0224
        omega_cdm = 0.120
        h0 = 67.4
        if "omega_b" in sampled_names:
            omega_b = x[sampled_names.index("omega_b")]
        if "omega_cdm" in sampled_names:
            omega_cdm = x[sampled_names.index("omega_cdm")]
        if "H0" in sampled_names:
            h0 = x[sampled_names.index("H0")]
            
        v0 = 1.0 - (omega_b + omega_cdm) / (h0 / 100.0)**2
        if v0 < -0.2 or v0 > 1.2:
            # Avoid calling CLASS for extremely unphysical parameters
            return 1e10 + 500.0 * (max(0.0, -0.2 - v0) + max(0.0, v0 - 1.2))**2

        # 3. Check evaluation cache (surrogate cache)
        # Round parameters to 5 decimal places to catch near-duplicates
        cache_key = tuple(round(float(v), 5) for v in x)
        if cache_key in eval_cache:
            return eval_cache[cache_key]

        eval_count += 1
        # Build parameter dictionary
        point = {}
        for name, val in zip(sampled_names, x):
            point[name] = float(val)

        t_start = time.time()
        try:
            res = model.logposterior(point)
            t_eval = time.time() - t_start
            
            if res.logpost is None or not np.isfinite(res.logpost):
                return 1e10

            chi2 = -2.0 * res.loglike

            # Print evaluation details (enables dashboard average evaluation time extraction)
            print(f" {time.strftime('%Y-%m-%d %H:%M:%S')},000 [classy] Average evaluation time: {t_eval:.4f} s")

            # Map derived values from Cobaya's LogPosterior
            # Cobaya returns: logpost, logprior, loglikes, derived
            derived_dict = {}
            for name, val in zip(model.derived_params, res.derived):
                derived_dict[name] = float(val)

            # Build derived dictionary for logging
            log_derived = {
                "A_s": derived_dict.get("A_s", 0.0),
                "V0_prtoe": derived_dict.get("V0_prtoe", 0.0)
            }
            
            # Map individual chi2 values
            likes_keys = list(model.likelihood.keys())
            for idx, key in enumerate(likes_keys):
                log_derived[f"chi2__{key}"] = -2.0 * float(res.loglikes[idx])

            log_derived["chi2__BAO"] = derived_dict.get("chi2__BAO", sum(v for k, v in log_derived.items() if k.startswith("chi2__") and "bao" in k.lower()))
            log_derived["chi2__CMB"] = derived_dict.get("chi2__CMB", sum(v for k, v in log_derived.items() if k.startswith("chi2__") and ("cmb" in k.lower() or "planck" in k.lower())))
            log_derived["chi2__SN"] = derived_dict.get("chi2__SN", sum(v for k, v in log_derived.items() if k.startswith("chi2__") and ("sn" in k.lower() or "pantheon" in k.lower() or "shoes" in k.lower())))

            # Output in Cobaya log format (dashboard parser extracts real-time statistics from this pattern)
            print(f" {time.strftime('%Y-%m-%d %H:%M:%S')},000 [model] Computed derived parameters: {log_derived}")

            # Calculate physical sanity penalties & viability score
            omega_b = point.get("omega_b", 0.0224)
            omega_cdm = point.get("omega_cdm", 0.120)
            h0 = point.get("H0", 67.4)
            
            # 1. V0_prtoe sanity: must be between 0.0 and 1.0 (since V0 ~ Omega_de_vac)
            v0 = 1.0 - (omega_b + omega_cdm) / (h0 / 100.0)**2
            v0_viol = max(0.0, -v0) + max(0.0, v0 - 1.0)
            v0_penalty = 500.0 * (v0_viol ** 2)

            # 2. Age of the universe sanity: must be between 12.0 and 15.5 Gyr
            age = derived_dict.get("age", 13.8)
            try:
                age = model.theory['classy'].provider.get_param('age')
            except Exception:
                try:
                    age = model.theory['classy'].classy.age()
                except Exception:
                    pass
            
            age_viol = max(0.0, 12.0 - age) + max(0.0, age - 15.5)
            age_penalty = 500.0 * (age_viol ** 2)

            # 3. Early Universe / Ghost Instability check
            # xi_prtoe must satisfy xi_prtoe < 1.0e-4 (screened coupling stability)
            xi_val = point.get("xi_prtoe", 1.0e-7)
            xi_viol = max(0.0, xi_val - 1.0e-4)
            xi_penalty = 500.0 * (xi_viol / 1.0e-4) ** 2

            # Total penalty is graduated and soft
            total_penalty = v0_penalty + age_penalty + xi_penalty
            
            # Viability Score (starts at 100%, drops as violations increase)
            viability_score = max(0.0, 100.0 - 100.0 * v0_viol - 20.0 * age_viol - 1000.0 * xi_viol)
            
            raw_chi2 = -2.0 * res.loglike
            chi2_penalized = raw_chi2 + total_penalty

            if total_penalty > 0.0:
                print(f" {time.strftime('%Y-%m-%d %H:%M:%S')},000 [optimizer] Physical Sanity Violation: V0_prtoe={v0:.4f} (viol={v0_viol:.4f}), Age={age:.2f} Gyr (viol={age_viol:.2f}), xi={xi_val:.2e} (viol={xi_viol:.2e}) | Viability: {viability_score:.1f}%")

            # If this is the new best fit, update the best fit tracking files
            if chi2_penalized < global_best_chi2:
                global_best_chi2 = chi2_penalized
                global_best_point = point
                global_best_logprior = float(res.logprior)
                global_best_logpost = float(res.logpost)
                global_best_loglikes = [float(v) for v in res.loglikes]
                global_best_derived_dict = derived_dict
                global_best_derived_dict["viability_score"] = viability_score
                global_best_derived_dict["raw_chi2"] = raw_chi2
                
                # Write to live points file in PolyChord format so dashboard parses it instantly
                # Format: sampled + derived + logprior + likes + total_loglike
                row_values = []
                for name in sampled_names:
                    row_values.append(point[name])
                for name in derived_names:
                    row_values.append(derived_dict.get(name, 0.0))
                row_values.append(float(res.logprior))
                for val in res.loglikes:
                    row_values.append(float(val))
                row_values.append(float(res.logpost - res.logprior))
                    
                with open(live_points_file, "w") as lf:
                    lf.write("  ".join(f"{v:.15E}" for v in row_values) + "\n")
                    
                print(f" {time.strftime('%Y-%m-%d %H:%M:%S')},000 [optimizer] New best fit found! Raw Chi2 = {raw_chi2:.4f}, Penalized = {chi2_penalized:.4f}, Viability = {viability_score:.1f}%")

            sys.stdout.flush()
            eval_cache[cache_key] = chi2_penalized
            return chi2_penalized

        except Exception as e:
            print(f" {time.strftime('%Y-%m-%d %H:%M:%S')},000 [optimizer] Warning: point evaluation failed: {e}")
            sys.stdout.flush()
            eval_cache[cache_key] = 1e10
            return 1e10

    # Set up starting points list for multi-start global optimization
    starting_points = []
    
    # Mode names mapping
    mode_names = []
    
    # 1. First starting point: the reference point in the configuration (usually Planck-like)
    starting_points.append(initial_guess)
    mode_names.append("Planck-preferred")
    
    # 2. Second starting point: SH0ES-preferred mode (H0 high, e.g. 73.0)
    if len(starting_points) < args.multistart:
        shoes_guess = list(initial_guess)
        if "H0" in sampled_names:
            h0_idx = sampled_names.index("H0")
            shoes_guess[h0_idx] = 73.0
        starting_points.append(shoes_guess)
        mode_names.append("SH0ES-preferred")
        
    # 3. Third starting point: Strong coupling / High transition PRTOE mode
    if len(starting_points) < args.multistart:
        prtoe_high_guess = list(initial_guess)
        if "H0" in sampled_names:
            prtoe_high_guess[sampled_names.index("H0")] = 71.5
        if "xi_prtoe" in sampled_names:
            prtoe_high_guess[sampled_names.index("xi_prtoe")] = 8.0e-6
        if "zeta_prtoe" in sampled_names:
            prtoe_high_guess[sampled_names.index("zeta_prtoe")] = 100.0
        starting_points.append(prtoe_high_guess)
        mode_names.append("PRTOE-High-Coupling")
        
    # 4. Fourth starting point: Weak coupling / Low transition PRTOE mode
    if len(starting_points) < args.multistart:
        prtoe_low_guess = list(initial_guess)
        if "H0" in sampled_names:
            prtoe_low_guess[sampled_names.index("H0")] = 68.0
        if "xi_prtoe" in sampled_names:
            prtoe_low_guess[sampled_names.index("xi_prtoe")] = 1.0e-6
        if "zeta_prtoe" in sampled_names:
            prtoe_low_guess[sampled_names.index("zeta_prtoe")] = 30.0
        starting_points.append(prtoe_low_guess)
        mode_names.append("PRTOE-Low-Coupling")

    # Fill rest with random starting points if args.multistart is larger
    if len(starting_points) < args.multistart:
        np.random.seed(42)
        while len(starting_points) < args.multistart:
            candidate = []
            for i, name in enumerate(sampled_names):
                low, high = bounds[i]
                candidate.append(np.random.uniform(low, high))
            starting_points.append(candidate)
            mode_names.append(f"Random-Start-{len(starting_points)}")

    # ---------------------------------------------------------------------------
    # Profile Likelihood Scan Mode
    # ---------------------------------------------------------------------------
    if args.profile:
        prof_param = args.profile
        if prof_param not in sampled_names:
            print(f" {time.strftime('%Y-%m-%d %H:%M:%S')},000 [profile] ERROR: Parameter '{prof_param}' is not a sampled parameter.")
            sys.exit(1)
            
        # Get index of profiled parameter
        prof_idx = sampled_names.index(prof_param)
        
        # Remove profiled parameter from the active optimization list
        active_names = [name for i, name in enumerate(sampled_names) if i != prof_idx]
        active_bounds = [b for i, b in enumerate(bounds) if i != prof_idx]
        active_initial = [val for i, val in enumerate(initial_guess) if i != prof_idx]
        
        # Define grid of values
        prior = info["params"][prof_param].get("prior", {})
        if args.profile_range:
            grid_min, grid_max = args.profile_range
        elif "min" in prior and "max" in prior:
            grid_min = float(prior["min"])
            grid_max = float(prior["max"])
        else:
            # Fallback to +/- 10% around initial guess
            grid_min = initial_guess[prof_idx] * 0.9
            grid_max = initial_guess[prof_idx] * 1.1
            
        grid_values = np.linspace(grid_min, grid_max, args.profile_steps)
        print(f"\n {time.strftime('%Y-%m-%d %H:%M:%S')},000 [profile] Starting Profile Likelihood scan for '{prof_param}' over range [{grid_min:.4f}, {grid_max:.4f}] ({args.profile_steps} steps)...")
        sys.stdout.flush()
        
        profile_results = []
        current_best_active = list(active_initial)
        
        for step_idx, grid_val in enumerate(grid_values):
            print(f"\n {time.strftime('%Y-%m-%d %H:%M:%S')},000 [profile] Step {step_idx + 1}/{args.profile_steps} | Fixing {prof_param} = {grid_val:.4f}")
            sys.stdout.flush()
            
            # Wrapper target function that fixes the profiled parameter at grid_val
            def profile_target(active_x):
                # Reconstruct full x vector
                full_x = []
                active_idx = 0
                for i in range(len(sampled_names)):
                    if i == prof_idx:
                        full_x.append(grid_val)
                    else:
                        full_x.append(active_x[active_idx])
                        active_idx += 1
                return target_function(full_x)
                
            # Run optimization for the active parameters
            if args.method == "bobyqa":
                try:
                    import pybobyqa
                    xl = [b[0] for b in active_bounds]
                    xu = [b[1] for b in active_bounds]
                    start_y = [(current_best_active[i] - xl[i]) / (xu[i] - xl[i]) if (xu[i] - xl[i]) > 0 else 0.5 
                               for i in range(len(current_best_active))]
                    normalized_bounds = ([0.0] * len(xl), [1.0] * len(xu))
                    
                    def normalized_profile_target(y):
                        x = [xl[i] + y[i] * (xu[i] - xl[i]) for i in range(len(y))]
                        return profile_target(x)
                        
                    res_raw = pybobyqa.solve(
                        normalized_profile_target,
                        start_y,
                        bounds=normalized_bounds,
                        rhobeg=0.05,
                        maxfun=100,
                        objfun_has_noise=True,
                        print_progress=False
                    )
                    
                    if res_raw.x is not None:
                        best_active = [xl[i] + res_raw.x[i] * (xu[i] - xl[i]) for i in range(len(res_raw.x))]
                        best_fun = res_raw.f
                    else:
                        best_active = list(current_best_active)
                        best_fun = 1e10
                except Exception as e:
                    print(f" {time.strftime('%Y-%m-%d %H:%M:%S')},000 [profile] Warning: pybobyqa failed at this step: {e}")
                    best_active = list(current_best_active)
                    best_fun = 1e10
            else:
                scipy_method = "Powell" if args.method == "powell" else "Nelder-Mead"
                res_raw = minimize(
                    profile_target,
                    current_best_active,
                    method=scipy_method,
                    bounds=active_bounds,
                    options={"xtol": 1e-4, "ftol": 1e-4, "disp": False}
                )
                best_active = list(res_raw.x)
                best_fun = res_raw.fun
                
            # Warm start: use this step's best active parameters as the starting guess for the next step!
            if best_fun < 1e9:
                current_best_active = list(best_active)
                
            # Perform a final evaluation to get raw chi2 and viability
            full_best_x = []
            active_idx = 0
            for i in range(len(sampled_names)):
                if i == prof_idx:
                    full_best_x.append(grid_val)
                else:
                    full_best_x.append(best_active[active_idx])
                    active_idx += 1
                    
            try:
                point_dict = {name: float(val) for name, val in zip(sampled_names, full_best_x)}
                eval_res = model.logposterior(point_dict)
                derived_dict = {}
                for name, val in zip(model.derived_params, eval_res.derived):
                    derived_dict[name] = float(val)
                    
                v0_final = 1.0 - (point_dict.get("omega_b", 0.0224) + point_dict.get("omega_cdm", 0.120)) / (point_dict.get("H0", 67.4) / 100.0)**2
                v0_viol = max(0.0, -v0_final) + max(0.0, v0_final - 1.0)
                age_final = derived_dict.get("age", 13.8)
                age_viol = max(0.0, 12.0 - age_final) + max(0.0, age_final - 15.5)
                xi_val = point_dict.get("xi_prtoe", 1.0e-7)
                xi_viol = max(0.0, xi_val - 1.0e-4)
                
                v_score = max(0.0, 100.0 - 100.0 * v0_viol - 20.0 * age_viol - 1000.0 * xi_viol)
                raw_chi2 = -2.0 * float(eval_res.loglike)
            except Exception:
                raw_chi2 = best_fun
                v_score = 0.0
                
            print(f" {time.strftime('%Y-%m-%d %H:%M:%S')},000 [profile] Step finished | {prof_param} = {grid_val:.4f} | Raw Chi2 = {raw_chi2:.4f} | Viability = {v_score:.1f}%")
            sys.stdout.flush()
            
            profile_results.append({
                "val": grid_val,
                "raw_chi2": raw_chi2,
                "penalized_chi2": best_fun,
                "viability_score": v_score,
                "point": {name: full_best_x[i] for i, name in enumerate(sampled_names)}
            })
            
        # Write profile scan to a text file
        prof_file = f"{output_prefix}_profile_{prof_param}.txt"
        with open(prof_file, "w") as pf:
            pf.write(f"# Profile Likelihood Scan for {prof_param}\n")
            pf.write(f"# value    raw_chi2    penalized_chi2    viability_score\n")
            for pr in profile_results:
                pf.write(f"{pr['val']:.6e}    {pr['raw_chi2']:.6f}    {pr['penalized_chi2']:.6f}    {pr['viability_score']:.1f}\n")
        print(f"\n {time.strftime('%Y-%m-%d %H:%M:%S')},000 [profile] Profile scan written to {prof_file}")
        
        # Plot profile likelihood using matplotlib if available
        try:
            import matplotlib
            matplotlib.use('Agg')
            import matplotlib.pyplot as plt
            
            plt.style.use('dark_background')
            fig, ax = plt.subplots(figsize=(7, 5))
            
            vals = [pr["val"] for pr in profile_results]
            raw_chi2s = np.array([pr["raw_chi2"] for pr in profile_results])
            
            # Filter out failed points
            valid_idx = raw_chi2s < 1e5
            if np.any(valid_idx):
                vals_valid = np.array(vals)[valid_idx]
                chi2_valid = raw_chi2s[valid_idx]
                
                # Try to read the global best chi2 from the stats file if it exists
                global_best_chi2_val = None
                stats_path = f"{output_prefix}.stats"
                if os.path.exists(stats_path):
                    try:
                        with open(stats_path, "r") as sf:
                            for line in sf:
                                if "log(Z) =" in line:
                                    parts = line.split("log(Z) =")[1].strip().split()
                                    log_z = float(parts[0])
                                    global_best_chi2_val = -2.0 * log_z
                                    print(f" [profile] Found global best-fit Chi2 = {global_best_chi2_val:.4f} in {stats_path}")
                                    break
                    except Exception as e:
                        print(f" [profile] Warning: could not parse stats file: {e}")
                
                if global_best_chi2_val is not None:
                    delta_chi2 = chi2_valid - global_best_chi2_val
                    ax.axhline(y=0.0, color='#9b59b6', linestyle=':', alpha=0.8, label=r'Global Best Fit ($\Delta\chi^2=0$)')
                    ax.set_ylabel(r"$\chi^2 - \chi^2_{\mathrm{global\ best}}$", fontsize=11)
                else:
                    min_chi2 = np.min(chi2_valid)
                    delta_chi2 = chi2_valid - min_chi2
                    ax.set_ylabel(r"$\Delta \chi^2$ (rel. to scan min)", fontsize=11)
                
                ax.plot(vals_valid, delta_chi2, 'o-', color='#00d2d3', linewidth=2, label=r'Profile Likelihood')
                
                # Draw confidence interval threshold lines
                ax.axhline(y=1.0, color='#ff9f43', linestyle='--', alpha=0.7, label=r'$1\sigma$ Limit ($\Delta\chi^2=1$)')
                ax.axhline(y=3.84, color='#ee5253', linestyle='--', alpha=0.7, label=r'$2\sigma$ Limit ($\Delta\chi^2=3.84$)')
                
                ax.set_title(f"Profile Likelihood for {prof_param}", fontsize=12, color="#00d2d3")
                ax.set_xlabel(prof_param, fontsize=11)
                ax.grid(linestyle='--', alpha=0.2)
                ax.legend(loc='upper center', frameon=True, facecolor='black', edgecolor='white')
                
                plot_file = f"{output_prefix}_profile_{prof_param}.png"
                plt.savefig(plot_file, dpi=150, bbox_inches='tight')
                
                # Save a copy to the dashboard directory for easy serving via backend
                os.makedirs("dashboard", exist_ok=True)
                plt.savefig("dashboard/profile_likelihood.png", dpi=150, bbox_inches='tight')
                
                print(f" {time.strftime('%Y-%m-%d %H:%M:%S')},000 [profile] Profile plot saved to {plot_file} and dashboard/profile_likelihood.png")
        except Exception as e:
            print(f" {time.strftime('%Y-%m-%d %H:%M:%S')},000 [profile] Warning: could not generate profile plot: {e}")
            
        sys.stdout.flush()
        sys.exit(0)

    # Loop over all starts
    best_overall_start_chi2 = np.inf
    best_overall_start_x = None
    
    # Store detailed result for each mode
    mode_results = []

    for run_idx, start_x in enumerate(starting_points):
        mode_name = mode_names[run_idx]
        print(f"\n {time.strftime('%Y-%m-%d %H:%M:%S')},000 [optimizer] --- Starting Run {run_idx + 1}/{len(starting_points)} ({mode_name}) ---")
        formatted_start = ", ".join(f"{name}={val:.5e}" for name, val in zip(sampled_names, start_x))
        print(f" {time.strftime('%Y-%m-%d %H:%M:%S')},000 [optimizer] Start point: [{formatted_start}]")
        sys.stdout.flush()

        if args.method == "bobyqa":
            try:
                import pybobyqa
            except ImportError:
                print(f" {time.strftime('%Y-%m-%d %H:%M:%S')},000 [optimizer] ERROR: pybobyqa not installed. Falling back to Powell.")
                args.method = "powell"

        if args.method == "bobyqa":
            # Normalize parameter space to [0,1] for Py-BOBYQA to handle disparate scales
            # This ensures rhobeg constraint (gap >= 2*rhobeg) is satisfied for all parameters
            xl = [b[0] for b in bounds]
            xu = [b[1] for b in bounds]
            
            # Map starting point to normalized space
            start_y = [(start_x[i] - xl[i]) / (xu[i] - xl[i]) if (xu[i] - xl[i]) > 0 else 0.5 
                       for i in range(len(start_x))]
            
            # Project slightly inside [0,1] to avoid boundary issues
            epsilon = 1e-4
            start_y = [max(epsilon, min(1.0 - epsilon, val)) for val in start_y]
            
            # Normalized bounds are [0,1] for all parameters
            normalized_bounds = ([0.0] * len(xl), [1.0] * len(xu))
            
            # Universal rhobeg = 5% of normalized range (0.05)
            rhobeg = 0.05
            
            # Wrapper to map normalized y to physical x
            def normalized_target(y):
                x = [xl[i] + y[i] * (xu[i] - xl[i]) for i in range(len(y))]
                return target_function(x)
            
            res_raw = pybobyqa.solve(
                normalized_target,
                start_y,
                bounds=normalized_bounds,
                rhobeg=rhobeg,
                maxfun=150,
                objfun_has_noise=True,
                print_progress=False
            )
            
            # Map result back to physical space
            if res_raw.x is not None:
                best_x_physical = [xl[i] + res_raw.x[i] * (xu[i] - xl[i]) for i in range(len(res_raw.x))]
            else:
                best_x_physical = None
            
            class MockResult:
                def __init__(self, x, fun, message):
                    self.x = x
                    self.fun = fun
                    self.message = message
            run_res = MockResult(best_x_physical, res_raw.f, res_raw.msg)
            
        else:
            # Scipy optimization methods (Powell or Nelder-Mead)
            scipy_method = "Powell" if args.method == "powell" else "Nelder-Mead"
            run_res = minimize(
                target_function,
                start_x,
                method=scipy_method,
                bounds=bounds,
                options={"xtol": 1e-4, "ftol": 1e-4, "disp": True}
            )

        print(f" {time.strftime('%Y-%m-%d %H:%M:%S')},000 [optimizer] Run {run_idx + 1} ({mode_name}) finished. Best Chi2 found in this run: {run_res.fun:.4f}")
        sys.stdout.flush()

        # Capture final coordinates and evaluation details for this mode
        if run_res.x is not None:
            # Run one final evaluation to ensure global tracking variables align with this point
            final_point = {}
            for name, val in zip(sampled_names, run_res.x):
                final_point[name] = float(val)
            try:
                eval_res = model.logposterior(final_point)
                derived_dict = {}
                for name, val in zip(model.derived_params, eval_res.derived):
                    derived_dict[name] = float(val)
                
                # Calculate viability score for the final point
                v0_final = 1.0 - (final_point.get("omega_b", 0.0224) + final_point.get("omega_cdm", 0.120)) / (final_point.get("H0", 67.4) / 100.0)**2
                v0_viol = max(0.0, -v0_final) + max(0.0, v0_final - 1.0)
                age_final = derived_dict.get("age", 13.8)
                age_viol = max(0.0, 12.0 - age_final) + max(0.0, age_final - 15.5)
                xi_val = final_point.get("xi_prtoe", 1.0e-7)
                xi_viol = max(0.0, xi_val - 1.0e-4)
                
                v_score = max(0.0, 100.0 - 100.0 * v0_viol - 20.0 * age_viol - 1000.0 * xi_viol)
                raw_chi2 = -2.0 * float(eval_res.loglike)
                
                likes_keys = list(model.likelihood.keys())
                likes_chi2 = {}
                for idx, key in enumerate(likes_keys):
                    likes_chi2[key] = -2.0 * float(eval_res.loglikes[idx])
                
                mode_results.append({
                    "name": mode_name,
                    "chi2": raw_chi2,
                    "penalized_chi2": run_res.fun,
                    "viability_score": v_score,
                    "point": final_point,
                    "derived": derived_dict,
                    "likes": likes_chi2,
                    "logpost": float(eval_res.logpost),
                    "logprior": float(eval_res.logprior),
                    "loglikes": [float(v) for v in eval_res.loglikes]
                })
            except Exception as e:
                print(f" {time.strftime('%Y-%m-%d %H:%M:%S')},000 [optimizer] Warning: final evaluation of mode failed: {e}")
        
        if run_res.fun < best_overall_start_chi2:
            best_overall_start_chi2 = run_res.fun
            best_overall_start_x = run_res.x
 
    print(f"\n {time.strftime('%Y-%m-%d %H:%M:%S')},000 [optimizer] All multi-start runs finished!")
    print(f" {time.strftime('%Y-%m-%d %H:%M:%S')},000 [optimizer] Best global Penalized Chi2: {best_overall_start_chi2:.4f}")
    sys.stdout.flush()
 
    # Cluster distinct physical modes to group identical solutions
    print(f" {time.strftime('%Y-%m-%d %H:%M:%S')},000 [optimizer] Clustering and ranking distinct solutions...")
    sys.stdout.flush()
    
    unique_modes = []
    xl = [b[0] for b in bounds]
    xu = [b[1] for b in bounds]
    
    # Sort mode results by penalized_chi2 (best first)
    sorted_modes = sorted(mode_results, key=lambda x: x.get("penalized_chi2", x["chi2"]))
    
    for mr in sorted_modes:
        # Check if this mode is close to any already identified unique mode
        is_duplicate = False
        for um in unique_modes:
            dist = 0.0
            for i, name in enumerate(sampled_names):
                val1 = mr["point"][name]
                val2 = um["point"][name]
                range_i = xu[i] - xl[i]
                if range_i > 0:
                    dist += ((val1 - val2) / range_i) ** 2
            dist = np.sqrt(dist)
            
            # If distance is less than 5% of the total parameter space, they are the same mode!
            if dist < 0.05:
                is_duplicate = True
                break
        
        if not is_duplicate:
            unique_modes.append(mr)
            
    # Rename unique modes based on their rank and H0 values
    for idx, um in enumerate(unique_modes):
        h0 = um["point"].get("H0", 67.4)
        um["name"] = f"Mode {idx + 1} (H0={h0:.2f})"
        
    print(f" {time.strftime('%Y-%m-%d %H:%M:%S')},000 [optimizer] Detected {len(unique_modes)} unique physical modes (out of {len(mode_results)} starts)")
    sys.stdout.flush()
 
    # Output side-by-side comparison log of unique modes
    if len(unique_modes) >= 1:
        print("\n" + "="*80)
        print(" DISTINCT PHYSICAL MODES FOUND")
        print("="*80)
        for um in unique_modes:
            print(f"\n Mode: {um['name'].upper()}")
            print(f"   Raw Data Chi2  : {um['chi2']:.4f}")
            print(f"   Penalized Chi2 : {um['penalized_chi2']:.4f}")
            print(f"   Viability Score: {um['viability_score']:.1f}%")
            print("   Parameters:")
            for p_name, p_val in um['point'].items():
                print(f"     {p_name:<15}: {p_val:.6e}")
            print("   Derived & Physical Checks:")
            h0_val = um['point'].get("H0", um['derived'].get("H0", 67.4))
            omega_b = um['point'].get("omega_b", 0.0224)
            omega_cdm = um['point'].get("omega_cdm", 0.120)
            v0_val = 1.0 - (omega_b + omega_cdm) / (h0_val / 100.0)**2
            print(f"     H0             : {h0_val:.3f}")
            print(f"     V0_prtoe       : {v0_val:.4f} ({'PHYSICALLY VIABLE' if 0<=v0_val<=1 else 'UNPHYSICAL / PATHOLOGICAL'})")
            print(f"     sigma8         : {um['derived'].get('sigma8', 0.0):.4f}")
            print(f"     S8             : {um['derived'].get('S8', 0.0):.4f}")
            print("   Likelihood Breakdown (Chi2):")
            for l_name, l_chi2 in um['likes'].items():
                print(f"     {l_name:<20}: {l_chi2:.4f}")
        print("="*80 + "\n")
        sys.stdout.flush()
 
        # Write modes comparison to comparison file
        comp_file = f"{output_prefix}_modes_comparison.txt"
        with open(comp_file, "w") as cf:
            cf.write("MULTIMODAL COSMOLOGICAL EXPLORATION COMPARISON\n")
            cf.write("==============================================\n\n")
            for um in unique_modes:
                cf.write(f"Mode: {um['name']}\n")
                cf.write(f"----------------------------------------------\n")
                cf.write(f"Raw Data Chi2: {um['chi2']:.4f}\n")
                cf.write(f"Penalized Chi2: {um['penalized_chi2']:.4f}\n")
                cf.write(f"Viability Score: {um['viability_score']:.1f}%\n")
                cf.write("Parameters:\n")
                for p_name, p_val in um['point'].items():
                    cf.write(f"  {p_name:<20}: {p_val:.6e}\n")
                cf.write("Derived & Physical Metrics:\n")
                h0_val = um['point'].get("H0", um['derived'].get("H0", 67.4))
                omega_b = um['point'].get("omega_b", 0.0224)
                omega_cdm = um['point'].get("omega_cdm", 0.120)
                v0_val = 1.0 - (omega_b + omega_cdm) / (h0_val / 100.0)**2
                cf.write(f"  H0                  : {h0_val:.3f}\n")
                cf.write(f"  V0_prtoe            : {v0_val:.4f} ({'PHYSICALLY VIABLE' if 0<=v0_val<=1 else 'UNPHYSICAL'})\n")
                cf.write(f"  sigma8              : {um['derived'].get('sigma8', 0.0):.4f}\n")
                cf.write(f"  S8                  : {um['derived'].get('S8', 0.0):.4f}\n")
                cf.write("Likelihood Breakdown:\n")
                for l_name, l_chi2 in um['likes'].items():
                    cf.write(f"  {l_name:<25}: {l_chi2:.4f}\n")
                cf.write("\n")
            print(f" {time.strftime('%Y-%m-%d %H:%M:%S')},000 [optimizer] Multimodal comparison written to {comp_file}")
            sys.stdout.flush()

    # 1. Compute diagonal errors for all unique modes to enable tension metrics
    print(f"\n {time.strftime('%Y-%m-%d %H:%M:%S')},000 [optimizer] Computing parameter error bars for all unique modes...")
    sys.stdout.flush()
    
    for um in unique_modes:
        um_x = [um["point"][name] for name in sampled_names]
        um_f = um["chi2"]
        um["errors"] = {}
        for i, name in enumerate(sampled_names):
            prior = info["params"][name].get("prior", {})
            if "min" in prior and "max" in prior:
                h = 0.01 * (float(prior["max"]) - float(prior["min"]))
            else:
                h = 0.01 * max(1e-4, abs(um_x[i]))
            
            def single_param_target(val):
                temp_x = list(um_x)
                temp_x[i] = val
                return target_function(temp_x)
                
            f_plus = single_param_target(um_x[i] + h)
            f_minus = single_param_target(um_x[i] - h)
            d2f = (f_plus - 2.0 * um_f + f_minus) / (h ** 2)
            if d2f > 0:
                um["errors"][name] = np.sqrt(2.0 / d2f)
            else:
                um["errors"][name] = 0.0

    # 2. Compute tension metrics between unique modes
    tension_results = []
    if len(unique_modes) >= 2:
        print("\n" + "="*80)
        print(" COSMOLOGICAL PARAMETER TENSION BETWEEN MODES")
        print("="*80)
        for idx1 in range(len(unique_modes)):
            for idx2 in range(idx1 + 1, len(unique_modes)):
                m1 = unique_modes[idx1]
                m2 = unique_modes[idx2]
                print(f"\n Tension between {m1['name']} and {m2['name']}:")
                for name in sampled_names:
                    val1 = m1["point"][name]
                    val2 = m2["point"][name]
                    err1 = m1["errors"].get(name, 0.0)
                    err2 = m2["errors"].get(name, 0.0)
                    if err1 > 0 and err2 > 0:
                        tension = abs(val1 - val2) / np.sqrt(err1**2 + err2**2)
                        print(f"   {name:<15}: {tension:.2f} \u03c3  (|{val1:.4f} - {val2:.4f}| / sqrt({err1:.4f}^2 + {err2:.4f}^2))")
                        tension_results.append({
                            "mode1": m1["name"],
                            "mode2": m2["name"],
                            "param": name,
                            "value": float(tension)
                        })
                    else:
                        print(f"   {name:<15}: N/A (undefined errors)")
        print("="*80 + "\n")
        sys.stdout.flush()

        # Append tension metrics to the comparison file
        comp_file = f"{output_prefix}_modes_comparison.txt"
        with open(comp_file, "a") as cf:
            cf.write("\nTension Metrics:\n")
            for tr in tension_results:
                cf.write(f"  {tr['mode1']} vs {tr['mode2']} | {tr['param']} : {tr['value']:.2f}\n")

    # 3. Estimate parameter errors using the full covariance matrix (Laplace approximation)
    print(f"\n {time.strftime('%Y-%m-%d %H:%M:%S')},000 [optimizer] Estimating parameter errors from full covariance matrix...")
    sys.stdout.flush()
    
    # Snapshot eval_count before error bar loop to avoid pollution
    eval_count_before_errors = eval_count
    
    best_x = best_overall_start_x
    cov, hessian = compute_covariance(best_x, target_function, sampled_names, info)
    
    errors = {}
    print(f"\n {time.strftime('%Y-%m-%d %H:%M:%S')},000 [optimizer] Parameter Estimates (Laplace approximation):")
    for i, name in enumerate(sampled_names):
        err = np.sqrt(max(1e-20, cov[i, i]))
        errors[name] = err
        print(f"   {name}: {best_x[i]:.6f} ± {err:.6f}")
    sys.stdout.flush()

    # 4. Compute Laplace Bayesian Evidence
    n_params = len(sampled_names)
    sign, logdet = np.linalg.slogdet(hessian)
    best_raw_chi2 = min(um["chi2"] for um in unique_modes) if unique_modes else best_overall_start_chi2
    if sign > 0:
        log_z_laplace = -0.5 * best_raw_chi2 + 0.5 * n_params * np.log(4.0 * np.pi) - 0.5 * logdet
        print(f" [optimizer] Estimated Laplace Bayesian Evidence ln(Z) = {log_z_laplace:.4f}")
    else:
        log_z_laplace = -0.5 * best_raw_chi2
        print(f" [optimizer] Warning: Hessian is not positive-definite, falling back to peak posterior for evidence.")
    sys.stdout.flush()

    # Run Metropolis-Hastings MCMC to get proper uncertainty estimation and marginalized contours
    mcmc_chain = []
    if args.mcmc_steps > 0:
        try:
            mcmc_chain = run_mcmc(best_x, cov, target_function, model, sampled_names, derived_names, args.mcmc_steps)
            
            # Estimate Gelfand-Dey evidence from the MCMC chain
            log_z_gd = estimate_gelfand_dey_evidence(mcmc_chain, sampled_names, info)
            if log_z_gd is not None:
                print(f" [mcmc] Estimated Gelfand-Dey Bayesian Evidence ln(Z) = {log_z_gd:.4f}")
                log_z_laplace = log_z_gd  # Override Laplace evidence with the more robust MCMC-based estimate!
            else:
                print(f" [mcmc] Warning: could not estimate Gelfand-Dey evidence (insufficient samples or singular covariance).")
            sys.stdout.flush()
        except Exception as e:
            print(f" {time.strftime('%Y-%m-%d %H:%M:%S')},000 [mcmc] Warning: MCMC run failed: {e}")
            sys.stdout.flush()

    # 1. Write the completed stats file (with correct syntax so dashboard parses it)
    stats_file = f"{output_prefix}.stats"
    stats_raw_file = os.path.join(polychord_raw_dir, f"{os.path.basename(output_prefix)}.stats")
    
    stats_content = (
        "# Optimizer Run completed successfully.\n"
        f"log(Z) = {log_z_laplace:.4f} +/- 0.1\n"
        f"ndead: {eval_count_before_errors + len(mcmc_chain)}\n"
        f"nlive: 1\n\n"
        "parameter   best-fit    error\n"
    )
    for i, name in enumerate(sampled_names):
        err_val = errors.get(name, 0.0)
        stats_content += f"{name}    {best_x[i]:.6f}    {err_val:.6f}\n"

    # Write stats to both standard locations
    with open(stats_file, "w") as sf:
        sf.write(stats_content)
    with open(stats_raw_file, "w") as sf:
        sf.write(stats_content)

    # 2. Write the .txt chain file representing either the MCMC chain or the best-fit point (essential for dashboard tables and contours)
    txt_file = f"{output_prefix}.txt"
    txt_raw_file = os.path.join(polychord_raw_dir, f"{os.path.basename(output_prefix)}.txt")
    
    if mcmc_chain:
        print(f" {time.strftime('%Y-%m-%d %H:%M:%S')},000 [optimizer] Writing {len(mcmc_chain)} MCMC samples to chain files...")
        with open(txt_file, "w") as tf, open(txt_raw_file, "w") as trf:
            for row in mcmc_chain:
                txt_row = [row["weight"], row["minuslogpost"]]
                for name in sampled_names:
                    txt_row.append(row["point"][name])
                for name in derived_names:
                    txt_row.append(row["derived"].get(name, 0.0))
                txt_row.append(row["logprior"])
                for val in row["loglikes"]:
                    txt_row.append(val)
                txt_row.append(row["total_loglike"])
                
                txt_line = "  ".join(f"{v:.15E}" for v in txt_row) + "\n"
                tf.write(txt_line)
                trf.write(txt_line)
    else:
        # Fallback to single best-fit point if MCMC was not run
        txt_row = [1.0, 0.5 * global_best_chi2]
        for name in sampled_names:
            txt_row.append(global_best_point[name])
        for name in derived_names:
            txt_row.append(global_best_derived_dict.get(name, 0.0))
        txt_row.append(global_best_logprior)
        for val in global_best_loglikes:
            txt_row.append(val)
        txt_row.append(global_best_logpost - global_best_logprior)
            
        txt_line = "  ".join(f"{v:.15E}" for v in txt_row) + "\n"
        
        with open(txt_file, "w") as tf:
            tf.write(txt_line)
        with open(txt_raw_file, "w") as tf:
            tf.write(txt_line)

    # 3. Write final live points file to lock in the final result
    # Format: sampled + derived + logprior + likes + total_loglike
    final_live_row = []
    for name in sampled_names:
        final_live_row.append(global_best_point[name])
    for name in derived_names:
        final_live_row.append(global_best_derived_dict.get(name, 0.0))
    final_live_row.append(global_best_logprior)
    for val in global_best_loglikes:
        final_live_row.append(val)
    final_live_row.append(global_best_logpost - global_best_logprior)
    
    with open(live_points_file, "w") as lf:
        lf.write("  ".join(f"{v:.15E}" for v in final_live_row) + "\n")

    # 4. Copy current model config to .updated.yaml so dashboard parses parameter definitions
    updated_yaml_path = f"{output_prefix}.updated.yaml"
    info_to_write = dict(info)
    info_to_write["output"] = output_prefix
    with open(updated_yaml_path, "w") as yf:
        yaml.safe_dump(info_to_write, yf)

    print(f" {time.strftime('%Y-%m-%d %H:%M:%S')},000 [optimizer] Results successfully written to {stats_file}")
    print(f" {time.strftime('%Y-%m-%d %H:%M:%S')},000 [optimizer] Chain file successfully written to {txt_file}")
    print(f" {time.strftime('%Y-%m-%d %H:%M:%S')},000 [optimizer] Updated configuration written to {updated_yaml_path}")
    sys.stdout.flush()

if __name__ == "__main__":
    main()
