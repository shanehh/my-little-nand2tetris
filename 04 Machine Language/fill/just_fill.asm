// for i in range(screen, screen_end):
//     ram[i] = color


// screen_end = screen memory map base addresse + ...
@SCREEN
D = A
// 8192: screen memory map size
// 512 * 256 / 16
@8192
D = D + A
@screen_end
M = D


// render loop init, i = 0
@i
M = 0
(RENDER_LOOP)
    // pointer = i + screen
    @SCREEN
    D = A
    @i
    D = M + D
    @pointer
    M = D

    // if pointer >= screen_end, goto RENDER_END
    @screen_end
    D = M
    @pointer
    D = M - D
    @RENDER_END
    D;JGE

    @pointer
    A = M
    M = -1

    // i ++
    @i
    M = M + 1
    @RENDER_LOOP
    0;JMP
(RENDER_END)

(END)
@END
0;JMP
