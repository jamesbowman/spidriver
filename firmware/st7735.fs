$00 constant NOP      $2B constant RASET    $C2 constant PWCTR3
$01 constant SWRESET  $2C constant RAMWR    $C3 constant PWCTR4
$04 constant RDDID    $2E constant RAMRD    $C4 constant PWCTR5
$09 constant RDDST    $30 constant PTLAR    $C5 constant VMCTR1
$10 constant SLPIN    $36 constant MADCTL   $DA constant RDID1
$11 constant SLPOUT   $3A constant COLMOD   $DB constant RDID2
$12 constant PTLON    $B1 constant FRMCTR1  $DC constant RDID3
$13 constant NORON    $B2 constant FRMCTR2  $DD constant RDID4
$20 constant INVOFF   $B3 constant FRMCTR3  $E0 constant GMCTRP1
$21 constant INVON    $B4 constant INVCTR   $E1 constant GMCTRN1
$28 constant DISPOFF  $B6 constant DISSET5  $FC constant PWCTR6
$29 constant DISPON   $C0 constant PWCTR1
$2A constant CASET    $C1 constant PWCTR2
$80 constant DELAY

here constant init-table
    SWRESET       ,   DELAY ,           \ Software reset, 0 args, w/delay
      120 ,                             \ 120 ms delay
    SLPOUT        ,   DELAY ,           \ Out of sleep mode, 0 args, w/delay
      120 ,                             \ 120 ms delay
    FRMCTR1       , 3      ,            \ Frame rate ctrl - normal mode, 3 args:
      0x01 , 0x2C , 0x2D ,              \ Rate = fosc/(1x2+40) * (LINE+2C+2D)
    FRMCTR2       , 3      ,            \ Frame rate control - idle mode, 3 args:
      0x01 , 0x2C , 0x2D ,              \ Rate = fosc/(1x2+40) * (LINE+2C+2D)
    FRMCTR3       , 6      ,            \ Frame rate ctrl - partial mode, 6 args:
      0x01 , 0x2C , 0x2D ,              \ Dot inversion mode
      0x01 , 0x2C , 0x2D ,              \ Line inversion mode
    PWCTR1        , 3      ,            \ Power control, 3 args:
      0xA2 ,
      0x02 ,                            \ -4.6V
      0x84 ,                            \ AUTO mode
    PWCTR2        , 1      ,            \ Power control, 1 arg:
      0xC5 ,                            \ VGH25 = 2.4C VGSEL = -10 VGH = 3 * AVDD
    PWCTR3        , 2      ,            \ Power control, 2 args:
      0x0A ,                            \ Opamp current small
      0x00 ,                            \ Boost frequency
    PWCTR4        , 2      ,            \ Power control, 2 args:
      0x8A ,                            \ BCLK/2, Opamp current small & Medium low
      0x2A ,
    PWCTR5        , 2      ,            \ Power control, 2 args:
      0x8A , 0xEE ,
    VMCTR1        , 1      ,            \ Power control, 1 arg:
      0x0E ,
    MADCTL        , 1      ,            \ Memory access control (directions), 1 arg:
      0xC8 ,                            \ row addr/col addr, bottom to top refresh
    COLMOD        , 1      ,            \ set color mode, 1 arg:
      0x03 ,                            \ 12-bit color
    GMCTRP1       , 16      ,           \ Gamma + polarity Correction Characterstics
      0x02 , 0x1c , 0x07 , 0x12 ,
      0x37 , 0x32 , 0x29 , 0x2d ,
      0x29 , 0x25 , 0x2B , 0x39 ,
      0x00 , 0x01 , 0x03 , 0x10 ,
    GMCTRN1       , 16      ,           \ Gamma - polarity Correction Characterstics
      0x03 , 0x1d , 0x07 , 0x06 ,
      0x2E , 0x2C , 0x29 , 0x2D ,
      0x2E , 0x2E , 0x37 , 0x3F ,
      0x00 , 0x00 , 0x02 , 0x10 ,
    NORON         , 0       ,           \ Normal display on
    0 ,

: unsel 3 .p1 set ;
: sel   3 .p1 clr ;
:m clk  [ 0 .p1 set 0 .p1 clr ] m;
:m 1bit 2*' 2 .p1 movcb clk m;
:m /C/  [ 4 .p1 clr ] m;
:m /D/  [ 4 .p1 set ] m;

: (>st) 1bit 1bit 1bit 1bit
: _4    1bit 1bit 1bit 1bit 2*' ;
: (4>st) 2*' 2*' 2*' 2*' _4 ;
: 4>st  (4>st) drop ;

: write-cmd  ( c -- )   /C/
: 1>st       ( c -- )   sel (>st) drop unsel ;
: write-data ( c -- )   /D/ 1>st ;
: data16                0# write-data write-data ;

: args
    begin
        0=if drop; then
        @p+ write-data
        1-
    again

: coldregs
    init-table ##p!
    begin
        @p+
        0=if drop; then
        write-cmd
        @p+
        dup $7f # and args
        -if @p+ ms then
        drop
    again

: dim ( x w )
    over data16 + 1- data16 ;
: rect              ( x y w h )
    twist           ( x w y h )
    RASET # write-cmd dim
    CASET # write-cmd dim
: writing
    RAMWR # write-cmd
    /D/ sel
;

: dark
    2 .p1 clr
    clk clk clk clk
    clk clk clk clk
    clk clk clk clk ;

: full
    blu #@ (4>st)
    grn (#@) (4>st) red (#@) 4>st ;

: half 10 #
: gray
    0=if
        dark drop;
    then
    dup [ blu b mov mul ] $f # + _4 drop
    dup [ grn b mov mul ] $f # + _4 drop
        [ red b mov mul ] $f # + _4 drop ;

: cls       ( )
    0# 0# 128 # 160 #
    rect

    160 # 7 #for
        128 # 6 #for
            dark
        6 #next
    7 #next
    unsel ;

: /st7735
    %11111111 # P1SKIP #!
    %00011101 # P1MDOUT #!
    [ 0 .p1 clr ] unsel
    coldregs
    cls
: white
    $f #
: setgray
    red (#!) grn (#!) blu #! ; 

947 here
include fontsize.fs
$0fff FONTDATA_SIZE - org
include font.fs
org 947 <> throw

: 4.4
    @p+
    dup [swap] $f # and swap $f # and ;

: skip
    4.4 * 1+ 2/
: +p
    [ dpl add ] dpl (#!)
    [ clra dph addc ] dph (#!)
    drop;

: seek ( c -- ) \ p points to the data for character c
    font ##p!
    begin
        dup @p+ xor 0=if 2drop ; then
        drop skip
    again

: xy!   y #! x #! ;
: adv   x #+! ;            \ advance cursor

: ch ( c -- )
    p>r
    seek
    x #@ y #@
    4.4                     ( w h )
    over adv
    2dup * push             ( w h  r: w*h )
    rect
    pop 1+ 2/ 7 #for
        4.4 swap gray gray
    7 #next
    unsel
    r>p ;

: blch
    x #@ y #@ 8 # 9 # rect
    [ 8 9 * ] # 7 #for dark 7 #next
    8 # adv ;

: str
    @p+ 6 #for
        @p+
        ch
    6 #next ;

: hl ( x - x-hi x-lo )
    dup [swap] $f # and swap $f # and ;

: setcolor
    @p+ hl grn #! red #! @p+ blu #! ;

: fixed
    tplan ##p!
    begin
        @p+ 0=if drop; then
        @p+ xy!
        setcolor
        str
    again

: alabel ( n -- )
    tplan ##p!
    begin
        0=if drop; then
        p+ p+ p+ p+
        @p+ +p
        1-
    again

: hi full
: 8dark
    dark dark dark dark
    dark dark dark dark ;
: lo 8dark full ;
: change
    full full full full full full full full full ;
: lohi
    0 .t if. hi ; then lo ;
: 0=lo
    if hi ; then lo ;
: disconn
    half half half half half half half half half ;

: 1wave
    p+
    RASET # write-cmd
    38 # data16 127 # data16
    CASET # write-cmd
    @p+ dup data16 8 # + data16
    setcolor
    MADCTL # write-cmd %10101000 # write-data
    90 # 7 #!                   \ 90 columns, R7 counter
    story # a!                  \ start reading the story
    writing
    ;

:m column $df cond ; then m;    \ forward DJNZ R7 over RET

8 constant XWIDTH               \ width of the 'disconnect' bar

: width ( n )
    7 # and $83 , ;
    7 , 18 , 18 , XWIDTH ,

: match' ( a -- a )   \ C if a==B
    draw.MOSI if. 1 .t movbc ; then
    'c' # =if setc ; then
    clrc ;

: paint-sck
    begin
        @+ a+ a+
        1 .t if.
            drop
            lo column
            8 # 6 #for
                change column lo column
            6 #next
            lo column
        else
            width
            XWIDTH # =if
                6 #for disconn column 6 #next
            else
                6 #for lo column 6 #next
            then
        then
    again

: changes ( old cmd -- old cmd ) \ if my bit changes, set carry
    'a' # =if
        over @ xor 5 #@ and $ff # +
        drop ;
    then
    clrc ;

: paint-bit
    p0snap #@
    5 #@ and
    begin
        @+
        changes if'
            drop a+ a+
            3 # 6 #for 0=lo column 6 #next
            5 #@ xor change column
            3 # 6 #for 0=lo column 6 #next
        else
            width
            XWIDTH # =if
                6 #for disconn column 6 #next
            else
                6 #for 0=lo column 6 #next
            then
            a+ a+
        then
    again

: 0' ( old new -- new ) \ C set if bit0 changed
    tuck xor 2/' drop ;

: pick
    draw.MOSI if. (@+) a+ ; then
    a+ (@+) ;

: paint-m_s_
    dup
    begin
        (@+)
        match' if'
            pick
            0 .t if. change else lo then column
            8 # 6 #for
                lohi column
                dup clrc 2/' 0'
                if' change else lohi then column
            6 #next
            lo column
        else
            a+ a+ dup width
            XWIDTH # =if   
                6 #for disconn column 6 #next
            else
                6 #for lo column 6 #next
            then
        then
    again

: hex1 ( h x y -- )
    x #@ y #@ 4 # 5 # rect
    micro ##p!
    $f # and 10 # * +p
    10 # 7 #for 4.4 swap gray gray 7 #next
    unsel
    5 # x #+! ;

: drawhex ( hh x y -- )
    dup [swap] hex1 hex1 ;

: annotate
    0# y #@ 90 # 5 # rect
    5 # 7 #for
        90 # 6 #for
            dark
        6 #next
    7 #next
    [ 90 13 - ] #
    story # a!
    begin
        -if drop; then
        x (#!)
        @+
        match' if'
            dup pick drawhex
        else
            a+ a+
        then
        width negate +
    again

\ here constant fiction ," rcrdterfa1a0a1a0a0a0a0a0a0a0"

30 constant BOXW

: hbar ( x y )
    BOXW # 1 #
: bar
    2dup * push rect
    pop 7 #for $d # gray 7 #next ;
: vbar
    1 # 14 # bar ;

: colorbox
    0 # setgray
    if' setcolor then
: box ( x y )
    over [ BOXW 1- ] # + over vbar
    2dup hbar
    2dup 14 # + hbar
    vbar ;

: prebox
    alabel p+ 97 # @p+ -3 # + ;

: boxes
    3 # prebox [ 3 .p0 movbc ] colorbox
    4 # prebox [ 6 .p0 movbc ] colorbox
    5 # prebox [ 7 .p0 movbc ] colorbox ;

: waves
    \ fiction ##p! p+ story # a!  32 # 7 #for @p+ !+ 7 #next
    0 # alabel 1wave            paint-sck
    1 # alabel 1wave draw.MOSI clr paint-m_s_ drop
    2 # alabel 1wave draw.MOSI set paint-m_s_ drop
    3 # alabel 1wave $08 # 5 #! paint-bit drop
    4 # alabel 1wave $40 # 5 #! paint-bit drop
    5 # alabel 1wave $80 # 5 #! paint-bit drop
    MADCTL # write-cmd %11001000 # write-data
    $e # setgray
    76 # y #! draw.MOSI clr annotate
    97 # y #! draw.MOSI set annotate

    boxes
    DISPON # write-cmd
    ;
