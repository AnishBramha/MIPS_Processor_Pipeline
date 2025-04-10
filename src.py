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
            self.id_ex['ins']=None
            return
        ins=self.if_id['ins']
        self.id_ex['ins']=ins
        self.id_ex['pc']=self.if_id['pc']
        parts=ins.replace(',','').split()
        op=parts[0]
        self.id_ex['control']={
            'regwrite':0,
            'memread':0,
            'memwrite':0,
            'branch':0,
            'jump':0,
            'alusrc':0,
            'regdst':0,
            'aluop':'add'
        }
        if op=='add':
            self.id_ex['rd']=int(parts[1][1:])
            self.id_ex['rs']=int(parts[2][1:])
            self.id_ex['rt']=int(parts[3][1:])
            self.id_ex['control'].update({
                'regwrite':1,
                'regdst':1,
                'aluop':'add'
            })
        elif op=='addi':
            self.id_ex['rt']=int(parts[1][1:])
            self.id_ex['rs']=int(parts[2][1:])
            self.id_ex['imm']=int(parts[3])
            self.id_ex['control'].update({
                'regwrite':1,
                'alusrc':1,
                'aluop':'add'
            })
        elif op=='lw':
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
        elif op=='sw':
            rt=parts[1][1:]
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
            self.id_ex['imm'] = int(parts[3])
            self.id_ex['control'].update({
                'branch': 1,
                'aluop': 'sub'  
            })
        elif op=='j':
            self.id_ex['imm'] = int(parts[1])
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

    def ex_stage(self) -> None:

        if not self.id_ex['ins'] == None:
            
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

        if self.id_ex['control']['branch']:

            if self.ex_mem['alu_res'] == 0:

                self.pc = self.id_ex['pc'] + 4 + (self.id_ex['imm'] << 2)
                self.branch_taken = True

                pc_next = self.id_ex['pc'] + 4

                if pc_next in self.ins_mem and not self.ins_mem[pc_next].startswith('nop'):
                    self.delay_slot_used += 1

                else:
                    self.delay_slot_wasted += 1

        if self.id_ex['control']['memread'] and ((self.id_ex['rs'] is not None and self.id_ex['rs'] == self.ex_mem['rd']) or (self.id_ex['rt'] is not None and self.id_ex['rt'] == self.id_ex['rd'])):

            self.stall = True
            self.stall_count += 1
            self.load_stalls += 1
