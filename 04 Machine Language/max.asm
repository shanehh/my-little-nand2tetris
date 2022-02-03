    @R1
    D = M
    @R2
    D = D - M
    // 傻瓜 if else
    @R1GREATER
    D;JGE
    @R2GREATER
    0;JMP
    
(R1GREATER)
    @R1
    D = M
    @R0
    M = D
    @END
    0;JMP


(R2GREATER)
    @R2
    D = M
    @R0
    M = D
    @END
    0;JMP

(END)
    @END
    0;JMP