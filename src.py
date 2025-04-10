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
