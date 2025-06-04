#!/usr/bin/env python3
"""
GTU-C312 CPU Simulator - COMPREHENSIVE FIX
CSE 312 Operating Systems Project
Author: helinsygl
Date: 2025-06-04 14:25:46 UTC
"""

import sys
import time
from typing import Dict, List, Optional, Any
from output_manager import OutputManager

class GTUC312CPU:
    def __init__(self, debug_mode: int = 0):
        # 20000 address memory space
        self.memory = [0] * 20000
        
        # CPU state
        self.halted = False
        self.kernel_mode = True
        self.debug_mode = debug_mode
        
        # Instruction storage (address -> instruction string)
        self.instructions = {}
        
        # Statistics
        self.total_instructions = 0
        self.context_switches = 0
        
        # OS scheduler address for SYSCALL YIELD returns
        self.os_scheduler_address = 102  # Where OS scheduler loop starts
        
        # Output manager
        self.output_manager = OutputManager()
        
        print(f"GTU-C312 CPU Simulator initialized")
        print(f"Debug Mode: {debug_mode}")
        print(f"Memory Size: {len(self.memory)} addresses")
        
    def load_program(self, filename: str):
        """Load GTU-C312 program file"""
        try:
            with open(filename, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Start output session
            self.output_manager.start_session(filename.replace('.txt', ''), self.debug_mode)
            
            self._parse_and_load(content)
            print(f"✓ Program loaded successfully: {filename}")
            self.output_manager.log(f"✓ Program loaded successfully: {filename}")
            
        except FileNotFoundError:
            print(f"✗ Error: File '{filename}' not found")
            sys.exit(1)
        except Exception as e:
            print(f"✗ Error loading program: {e}")
            sys.exit(1)
    
    def _parse_and_load(self, content: str):
        """Parse program content and load into memory"""
        lines = content.split('\n')
        current_section = None
        
        for line_num, line in enumerate(lines, 1):
            line = line.strip()
            
            # Skip empty lines and comments
            if not line or line.startswith('#'):
                continue
                
            try:
                # Section markers
                if 'Begin Data Section' in line:
                    current_section = 'data'
                    continue
                elif 'End Data Section' in line:
                    current_section = None
                    continue
                elif 'Begin Instruction Section' in line:
                    current_section = 'instruction'
                    continue
                elif 'End Instruction Section' in line:
                    current_section = None
                    continue
                
                # Parse content based on section
                if current_section == 'data':
                    self._load_data_line(line)
                elif current_section == 'instruction':
                    self._load_instruction_line(line)
                    
            except Exception as e:
                error_msg = f"Parse error at line {line_num}: {line} - {e}"
                print(error_msg)
                self.output_manager.log_error(error_msg)
                continue
    
    def _load_data_line(self, line: str):
        """Load data section line into memory"""
        clean_line = line.split('#')[0].strip()
        if not clean_line:
            return
            
        parts = clean_line.split()
        if len(parts) >= 2:
            try:
                addr = int(parts[0])
                value = int(parts[1])
                
                if 0 <= addr < len(self.memory):
                    self.memory[addr] = value
                else:
                    print(f"Warning: Data address {addr} out of bounds")
                    
            except ValueError as e:
                print(f"Warning: Invalid data line: {line} - {e}")
    
    def _load_instruction_line(self, line: str):
        """Load instruction line into instruction memory"""
        clean_line = line.split('#')[0].strip()
        if not clean_line:
            return
            
        parts = clean_line.split(None, 1)
        if len(parts) >= 2:
            try:
                addr = int(parts[0])
                instruction = parts[1].strip()
                
                self.instructions[addr] = instruction
                
            except ValueError as e:
                print(f"Warning: Invalid instruction line: {line} - {e}")
    
    def run(self):
        """Main execution loop"""
        start_msg = f"🚀 Starting GTU-C312 execution..."
        print(start_msg)
        self.output_manager.log(start_msg)
        
        initial_info = f"Initial PC: {self.get_pc()}, SP: {self.get_sp()}"
        print(initial_info)
        self.output_manager.log(initial_info)
        self.output_manager.log("-" * 50)
        
        safety_counter = 0
        max_instructions = 10000  # Reduced for better testing
        
        while not self.halted and safety_counter < max_instructions:
            try:
                self.execute_single()
                safety_counter += 1
                
                # Debug mode 2: step by step
                if self.debug_mode == 2:
                    self._debug_step()
                    
            except KeyboardInterrupt:
                interrupt_msg = "\n⚠️ Execution interrupted by user"
                print(interrupt_msg)
                self.output_manager.log(interrupt_msg)
                break
            except Exception as e:
                error_msg = f"💥 Runtime error: {e} (PC: {self.get_pc()})"
                print(error_msg)
                self.output_manager.log_error(error_msg)
                break
        
        if safety_counter >= max_instructions:
            limit_msg = f"⚠️ Execution stopped: reached safety limit ({max_instructions} instructions)"
            print(limit_msg)
            self.output_manager.log(limit_msg)
        
        # Final statistics
        final_msg = "🏁 Execution completed"
        print(final_msg)
        self.output_manager.log_final_stats(
            self.get_instruction_count(),
            self.context_switches,
            self.get_pc()
        )
        
        # Final memory state
        if self.debug_mode in [0, 1]:
            self.output_manager.log_memory_state(self.memory)
        
        # Close output session
        self.output_manager.close_session()
    
    def execute_single(self):
        """Execute single instruction"""
        if self.halted:
            return
            
        pc = self.get_pc()
        
        # Memory protection check (USER mode)
        if not self.kernel_mode and pc < 1000:
            error_msg = f"💥 SEGMENTATION FAULT: Accessing kernel memory at address {pc}"
            print(error_msg)
            self.output_manager.log_error(error_msg)
            self.halt()
            return
        
        # Get and execute instruction
        if pc in self.instructions:
            instruction = self.instructions[pc]
            
            # Log instruction execution
            if self.debug_mode >= 1:
                self.output_manager.log_instruction(
                    self.get_instruction_count(), pc, instruction
                )
            
            self._execute_instruction(instruction)
        else:
            error_msg = f"⚠️ No instruction at PC={pc}, halting"
            print(error_msg)
            self.output_manager.log_error(error_msg)
            self.halt()
            return
        
        # Update instruction counter
        self.memory[3] += 1
    
    def _execute_instruction(self, instruction: str):
        """Execute a GTU-C312 instruction"""
        parts = instruction.strip().split()
        if not parts:
            self.set_pc(self.get_pc() + 1)
            return
        
        cmd = parts[0].upper()
        
        try:
            if cmd == 'SET':
                value = int(parts[1])
                addr = int(parts[2])
                self._check_memory_access(addr, "write")
                self.memory[addr] = value
                self.set_pc(self.get_pc() + 1)
                
            elif cmd == 'CPY':
                src = int(parts[1])
                dst = int(parts[2])
                self._check_memory_access(src, "read")
                self._check_memory_access(dst, "write")
                self.memory[dst] = self.memory[src]
                self.set_pc(self.get_pc() + 1)
                
            elif cmd == 'CPYI':
                src_addr = int(parts[1])
                dst = int(parts[2])
                self._check_memory_access(src_addr, "read")
                src_indirect = self.memory[src_addr]
                self._check_memory_access(src_indirect, "read")
                self._check_memory_access(dst, "write")
                self.memory[dst] = self.memory[src_indirect]
                self.set_pc(self.get_pc() + 1)
                
            elif cmd == 'CPYI2':
                src_addr = int(parts[1])
                dst_addr = int(parts[2])
                self._check_memory_access(src_addr, "read")
                self._check_memory_access(dst_addr, "read")
                src_indirect = self.memory[src_addr]
                dst_indirect = self.memory[dst_addr]
                self._check_memory_access(src_indirect, "read")
                self._check_memory_access(dst_indirect, "write")
                self.memory[dst_indirect] = self.memory[src_indirect]
                self.set_pc(self.get_pc() + 1)
                
            elif cmd == 'ADD':
                addr = int(parts[1])
                value = int(parts[2])
                self._check_memory_access(addr, "write")
                self.memory[addr] += value
                self.set_pc(self.get_pc() + 1)
                
            elif cmd == 'ADDI':
                addr1 = int(parts[1])
                addr2 = int(parts[2])
                self._check_memory_access(addr1, "write")
                self._check_memory_access(addr2, "read")
                self.memory[addr1] += self.memory[addr2]
                self.set_pc(self.get_pc() + 1)
                
            elif cmd == 'SUBI':
                addr1 = int(parts[1])
                addr2 = int(parts[2])
                self._check_memory_access(addr1, "read")
                self._check_memory_access(addr2, "write")
                result = self.memory[addr1] - self.memory[addr2]
                self.memory[addr2] = result
                self.set_pc(self.get_pc() + 1)
                
            elif cmd == 'JIF':
                addr = int(parts[1])
                jump_addr = int(parts[2])
                self._check_memory_access(addr, "read")
                if self.memory[addr] <= 0:
                    self.set_pc(jump_addr)
                else:
                    self.set_pc(self.get_pc() + 1)
                    
            elif cmd == 'PUSH':
                addr = int(parts[1])
                self._check_memory_access(addr, "read")
                sp = self.get_sp()
                if sp <= 0:
                    raise RuntimeError("Stack overflow")
                self.memory[sp] = self.memory[addr]
                self.set_sp(sp - 1)
                self.set_pc(self.get_pc() + 1)
                
            elif cmd == 'POP':
                addr = int(parts[1])
                self._check_memory_access(addr, "write")
                sp = self.get_sp() + 1
                if sp >= len(self.memory):
                    raise RuntimeError("Stack underflow")
                self.set_sp(sp)
                self.memory[addr] = self.memory[sp]
                self.set_pc(self.get_pc() + 1)
                
            elif cmd == 'CALL':
                call_addr = int(parts[1])
                sp = self.get_sp()
                if sp <= 0:
                    raise RuntimeError("Stack overflow in CALL")
                self.memory[sp] = self.get_pc() + 1
                self.set_sp(sp - 1)
                self.set_pc(call_addr)
                
            elif cmd == 'RET':
                sp = self.get_sp() + 1
                if sp >= len(self.memory):
                    raise RuntimeError("Stack underflow in RET")
                self.set_sp(sp)
                return_addr = self.memory[sp]
                self.set_pc(return_addr)
                
            elif cmd == 'HLT':
                halt_msg = "🛑 CPU HALT instruction executed"
                print(halt_msg)
                self.output_manager.log(halt_msg)
                self.halt()
                
            elif cmd == 'USER':
                addr = int(parts[1])
                self._check_memory_access(addr, "read")
                target_addr = self.memory[addr]
                switch_msg = f"🔄 Switching to USER mode, jumping to address {target_addr}"
                print(switch_msg)
                self.output_manager.log_context_switch(switch_msg)
                self.kernel_mode = False
                self.context_switches += 1
                self.set_pc(target_addr)
                
            elif cmd == 'SYSCALL':
                self._handle_syscall(parts[1:])
                
            else:
                unknown_msg = f"⚠️ Unknown instruction: {cmd}"
                print(unknown_msg)
                self.output_manager.log_error(unknown_msg)
                self.set_pc(self.get_pc() + 1)
                
        except (IndexError, ValueError) as e:
            format_error = f"💥 Instruction format error: {instruction} - {e}"
            print(format_error)
            self.output_manager.log_error(format_error)
            self.set_pc(self.get_pc() + 1)
        except (MemoryError, RuntimeError) as e:
            runtime_error = f"💥 Runtime error: {e}"
            print(runtime_error)
            self.output_manager.log_error(runtime_error)
            self.halt()
    
    def _handle_syscall(self, args: List[str]):
        """Handle system calls - COMPREHENSIVE FIX"""
        if not args:
            error_msg = "⚠️ SYSCALL with no arguments"
            print(error_msg)
            self.output_manager.log_error(error_msg)
            self.set_pc(self.get_pc() + 1)
            return
        
        # Switch to kernel mode
        was_user_mode = not self.kernel_mode
        self.kernel_mode = True
        
        syscall_type = args[0].upper()
        
        if syscall_type == 'PRN':
            if len(args) > 1:
                try:
                    addr = int(args[1])
                    self._check_memory_access(addr, "read")
                    value = self.memory[addr]
                    self.output_manager.log_output(value)
                    self.memory[2] = value
                except (ValueError, MemoryError) as e:
                    error_msg = f"💥 SYSCALL PRN error: {e}"
                    print(error_msg)
                    self.output_manager.log_error(error_msg)
            else:
                error_msg = "⚠️ SYSCALL PRN missing address argument"
                print(error_msg)
                self.output_manager.log_error(error_msg)
            
            self.set_pc(self.get_pc() + 1)
                
        elif syscall_type == 'HLT':
            halt_msg = "🛑 SYSCALL HLT - Thread termination requested"
            print(halt_msg)
            self.output_manager.log(halt_msg)
            self.halt()
            
        elif syscall_type == 'YIELD':
            # CRITICAL FIX: Proper SYSCALL YIELD handling
            yield_msg = "🔄 SYSCALL YIELD - Thread yielding CPU"
            print(yield_msg)
            self.output_manager.log_context_switch(yield_msg)
            self.context_switches += 1
            
            if was_user_mode:
                # Switch back to kernel mode and jump to OS scheduler
                self.kernel_mode = True
                self.set_pc(self.os_scheduler_address)
                return_msg = f"🔄 Returning to OS scheduler at address {self.os_scheduler_address}"
                print(return_msg)
                self.output_manager.log_context_switch(return_msg)
            else:
                # If already in kernel mode, just continue
                self.set_pc(self.get_pc() + 1)
            
        else:
            unknown_msg = f"⚠️ Unknown system call: {syscall_type}"
            print(unknown_msg)
            self.output_manager.log_error(unknown_msg)
            self.set_pc(self.get_pc() + 1)
    
    def _check_memory_access(self, addr: int, access_type: str):
        """Check memory access permissions"""
        if addr < 0 or addr >= len(self.memory):
            raise MemoryError(f"Memory address out of bounds: {addr}")
        
        if not self.kernel_mode and addr < 1000:
            raise MemoryError(f"Memory protection violation: {access_type} access to address {addr}")
    
    # Register access methods
    def get_pc(self) -> int:
        return self.memory[0]
    
    def set_pc(self, value: int):
        self.memory[0] = value
    
    def get_sp(self) -> int:
        return self.memory[1]
    
    def set_sp(self, value: int):
        self.memory[1] = value
    
    def get_instruction_count(self) -> int:
        return self.memory[3]
    
    def halt(self):
        self.halted = True
        halt_msg = "🛑 CPU HALTED"
        print(halt_msg)
        self.output_manager.log(halt_msg)
    
    def is_halted(self) -> bool:
        return self.halted
    
    def _debug_step(self):
        """Debug mode 2: step by step execution"""
        try:
            user_input = input("Press Enter to continue (or 'q' to quit): ").strip().lower()
            if user_input == 'q':
                print("🛑 User requested quit")
                self.output_manager.log("🛑 User requested quit")
                self.halt()
        except KeyboardInterrupt:
            print("\n🛑 User interrupted")
            self.output_manager.log("🛑 User interrupted")
            self.halt()


def main():
    """Main function with enhanced output management"""
    if len(sys.argv) < 2:
        print("Usage: python cpu_simulator_fixed.py <program_file> [-D <debug_mode>]")
        print("\nDebug modes:")
        print("  0 - Final memory state only")
        print("  1 - Memory state after each instruction")
        print("  2 - Step-by-step execution (interactive)")
        print("  3 - Thread state information")
        print("\nExample: python cpu_simulator_fixed.py os_program.txt -D 1")
        sys.exit(1)
    
    filename = sys.argv[1]
    debug_mode = 0
    
    # Parse debug mode
    if len(sys.argv) >= 4 and sys.argv[2] == '-D':
        try:
            debug_mode = int(sys.argv[3])
            if debug_mode < 0 or debug_mode > 3:
                print("Debug mode must be 0, 1, 2, or 3")
                sys.exit(1)
        except ValueError:
            print("Invalid debug mode value")
            sys.exit(1)
    
    print("🖥️  GTU-C312 CPU Simulator - COMPREHENSIVE FIX")
    print("=" * 60)
    print(f"Program: {filename}")
    print(f"Debug Mode: {debug_mode}")
    print(f"Author: helinsygl")
    print(f"Date: 2025-06-04 14:25:46 UTC")
    print("=" * 60)
    
    # Create and run CPU
    cpu = GTUC312CPU(debug_mode)
    cpu.load_program(filename)
    cpu.run()
    
    print("\n✅ Simulation completed successfully!")
    print(f"📁 Check outputs/ directory for detailed logs")


if __name__ == "__main__":
    main()