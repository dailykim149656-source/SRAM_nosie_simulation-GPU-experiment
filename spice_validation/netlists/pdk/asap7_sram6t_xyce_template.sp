* ASAP7 6T SRAM template for Xyce (BSIM-CMG level-107 transformed decks)
* Placeholders replaced by run_spice_validation.py:
*   __CORNER__ __TEMP_K__ __VDD__
*   __PDK_NMOS_CORNER_FILE__
*   __PDK_NMOS_MODEL__ __PDK_PMOS_MODEL__

.option noinit
.option reltol=1e-4 abstol=1e-12 method=gear

.param TEMP_K=__TEMP_K__
.param TEMP_C={TEMP_K-273.15}
.param VDD=__VDD__

* FinFET base geometry
.param LCH=20n
.param NFPU=2
.param NFPD=3
.param NFAX=2

* Xyce-transformed ASAP7 corner model file
.include "__PDK_NMOS_CORNER_FILE__"

* Power and control waveforms
VDDSRC vdd 0 {VDD}
VWL wl 0 PWL(0.00n 0 0.90n 0 1.00n {VDD} 3.90n {VDD} 4.00n 0 5.00n 0)

* BL/BLB phases:
* - 0.0ns~2.0ns: precharge/read (BL=BLB=VDD)
* - 2.0ns~3.0ns: write-0 (BL=0, BLB=VDD)
* - 3.0ns~4.0ns: write-1 (BL=VDD, BLB=0)
VBL bl 0 PWL(0.00n {VDD} 1.99n {VDD} 2.00n 0 2.99n 0 3.00n {VDD} 5.00n {VDD})
VBLB blb 0 PWL(0.00n {VDD} 2.99n {VDD} 3.00n 0 3.99n 0 4.00n {VDD} 5.00n {VDD})

* Cross-coupled inverters (FinFET model uses nfin instead of W)
Mpu1 q  qb vdd vdd __PDK_PMOS_MODEL__ nfin={NFPU*__MC_W_PU1__} l={LCH*__MC_L_PU1__}
Mpd1 q  qb 0   0   __PDK_NMOS_MODEL__ nfin={NFPD*__MC_W_PD1__} l={LCH*__MC_L_PD1__}
Mpu2 qb q  vdd vdd __PDK_PMOS_MODEL__ nfin={NFPU*__MC_W_PU2__} l={LCH*__MC_L_PU2__}
Mpd2 qb q  0   0   __PDK_NMOS_MODEL__ nfin={NFPD*__MC_W_PD2__} l={LCH*__MC_L_PD2__}

* Access transistors
Max1 q  bl  wl 0 __PDK_NMOS_MODEL__ nfin={NFAX*__MC_W_AX1__} l={LCH*__MC_L_AX1__}
Max2 qb blb wl 0 __PDK_NMOS_MODEL__ nfin={NFAX*__MC_W_AX2__} l={LCH*__MC_L_AX2__}

* Start from a valid memory state
.ic v(q)={VDD} v(qb)=0

.temp {TEMP_C}
.tran 1p 5n uic

* ngspice control block is replaced by Xyce adapter in run_spice_validation.py.
.control
run
quit
.endc

.end
