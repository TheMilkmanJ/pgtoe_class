# Getting Started with PRTOE_COSMICFORGE

A comprehensive guide to running cosmological parameter estimation with the PRTOE (Precision Theoretical Observable Effects) framework.

## Prerequisites

Before you begin, ensure you have the following installed:

- **Python 3.8+** (recommended: 3.9-3.12)
- **Git**
- **Make**
- **GCC** (for compiling CLASS)
- **Python dependencies** (listed in `requirements.txt`)

### Required Python Packages

```bash
pip install numpy scipy cobaya pyyaml matplotlib
```

### CLASS Installation

This repository includes a modified version of CLASS that supports PRTOE parameters. The library is compiled automatically when you run the code.

## Quick Start

### 1. Clone the Repository

```bash
git clone https://github.com/your-repo/prtoe_class.git
cd prtoe_class
```

### 2. Run a Test Analysis

The fastest way to test the installation is to run in toy mode:

```bash
python run_cosmicforge.py prtoe_standard.yaml --test-toy --cores 4
```

This runs a fast 4D toy cosmological likelihood for testing, typically completing in under a minute.

### 3. Run a Full Analysis

For a full cosmological parameter estimation:

```bash
python run_cosmicforge.py prtoe_standard.yaml --cores 4
```

**Note:** The filename is `prtoe_standard.yaml` (lowercase 's'), not `prtoe_Standard.yaml`.

## Configuration Files

The YAML configuration files define your cosmological model, parameters, likelihoods, and sampler settings.

### Main Configuration File: `prtoe_standard.yaml`

This file includes:

- **Likelihoods**: Planck, BAO, SN data
- **Theory**: CLASS with PRTOE modifications
- **Parameters**: Standard cosmological + PRTOE parameters
- **Sampler**: PolyChord nested sampling

### Key Parameters

| Parameter | Description | Typical Range |
|-----------|-------------|---------------|
| `H0` | Hubble constant (km/s/Mpc) | 55-85 |
| `omega_b` | Baryon density parameter | 0.019-0.026 |
| `omega_cdm` | CDM density parameter | 0.1-0.2 |
| `xi_prtoe` | PRTOE coupling parameter | 1e-7 - 1.2e-5 |
| `zeta_prtoe` | PRTOE scaling parameter | 0.0001-5.0 |

## Command Line Options

```bash
# Basic usage
python run_cosmicforge.py config.yaml

# Specify number of cores
python run_cosmicforge.py config.yaml --cores 8

# Change optimization method
python run_cosmicforge.py config.yaml --method bobyqa

# Disable MCMC (optimizer only)
python run_cosmicforge.py config.yaml --mcmc-steps 0

# Run in toy mode for testing
python run_cosmicforge.py config.yaml --test-toy

# Run PolyChord-only (legacy mode)
python run_cosmicforge.py config.yaml --polychord

# Run PolyChord after optimizer for cross-validation
python run_cosmicforge.py config.yaml --run-polychord

# Profile a parameter
python run_cosmicforge.py config.yaml --profile H0 --profile-range 65 75 --profile-steps 10

# Multi-start optimization
python run_cosmicforge.py config.yaml --multistart 5
```

## Output Structure

The code creates a `chains/` directory (or the directory specified in the config) containing:

```
chains/
├── prtoe_poly.log              # Log file
├── prtoe_poly.summary.json     # Summary statistics
├── prtoe_poly.json             # Parameter samples
├── prtoe_poly.stats            # PolyChord statistics
└── prtoe_poly_*.txt            # Individual chain files
```

## Custom Configuration

### Creating a Custom Config File

Start with an existing config and modify it:

```bash
cp prtoe_standard.yaml my_analysis.yaml
```

### Adding Custom Parameters

```yaml
params:
  my_param:
    prior:
      min: 0.0
      max: 1.0
    ref: 0.5
    proposal: 0.1
    latex: my_param
```

### Using Different Likelihoods

```yaml
likelihood:
  planck_2018_lowl.TT: null
  planck_2018_lowl.EE: null
  # Add your custom likelihoods here
```

## Running the Validation Suite

To validate your installation and ensure numerical correctness:

```bash
# Run numerical validation
python validate_numerical.py

# Run comprehensive test suite
python test_comprehensive.py
```

Both should pass all tests for a working installation.

## Troubleshooting

### Common Issues

#### 1. "Configuration file not found"
- **Solution**: Check the filename is correct (case-sensitive). Use `prtoe_standard.yaml` not `prtoe_Standard.yaml`.

#### 2. "No module named 'classy'"
- **Solution**: The CLASS library needs to be compiled. Run `python run_cosmicforge.py --test-toy` to trigger automatic compilation.

#### 3. "Failed to import cobaya"
- **Solution**: Install cobaya: `pip install cobaya`

#### 4. Segmentation fault with pytest
- **Solution**: Use unittest instead: `python -m unittest test_comprehensive.py`

#### 5. "Process won't abort from dashboard"
- **Solution**: Use `kill -9 PID` or the script will automatically clean up zombie processes.

## Advanced Usage

### Custom Physical Constraints

Add constraints to your YAML file:

```yaml
physical_constraints:
  - name: age_constraint
    derived: age
    min: 12.0
    max: 15.5
    weight: 20.0
  - name: V0_prtoe_constraint
    expression: "1.0 - (omega_b + omega_cdm) / (H0/100)**2"
    min: 0.0
    max: 1.0
    weight: 500.0
```

### Seeding PolyChord with Optimizer Results

```bash
python run_cosmicforge.py config.yaml --seed-polychord --seed-nlive 200
```

This runs the optimizer first, then uses the results to seed a PolyChord analysis.

## Performance Optimization

- **Use more cores**: `--cores N` where N is the number of CPU cores
- **Reduce MCMC steps for testing**: `--mcmc-steps 1000`
- **Disable MCMC entirely**: `--mcmc-steps 0`
- **Use faster optimizer**: `--method bobyqa`

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Run the test suite: `python test_comprehensive.py`
5. Submit a pull request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Support

For issues, questions, or contributions:

- **GitHub Issues**: https://github.com/your-repo/prtoe_class/issues
- **Documentation**: See the `doc/` directory and `README.md`
- **Contact**: Your contact information

---

**Last updated**: 2026-06-29
**Version**: PRTOE_COSMICFORGE v1.0
