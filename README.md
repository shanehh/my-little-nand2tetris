# My little journey of nand2tetris

## motivations

I just want to see, know a computer works!

Quoted from course [syllabus](https://drive.google.com/file/d/1EWCOVIcg0-dX0XtL3KwNyra6jzMogXLL/view?usp=sharing)

> > Nothing is more important than seeing the sources of invention which are, in my opinion, more interesting than the inventions themselves. –Leibnitz (1646-1716)
>
> The elementary logic gate Nand (or its close relative Nor) is the fundamental building block from which all hardware platforms are made. In this course we start from the humble Nand gate and work our way through the construction of a modern computer system – hardware and software – capable of running Tetris and any other program. In the process, we will learn how computers work, how they are constructed, and how to plan and execute largescale systems building rojects.

## links

course homepage: https://www.nand2tetris.org/

## setup

For macos x user. follow the `https://drive.google.com/file/d/1QDYIvriWBS_ARntfmZ5E856OEPpE4j1F/view` (tl;dr, install java, and run the shell.)

But for more convenience, I have `+x` to every `*.sh` with prefix `nand2tetris-` as things like namespace. Finally put the `tools` dir in my `$PATH`.

```
~/code/nand2tetris/tools
├── OS
├── bin
├── builtInChips
├── builtInVMCode
├── nand2tetris-Assembler
├── nand2tetris-CPUEmulator
├── nand2tetris-HardwareSimulator
├── nand2tetris-JackCompiler
├── nand2tetris-TextComparer
└── nand2tetris-VMEmulator
```
