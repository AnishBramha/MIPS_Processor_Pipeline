import random

class Processor: # The processor!
    
    def __init__(self) -> None: # Default values initialisation
        
        self.regs : list[int] = [0] * 32 # 32 basic registers
        self.ins_mem : list[str] = {} # Instruction memory
        self.data_mem : list[str] = {} # Data memory
        self.pc : int = 0 # Program counter    
        self.cycles : int = 0 # Total clock cycles
        self.branch_taken : bool = False # Whether a branch is taken or not
        self.stall_next_cycle : bool = False # Whether to stall next cycle
        
        
        self.if_id : dict[int, str] = {} # The if-id pipelined register
        self.id_ex : dict[int, str] = {} # The id-ex pipelined register
        self.ex_mem : dict[int, str] = {} # The ex-mem pipelined register
        self.mem_wb : dict[int, str] = {}  # The mem-wb pipelined register
        
        self.stall_cycles : int = 0 # Number of stall cycles
        self.instructions_executed : int = 0 # Number of instructions executed
        self.load_stalls : int = 0 # Number of load stalls
        self.branch_count : int = 0 # Number of branch statements executed
        self.mem_delay_cycles : int = 0 # Number of memory delay cycles

    def load_program(self) -> None: # Function to load the MIPS program from a file 

        with open('program.asm', 'r') as file: # Open the file in read mode
            program : list[str] = [line.strip() for line in file if line!=""] # Taking only the non empty lines
        
        labels : dict[str, int] = {} # Dictionary to store branch labels and their addresses
        current_addr : int = 0 # Current address in the instruction memory

        for line in program: # Iterating through the lines of the program

            if ':' in line: # Branch/jump address handling
                label, instr = line.split(':', 1) 
                labels[label.strip()] = current_addr # Stores the branch addresses
                line = instr.strip()

            if line:
                current_addr += 4 # Incrementing the address by 4 bytes for each instruction
        
        current_addr = 0 # Resetting the address to 0 for loading instructions

        for line in program:
            if ':' in line: # If the line has a label, we need to split it and extract the instruction
                line = line.split(':', 1)[1].strip()

            if not line:
                continue

            parts : list[str] = line.split()

            if parts[0] == 'beq' and parts[-1] in labels: # If its a branch and the last element is in the labels collected earlier
                target = labels[parts[-1]] # The adress to jump to
                offset = (target - (current_addr + 4)) // 4 # Calculates the offset
                parts[-1] = str(offset) # Replaces the label with the offset

            self.ins_mem[current_addr] = ' '.join(parts) # Storing the instructions in the instruction memory
            current_addr += 4 # Incrementing the address by 4 bytes for each instruction

    def if_stage(self, stall=False): # Instruction Fetch Stage (First of five stages)

        if not stall and self.pc in self.ins_mem: # If not stalled and the PC is valid
            self.if_id['ins'] = self.ins_mem[self.pc] # Fetch the instruction
            self.pc += 4 # Increment the PC by 4
        elif stall: # If stalled
            self.if_id.clear()
            pass # Do nothing
        else: # If invalid
            self.if_id['ins'] = None # Clear the IF/ID register

    def id_stage(self, stall=False): # Instruction Decode Stage (Second of five stages)
        if stall: # If stalled
            self.id_ex.clear() # Clear the ID/EX register
            return
        
        if 'ins' not in self.if_id or not self.if_id['ins']: # If invalid instruction
            self.id_ex.clear() # Clear the ID/EX register
            return
        
        ins = self.if_id['ins'] 
        parts = ins.split()
        op = parts[0] # The operation
        if op == 'beq': # If branch instruction
            self.stall_next_cycle = True # Stall for one cycle
        self.id_ex['ins'] = ins 

        # Decoding the instruction (We only support these instructions)
        if op in ('addi', 'subi'): 
            self.id_ex['rd'] = int(parts[1][1:-1])
            self.id_ex['rs'] = int(parts[2][1:-1])
            self.id_ex['imm'] = int(parts[3])
        elif op in ('add', 'sub'):
            self.id_ex['rd'] = int(parts[1][1:-1])
            self.id_ex['rs'] = int(parts[2][1:-1])
            self.id_ex['rt'] = int(parts[3][1:])
        elif op in ('lw', 'sw'):
            self.id_ex['rt'] = int(parts[1][1:-1])
            offset_reg = parts[2].split('(')
            self.id_ex['offset'] = int(offset_reg[0])
            self.id_ex['rs'] = int(offset_reg[1].split(')')[0][1:])
        elif op == 'beq':
            self.id_ex['rs'] = int(parts[1][1:-1])
            self.id_ex['rt'] = int(parts[2][1:-1])
            self.id_ex['offset'] = int(parts[3])
        elif op != 'halt':
            raise ValueError(f'INVALID INSTRUCTION/UNSUPPORTED: {ins}')

    def ex_stage(self) -> None: # Execute Stage (Third of five stages)
        
        if 'ins' not in self.id_ex or not self.id_ex['ins']:
            return
        
        ins : str = self.id_ex['ins']
        parts : list[str] = ins.split()
        op : str = parts[0]
        
        self.ex_mem['ins'] = ins

        if op == 'addi':
            self.ex_mem['result'] = self.regs[self.id_ex['rs']] + self.id_ex['imm']
            self.ex_mem['rd'] = self.id_ex['rd']

        elif op == 'subi':
            self.ex_mem['result'] = self.regs[self.id_ex['rs']] - self.id_ex['imm']
            self.ex_mem['rd'] = self.id_ex['rd']

        elif op == 'add':
            self.ex_mem['result'] = self.regs[self.id_ex['rs']] + self.regs[self.id_ex['rt']]
            self.ex_mem['rd'] = self.id_ex['rd']

        elif op == 'sub':
            self.ex_mem['result'] = self.regs[self.id_ex['rs']] + self.regs[self.id_ex['rt']]
            self.ex_mem['rd'] = self.id_ex['rd']

        elif op in ('lw', 'sw'):
            self.ex_mem['addr'] = self.regs[self.id_ex['rs']] + self.id_ex['offset']
            self.ex_mem['rt'] = self.id_ex['rt']

            if op == 'sw':
                self.ex_mem['value'] = self.regs[self.id_ex['rt']]

            self.ex_mem['mem_cycles_left'] = random.choice([2, 3]) # Randomly chooses 2 or 3 cycles for memory access delay

        elif op == 'beq':

            if self.regs[self.id_ex['rs']] - self.regs[self.id_ex['rt']] == 0:
                self.pc = self.pc - 4 + (self.id_ex['offset'] * 4)
                self.branch_taken = True
                self.branch_count += 1

        self.ex_mem.setdefault('mem_cycles_left', 0)

    def mem_stage(self): # Memory Stage (Fourth of five stages)
        if 'ins' not in self.ex_mem or not self.ex_mem['ins']:
            self.mem_wb.clear()
            return
        
        ins = self.ex_mem['ins']
        parts = ins.split()
        op = parts[0]
        if self.ex_mem['mem_cycles_left'] > 0: # If there are any memory cycles leftover
            self.ex_mem['mem_cycles_left'] -= 1 # Continue the memory access
            self.mem_delay_cycles += 1 # This leads to a memory delay cycle
            return
        
        if op in ['addi', 'subi', 'add', 'sub']:
            self.mem_wb['result'] = self.ex_mem['result']
            self.mem_wb['rd'] = self.ex_mem['rd']
        elif op == 'lw':
            self.mem_wb['result'] = self.data_mem.get(self.ex_mem['addr'], 0) # Getting the data from data memory
            self.mem_wb['rd'] = self.ex_mem['rt']
        elif op == 'sw':
            self.data_mem[self.ex_mem['addr']] = self.ex_mem['value'] # Writing the data onto data memory
        
        self.mem_wb['ins'] = ins
        self.ex_mem.clear()

    def wb_stage(self): # Write Back Stage (Fifth of five stages)
        if 'ins' in self.mem_wb and self.mem_wb['ins']:
            ins = self.mem_wb['ins']
            parts = ins.split()
            op = parts[0]
            if op in ['addi', 'subi', 'add', 'lw', 'sub'] and self.mem_wb['rd'] != 0:
                self.regs[self.mem_wb['rd']] = self.mem_wb['result'] # Store the result in the destination register
            self.instructions_executed += 1

    def print_pipeline_state(self) -> None:
        
        print(f'Clock Cycle {self.cycles}:')
        print(f'IF/ID: {self.if_id.get('ins', 'NOP')}')
        print(f'ID/EX: {self.id_ex.get('ins', 'NOP')}')
        print(f'EX/MEM: {self.ex_mem.get('ins', 'NOP')} (Mem Cycles Left: {self.ex_mem.get('mem_cycles_left', 0)})')
        print(f'MEM/WB: {self.mem_wb.get('ins', 'NOP')}')
        print(f'PC: {self.pc}')
        print('Registers:', [f'${i}:{self.regs[i]}' for i in range(10)])
        print('------------------------')

    def print_statistics(self) -> None:
        
        print('\nSimulation Statistics:')
        print(f'Total clock cycles: {self.cycles}')
        print(f'No. of instructions executed: {self.instructions_executed}')
        print(f'Stall cycles: {self.stall_cycles}')
        print(f'Load-stalls: {self.load_stalls}')
        print(f'Branch statements executed: {self.branch_count}')
        print(f'Memory delay cycles: {self.mem_delay_cycles}')


    def run(self) -> None:
        
        print('SIMULATION\n==========')
        
        while True: # Keep running until program ends (halt)

            self.cycles += 1 
            memory_stall : bool = 'mem_cycles_left' in self.ex_mem and self.ex_mem['mem_cycles_left'] > 0
            branch_stall : bool = self.stall_next_cycle
            
            if memory_stall or branch_stall:
                self.stall_cycles += 1

                if memory_stall and 'ins' in self.ex_mem and self.ex_mem['ins'].startswith('lw'):
                    self.load_stalls += 1
            
            self.wb_stage()
            self.mem_stage()

            if not memory_stall:
                self.ex_stage()
                self.id_stage()
                self.if_stage(branch_stall)
 
            if branch_stall:
                self.stall_next_cycle = False
            
            self.print_pipeline_state()
            
            if self.mem_wb.get('ins') == 'halt': # if it's halt then end the program
                break
        
        self.print_statistics()

def main() -> None:

    core = Processor()
    core.load_program()
    core.run()

if __name__ == '__main__':
    main()
