// This file is part of www.nand2tetris.org
// and the book "The Elements of Computing Systems"
// by Nisan and Schocken, MIT Press.
// File name: projects/04/Mult.asm

// Multiplies R0 and R1 and stores the result in R2.
// (R0, R1, R2 refer to RAM[0], RAM[1], and RAM[2], respectively.)
//
// This program only needs to handle arguments that satisfy
// R0 >= 0, R1 >= 0, and R0*R1 < 32768.

// persudo code
// 
// i = 0
// R2 = 0
// while i < R0:
//     R2 += R1
//     i ++
// 

    @i
    M = 0
    @R2
    M = 0

(LOOP)
    // while i < R0
    @i
    D = M
    @R0
    D = D - M
    @END
    D;JGE

    // R2 += R1
    @R1
    D = M
    @R2
    M = M + D

    // i ++
    @i
    M = M + 1

    @LOOP
    0;JMP
    
(END)
    @END
    0;JMP
    