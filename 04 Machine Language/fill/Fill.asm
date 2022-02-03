// This file is part of www.nand2tetris.org
// and the book "The Elements of Computing Systems"
// by Nisan and Schocken, MIT Press.
// File name: projects/04/Fill.asm

// Runs an infinite loop that listens to the keyboard input.
// When a key is pressed (any key), the program blackens the screen,
// i.e. writes "black" in every pixel;
// the screen should remain fully black as long as the key is pressed. 
// When no key is pressed, the program clears the screen, i.e. writes
// "white" in every pixel;
// the screen should remain fully clear as long as no key is pressed.


// persudo code
// 
// while True:
//     color =  0 # white
//     if key != 0: # pressed
//         color = -1 # black
//
//     for i in range(screen, screen_end):
//         ram[i] = color


// screen_end = screen memory map base addresse + ...
@SCREEN
D = A
// 8192: screen memory map size
// 512 * 256 / 16
@8192
D = D + A
@screen_end
M = D


(MAIN)
    // color = 0
    @color
    M = 0

    // if key == 0, goto DONT_SET
    @KBD
    D = M
    @DONT_SET
    D;JEQ

    // set color -1
    // equal RAM 1111111111111111
    @color
    M = -1

    (DONT_SET)

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

        // RAM[pointer] = color
        @color
        D = M
        @pointer
        A = M
        M = D

        // i ++
        @i
        M = M + 1

        @RENDER_LOOP
        0;JMP
    (RENDER_END)

    @MAIN
    0;JMP
