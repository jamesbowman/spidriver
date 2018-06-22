24500000 constant SYSCLK

\ P0.0  SCK
\ P0.1  MISO
\ P0.2  MOSI
\ P0.3  CS
\ P0.4  TX
\ P0.5  RX
\ P0.6  A
\ P0.7  B

\ P1.0  SCK             \ 
\ P1.1  MISO (SDA)      | to ST7735s LCD 
\ P1.2  MOSI (SDA)      |
\ P1.3  CS              /
\ P1.4  
\ P1.5  USBV analog
\ P1.6  current sense

0 [if]
There are 4 threads:

         1000Hz tick. Increments the BCD milliscond timer.
         Timer 2 interrupt.

         ADC drive. Runs ADC conversions, stores results in variables.
         ADC end of conversion interrupt.

         UART/SPI service. Runs the transport.
         UART and SPI interrupts.
         [DPTR, R0]

         graphics. renders the main image.
         Main thread.
         [DPTR, R0-7]

[then]
[ : ," '"' parse dup ] , [
    bounds do
        i c@ ] , [
    loop
;
]

$005a org
: 2dup  |over
: over  |over ;
: tuck  swap over ;
:m p>r  [ dpl push dph push ] m;
: r>p   [ dph pop  dpl pop ] ;  \ MUST be followed by ;
: @p    |@p ;
: @p+   |@p+ ;
: *     |* ;
: um*   |um* ;
:m #+! [ dup add ] #! m;
: dnegate
    swap invert 1 # + swap invert 0 # +' ;

: d+	push swap push + pop pop +' ;
:m d2/  clrc 2/' swap 2/' swap m;


: twist ( a b c d -- a c b d )
    push swap pop ;

:m /uart
    REN0 set                    \ Receive enable

    TR1 set
    $20 # TMOD #!
    $18 # CKCON #!              \ Use system clock (T1,T2)
    [ SYSCLK 2/ 115200 4 * / ] ~#
    TH1 #!                      \ speed
    ES0 set
m;

[ : array create , does> @ + ; ]

$08 cpuORG

cpuHERE constant other 1 cpuALLOT   \ context SP save
cpuHERE constant tempr 2 cpuALLOT   \ temperature ADC
cpuHERE constant tempd 2 cpuALLOT   \             decimal
cpuHERE constant vbusr 2 cpuALLOT   \ voltage ADC
cpuHERE constant vbusd 2 cpuALLOT   \             decimal
cpuHERE constant currr 2 cpuALLOT   \ current ADC
cpuHERE constant currd 2 cpuALLOT   \             decimal
cpuHERE constant slowc 1 cpuALLOT   \ slow refresh counter
cpuHERE constant charc 1 cpuALLOT   \ character counter
cpuHERE constant in.l  1 cpuALLOT   \ 
cpuHERE constant in.h  1 cpuALLOT
cpuHERE constant log   1 cpuALLOT
cpuHERE    array clock 6 cpuALLOT

cpuHERE $20 <> throw

cpuHERE constant flags 1 cpuALLOT           $00 constant dirty
                                            $01 constant draw.MOSI
cpuHERE constant p0snap 1 cpuALLOT
cpuHERE constant story 42 cpuALLOT

[
cpuHERE constant red 1 cpuALLOT
cpuHERE constant grn 1 cpuALLOT
cpuHERE constant blu 1 cpuALLOT
]
3 constant x                        \ graphics x coordinate
4 constant y                        \ graphics y coordinate
cpuHERE constant spixb 64 cpuALLOT

: swapctx [
    0 push
    1 push
    t push
    psw push
    dph push
    dpl push
    ]
    SP (#@)
    [ other xch ]
    SP (#!)
    [
    dpl pop
    dph pop
    psw pop
    t pop
    1 pop
    0 pop
    ]
    ;

: 0#    dup [ clra ] ;
: key   begin TI0 clr RI0 0=while. swapctx TI0 clr repeat SBUF0 #@ RI0 clr ;
: emit  SBUF0 (#!) begin swapctx RI0 clr TI0 until. TI0 clr [ charc dec ]
: _drop drop ;

:m drop; _drop ; m;

: depth S #@ invert ;
0 [if]
include debug.fs
[then]
: ms
    slowc (#!)
    begin slowc (#@) 0=until drop;

:m unsel 3 .p0 set m;
:m sel   3 .p0 clr m;
:m /spi
    unsel
    $40 # SPI0CFG #!
    [ SYSCLK 500000 / 2/ ] # SPI0CKR #!
    $01 # SPI0CN #! m;
: >spi  SPI0DAT #! ;
: spi>  $ff #
: spix  SPI0DAT (#!)
        begin swapctx SPIF until.
        SPIF clr
        SPI0DAT (#@) ;

5 constant d.l          \ decimal accumulator
6 constant d.h

HERE constant WIP
: decimal ( u. -- d. )   \ d is the BCD of u
    0 # d.l #!
    0 # d.h #!
    16 # 7 #for
        swap 2*' swap 2*'
        d.l #@ [ d.l addc da ] d.l #!
        d.h #@ [ d.h addc da ] d.h #!
    7 #next
    2drop d.l #@ d.h #@ ;

: 10trunc
    swap $f0 # and swap ;
: 5trunc
    swap
    dup $f # and 5 # <if
        0#
    else
        5 #
    then
    push xor pop + swap ;

: fold  ( d. -- )           \ Add d to [4 5 6]
        swap
        5 #+!
        [ 6 addc ] 6 #!
        if' [ 7 inc ] then ;

: (uq*)  ( a. b. -- q.. )
                            \ 4     5    6    7
        4 #2!               \ bl    bh
        7 #!                \                 ah
        6 (#!)              \            al

             5 #@ um*       \ m16 = 5 * 6
        4 #@ 7 #@ um*       \ m16 = 4 * 7

        5 #@ 7 #@ um*       \ hi16
        4 #@ 6 #@ um*       \ lo16

                            \ 4     5    6    7
                            \ LSB           MSB
        5 #! 4 #! 7 #! 6 #!
        fold fold ;

: uq*   (uq*) 4 #2@
: 67@   6 #2@ ;
: h*    (uq*) 67@ ;

\ ---------------------------------------- CRC16
:m /crc
    %1100 # CRC0CN0 #!
    m;

:m crc16
    CRC0DAT #@
    CRC0DAT #@ m;

\ ---------------------------------------- Analog thread

:m /adc
    AD0EN set
    BURSTEN set
    5 # ADC0AC #!               \ accumulate 64 samples
    1 # ADC0CN1 #!              \ common mode buffer enabled
    %00011100 # REF0CN #!       \ temp sensor on, 1.65 V ref
    $40 # ADC0PWR #!
    \ $BF # ADC0TK #!
    m;

:m 1.65v %11111001 # ADC0CF #! m; \ PGA gain is 1
:m 3.3v  %11111000 # ADC0CF #! m; \ PGA gain is 0.5

\ Temperature calibration
\
\ 26.3 C is reads as 32508
\
\ so multiply by 65536 * 2994 / 32508
[
: converts ( val adc ) $10000 swap */ constant ;
]

include cal-b3.fs

here constant "devname ," spidriver1"

: snap
    [ EA clr ]
    [ P0 p0snap mov ]
    [ log dpl mov ]
    [ EA set ]
    story # a!
    dup
    42 # 7 #for
        [ dpl dec ]
        (@x)
        (!+)
    7 #next drop;

: type
    @p+ 2 #for @p+ emit 2 #next ;

: hdigit
    dup
: (hdigit)
    [swap]
: digit
    $f # and
    -10 # + -if -39 # + then 97 # + emit ;
: dd     hdigit digit ;
: space
    32 # emit ;
: point
    '.' # emit ;
: d3 ( d. )                         \ 3-digit space padded
    if digit dd ; then              \ ###
    drop
    [ hide ] 10 # <if digit ; then  \ #
    dd ;                            \ ##
: d.d
    hdigit point digit ;

: .'   \ print carry
    [ '0' 2/ ] # 2*' emit space ;

: info
    '[' # emit
    78 # charc #!
    "devname ##p! type space
    "serial  ##p! type space

    5 clock #@ dd
    4 clock #@ dd
    3 clock #@ dd
    2 clock #@ dd
    1 clock #@ (hdigit)
    space

    vbusd #2@ d.d dd space
    currd #2@ d3 space
    tempd #2@ digit d.d space

    \ 6: A  7: B  3: CS
    [ 6 .p0 movbc ] .'
    [ 7 .p0 movbc ] .'
    [ 3 .p0 movbc ] .'

    crc16
    dd dd
    charc #@ begin
        space 1-
    0=until
    drop
    ']' # emit ;

\ Commands are:
\   e       echo next byte
\   s       select
\   u       unselect
\   80-bf   read 1-64 bytes
\   c0-ff   write 1-64 bytes

:m disconnect
    [
        %00010000               \ TX
    ] # P0MDOUT #!
    [ SPIEN clr ]
m;
:m connect
    [
        %00010000               \ TX
        %00000101 +             \ SCK,MOSI
        %00001000 +             \ CS
        %11000000 +             \ A,B
    ] # P0MDOUT #!
    [ SPIEN set ]
m;

: count ( u -- u)
    63 # and 1+ ;

: p0log
    connect
    'a' #
: c>log ( code )
    p0 #@ dup
: >log ( code v0 v1 )
    [ dirty set ]
    [ log dpl mov   ]
    !x+ !x+ !x+
    [ dpl log mov   ]
    ;

: key'  key 2/' drop ;      \ LSB of key to carry

:m (>crc) CRC0IN (#!) m;

: service
    key
    -if
        connect
        6 .t if.
            count 2 #for
                key
                'b' # over $ff # >log
                (>crc)
                >spi
            2 #next ;
        then
        [ ESPI0 set SPIF clr ]
        count

        spixb # a!
        dup 2 #for
            key (>crc) !+
        2 #next
        spixb # a!
        2 #for
            'c' #
            @+ dup spix dup (>crc) emit
            >log
        2 #next
        [ ESPI0 clr ]
        ;
    then
    '?' # =if  info     then
    'e' # =if  key emit then
    'u' # =if  p0log unsel    then
    's' # =if  p0log sel      then
    'a' # =if  key' p0log [ 6 .p0 movcb ] then
    'b' # =if  key' p0log [ 7 .p0 movcb ] then
    'x' # =if  disconnect 'd' # c>log then
    drop ;

: thread2
    0 # 2 #for
        '@' # !x+
    2 #next
    begin
        service
    again ;

12 constant Y_V
14 constant X_V
70 constant X_MA

include st7735.fs

: hdigit dup [swap]
: digit $f # and '0' # + ch ;
: dd     hdigit digit ;
: d3 ( d. )                         \ 3-digit space padded
    if digit dd ; then              \ ###
    drop blch
    10 # <if blch digit ; then      \ __#
    dd ;                            \ _##
: results
    white
    X_V  # Y_V # xy! vbusd #2@ hdigit '.' # ch digit hdigit drop
    X_MA # Y_V # xy! currd #2@ d3 ;


:m 2move [ over 1+ over 1+ mov mov ] m;

\ Exponential Moving Average, alpha is 1/8

: alpha d2/ d2/ d2/ ;

: ema ( addr -- )
    [ psw push 1 push ]

    (a!) (@+) @
    2dup alpha dnegate d+
    ADC0L #2@ alpha d+
    !- !

    [ 1 pop psw pop ] ;

: startconv
    AD0BUSY set
    [ in.h pop in.l pop
      reti ]
: converter
    begin
        %10000 # ADC0MX #!          \ mux temperature
        1.65v startconv
        tempr # ema

        %01101 # ADC0MX #!          \ mux P1.5
        3.3v startconv
        vbusr # ema

        %01110 # ADC0MX #!          \ mux P1.6
        startconv
        currr # ema
    again

: conversions
    vbusr #2@ voltage ## h*
    decimal vbusd #2!
    tempr #2@ kel ## h* celsius ## d+
    decimal tempd #2!
    currr #2@
    \ 0current ## d+ 0=if' 2drop 0 ## then
    current ## h*
    decimal 5trunc currd #2!
;

cpuHERE constant STACKS

: go
    $de # WDTCN #!
    $ad # WDTCN #!

    $03 # XBR0 #!
    $00 # XBR1 #!
    $c0 # XBR2 #!

    $00 # CLKSEL #!

    \ Clear RAM
    $08 # a!
    [ $100 $08 - ] # 7 #for 0 # !+ 7 #next

    $c0 SP! STACKS RP!
    [ ' thread2 >body @ ] ##p!
    [
    dpl push
    dph push
    0 push
    ]
    [ STACKS 8 + ] # other #!

    $100 SP! $c0 RP!

    [ ' converter >body @ dup ] # in.l #!
    [ 8 rshift ] # in.h #!
    
    %11001000 # P0SKIP #!
    %11111111 # P1SKIP #!

HERE constant WIP
    connect
    %00011101 # P1MDOUT #!
    %10011111 # P1MDIN #!       \ analog P1.5 P1.6
    /spi
    /uart
    /adc
    /crc

    [ ticks/ms negate          ] # TMR2RLL #!
    [ ticks/ms negate 8 rshift ] # TMR2RLH #!

    %11010000 # IP #!           \ top priority for UART,SPI

    [ ET2 set ]                 \ Timer 2 interrupt enable
    [ TR2 set ]                 \ Timer 2 enable
    [ EA set ]

    $08 # EIE1 ior!             \ ADC end of conversion interrupt enable
    AD0BUSY set                 \ Trigger first ADC to start thread
    [ dirty set ]
    swapctx

    /st7735 fixed

    begin
        conversions

        dirty if.
            snap
            [ dirty clr ]
            waves
        then
        \ [ 7 .p0 toggle ]

        slowc #@ 0=if
            250 # slowc #!
            results
        then drop

    again

: timer2
    [ psw push t push ]
    slowc (#@) if [ slowc dec ] then
    [
    setc
    clra 0 clock dup addc da (#!)
    clra 1 clock dup addc da (#!)
    clra 2 clock dup addc da (#!)
    clra 3 clock dup addc da (#!)
    clra 4 clock dup addc da (#!)
    clra 5 clock dup addc da (#!)
    ] [ t pop psw pop ] ;

here

\ Reset
$000 org go ;

\ UART interrupt
$023 org
    swapctx [ reti ]

\ Timer 2 overflow
$02b org [
    ] timer2 [
    TF2H clr
    reti
]

\ SPI0
$033 org
    swapctx [ reti ]

\ ADC end of conversion
$053 org [
    AD0INT clr
    in.l push in.h push
    ] ;


org
