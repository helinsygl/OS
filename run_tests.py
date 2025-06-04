#!/usr/bin/env python3
"""
GTU-C312 Automated Test Runner
Author: helinsygl
Date: 2025-06-04 14:25:46 UTC
"""

import subprocess
import sys
import os
from datetime import datetime

def run_test(program_file: str, debug_mode: int = 0):
    """Run a single test with the CPU simulator"""
    print(f"\n🧪 Testing: {program_file} (Debug Mode: {debug_mode})")
    print("-" * 50)
    
    try:
        # Run the simulator
        result = subprocess.run([
            sys.executable, "cpu_simulator_fixed.py", 
            program_file, "-D", str(debug_mode)
        ], capture_output=True, text=True, timeout=30)
        
        if result.returncode == 0:
            print("✅ Test passed!")
            print("STDOUT:", result.stdout[-500:])  # Last 500 chars
        else:
            print("❌ Test failed!")
            print("STDERR:", result.stderr)
            
    except subprocess.TimeoutExpired:
        print("⏰ Test timed out!")
    except Exception as e:
        print(f"💥 Test error: {e}")

def main():
    """Run all tests"""
    print("🎯 GTU-C312 Automated Test Suite")
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}")
    print("=" * 60)
    
    # Test files to run
    test_files = [
        "fixed_multithreading_os.txt",
        "full_multithreading_os.txt"  # If you want to compare
    ]
    
    # Debug modes to test
    debug_modes = [0, 1, 3]
    
    for test_file in test_files:
        if os.path.exists(test_file):
            for debug_mode in debug_modes:
                run_test(test_file, debug_mode)
        else:
            print(f"⚠️ Test file not found: {test_file}")
    
    print("\n🏁 All tests completed!")
    print("📁 Check outputs/ directory for detailed results")

if __name__ == "__main__":
    main()