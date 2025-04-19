addi $6, $0, 2
add $5, $6, $0
beq $5, $6, jump
sub $5, $6, $5
addi $7, $6, 14
addi $5, $6, 5
jump: sw $5, 0($6)
add $6, $7, $5
add $9, $8, $0
sub $9, $5, $6
lw $9, 0($5)
add $6, $7, $5
add $9, $8, $0
sub $9, $5, $6

halt