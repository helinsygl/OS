# Project Conversation Summary

## Overview
This document provides a detailed summary of the conversation regarding the implementation and testing of a CPU simulator and OS scheduler project.

## Key Points Discussed

1. **Round Robin Scheduler**
   - The codebase includes a round robin scheduler implementation.
   - The scheduler is located in `os.gtu` and manages thread states and context switching.

2. **Thread States**
   - Thread states include READY, RUNNING, and BLOCKED.
   - The `DONE` state was removed as it was not part of the assignment.

3. **Standalone vs. OS Mode**
   - Threads can be run in standalone mode or with the OS.
   - In standalone mode, threads should end with `SYSCALL HLT`.
   - In OS mode, threads should use `SYSCALL YIELD` or `SYSCALL PRN`.

4. **Debug Mode**
   - Debug mode 3 displays the thread table with states.
   - The thread table should show READY, BLOCKED, and RUNNING states.

5. **Issues Encountered**
   - "Invalid PC: 102" error when running threads in standalone mode.
   - "Invalid PC: 9" error when running the OS.

6. **Solutions Proposed**
   - Adjusting the PC to point to the correct thread start addresses.
   - Ensuring thread states are correctly managed in both standalone and OS modes.

## Conclusion
The conversation highlights the importance of correctly managing thread states and PC values in both standalone and OS modes to ensure the CPU simulator and OS scheduler function as expected.