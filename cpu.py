#!/usr/bin/env python3
"""
GTU-C312 CPU Simulator - COMPLETE WORKING VERSION
CSE 312 Operating Systems Project
Author: helinsygl
Date: 2025-06-04 15:19:40 UTC
"""

import sys
import time
import os
from typing import Dict, List, Optional, Any, Tuple
from enum import Enum

class ThreadState(Enum):
    READY = 1
    RUNNING = 2
    BLOCKED = 3

class OutputManager:
    def __init__(self):
        self.output_file = None
        self.session_active = False
        self.log_buffer = []
        self.buffer_size = 100
        
    def start_session(self, program_name: str, debug_mode: int):
        """Start output session"""
        if not os.path.exists('outputs'):
            os.makedirs('outputs')
        
        timestamp = time.strftime("%Y-%m-%d_%H-%M-%S", time.localtime())
        filename = f"outputs/{program_name}_{debug_mode}_{timestamp}.txt"
        
        try:
            self.output_file = open(filename, 'w', encoding='utf-8')
            self.session_active = True
            print(f"📝 Output session started: {filename}")
        except Exception as e:
            print(f"Warning: Could not create output file: {e}")
            self.session_active = False
    
    def log(self, message: str, to_console: bool = False):
        """Log message to file and optionally to console"""
        if self.session_active:
            self.log_buffer.append(message)
            if len(self.log_buffer) >= self.buffer_size:
                self._flush_buffer()
        if to_console:
            print(message)
    
    def _flush_buffer(self):
        """Flush log buffer to file"""
        if self.session_active and self.output_file:
            self.output_file.write('\n'.join(self.log_buffer) + '\n')
            self.output_file.flush()
            self.log_buffer.clear()
    
    def log_instruction(self, count: int, pc: int, instruction: str):
        """Log instruction execution"""
        if self.session_active:
            self.log(f"[{count:04d}] PC:{pc:04d} | {instruction}")
    
    def log_context_switch(self, message: str):
        """Log context switch"""
        if self.session_active:
            self.log(f"CONTEXT: {message}")
    
    def log_error(self, message: str):
        """Log error message"""
        if self.session_active:
            self.log(f"ERROR: {message}")
    
    def log_final_stats(self, instructions: int, switches: int, final_pc: int):
        """Log final statistics"""
        if self.session_active:
            self.log("=" * 60)
            self.log("EXECUTION COMPLETED")
            self.log("=" * 60)
            self.log(f"Total Instructions Executed: {instructions}")
            self.log(f"Context Switches: {switches}")
            self.log(f"Final PC: {final_pc}")
            self.log(f"End Time: {time.strftime('%Y-%m-%d %H:%M:%S UTC', time.gmtime())}")
            self.log("=" * 60)
    
    def log_memory_state(self, memory: List[int]):
        """Log final memory state"""
        if self.session_active:
            non_zero = [(i, v) for i, v in enumerate(memory) if v != 0]
            self.log(f"\n🏁 === FINAL MEMORY STATE ===")
            self.log(f"Non-zero memory locations: {len(non_zero)}")
            self.log("=" * 30)
            
            for addr, value in non_zero[:50]:  # Limit output
                self.log(f"[{addr:04d}] = {value}")
            
            if len(non_zero) > 50:
                self.log(f"... and {len(non_zero) - 50} more locations")
    
    def close_session(self):
        """Close output session"""
        if self.session_active:
            self._flush_buffer()  # Flush any remaining logs
            if self.output_file:
                self.output_file.close()
                print(f"💾 Output session saved to: {self.output_file.name}")
            self.session_active = False

class GTUC312CPU:
    def __init__(self, debug_mode: int = 0):
        # 20000 address memory space
        self.memory = [0] * 20000
        
        # CPU registers (0-9)
        self.registers = [0] * 10
        
        # CPU state
        self.halted = False
        self.kernel_mode = True
        self.user_mode = False  # Added user_mode
        self.debug_mode = debug_mode
        
        # Instruction storage (address -> instruction string)
        self.instructions = {}
        
        # Statistics
        self.total_instructions = 0
        self.context_switches = 0
        
        # OS scheduler address for SYSCALL YIELD returns
        self.os_scheduler_address = 102  # Where OS scheduler loop starts
        
        # Thread management
        self.current_thread = 0  # 0 = OS, 1-10 = threads
        self.thread_states = {}  # Thread ID -> ThreadState
        
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
            base_name = os.path.splitext(os.path.basename(filename))[0]
            self.output_manager.start_session(base_name, self.debug_mode)
            
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
                    if self.debug_mode >= 1:
                        print(f"Loaded data: mem[{addr}] = {value}")
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
        max_instructions = 50000  # Increased limit
        
        while not self.halted and safety_counter < max_instructions:
            try:
                self.execute_single()
                safety_counter += 1
                
                # Debug mode 1: memory state after each instruction
                if self.debug_mode == 1:
                    self.output_manager.log_memory_state(self.memory)
                
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
        
        # Log final statistics
        self.output_manager.log_final_stats(
            self.total_instructions,
            self.context_switches,
            self.get_pc()
        )
        
        # Log final memory state
        self.output_manager.log_memory_state(self.memory)
        
        # Close output session
        self.output_manager.close_session()
    
    def execute_single(self):
        """Execute a single instruction"""
        pc = self.get_pc()
        
        if pc not in self.instructions:
            raise ValueError(f"Invalid PC: {pc}")
        
        instruction = self.instructions[pc]
        self.output_manager.log_instruction(self.total_instructions, pc, instruction)
        
        self._execute_instruction(instruction)
        self.total_instructions += 1
        
        # Print register state in debug mode >= 2
        if self.debug_mode >= 2:
            reg_str = ', '.join([f'R{i}={v}' for i, v in enumerate(self.registers)])
            print(f"Registers: {reg_str}")
    
    def _execute_instruction(self, instruction: str):
        """Execute a single instruction"""
        parts = instruction.split()
        opcode = parts[0].upper()
        
        try:
            if opcode == 'SET':
                value = int(parts[1])
                addr = int(parts[2])
                self.memory[addr] = value
                self.set_pc(self.get_pc() + 1)
                
            elif opcode == 'CPY':
                src = int(parts[1])
                dest = int(parts[2])
                self.memory[dest] = self.memory[src]
                self.set_pc(self.get_pc() + 1)
                
            elif opcode == 'CPYI':
                src = int(parts[1])
                dest = int(parts[2])
                self.memory[dest] = self.memory[self.memory[src]]
                self.set_pc(self.get_pc() + 1)
                
            elif opcode == 'CPYI2':
                dest = int(parts[1])
                src = int(parts[2])
                self.memory[self.memory[dest]] = self.memory[self.memory[src]]
                self.set_pc(self.get_pc() + 1)
                
            elif opcode == 'ADD':
                dest = int(parts[1])
                value = int(parts[2])
                self.memory[dest] += value
                self.set_pc(self.get_pc() + 1)
                
            elif opcode == 'ADDI':
                dest = int(parts[1])
                src = int(parts[2])
                self.memory[dest] += self.memory[src]
                self.set_pc(self.get_pc() + 1)
                
            elif opcode == 'SUBI':
                dest = int(parts[1])
                src = int(parts[2])
                self.memory[dest] = self.memory[dest] - self.memory[src]
                self.set_pc(self.get_pc() + 1)
                
            elif opcode == 'JIF':
                addr = int(parts[1])
                target = int(parts[2])
                if self.memory[addr] <= 0:
                    self.set_pc(target)
                else:
                    self.set_pc(self.get_pc() + 1)
                    
            elif opcode == 'PUSH':
                addr = int(parts[1])
                self.memory[self.get_sp()] = self.memory[addr]
                self.set_sp(self.get_sp() - 1)
                self.set_pc(self.get_pc() + 1)
                
            elif opcode == 'POP':
                addr = int(parts[1])
                self.set_sp(self.get_sp() + 1)
                self.memory[addr] = self.memory[self.get_sp()]
                self.set_pc(self.get_pc() + 1)
                
            elif opcode == 'CALL':
                target = int(parts[1])
                self.memory[self.get_sp()] = self.get_pc() + 1
                self.set_sp(self.get_sp() - 1)
                self.set_pc(target)
                
            elif opcode == 'RET':
                self.set_sp(self.get_sp() + 1)
                self.set_pc(self.memory[self.get_sp()])
                
            elif opcode == 'HLT':
                self.halt()
                
            elif opcode == 'USER':
                addr = int(parts[1])
                self.user_mode = True
                self.set_pc(self.memory[addr])
                
            elif opcode == 'SYSCALL':
                if len(parts) > 1 and parts[1] == 'HLT':
                    self.halt()
                else:
                    self._handle_syscall(parts[1:])
                
            else:
                raise ValueError(f"Unknown instruction: {opcode}")
                
        except IndexError:
            raise ValueError(f"Invalid instruction format: {instruction}")
        except ValueError as e:
            raise ValueError(f"Error executing {instruction}: {e}")
    
    def _handle_syscall(self, args: List[str]):
        """Handle system calls"""
        syscall_type = args[0]
        
        if syscall_type == "PRN":
            # Block thread for 100 instructions
            self.thread_states[self.current_thread] = ThreadState.BLOCKED
            # Store remaining block count in thread state
            self.memory[self.get_sp()] = 100  # Store block count on stack
            # Switch to kernel mode
            self.kernel_mode = True
            # Return to scheduler
            self.set_pc(self.os_scheduler_address)
            # Log thread table in debug mode 3
            self.log_thread_states()
        elif syscall_type == "YIELD":
            # Normal yield handling
            self.thread_states[self.current_thread] = ThreadState.READY
            self.kernel_mode = True
            self.set_pc(102)  # Set PC to OS scheduler address
            # Log thread table in debug mode 3
            self.log_thread_states()
        elif syscall_type == 'HALT':
            self.halt()
        else:
            raise ValueError(f"Unknown syscall: {syscall_type}")
    
    def _save_thread_state(self):
        """Save current thread state to thread table and update state"""
        if self.current_thread > 0:
            base_addr = 20 + (self.current_thread - 1) * 6
            # Save PC and SP
            self.memory[base_addr + 2] = self.get_pc()
            self.memory[base_addr + 3] = self.get_sp()
            # Update instruction count
            self.memory[base_addr + 5] += 1
            # Set state to READY in both memory and dict
            self.memory[base_addr + 1] = ThreadState.READY.value
            self.thread_states[self.current_thread] = ThreadState.READY
    
    def _load_thread_state(self, thread_id: int):
        """Load thread state from thread table and update state"""
        if thread_id > 0:
            base_addr = 20 + (thread_id - 1) * 6
            # Load PC and SP
            self.set_pc(self.memory[base_addr + 2])
            self.set_sp(self.memory[base_addr + 3])
            # Set state to RUNNING in both memory and dict
            self.memory[base_addr + 1] = ThreadState.RUNNING.value
            self.thread_states[thread_id] = ThreadState.RUNNING
            # Update current thread
            self.current_thread = thread_id
    
    def _check_memory_access(self, addr: int, access_type: str):
        """Check if memory access is allowed in current mode"""
        if not self.kernel_mode and addr < 100:  # Only protect system registers
            # Thread attempted to access protected memory
            self.output_manager.log_error(f"Thread {self.current_thread} attempted to access protected memory at {addr}")
            # Terminate the thread
            self.thread_states[self.current_thread] = ThreadState.READY
            # Switch back to kernel mode
            self.kernel_mode = True
            # Set PC to scheduler
            self.set_pc(self.os_scheduler_address)
            return False
        return True
    
    def get_pc(self) -> int:
        """Get program counter"""
        return self.memory[0]
    
    def set_pc(self, value: int):
        """Set program counter"""
        self._check_memory_access(value, "read")
        self.memory[0] = value
    
    def get_sp(self) -> int:
        """Get stack pointer"""
        return self.memory[1]
    
    def set_sp(self, value: int):
        """Set stack pointer"""
        self._check_memory_access(value, "read")
        self.memory[1] = value
    
    def get_instruction_count(self) -> int:
        """Get total instruction count"""
        return self.total_instructions
    
    def halt(self):
        """Halt CPU execution"""
        self.halted = True
    
    def is_halted(self) -> bool:
        """Check if CPU is halted"""
        return self.halted
    
    def _debug_step(self):
        """Debug step-by-step execution"""
        input("Press Enter to continue...")
        print(f"PC: {self.get_pc()}, SP: {self.get_sp()}")
        print(f"Current Thread: {self.current_thread}")
        print(f"Instructions: {self.total_instructions}")
        print(f"Context Switches: {self.context_switches}")
        print("-" * 50)
    
    def log_thread_states(self):
        """Print thread table in debug mode 3"""
        if self.debug_mode == 3:
            print("\n=== Thread Table ===")
            print("ID  State      PC    SP    Start   Instr")
            print("-" * 40)
            
            for thread_id in range(1, 11):
                state = self.thread_states.get(thread_id, ThreadState.READY)
                state_str = state.name
                
                # Get thread info from memory
                base_addr = 20 + (thread_id - 1) * 6
                pc = self.memory[base_addr + 2]
                sp = self.memory[base_addr + 3]
                start = self.memory[base_addr + 4]
                instr = self.memory[base_addr + 5]
                
                print(f"{thread_id:2d}  {state_str:<10} {pc:5d} {sp:5d} {start:6d} {instr:6d}")
            print("=" * 40)

    def log_extra_output(self, message: str):
        """Log extra output messages to console and file"""
        self.output_manager.log(f"📤 EXTRA OUTPUT: {message}", to_console=True)

def main():
    """Main entry point"""
    if len(sys.argv) < 4:
        print("Usage: python3 cpu.py <program_file> -D <debug_mode>")
        sys.exit(1)
    if sys.argv[2] != '-D':
        print("Invalid debug mode format. Use -D followed by 0, 1, 2, or 3.")
        sys.exit(1)
    debug_mode = int(sys.argv[3])
    program_file = sys.argv[1]
    cpu = GTUC312CPU(debug_mode)
    cpu.load_program(program_file)
    cpu.run()

if __name__ == "__main__":
    main()