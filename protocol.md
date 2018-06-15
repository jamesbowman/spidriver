
Commands are:

    ?        transmit status info
    e <byte> echo <byte>
    s        select
    u        unselect
    a <byte> set A signal to 0/1
    b <byte> set B signal to 0/1
    x        disconnect from SPI bus
    80-bf    write and read 1-64 bytes
    c0-ff    write 1-64 bytes

So for example to select, then transfer two bytes 0x12, and unselect, the host sends 5 bytes:

    s
    0x81
    0x12
    0x34
    u

The command 0x81 is a two byte send/receive, so two bytes are returned to the PC.

