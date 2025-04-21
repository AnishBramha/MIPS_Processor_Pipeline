addi $6, $0, 2
addi $7, $0, 0
add  $5, $6, $0
beq  $6, $7, skip
subi $8, $5, 1
addi $1, $0, 10
skip: addi $7, $6, 14
beq  $5, $5, jump
sub  $5, $6, $5
addi $5, $6, 5
jump: sw   $5, 0($6)
add  $6, $7, $5
add  $9, $8, $0
sub  $9, $5, $6
lw   $9, 0($5)
add  $6, $7, $5
add  $9, $8, $0
sub  $9, $5, $6
halt
