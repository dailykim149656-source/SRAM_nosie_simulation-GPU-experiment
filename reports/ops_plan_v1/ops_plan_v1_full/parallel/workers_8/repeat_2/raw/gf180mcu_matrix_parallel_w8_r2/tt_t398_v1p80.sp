* GF180MCU 6T SRAM ngspice template (real PDK deck include)
* Placeholders replaced by run_spice_validation.py:
*   tt 398.150000 1.800000
*   C:/Users/daily/AppData/Local/Temp/sram_spice_workspace/tt_t398_v1p80/assets/ngspice/design.ngspice C:/Users/daily/AppData/Local/Temp/sram_spice_workspace/tt_t398_v1p80/assets/ngspice/sm141064.ngspice typical
*   nmos_3p3 pmos_3p3

.option noinit
.option reltol=1e-4 abstol=1e-12 method=gear

.param TEMP_K=398.150000
.param TEMP_C={TEMP_K-273.15}
.param VDD=1.800000

.param LCH=0.28u
.param WPU=1.20u
.param WPD=2.00u
.param WAX=1.20u

* Load GF180 global switches and process-corner model deck.
.include "C:/Users/daily/AppData/Local/Temp/sram_spice_workspace/tt_t398_v1p80/assets/ngspice/design.ngspice"
.lib "C:/Users/daily/AppData/Local/Temp/sram_spice_workspace/tt_t398_v1p80/assets/ngspice/sm141064.ngspice" typical

* Power and control waveforms
VDDSRC vdd 0 {VDD}
VWL wl 0 PWL(0.00n 0 0.90n 0 1.00n {VDD} 3.90n {VDD} 4.00n 0 5.00n 0)

* BL/BLB phases:
* - 0.0ns~2.0ns: precharge/read (BL=BLB=VDD)
* - 2.0ns~3.0ns: write-0 (BL=0, BLB=VDD)
* - 3.0ns~4.0ns: write-1 (BL=VDD, BLB=0)
VBL bl 0 PWL(0.00n {VDD} 1.99n {VDD} 2.00n 0 2.99n 0 3.00n {VDD} 5.00n {VDD})
VBLB blb 0 PWL(0.00n {VDD} 2.99n {VDD} 3.00n 0 3.99n 0 4.00n {VDD} 5.00n {VDD})

* Cross-coupled inverters (GF180 MOS devices are exposed as subcircuits)
Xpu1 q  qb vdd vdd pmos_3p3 w={WPU*1.0} l={LCH*1.0}
Xpd1 q  qb 0   0   nmos_3p3 w={WPD*1.0} l={LCH*1.0}
Xpu2 qb q  vdd vdd pmos_3p3 w={WPU*1.0} l={LCH*1.0}
Xpd2 qb q  0   0   nmos_3p3 w={WPD*1.0} l={LCH*1.0}

* Access transistors
Xax1 q  bl  wl 0 nmos_3p3 w={WAX*1.0} l={LCH*1.0}
Xax2 qb blb wl 0 nmos_3p3 w={WAX*1.0} l={LCH*1.0}

* Start from a valid memory state
.ic v(q)=VDD v(qb)=0

.temp {TEMP_C}
.tran 1p 5n uic

* Measurements
.control
run

meas tran vq_hold find v(q) at=0.90n
meas tran vq_read find v(q) at=1.90n
meas tran vq_w0   find v(q) at=2.90n
meas tran vq_w1   find v(q) at=3.90n
let vdiff = abs(v(q)-v(qb))
meas tran snm_proxy min vdiff from=1.00n to=2.00n

let snm_mv = snm_proxy * 500.000000
let hold_snm_mv = snm_mv
let read_disturb = abs(vq_read - vq_hold)
let read_snm_mv = snm_mv - (read_disturb * 1000.0)
let write_error = abs(vq_w1 - 1.800000)
let write_margin_mv = (1.800000 - write_error) * 1000.0
let noise_proxy = 1.000000 * (read_disturb + 0.500000 * write_error) / (1.800000 + 1e-9)
let noise_sigma = noise_proxy
let read_fail = 1.0 / (1.0 + exp((read_snm_mv - 50.0) / 8.0))
let write_fail = 1.0 / (1.0 + exp((write_margin_mv - 50.0) / 8.0))
let ber_proxy = 1.0 / (1.0 + exp((snm_mv - 120.000000) / 10.000000))
echo MEAS_CORNER=tt
echo MEAS_TEMP_K=398.150000
echo MEAS_VDD=1.800000
echo MEAS_SNM_MV=$&snm_mv
echo MEAS_NOISE=$&noise_proxy
echo MEAS_BER=$&ber_proxy
echo MEAS_HOLD_SNM_MV=$&hold_snm_mv
echo MEAS_READ_SNM_MV=$&read_snm_mv
echo MEAS_WRITE_MARGIN_MV=$&write_margin_mv
echo MEAS_NOISE_SIGMA=$&noise_sigma
echo MEAS_READ_FAIL=$&read_fail
echo MEAS_WRITE_FAIL=$&write_fail
quit
.endc

.end
