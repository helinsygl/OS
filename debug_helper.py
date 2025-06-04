#!/usr/bin/env python3
"""
GTU-C312 Debug Helper
CSE 312 Operating Systems Project
Author: Helin Sygl (helinsygl)
Date: 2025-06-04 11:40:30 UTC
"""

import sys
import os
from typing import Dict, List, Tuple, Optional

class GTUDebugHelper:
    def __init__(self):
        self.errors = []
        self.warnings = []
        self.data_section = {}
        self.instruction_section = {}
        
    def check_file_format(self, filename: str) -> bool:
        """Check if program file format is correct"""
        print(f"🔍 Analyzing file: {filename}")
        print("=" * 50)
        
        if not os.path.exists(filename):
            print(f"❌ File not found: {filename}")
            return False
            
        try:
            with open(filename, 'r', encoding='utf-8') as f:
                lines = f.readlines()
        except Exception as e:
            print(f"❌ Error reading file: {e}")
            return False
        
        return self._analyze_file_structure(lines, filename)
    
    def _analyze_file_structure(self, lines: List[str], filename: str) -> bool:
        """Analyze the complete file structure"""
        has_data_section = False
        has_instruction_section = False
        data_lines = 0
        instruction_lines = 0
        current_section = None
        section_line_start = 0
        
        print("📋 File Structure Analysis:")
        print("-" * 30)
        
        for i, line in enumerate(lines, 1):
            original_line = line
            line = line.strip()
            
            # Section markers
            if 'Begin Data Section' in line:
                has_data_section = True
                current_section = 'data'
                section_line_start = i
                print(f"✓ Data section starts at line {i}")
                
            elif 'End Data Section' in line:
                current_section = None
                print(f"✓ Data section ends at line {i} ({data_lines} data entries)")
                
            elif 'Begin Instruction Section' in line:
                has_instruction_section = True
                current_section = 'instruction'
                section_line_start = i
                print(f"✓ Instruction section starts at line {i}")
                
            elif 'End Instruction Section' in line:
                current_section = None
                print(f"✓ Instruction section ends at line {i} ({instruction_lines} instructions)")
                
            # Parse content
            elif line and not line.startswith('#'):
                if current_section == 'data':
                    self._parse_data_line(line, i)
                    data_lines += 1
                elif current_section == 'instruction':
                    self._parse_instruction_line(line, i)
                    instruction_lines += 1
        
        # Summary
        print("\n📊 Structure Summary:")
        print(f"   Data section found: {'✓' if has_data_section else '✗'}")
        print(f"   Instruction section found: {'✓' if has_instruction_section else '✗'}")
        print(f"   Data entries: {data_lines}")
        print(f"   Instructions: {instruction_lines}")
        
        success = has_data_section and has_instruction_section
        
        if success:
            self._validate_content()
            self._check_memory_layout()
            self._analyze_program_flow()
        
        self._print_issues()
        
        return success and len(self.errors) == 0
    
    def _parse_data_line(self, line: str, line_num: int):
        """Parse and validate data section line"""
        clean_line = line.split('#')[0].strip()
        if not clean_line:
            return
            
        parts = clean_line.split()
        if len(parts) >= 2:
            try:
                addr = int(parts[0])
                value = int(parts[1])
                
                if addr in self.data_section:
                    self.warnings.append(f"Line {line_num}: Duplicate address {addr}")
                
                self.data_section[addr] = {
                    'value': value,
                    'line': line_num,
                    'raw': line
                }
                
            except ValueError:
                self.errors.append(f"Line {line_num}: Invalid data format - {line}")
        else:
            self.errors.append(f"Line {line_num}: Incomplete data entry - {line}")
    
    def _parse_instruction_line(self, line: str, line_num: int):
        """Parse and validate instruction section line"""
        clean_line = line.split('#')[0].strip()
        if not clean_line:
            return
            
        parts = clean_line.split(None, 1)
        if len(parts) >= 2:
            try:
                addr = int(parts[0])
                instruction = parts[1].strip()
                
                if addr in self.instruction_section:
                    self.warnings.append(f"Line {line_num}: Duplicate instruction address {addr}")
                
                self.instruction_section[addr] = {
                    'instruction': instruction,
                    'line': line_num,
                    'raw': line
                }
                
                # Validate instruction format
                self._validate_instruction(instruction, addr, line_num)
                
            except ValueError:
                self.errors.append(f"Line {line_num}: Invalid instruction address - {line}")
        else:
            self.errors.append(f"Line {line_num}: Incomplete instruction - {line}")
    
    def _validate_instruction(self, instruction: str, addr: int, line_num: int):
        """Validate individual instruction syntax"""
        parts = instruction.split()
        if not parts:
            return
            
        cmd = parts[0].upper()
        
        # Valid GTU-C312 instructions
        valid_instructions = {
            'SET': 2,      # SET value address
            'CPY': 2,      # CPY src dst
            'CPYI': 2,     # CPYI src_addr dst
            'CPYI2': 2,    # CPYI2 src_addr dst_addr
            'ADD': 2,      # ADD addr value
            'ADDI': 2,     # ADDI addr1 addr2
            'SUBI': 2,     # SUBI addr1 addr2
            'JIF': 2,      # JIF addr jump_addr
            'PUSH': 1,     # PUSH addr
            'POP': 1,      # POP addr
            'CALL': 1,     # CALL addr
            'RET': 0,      # RET
            'HLT': 0,      # HLT
            'USER': 1,     # USER addr
            'SYSCALL': -1  # SYSCALL PRN/HLT/YIELD [args]
        }
        
        if cmd not in valid_instructions:
            self.errors.append(f"Line {line_num}: Unknown instruction '{cmd}' at address {addr}")
            return
        
        expected_args = valid_instructions[cmd]
        actual_args = len(parts) - 1
        
        if cmd == 'SYSCALL':
            if actual_args < 1:
                self.errors.append(f"Line {line_num}: SYSCALL missing type at address {addr}")
            elif parts[1].upper() == 'PRN' and actual_args != 2:
                self.errors.append(f"Line {line_num}: SYSCALL PRN requires 1 argument at address {addr}")
            elif parts[1].upper() in ['HLT', 'YIELD'] and actual_args != 1:
                self.errors.append(f"Line {line_num}: SYSCALL {parts[1]} requires no arguments at address {addr}")
        elif expected_args != actual_args:
            self.errors.append(f"Line {line_num}: {cmd} expects {expected_args} arguments, got {actual_args} at address {addr}")
    
    def _validate_content(self):
        """Validate memory addresses and values"""
        print("\n🔍 Content Validation:")
        print("-" * 25)
        
        # Check system registers (0-20)
        required_registers = [0, 1, 2, 3]  # PC, SP, syscall_result, instruction_count
        
        for reg in required_registers:
            if reg in self.data_section:
                value = self.data_section[reg]['value']
                if reg == 0 and value not in self.instruction_section:
                    self.warnings.append(f"PC points to {value} but no instruction found there")
                elif reg == 1 and value < 1000:
                    self.warnings.append(f"Stack pointer {value} seems too low")
                print(f"   Register {reg}: {value}")
            else:
                self.errors.append(f"Missing required register {reg}")
        
        # Check for memory conflicts
        data_addrs = set(self.data_section.keys())
        inst_addrs = set(self.instruction_section.keys())
        
        conflicts = data_addrs.intersection(inst_addrs)
        if conflicts:
            self.errors.append(f"Address conflicts between data and instructions: {conflicts}")
        
        print(f"   Data addresses: {len(data_addrs)} ({min(data_addrs) if data_addrs else 'N/A'} - {max(data_addrs) if data_addrs else 'N/A'})")
        print(f"   Instruction addresses: {len(inst_addrs)} ({min(inst_addrs) if inst_addrs else 'N/A'} - {max(inst_addrs) if inst_addrs else 'N/A'})")
    
    def _check_memory_layout(self):
        """Check GTU-C312 memory layout requirements"""
        print("\n🏗️  Memory Layout Check:")
        print("-" * 25)
        
        # Expected layout from assignment
        regions = {
            "System Registers": (0, 20),
            "OS Area": (21, 999),
            "Thread 1": (1000, 1999),
            "Thread 2": (2000, 2999),
            "Thread 3": (3000, 3999),
            "Additional Threads": (4000, 10999)
        }
        
        all_addrs = set(self.data_section.keys()) | set(self.instruction_section.keys())
        
        for region_name, (start, end) in regions.items():
            addrs_in_region = [addr for addr in all_addrs if start <= addr <= end]
            if addrs_in_region:
                print(f"   {region_name}: {len(addrs_in_region)} addresses ({min(addrs_in_region)}-{max(addrs_in_region)})")
            else:
                if region_name in ["System Registers", "Thread 1"]:  # Required regions
                    self.warnings.append(f"No addresses found in {region_name} region")
    
    def _analyze_program_flow(self):
        """Analyze program execution flow"""
        print("\n🔄 Program Flow Analysis:")
        print("-" * 28)
        
        if 0 in self.data_section:
            start_pc = self.data_section[0]['value']
            print(f"   Program starts at: {start_pc}")
            
            if start_pc in self.instruction_section:
                print(f"   First instruction: {self.instruction_section[start_pc]['instruction']}")
            else:
                self.errors.append(f"Start PC {start_pc} has no instruction")
        
        # Find potential jump targets
        jump_targets = set()
        for addr, inst_info in self.instruction_section.items():
            instruction = inst_info['instruction']
            parts = instruction.split()
            
            if len(parts) >= 2:
                cmd = parts[0].upper()
                if cmd in ['JIF', 'CALL', 'USER']:
                    try:
                        if cmd == 'USER':
                            # USER instruction jumps to address stored in memory
                            target_addr = int(parts[1])
                            if target_addr in self.data_section:
                                actual_target = self.data_section[target_addr]['value']
                                jump_targets.add(actual_target)
                        else:
                            target = int(parts[-1])
                            jump_targets.add(target)
                    except ValueError:
                        pass
        
        print(f"   Jump targets found: {len(jump_targets)}")
        for target in sorted(jump_targets):
            if target in self.instruction_section:
                print(f"     → {target}: {self.instruction_section[target]['instruction']}")
            else:
                self.warnings.append(f"Jump target {target} has no instruction")
        
        # Check for HLT instructions
        halt_count = sum(1 for inst_info in self.instruction_section.values() 
                        if inst_info['instruction'].upper().startswith('HLT'))
        print(f"   HLT instructions: {halt_count}")
        
        if halt_count == 0:
            self.warnings.append("No HLT instruction found - program may run forever")
    
    def _print_issues(self):
        """Print all errors and warnings"""
        print("\n" + "=" * 50)
        
        if self.errors:
            print("❌ ERRORS:")
            for error in self.errors:
                print(f"   • {error}")
        
        if self.warnings:
            print("⚠️  WARNINGS:")
            for warning in self.warnings:
                print(f"   • {warning}")
        
        if not self.errors and not self.warnings:
            print("✅ No issues found!")
        
        print("=" * 50)
    
    def generate_memory_map(self, filename: str):
        """Generate memory map visualization"""
        print(f"\n🗺️  Memory Map for {filename}:")
        print("=" * 40)
        
        all_addrs = {}
        
        # Add data addresses
        for addr, info in self.data_section.items():
            all_addrs[addr] = f"DATA: {info['value']}"
        
        # Add instruction addresses
        for addr, info in self.instruction_section.items():
            all_addrs[addr] = f"INST: {info['instruction'][:30]}..."
        
        # Sort and display
        for addr in sorted(all_addrs.keys()):
            region = self._get_memory_region(addr)
            print(f"{addr:4d} | {region:15} | {all_addrs[addr]}")
    
    def _get_memory_region(self, addr: int) -> str:
        """Get memory region name for address"""
        if 0 <= addr <= 20:
            return "SYS_REGISTERS"
        elif 21 <= addr <= 999:
            return "OS_AREA"
        elif 1000 <= addr <= 1999:
            return "THREAD_1"
        elif 2000 <= addr <= 2999:
            return "THREAD_2"
        elif 3000 <= addr <= 3999:
            return "THREAD_3"
        elif 4000 <= addr <= 10999:
            return f"THREAD_{4 + (addr-4000)//1000}"
        else:
            return "UNKNOWN"


def main():
    """Main debug function"""
    print("🔧 GTU-C312 Debug Helper")
    print(f"Author: helinsygl")
    print(f"Date: 2025-06-04 11:40:30 UTC")
    print("=" * 50)
    
    if len(sys.argv) < 2:
        print("Usage: python3 debug_helper.py <program_file> [options]")
        print("\nOptions:")
        print("  -m, --memory-map    Show detailed memory map")
        print("  -v, --verbose       Verbose output")
        print("\nExample:")
        print("  python3 debug_helper.py sorting_test.txt -m")
        sys.exit(1)
    
    filename = sys.argv[1]
    show_memory_map = '-m' in sys.argv or '--memory-map' in sys.argv
    verbose = '-v' in sys.argv or '--verbose' in sys.argv
    
    # Create debug helper and analyze file
    debugger = GTUDebugHelper()
    success = debugger.check_file_format(filename)
    
    if show_memory_map:
        debugger.generate_memory_map(filename)
    
    # Exit with appropriate code
    if success:
        print("\n✅ File analysis completed successfully!")
        sys.exit(0)
    else:
        print("\n❌ File analysis found issues!")
        sys.exit(1)


if __name__ == "__main__":
    main()