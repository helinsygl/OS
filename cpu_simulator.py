#!/usr/bin/env python3
"""
GTU-C312 CPU Simulator
CSE 312 Operating Systems Project
Author: Helin Sygl
Date: 2025-06-04
"""

import sys
import time
from typing import Dict, List, Optional, Any

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
        
        print(f"GTU-C312 CPU Simulator initialized")
        print(f"Debug Mode: {debug_mode}")
        print(f"Memory Size: {len(self.memory)} addresses")
        
    def load_program(self, filename: str):
        """Load GTU-C312 program file"""
        try:
            with open(filename, 'r', encoding='utf-8') as f:
                content = f.read()
            
            self._parse_and_load(content)
            print(f"✓ Program loaded successfully: {filename}")
            
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
        instruction_base = 0
        
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
                print(f"Parse error at line {line_num}: {line}")
                print(f"Error: {e}")
                continue
    
    def _load_data_line(self, line: str):
        """Load data section line into memory"""
        # Remove comments
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
        # Remove comments
        clean_line = line.split('#')[0].strip()
        if not clean_line:
            return
            
        parts = clean_line.split(None, 1)  # Split into address and instruction
        if len(parts) >= 2:
            try:
                addr = int(parts[0])
                instruction = parts[1].strip()
                
                self.instructions[addr] = instruction
                
            except ValueError as e:
                print(f"Warning: Invalid instruction line: {line} - {e}")
    
    def run(self):
        """Main execution loop"""
        print("🚀 Starting GTU-C312 execution...")
        print(f"Initial PC: {self.get_pc()}")
        print(f"Initial SP: {self.get_sp()}")
        print("-" * 50)
        
        safety_counter = 0
        max_instructions = 50000  # Safety limit
        
        while not self.halted and safety_counter < max_instructions:
            try:
                self.execute_single()
                safety_counter += 1
                
                # Debug mode 2: step by step
                if self.debug_mode == 2:
                    self._debug_step()
                    
            except KeyboardInterrupt:
                print("\n⚠️ Execution interrupted by user")
                break
            except Exception as e:
                print(f"💥 Runtime error: {e}")
                print(f"PC: {self.get_pc()}")
                break
        
        if safety_counter >= max_instructions:
            print(f"⚠️ Execution stopped: reached safety limit ({max_instructions} instructions)")
        
        print("-" * 50)
        print("🏁 Execution completed")
        print(f"Total instructions executed: {self.get_instruction_count()}")
        print(f"Context switches: {self.context_switches}")
        
        # Final memory state for debug mode 0
        if self.debug_mode == 0:
            self._print_final_memory_state()
    
    def execute_single(self):
        """Execute single instruction"""
        if self.halted:
            return
            
        pc = self.get_pc()
        
        # Memory protection check (USER mode)
        if not self.kernel_mode and pc < 1000:
            print(f"💥 SEGMENTATION FAULT: Accessing kernel memory at address {pc}")
            self.halt()
            return
        
        # Get and execute instruction
        if pc in self.instructions:
            instruction = self.instructions[pc]
            
            if self.debug_mode >= 1:
                print(f"[{self.get_instruction_count():4d}] PC={pc:4d}: {instruction}")
            
            self._execute_instruction(instruction)
        else:
            # No instruction at PC - check if it's a data value
            if pc < len(self.memory) and isinstance(self.memory[pc], int):
                print(f"⚠️ No instruction at PC={pc}, treating as data, halting")
            else:
                print(f"⚠️ Invalid PC={pc}, halting")
            self.halt()
            return
        
        # Update instruction counter
        self.memory[3] += 1
        
        # Debug outputs
        if self.debug_mode == 1:
            self._print_memory_state()
        elif self.debug_mode == 3:
            self._print_thread_state()
    
    def _execute_instruction(self, instruction: str):
        """Execute a GTU-C312 instruction"""
        parts = instruction.strip().split()
        if not parts:
            self.set_pc(self.get_pc() + 1)
            return
        
        cmd = parts[0].upper()
        
        try:
            if cmd == 'SET':
                # SET B A - Set memory A to value B
                value = int(parts[1])
                addr = int(parts[2])
                self._check_memory_access(addr, "write")
                self.memory[addr] = value
                self.set_pc(self.get_pc() + 1)
                
            elif cmd == 'CPY':
                # CPY A1 A2 - Copy memory A1 to A2
                src = int(parts[1])
                dst = int(parts[2])
                self._check_memory_access(src, "read")
                self._check_memory_access(dst, "write")
                self.memory[dst] = self.memory[src]
                self.set_pc(self.get_pc() + 1)
                
            elif cmd == 'CPYI':
                # CPYI A1 A2 - Copy memory[A1] to A2 (indirect source)
                src_addr = int(parts[1])
                dst = int(parts[2])
                self._check_memory_access(src_addr, "read")
                src_indirect = self.memory[src_addr]
                self._check_memory_access(src_indirect, "read")
                self._check_memory_access(dst, "write")
                self.memory[dst] = self.memory[src_indirect]
                self.set_pc(self.get_pc() + 1)
                
            elif cmd == 'CPYI2':
                # CPYI2 A1 A2 - Copy memory[A1] to memory[A2] (both indirect)
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
                # ADD A B - Add B to memory A
                addr = int(parts[1])
                value = int(parts[2])
                self._check_memory_access(addr, "write")
                self.memory[addr] += value
                self.set_pc(self.get_pc() + 1)
                
            elif cmd == 'ADDI':
                # ADDI A1 A2 - Add memory[A2] to memory[A1]
                addr1 = int(parts[1])
                addr2 = int(parts[2])
                self._check_memory_access(addr1, "write")
                self._check_memory_access(addr2, "read")
                self.memory[addr1] += self.memory[addr2]
                self.set_pc(self.get_pc() + 1)
                
            elif cmd == 'SUBI':
                # SUBI A1 A2 - Subtract memory[A2] from memory[A1], store in A2
                addr1 = int(parts[1])
                addr2 = int(parts[2])
                self._check_memory_access(addr1, "read")
                self._check_memory_access(addr2, "write")
                result = self.memory[addr1] - self.memory[addr2]
                self.memory[addr2] = result
                self.set_pc(self.get_pc() + 1)
                
            elif cmd == 'JIF':
                # JIF A C - Jump to C if memory[A] <= 0
                addr = int(parts[1])
                jump_addr = int(parts[2])
                self._check_memory_access(addr, "read")
                if self.memory[addr] <= 0:
                    self.set_pc(jump_addr)
                else:
                    self.set_pc(self.get_pc() + 1)
                    
            elif cmd == 'PUSH':
                # PUSH A - Push memory[A] onto stack
                addr = int(parts[1])
                self._check_memory_access(addr, "read")
                sp = self.get_sp()
                if sp <= 0:
                    raise RuntimeError("Stack overflow")
                self.memory[sp] = self.memory[addr]
                self.set_sp(sp - 1)
                self.set_pc(self.get_pc() + 1)
                
            elif cmd == 'POP':
                # POP A - Pop from stack to memory[A]
                addr = int(parts[1])
                self._check_memory_access(addr, "write")
                sp = self.get_sp() + 1
                if sp >= len(self.memory):
                    raise RuntimeError("Stack underflow")
                self.set_sp(sp)
                self.memory[addr] = self.memory[sp]
                self.set_pc(self.get_pc() + 1)
                
            elif cmd == 'CALL':
                # CALL C - Call subroutine at C
                call_addr = int(parts[1])
                sp = self.get_sp()
                if sp <= 0:
                    raise RuntimeError("Stack overflow in CALL")
                # Push return address
                self.memory[sp] = self.get_pc() + 1
                self.set_sp(sp - 1)
                self.set_pc(call_addr)
                
            elif cmd == 'RET':
                # RET - Return from subroutine
                sp = self.get_sp() + 1
                if sp >= len(self.memory):
                    raise RuntimeError("Stack underflow in RET")
                self.set_sp(sp)
                return_addr = self.memory[sp]
                self.set_pc(return_addr)
                
            elif cmd == 'HLT':
                # HLT - Halt CPU
                print("🛑 CPU HALT instruction executed")
                self.halt()
                
            elif cmd == 'USER':
                # USER A - Switch to user mode and jump to memory[A]
                addr = int(parts[1])
                self._check_memory_access(addr, "read")
                target_addr = self.memory[addr]
                print(f"🔄 Switching to USER mode, jumping to address {target_addr}")
                self.kernel_mode = False
                self.context_switches += 1
                self.set_pc(target_addr)
                
            elif cmd == 'SYSCALL':
                # SYSCALL - Handle system calls
                self._handle_syscall(parts[1:])
                
            else:
                print(f"⚠️ Unknown instruction: {cmd}")
                self.set_pc(self.get_pc() + 1)
                
        except (IndexError, ValueError) as e:
            print(f"💥 Instruction format error: {instruction}")
            print(f"Error: {e}")
            self.set_pc(self.get_pc() + 1)
        except (MemoryError, RuntimeError) as e:
            print(f"💥 Runtime error: {e}")
            self.halt()
    
    def _handle_syscall(self, args: List[str]):
        """Handle system calls"""
        if not args:
            print("⚠️ SYSCALL with no arguments")
            self.set_pc(self.get_pc() + 1)
            return
        
        # Switch to kernel mode
        was_kernel = self.kernel_mode
        self.kernel_mode = True
        
        syscall_type = args[0].upper()
        
        if syscall_type == 'PRN':
            # SYSCALL PRN A - Print memory[A]
            if len(args) > 1:
                try:
                    addr = int(args[1])
                    self._check_memory_access(addr, "read")
                    value = self.memory[addr]
                    print(f"📤 OUTPUT: {value}")
                    # Store result in system call result register
                    self.memory[2] = value
                except (ValueError, MemoryError) as e:
                    print(f"💥 SYSCALL PRN error: {e}")
            else:
                print("⚠️ SYSCALL PRN missing address argument")
                
        elif syscall_type == 'HLT':
            # SYSCALL HLT - Halt current thread
            print("🛑 SYSCALL HLT - Thread termination requested")
            self.halt()
            
        elif syscall_type == 'YIELD':
            # SYSCALL YIELD - Yield CPU to scheduler
            print("🔄 SYSCALL YIELD - Thread yielding CPU")
            self.context_switches += 1
            # In a real OS, this would trigger scheduler
            # For simulation, we continue execution
            
        else:
            print(f"⚠️ Unknown system call: {syscall_type}")
        
        if not self.halted:
            self.set_pc(self.get_pc() + 1)
    
    def _check_memory_access(self, addr: int, access_type: str):
        """Check memory access permissions"""
        # Bounds check
        if addr < 0 or addr >= len(self.memory):
            raise MemoryError(f"Memory address out of bounds: {addr}")
        
        # Protection check (USER mode cannot access < 1000)
        if not self.kernel_mode and addr < 1000:
            raise MemoryError(f"Memory protection violation: {access_type} access to address {addr}")
    
    # Register access methods
    def get_pc(self) -> int:
        """Get Program Counter"""
        return self.memory[0]
    
    def set_pc(self, value: int):
        """Set Program Counter"""
        self.memory[0] = value
    
    def get_sp(self) -> int:
        """Get Stack Pointer"""
        return self.memory[1]
    
    def set_sp(self, value: int):
        """Set Stack Pointer"""
        self.memory[1] = value
    
    def get_instruction_count(self) -> int:
        """Get instruction execution count"""
        return self.memory[3]
    
    def halt(self):
        """Halt the CPU"""
        self.halted = True
        print("🛑 CPU HALTED")
    
    def is_halted(self) -> bool:
        """Check if CPU is halted"""
        return self.halted
    
    def _debug_step(self):
        """Debug mode 2: step by step execution"""
        self._print_current_state()
        try:
            user_input = input("Press Enter to continue (or 'q' to quit): ").strip().lower()
            if user_input == 'q':
                print("🛑 User requested quit")
                self.halt()
        except KeyboardInterrupt:
            print("\n🛑 User interrupted")
            self.halt()
    
    def _print_current_state(self):
        """Print current CPU state"""
        print(f"\n📊 === CPU STATE ===", file=sys.stderr)
        print(f"PC: {self.get_pc():4d} | SP: {self.get_sp():4d} | Mode: {'KERNEL' if self.kernel_mode else 'USER'}", file=sys.stderr)
        print(f"Instructions: {self.get_instruction_count():4d} | Context Switches: {self.context_switches}", file=sys.stderr)
        
        # Show some relevant memory
        pc = self.get_pc()
        if pc in self.instructions:
            print(f"Next: {self.instructions[pc]}", file=sys.stderr)
        
        print("Recent memory changes:", file=sys.stderr)
        for addr in range(0, min(21, len(self.memory))):
            if self.memory[addr] != 0:
                print(f"  [{addr:3d}] = {self.memory[addr]:6d}", file=sys.stderr)
        print("==================\n", file=sys.stderr)
    
    def _print_memory_state(self):
        """Print full memory state (debug mode 1)"""
        print(f"\n📋 === MEMORY DUMP ===", file=sys.stderr)
        print(f"PC: {self.get_pc()} | SP: {self.get_sp()} | Instructions: {self.get_instruction_count()}", file=sys.stderr)
        
        # Print non-zero memory locations
        for addr in range(len(self.memory)):
            if self.memory[addr] != 0:
                print(f"MEM[{addr:4d}] = {self.memory[addr]:8d}", file=sys.stderr)
        print("====================\n", file=sys.stderr)
    
    def _print_thread_state(self):
        """Print thread state information (debug mode 3)"""
        print(f"\n🧵 === THREAD STATE ===", file=sys.stderr)
        print(f"PC: {self.get_pc()} | Mode: {'KERNEL' if self.kernel_mode else 'USER'}", file=sys.stderr)
        print(f"Instructions: {self.get_instruction_count()} | Context Switches: {self.context_switches}", file=sys.stderr)
        
        # Try to identify current thread based on PC
        pc = self.get_pc()
        if pc < 1000:
            print("Current: OS/Kernel", file=sys.stderr)
        elif 1000 <= pc < 2000:
            print("Current: Thread 1 (Sorting)", file=sys.stderr)
        elif 2000 <= pc < 3000:
            print("Current: Thread 2 (Search)", file=sys.stderr)
        elif 3000 <= pc < 4000:
            print("Current: Thread 3 (Custom)", file=sys.stderr)
        else:
            print(f"Current: Thread at {pc}", file=sys.stderr)
        
        print("======================\n", file=sys.stderr)
    
    def _print_final_memory_state(self):
        """Print final memory state (debug mode 0)"""
        print(f"\n🏁 === FINAL MEMORY STATE ===", file=sys.stderr)
        print(f"Total Instructions: {self.get_instruction_count()}", file=sys.stderr)
        print(f"Context Switches: {self.context_switches}", file=sys.stderr)
        print(f"Final PC: {self.get_pc()}", file=sys.stderr)
        
        # Print all non-zero memory
        non_zero_count = 0
        for addr in range(len(self.memory)):
            if self.memory[addr] != 0:
                print(f"MEM[{addr:4d}] = {self.memory[addr]:8d}", file=sys.stderr)
                non_zero_count += 1
        
        print(f"Non-zero memory locations: {non_zero_count}", file=sys.stderr)
        print("============================\n", file=sys.stderr)


def main():
    """Main function"""
    if len(sys.argv) < 2:
        print("Usage: python cpu_simulator.py <program_file> [-D <debug_mode>]")
        print("\nDebug modes:")
        print("  0 - Final memory state only")
        print("  1 - Memory state after each instruction")
        print("  2 - Step-by-step execution (interactive)")
        print("  3 - Thread state information")
        print("\nExample: python cpu_simulator.py os_program.txt -D 1")
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
    
    print("🖥️  GTU-C312 CPU Simulator")
    print("=" * 50)
    print(f"Program: {filename}")
    print(f"Debug Mode: {debug_mode}")
    print(f"Author: Helin Sygl")
    print(f"Date: 2025-06-04")
    print("=" * 50)
    
    # Create and run CPU
    cpu = GTUC312CPU(debug_mode)
    cpu.load_program(filename)
    cpu.run()
    
    print("\n✅ Simulation completed successfully!")


if __name__ == "__main__":
    main()