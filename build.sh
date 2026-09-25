cc -std=c11 -Wall -Wextra -Wpedantic -O2 \
    triton_agent1_main.c \
    -o triton-agent1

./triton-agent1 jovial program.jov
./triton-agent1 cms2 program.cms
./triton-agent1 tacpol program.tac
