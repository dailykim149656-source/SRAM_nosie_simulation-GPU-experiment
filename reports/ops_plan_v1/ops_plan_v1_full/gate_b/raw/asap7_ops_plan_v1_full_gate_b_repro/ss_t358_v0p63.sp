* ASAP7 6T SRAM template for Xyce (BSIM-CMG level-107 transformed decks)
* Placeholders replaced by run_spice_validation.py:
*   ss 358.150000 0.630000
*   C:/Users/daily/AppData/Local/Temp/sram_spice_workspace/ss_t358_v0p63/assets/asap7_xyce/7nm_SS_160803_l107.pm
*   nmos_sram pmos_sram

.option noinit
.option reltol=1e-4 abstol=1e-12 method=gear

.param TEMP_K=358.150000
.param TEMP_C={TEMP_K-273.15}
.param VDD=0.630000

* FinFET base geometry
.param LCH=20n
.param NFPU=2
.param NFPD=3
.param NFAX=2

* Xyce-transformed ASAP7 corner model file
.include "C:/Users/daily/AppData/Local/Temp/sram_spice_workspace/ss_t358_v0p63/assets/asap7_xyce/7nm_SS_160803_l107.pm"

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
Mpu1 q  qb vdd vdd pmos_sram nfin={NFPU*1.0} l={LCH*1.0}
Mpd1 q  qb 0   0   nmos_sram nfin={NFPD*1.0} l={LCH*1.0}
Mpu2 qb q  vdd vdd pmos_sram nfin={NFPU*1.0} l={LCH*1.0}
Mpd2 qb q  0   0   nmos_sram nfin={NFPD*1.0} l={LCH*1.0}

* Access transistors
Max1 q  bl  wl 0 nmos_sram nfin={NFAX*1.0} l={LCH*1.0}
Max2 qb blb wl 0 nmos_sram nfin={NFAX*1.0} l={LCH*1.0}

* Start from a valid memory state
.ic v(q)={VDD} v(qb)=0

.temp {TEMP_C}
.tran 1p 5n uic

* ngspice control block is replaced by Xyce adapter in run_spice_validation.py.
* Xyce-compatible measurement block (derived from ngspice control script)
.measure tran VQ_HOLD find v(q) at=0.90n
.measure tran VQ_READ find v(q) at=1.90n
.measure tran VQ_W0 find v(q) at=2.90n
.measure tran VQ_W1 find v(q) at=3.90n
.measure tran SNM_PROXY MIN PARAM='abs(v(q)-v(qb))' from=1.00n to=2.00n
.measure tran SNM_MV PARAM='SNM_PROXY * 500'
.measure tran HOLD_SNM_MV PARAM='SNM_MV'
.measure tran READ_DISTURB PARAM='abs(VQ_READ - VQ_HOLD)'
.measure tran READ_SNM_MV PARAM='SNM_MV - (READ_DISTURB * 1000.0)'
.measure tran WRITE_ERROR PARAM='abs(VQ_W1 - 0.63)'
.measure tran WRITE_MARGIN_MV PARAM='(0.63 - WRITE_ERROR) * 1000.0'
.measure tran NOISE_PROXY PARAM='1 * (READ_DISTURB + 0.5 * WRITE_ERROR) / (0.63 + 1e-9)'
.measure tran NOISE_SIGMA PARAM='NOISE_PROXY'
.measure tran READ_FAIL PARAM='1.0 / (1.0 + exp((READ_SNM_MV - 50.0) / 8.0))'
.measure tran WRITE_FAIL PARAM='1.0 / (1.0 + exp((WRITE_MARGIN_MV - 50.0) / 8.0))'
.measure tran BER_PROXY PARAM='1.0 / (1.0 + exp((SNM_MV - 120) / 10))'
.measure tran MEAS_SNM_MV PARAM='SNM_MV'
.measure tran MEAS_NOISE PARAM='NOISE_PROXY'
.measure tran MEAS_BER PARAM='BER_PROXY'
.measure tran MEAS_HOLD_SNM_MV PARAM='HOLD_SNM_MV'
.measure tran MEAS_READ_SNM_MV PARAM='READ_SNM_MV'
.measure tran MEAS_WRITE_MARGIN_MV PARAM='WRITE_MARGIN_MV'
.measure tran MEAS_NOISE_SIGMA PARAM='NOISE_SIGMA'
.measure tran MEAS_READ_FAIL PARAM='READ_FAIL'
.measure tran MEAS_WRITE_FAIL PARAM='WRITE_FAIL'

.end