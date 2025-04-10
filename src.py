import random

class Processor:

    def __init__(self):
        self.if_id = {'ins': None, 'pc': None}
        self.id_ex = {'ins': None, 'pc': None, 'rs': None, 'rt': None, 'rd': None, 'imm': None, 'control': None}
        self.ex_mem = {'ins': None, 'pc': None, 'alu_res': None, 'rt_data': None, 'rd': None, 'control': None}
        self.mem_wb = {'ins': None, 'alu_res': None, 'mem_data': None, 'rd': None, 'control': None}
        self.regs = [0 for _ in range(0, 32)]
        self.data_mem = {}
        self.ins_mem = {}

        self.pc = 0
        self.stall = False
        self.branch_taken = False
        self.current_stage_cycles = 0
        self.mem_latency = 0

        self.cycles = 0
        self.tot_ins = 0
        self.stall_count = 0
        self.load_stalls = 0
        self.delay_slot_used = 0
        self.delay_slot_wasted = 0
        self.mem_delay_cycles = 0

    def if_stage(self):
        if self.stall:
            return
        if self.pc in self.ins_mem:
            ins = self.ins_mem[self.pc]
            self.if_id['ins'] = ins
            self.if_id['pc'] = self.pc
            self.pc += 4
            self.tot_ins += 1
        else:
            self.if_id['ins'] = None
            self.if_id['pc'] = self.pc    
        
    def id_stage(self):
        if not self.if_id['ins']:
            self.id_ex['ins'] = None
            return
        ins = self.if_id['ins']
        self.id_ex['ins'] = ins
        self.id_ex['pc'] = self.if_id['pc']
        parts = ins.replace(',','').split()
        op = parts[0]
        self.id_ex['control'] = {
            'regwrite': 0,
            'memread': 0,
            'memwrite': 0,
            'branch': 0,
            'jump': 0,
            'alusrc': 0,
            'regdst': 0,
            'aluop': 'add'
        }
        if op == 'add':
            self.id_ex['rd'] = int(parts[1][1:])
            self.id_ex['rs'] = int(parts[2][1:])
            self.id_ex['rt'] = int(parts[3][1:])
            self.id_ex['control'].update({
                'regwrite': 1,
                'regdst': 1,
                'aluop': 'add'
            })
        elif op == 'addi':
            self.id_ex['rt'] = int(parts[1][1:])
            self.id_ex['rs'] = int(parts[2][1:])
            self.id_ex['imm'] = int(parts[3])
            self.id_ex['control'].update({
                'regwrite': 1,
                'alusrc': 1,
                'aluop': 'add'
            })
        elif op == 'lw':
            rt = parts[1][1:]
            offset_rs = parts[2].split('(')
            self.id_ex['rt'] = int(rt)
            self.id_ex['imm'] = int(offset_rs[0])
            self.id_ex['rs'] = int(offset_rs[1][1:-1])  
            self.id_ex['control'].update({
                'regwrite': 1,
                'memread': 1,
                'alusrc': 1,
                'aluop': 'add'
            })
            self.mem_latency = random.choice([2, 3]) 
        elif op == 'sw':
            rt = parts[1][1:]
            offset_rs = parts[2].split('(')
            self.id_ex['rt'] = int(rt)
            self.id_ex['imm'] = int(offset_rs[0])
            self.id_ex['rs'] = int(offset_rs[1][1:-1])
            self.id_ex['control'].update({
                'memwrite': 1,
                'alusrc': 1,
                'aluop': 'add'
            })
            self.mem_latency = random.choice([2, 3])
        elif op == 'beq':
            self.id_ex['rs'] = int(parts[1][1:])
            self.id_ex['rt'] = int(parts[2][1:])
            target = parts[3]
            
            # Handle both immediate offsets and labels
            if target.isdigit() or (target[0] == '-' and target[1:].isdigit()):
                self.id_ex['imm'] = int(target)
            else:
                # Search for the label in instruction memory
                for addr, instruction in self.ins_mem.items():
                    if instruction.startswith(target + ':'):
                        # Calculate offset from current PC (pc+4 is already in pipeline)
                        offset = (addr - (self.id_ex['pc'] + 4)) >> 2
                        self.id_ex['imm'] = offset
                        break
                else:
                    raise ValueError(f"Unknown branch target: {target}")
            
            self.id_ex['control'].update({
                'branch': 1,
                'aluop': 'sub'  
            })

        elif op == 'j':
            
            target = parts[1]
            if target.isdigit():
                self.id_ex['imm'] = int(target)
            else:
               
                for addr, instruction in self.ins_mem.items():
                    if instruction.startswith(target + ':'):
                        self.id_ex['imm'] = addr >> 2 
                        break
                else:
                    raise ValueError(f"Unknown jump target: {target}")
            self.id_ex['control']['jump'] = 1

        elif op == 'subi':
            self.id_ex['rt'] = int(parts[1][1:])
            self.id_ex['rs'] = int(parts[2][1:])
            self.id_ex['imm'] = int(parts[3])
            self.id_ex['control'].update({
                'regwrite': 1,
                'alusrc': 1,
                'aluop': 'sub'
            })
        elif op == 'halt':
            pass

    def ex_stage(self):
        if self.id_ex['ins'] is None:
            self.ex_mem['ins'] = None
            return
        
        ins = self.id_ex['ins']
        self.ex_mem['ins'] = ins
        self.ex_mem['pc'] = self.id_ex['pc']
        self.ex_mem['control'] = self.id_ex['control']

        rs_val = self.regs[self.id_ex['rs']] if self.id_ex['rs'] is not None else 0
        rt_val = self.regs[self.id_ex['rt']] if self.id_ex['rt'] is not None else 0

        if self.id_ex['control']['alusrc']:
            op2 = self.id_ex['imm']
        else:
            op2 = rt_val

        if self.id_ex['control']['aluop'] == 'add':
            self.ex_mem['alu_res'] = rs_val + op2
        elif self.id_ex['control']['aluop'] == 'sub':
            self.ex_mem['alu_res'] = rs_val - op2

        self.ex_mem['rt_data'] = rt_val
        self.ex_mem['rd'] = self.id_ex['rd'] if self.id_ex['rd'] is not None else self.id_ex['rt']

        
        if self.id_ex['control']['jump']:
            jump_target = (self.id_ex['pc'] & 0xF0000000) | (self.id_ex['imm'] << 2)
            self.pc = jump_target
            self.branch_taken = True
            pc_next = self.id_ex['pc'] + 4
            if pc_next in self.ins_mem and not self.ins_mem[pc_next].startswith('nop'):
                self.delay_slot_used += 1
            else:
                self.delay_slot_wasted += 1
                

        elif self.id_ex['control']['branch']:
            
            if rs_val == rt_val:  
                self.pc = self.id_ex['pc'] + 4 + (self.id_ex['imm'] << 2)
                self.branch_taken = True
                pc_next = self.id_ex['pc'] + 4
                if pc_next in self.ins_mem and not self.ins_mem[pc_next].startswith('nop'):
                    self.delay_slot_used += 1
                else:
                    self.delay_slot_wasted += 1

        if self.id_ex['control']['memread'] and ((self.id_ex['rs'] is not None and self.id_ex['rs'] == self.ex_mem['rd']) or 
        (self.id_ex['rt'] is not None and self.id_ex['rt'] == self.ex_mem['rd'])):
            self.stall = True
            self.stall_count += 1
            self.load_stalls += 1

    def mem_stage(self):
        if not self.ex_mem['ins']:
            self.mem_wb['ins'] = None
            return
        
        if self.current_stage_cycles > 0:
            self.current_stage_cycles -= 1
            self.mem_delay_cycles += 1
            self.stall = True
            self.stall_count += 1
            return
        
        self.stall = False
        ins = self.ex_mem['ins']
        self.mem_wb['ins'] = ins
        self.mem_wb['alu_res'] = self.ex_mem['alu_res']
        self.mem_wb['control'] = self.ex_mem['control']
        self.mem_wb['rd'] = self.ex_mem['rd']

        if self.ex_mem['control']['memread']:
            addr = self.ex_mem['alu_res']
            self.mem_wb['mem_data'] = self.data_mem.get(addr, 0)  
            self.current_stage_cycles = self.mem_latency - 1
        elif self.ex_mem['control']['memwrite']:
            addr = self.ex_mem['alu_res']
            self.data_mem[addr] = self.ex_mem['rt_data']
            self.current_stage_cycles = self.mem_latency - 1

    def wb_stage(self):
        if not self.mem_wb['ins']:
            return
        if self.mem_wb['control']['regwrite']:
            if self.mem_wb['control']['memread']:
                self.regs[self.mem_wb['rd']] = self.mem_wb['mem_data']  
            else: 
                self.regs[self.mem_wb['rd']] = self.mem_wb['alu_res']  

    def print_pipeline_state(self):
        """Print the current state of the pipeline"""
        print(f"Cycle {self.cycles}:")
        print(f"  IF: {self.if_id['ins'] or '---'}")
        print(f"  ID: {self.id_ex['ins'] or '---'}")
        print(f"  EX: {self.ex_mem['ins'] or '---'}")
        print(f"  MEM: {self.mem_wb['ins'] or '---'}")
        print(f"  WB: {self.mem_wb['ins'] if self.mem_wb['ins'] and 'halt' not in self.mem_wb['ins'] else '---'}")
        print("---")

    def print_statistics(self):
        """Print simulation statistics"""
        print("\nSimulation Statistics:")
        print("=====================")
        print(f"Total Clock Cycles: {self.cycles}")
        print(f"Total Instructions Executed: {self.tot_ins}")
        print(f"Total Stalls: {self.stall_count}")
        print(f"  Stalls due to Loads: {self.load_stalls}")
        print(f"  Stalls due to Memory Latency: {self.mem_delay_cycles}")
        print("Branch Delay Slot Effectiveness:")
        print(f"  Useful Delay Slots: {self.delay_slot_used}")
        print(f"  Wasted Delay Slots: {self.delay_slot_wasted}")
        if (self.delay_slot_used + self.delay_slot_wasted) > 0:
            effectiveness = (self.delay_slot_used / 
                           (self.delay_slot_used + self.delay_slot_wasted)) * 100
            print(f"  Effectiveness: {effectiveness:.2f}%")
        print("\nFinal Register Values:")
        for i in range(32):
            if self.regs[i] != 0:
                print(f"  ${i}: {self.regs[i]}")
        print("\nFinal Data Memory Contents:")
        for addr in sorted(self.data_mem.keys()):
            print(f"  MEM[{addr}]: {self.data_mem[addr]}")

    def load_sample_program(self):
        program = [
            'addi $4, $0, 5',    
            'addi $5, $0, 10',   
            'loop: lw $6, 0($1)',
            'add $7, $6, $2',    
            'sw $7, 0($3)',      
            'addi $1, $1, 4',     
            'addi $3, $3, 4',     
            'subi $4, $4, 1',     
            'beq $4, $0, loop',   
            'addi $8, $0, 100',  
            'lw $9, 0($2)',      
            'sw $9, 4($2)',      
            'add $10, $9, $5',    
            'j end',             
            'addi $11, $0, 200',  
            'end: halt'          
        ]
        
        for i, inst in enumerate(program):
            self.ins_mem[i*4] = inst

    def run(self):
        print("Starting MIPS Processor Simulation")
        print("=================================")
        
        while True:
            self.cycles += 1
            self.wb_stage()
            self.mem_stage()
            self.ex_stage()
            self.id_stage()
            self.if_stage()
            
            self.print_pipeline_state()
            
            if self.mem_wb['ins'] and 'halt' in self.mem_wb['ins']:
                break
            
            if self.branch_taken:
                self.branch_taken = False
            
        self.print_statistics()


core = Processor()
core.load_sample_program()
core.run()
