#!/usr/bin/env python3
"""
GTU-C312 Output Management System
Author: helinsygl
Date: 2025-06-04 14:25:46 UTC
"""

import os
import sys
from datetime import datetime
from typing import List, Optional

class OutputManager:
    def __init__(self, base_dir: str = "outputs"):
        self.base_dir = base_dir
        self.current_session = None
        self.session_file = None
        self.ensure_output_directory()
        
    def ensure_output_directory(self):
        """Create outputs directory if it doesn't exist"""
        if not os.path.exists(self.base_dir):
            os.makedirs(self.base_dir)
            print(f"📁 Created output directory: {self.base_dir}/")
        
    def start_session(self, program_name: str, debug_mode: int):
        """Start a new output session"""
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        self.current_session = f"{program_name}_{debug_mode}_{timestamp}"
        
        # Remove .txt extension if present for cleaner naming
        if self.current_session.endswith('.txt'):
            self.current_session = self.current_session[:-4]
            
        session_filename = f"{self.current_session}.txt"
        session_path = os.path.join(self.base_dir, session_filename)
        
        self.session_file = open(session_path, 'w', encoding='utf-8')
        
        # Write session header
        self.write_header(program_name, debug_mode)
        print(f"📝 Output session started: {session_path}")
        
    def write_header(self, program_name: str, debug_mode: int):
        """Write session header information"""
        header = f"""
{'='*60}
GTU-C312 CPU Simulator Output Log
{'='*60}
Session: {self.current_session}
Program: {program_name}
Debug Mode: {debug_mode}
Start Time: {datetime.now().strftime("%Y-%m-%d %H:%M:%S UTC")}
User: helinsygl
{'='*60}

"""
        self.session_file.write(header)
        self.session_file.flush()
        
    def log(self, message: str, to_console: bool = True):
        """Log message to both file and optionally console"""
        if self.session_file:
            self.session_file.write(message + '\n')
            self.session_file.flush()
            
        if to_console:
            print(message)
            
    def log_instruction(self, count: int, pc: int, instruction: str):
        """Log instruction execution"""
        msg = f"[{count:4d}] PC={pc:4d}: {instruction}"
        self.log(msg, to_console=False)  # Only to file for instructions
        
    def log_output(self, value: int):
        """Log program output"""
        msg = f"📤 OUTPUT: {value}"
        self.log(msg)
        
    def log_context_switch(self, message: str):
        """Log context switches"""
        self.log(f"🔄 {message}")
        
    def log_error(self, error: str):
        """Log errors"""
        self.log(f"💥 ERROR: {error}")
        
    def log_final_stats(self, total_instructions: int, context_switches: int, final_pc: int):
        """Log final execution statistics"""
        stats = f"""
{'='*60}
EXECUTION COMPLETED
{'='*60}
Total Instructions Executed: {total_instructions}
Context Switches: {context_switches} 
Final PC: {final_pc}
End Time: {datetime.now().strftime("%Y-%m-%d %H:%M:%S UTC")}
{'='*60}
"""
        self.log(stats)
        
    def log_memory_state(self, memory: List[int]):
        """Log final memory state"""
        self.log("\n🏁 === FINAL MEMORY STATE ===")
        non_zero_count = 0
        
        for addr in range(len(memory)):
            if memory[addr] != 0:
                self.log(f"MEM[{addr:4d}] = {memory[addr]:8d}", to_console=False)
                non_zero_count += 1
                
        self.log(f"Non-zero memory locations: {non_zero_count}")
        self.log("=" * 30)
        
    def close_session(self):
        """Close current output session"""
        if self.session_file:
            self.session_file.close()
            self.session_file = None
            print(f"💾 Output session saved to: {self.base_dir}/{self.current_session}.txt")