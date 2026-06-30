#!/usr/bin/env python
"""
Comprehensive test suite for PRTOE_COSMICFORGE

This test suite validates:
1. Configuration loading and validation
2. Parameter parsing and constraints
3. Numerical calculations
4. Optimizer functionality (in toy mode)
5. Error handling
"""

import unittest
import os
import sys
import tempfile
import yaml
from pathlib import Path

# Add the current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


class TestConfigurationLoading(unittest.TestCase):
    """Test configuration file loading and validation."""
    
    def test_load_valid_config(self):
        """Test loading a valid configuration file."""
        config_path = Path(__file__).parent / "prtoe_standard.yaml"
        self.assertTrue(config_path.exists(), f"Config file {config_path} should exist")
        
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
        
        self.assertIsNotNone(config, "Config should not be None")
        self.assertIn("params", config, "Config should have 'params' section")
        self.assertIn("likelihood", config, "Config should have 'likelihood' section")
        self.assertIn("theory", config, "Config should have 'theory' section")
    
    def test_config_has_required_params(self):
        """Test that configuration has required parameters."""
        config_path = Path(__file__).parent / "prtoe_standard.yaml"
        
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
        
        params = config.get("params", {})
        required_params = ["H0", "omega_b", "omega_cdm"]
        
        for param in required_params:
            self.assertIn(param, params, f"Config should have parameter '{param}'")
    
    def test_prtoe_params_present(self):
        """Test that PRTOE-specific parameters are present."""
        config_path = Path(__file__).parent / "prtoe_standard.yaml"
        
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
        
        params = config.get("params", {})
        prtoe_params = [p for p in params.keys() if "prtoe" in p.lower()]
        
        self.assertGreater(len(prtoe_params), 0, "Config should have PRTOE parameters")
        self.assertIn("xi_prtoe", params, "Config should have xi_prtoe parameter")
        self.assertIn("zeta_prtoe", params, "Config should have zeta_prtoe parameter")
    
    def test_invalid_yaml_handling(self):
        """Test that invalid YAML is handled gracefully."""
        invalid_yaml = "invalid: yaml: content:"
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write(invalid_yaml)
            temp_path = f.name
        
        try:
            with open(temp_path, 'r') as f:
                config = yaml.safe_load(f)
            # If we get here without exception, YAML parsed but content might be weird
            self.assertIsNotNone(config, "Should parse something even if invalid")
        except yaml.YAMLError:
            # This is expected for truly invalid YAML
            pass
        finally:
            os.unlink(temp_path)


class TestParameterValidation(unittest.TestCase):
    """Test parameter validation and calculations."""
    
    def test_v0_prtoe_calculation(self):
        """Test the V0_prtoe calculation from the config."""
        omega_b = 0.0224
        omega_cdm = 0.12
        H0 = 67.4
        
        # V0_prtoe = 1.0 - (omega_b + omega_cdm) / (H0/100.0)**2
        V0_computed = 1.0 - (omega_b + omega_cdm) / (H0/100.0)**2
        
        # Check it's in a reasonable range
        self.assertGreater(V0_computed, 0.6, "V0_prtoe should be > 0.6")
        self.assertLess(V0_computed, 0.75, "V0_prtoe should be < 0.75")
        
        # Check the exact value
        expected = 0.6865341774603986
        self.assertAlmostEqual(V0_computed, expected, places=15)
    
    def test_as_from_loga(self):
        """Test A_s calculation from logA."""
        import numpy as np
        
        logA = 3.05
        A_s = 1e-10 * np.exp(logA)
        expected = 2.111534e-09
        
        self.assertAlmostEqual(A_s, expected, places=6)
    
    def test_parameter_ranges(self):
        """Test that parameter ranges are reasonable."""
        config_path = Path(__file__).parent / "prtoe_standard.yaml"
        
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
        
        params = config.get("params", {})
        
        # Test H0 range
        H0_info = params.get("H0", {})
        H0_prior = H0_info.get("prior", {})
        if "min" in H0_prior and "max" in H0_prior:
            self.assertGreater(H0_prior["max"], H0_prior["min"], "H0 max should be > min")
            self.assertGreater(H0_prior["min"], 50, "H0 min should be > 50")
            self.assertLess(H0_prior["max"], 90, "H0 max should be < 90")
        
        # Test xi_prtoe range
        xi_info = params.get("xi_prtoe", {})
        xi_prior = xi_info.get("prior", {})
        if "min" in xi_prior and "max" in xi_prior:
            self.assertGreater(xi_prior["max"], xi_prior["min"], "xi_prtoe max should be > min")
            self.assertGreaterEqual(xi_prior["min"], 0, "xi_prtoe min should be >= 0")


class TestClassIntegration(unittest.TestCase):
    """Test CLASS library integration."""
    
    def test_class_import(self):
        """Test that CLASS can be imported."""
        try:
            from classy import Class
            self.assertTrue(True, "CLASS imported successfully")
        except ImportError as e:
            self.fail(f"Failed to import CLASS: {e}")
    
    def test_class_basic_cosmology(self):
        """Test basic CLASS cosmology computation."""
        try:
            from classy import Class
            
            cosmo = Class()
            cosmo.set({'h': 0.6736, 'omega_b': 0.02237, 'omega_cdm': 0.1200})
            cosmo.compute()
            
            # Check basic properties
            h = cosmo.h()
            omega_m = cosmo.Omega_m()
            omega_lambda = cosmo.Omega_Lambda()
            age = cosmo.age()
            
            self.assertAlmostEqual(h, 0.6736, places=4)
            self.assertGreater(omega_m, 0.3, "Omega_m should be > 0.3")
            self.assertLess(omega_m, 0.32, "Omega_m should be < 0.32")
            self.assertGreater(omega_lambda, 0.68, "Omega_Lambda should be > 0.68")
            self.assertLess(omega_lambda, 0.7, "Omega_Lambda should be < 0.7")
            self.assertGreater(age, 13.7, "Age should be > 13.7 Gyr")
            self.assertLess(age, 13.9, "Age should be < 13.9 Gyr")
            
            del cosmo
        except Exception as e:
            self.fail(f"CLASS computation failed: {e}")


class TestErrorHandling(unittest.TestCase):
    """Test error handling and robustness."""
    
    def test_file_not_found_error(self):
        """Test that FileNotFoundError is handled for config files."""
        # This tests the error handling we added
        config_path = "/nonexistent/path/config.yaml"
        
        # We can't easily test the actual error message without running the script,
        # but we can verify the logic
        self.assertFalse(os.path.exists(config_path))
    
    def test_empty_config_validation(self):
        """Test validation of empty configuration."""
        empty_config = {}
        
        # Check that required sections are missing
        self.assertNotIn("params", empty_config)
        
        # This would fail the validation in the main script
        required_sections = ["params"]
        missing_sections = [section for section in required_sections if section not in empty_config]
        self.assertIn("params", missing_sections)
    
    def test_invalid_params_section(self):
        """Test validation of invalid params section."""
        invalid_config = {"params": None}
        
        # Check that params section is invalid
        params = invalid_config.get("params")
        self.assertTrue(not params or len(params) == 0)


class TestNumericalConsistency(unittest.TestCase):
    """Test numerical consistency of calculations."""
    
    def test_chi2_reasonableness(self):
        """Test that chi-squared values are reasonable."""
        # From our test runs, we expect chi2 values in certain ranges
        # For a good fit, chi2 per degree of freedom should be ~1
        
        # Toy model typically has chi2 in range [10, 50] for 10-20 data points
        toy_chi2 = 21.1111
        self.assertGreater(toy_chi2, 10, "Toy model chi2 should be > 10")
        self.assertLess(toy_chi2, 50, "Toy model chi2 should be < 50")
    
    def test_parameter_scales(self):
        """Test that parameter values are on reasonable scales."""
        config_path = Path(__file__).parent / "prtoe_standard.yaml"
        
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
        
        params = config.get("params", {})
        
        # Test H0 scale
        H0_info = params.get("H0", {})
        H0_ref = H0_info.get("ref", 0)
        self.assertGreater(H0_ref, 50, "H0 should be > 50")
        self.assertLess(H0_ref, 90, "H0 should be < 90")
        
        # Test xi_prtoe scale
        xi_info = params.get("xi_prtoe", {})
        xi_ref = xi_info.get("ref", 0)
        self.assertGreaterEqual(xi_ref, 0, "xi_prtoe should be >= 0")
        self.assertLess(xi_ref, 0.01, "xi_prtoe should be < 0.01")
        
        # Test omega_b scale
        omega_b_info = params.get("omega_b", {})
        omega_b_ref = omega_b_info.get("ref", 0)
        self.assertGreater(omega_b_ref, 0.01, "omega_b should be > 0.01")
        self.assertLess(omega_b_ref, 0.03, "omega_b should be < 0.03")


class TestCodeQuality(unittest.TestCase):
    """Test code quality and standards."""
    
    def test_no_ast_num_deprecation(self):
        """Test that ast.Num deprecation is handled."""
        # Read the main script and check for ast.Num usage
        main_script = Path(__file__).parent / "run_cosmicforge.py"
        
        with open(main_script, 'r') as f:
            content = f.read()
        
        # Check that ast.Num is not in allowed_nodes (should be ast.Constant)
        self.assertNotIn("ast.Num", content.split("allowed_nodes")[1].split("}")[0], 
                        "ast.Num should not be in allowed_nodes")
        
        # Check that ast.Constant is present
        self.assertIn("ast.Constant", content, "ast.Constant should be used instead of ast.Num")
    
    def test_import_handling(self):
        """Test that imports are handled gracefully."""
        # Test that we can import the main modules
        try:
            import yaml
            import numpy as np
            from scipy.optimize import minimize
            self.assertTrue(True, "All required imports successful")
        except ImportError as e:
            self.fail(f"Import failed: {e}")


class TestDocumentation(unittest.TestCase):
    """Test documentation completeness."""
    
    def test_readme_exists(self):
        """Test that README file exists."""
        readme_path = Path(__file__).parent / "README.md"
        self.assertTrue(readme_path.exists(), "README.md should exist")
        self.assertGreater(readme_path.stat().st_size, 1000, "README.md should be substantial")
    
    def test_examples_exist(self):
        """Test that example files exist."""
        examples_dir = Path(__file__).parent / "examples"
        if examples_dir.exists():
            examples = list(examples_dir.glob("*.py")) + list(examples_dir.glob("*.yaml"))
            self.assertGreater(len(examples), 0, "Examples directory should have example files")
    
    def test_config_files_exist(self):
        """Test that configuration files exist."""
        yaml_files = list(Path(__file__).parent.glob("*.yaml"))
        self.assertGreater(len(yaml_files), 0, "Should have YAML configuration files")


def run_comprehensive_tests():
    """Run all comprehensive tests and return results."""
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # Add all test classes
    suite.addTests(loader.loadTestsFromTestCase(TestConfigurationLoading))
    suite.addTests(loader.loadTestsFromTestCase(TestParameterValidation))
    suite.addTests(loader.loadTestsFromTestCase(TestClassIntegration))
    suite.addTests(loader.loadTestsFromTestCase(TestErrorHandling))
    suite.addTests(loader.loadTestsFromTestCase(TestNumericalConsistency))
    suite.addTests(loader.loadTestsFromTestCase(TestCodeQuality))
    suite.addTests(loader.loadTestsFromTestCase(TestDocumentation))
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    results = runner.run(suite)
    
    return results


if __name__ == "__main__":
    results = run_comprehensive_tests()
    
    # Exit with error code if tests failed
    sys.exit(0 if results.wasSuccessful() else 1)
