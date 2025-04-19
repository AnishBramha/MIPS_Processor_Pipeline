import random

class Processor:
    
    def __init__(self) -> None:
        
        self.regs : list[int] = [0] * 32
        self.ins_mem : list[str] = {}
        self.data_mem : list[str] = {}
        self.pc : int = 0                   
        self.cycles : int = 0
        self.branch_taken : bool = False
        self.stall_next_cycle : bool = False
        
        
        self.if_id : dict[int, str] = {}
        self.id_ex : dict[int, str] = {}
        self.ex_mem : dict[int, str] = {}
        self.mem_wb : dict[int, str] = {}
        
        self.stall_cycles : int = 0
        self.instructions_executed : int = 0
        self.load_stalls : int = 0
        self.branch_count : int = 0
        self.mem_delay_cycles : int = 0

    def load_program(self) -> None:

        with open('program.asm', 'r') as file:
            program : list[str] = [line.strip() for line in file if line!=""]
        
        labels : dict[str, int] = {}
        current_addr : int = 0

        for line in program:

            if ':' in line:
                label, instr = line.split(':', 1)
                labels[label.strip()] = current_addr
                line = instr.strip()

            if line:
                current_addr += 4
        
        self.ins_mem.clear()
        current_addr = 0

        for line in program:
            if ':' in line:
                line = line.split(':', 1)[1].strip()

            if not line:
                continue

            parts : list[str]= line.split()

            if parts[0] == 'beq' and parts[-1] in labels:
                target = labels[parts[-1]]
                offset = (target - (current_addr + 4)) // 4
                parts[-1] = str(offset)

            self.ins_mem[current_addr] = ' '.join(parts)
            current_addr += 4

    def if_stage(self, stall):

        if not stall and self.pc in self.ins_mem:
            self.if_id['ins'] = self.ins_mem[self.pc]
            self.pc += 4
        elif stall:
            pass
        else:
            self.if_id['ins'] = None

    def id_stage(self, stall):
        if stall:
            self.id_ex.clear()
            return
        
        if 'ins' not in self.if_id or not self.if_id['ins']:
            self.id_ex.clear()
            return
        
        ins = self.if_id['ins']
        parts = ins.split()
        op = parts[0]
        if op == 'beq':
            self.stall_next_cycle = True
        self.id_ex['ins'] = ins

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
            raise ValueError(f'INVALID INSTRUCTION: {ins}')

    def ex_stage(self) -> None:
        
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

            self.ex_mem['mem_cycles_left'] = random.choice([2, 3])

        elif op == 'beq':

            if self.regs[self.id_ex['rs']] != self.regs[self.id_ex['rt']]:
                self.pc = self.pc - 4 + (self.id_ex['offset'] * 4)
                self.branch_taken = True
                self.branch_count += 1

        self.ex_mem.setdefault('mem_cycles_left', 0)

    def mem_stage(self):
        if 'ins' not in self.ex_mem or not self.ex_mem['ins']:
            self.mem_wb.clear()
            return
        
        ins = self.ex_mem['ins']
        parts = ins.split()
        op = parts[0]
        if self.ex_mem['mem_cycles_left'] > 0:
            self.ex_mem['mem_cycles_left'] -= 1
            self.mem_delay_cycles += 1
            return
        
        if op in ['addi', 'subi', 'add']:
            self.mem_wb['result'] = self.ex_mem['result']
            self.mem_wb['rd'] = self.ex_mem['rd']
        elif op == 'lw':
            self.mem_wb['result'] = self.data_mem.get(self.ex_mem['addr'], 0)
            self.mem_wb['rd'] = self.ex_mem['rt']
        elif op == 'sw':
            self.data_mem[self.ex_mem['addr']] = self.ex_mem['value']
        
        self.mem_wb['ins'] = ins
        self.ex_mem.clear()

    def wb_stage(self):
        if 'ins' in self.mem_wb and self.mem_wb['ins']:
            ins = self.mem_wb['ins']
            parts = ins.split()
            op = parts[0]
            if op in ['addi', 'subi', 'add', 'lw'] and self.mem_wb['rd'] != 0:
                self.regs[self.mem_wb['rd']] = self.mem_wb['result']
            self.instructions_executed += 1

    def print_pipeline_state(self) -> None:
        
        print(f'Clock Cycle {self.cycles}:')
        print(f'IF/ID: {self.if_id.get('ins', 'NOP')}')
        print(f'ID/EX: {self.id_ex.get('ins', 'NOP')}')
        print(f'EX/MEM: {self.ex_mem.get('ins', 'NOP')} (Mem Cycles Left: {self.ex_mem.get('mem_cycles_left', 0)})')
        print(f'MEM/WB: {self.mem_wb.get('ins', 'NOP')}')
        print(f'PC: {self.pc}')
        print('Registers:', [f'${i}:{self.regs[i]}' for i in range(8)])
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
        
        while True:

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
                self.id_stage(branch_stall)
                self.if_stage(branch_stall)
 
            if branch_stall:
                self.stall_next_cycle = False
            
            self.print_pipeline_state()
            
            if self.mem_wb.get('ins') == 'halt':
                break
        
        self.print_statistics()

def main() -> None:

    core = Processor()
    core.regs[1] = 0
    core.regs[2] = 4
    core.regs[3] = 7
    core.load_program()
    core.run()

if __name__ == '__main__':
    main()