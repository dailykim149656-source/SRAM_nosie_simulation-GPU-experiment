* IHP SG13G2 6T SRAM ngspice template (real PDK deck include)
* Placeholders replaced by run_spice_validation.py:
*   __CORNER__ __TEMP_K__ __VDD__
*   __PDK_MODEL_LIB__ __PDK_CORNER__
*   __PDK_NMOS_MODEL__ __PDK_PMOS_MODEL__

.option noinit
.option reltol=1e-4 abstol=1e-12 method=gear

.param TEMP_K=__TEMP_K__
.param TEMP_C={TEMP_K-273.15}
.param VDD=__VDD__

.param LCH=0.35u
.param WPU=0.70u
.param WPD=1.20u
.param WAX=0.80u

* Use SG13G2 low-voltage MOS corner deck.
.lib "__PDK_MODEL_LIB__" __PDK_CORNER__

* Power and control waveforms
VDDSRC vdd 0 {VDD}
VWL wl 0 PWL(0.00n 0 0.90n 0 1.00n {VDD} 3.90n {VDD} 4.00n 0 5.00n 0)

* BL/BLB phases:
* - 0.0ns~2.0ns: precharge/read (BL=BLB=VDD)
* - 2.0ns~3.0ns: write-0 (BL=0, BLB=VDD)
* - 3.0ns~4.0ns: write-1 (BL=VDD, BLB=0)
VBL bl 0 PWL(0.00n {VDD} 1.99n {VDD} 2.00n 0 2.99n 0 3.00n {VDD} 5.00n {VDD})
VBLB blb 0 PWL(0.00n {VDD} 2.99n {VDD} 3.00n 0 3.99n 0 4.00n {VDD} 5.00n {VDD})

* Cross-coupled inverters (IHP MOS devices are exposed as subcircuits)
Xpu1 q  qb vdd vdd __PDK_PMOS_MODEL__ w={WPU*__MC_W_PU1__} l={LCH*__MC_L_PU1__}
Xpd1 q  qb 0   0   __PDK_NMOS_MODEL__ w={WPD*__MC_W_PD1__} l={LCH*__MC_L_PD1__}
Xpu2 qb q  vdd vdd __PDK_PMOS_MODEL__ w={WPU*__MC_W_PU2__} l={LCH*__MC_L_PU2__}
Xpd2 qb q  0   0   __PDK_NMOS_MODEL__ w={WPD*__MC_W_PD2__} l={LCH*__MC_L_PD2__}

* Access transistors
Xax1 q  bl  wl 0 __PDK_NMOS_MODEL__ w={WAX*__MC_W_AX1__} l={LCH*__MC_L_AX1__}
Xax2 qb blb wl 0 __PDK_NMOS_MODEL__ w={WAX*__MC_W_AX2__} l={LCH*__MC_L_AX2__}

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

let snm_mv = snm_proxy * __SNM_SCALE_MV__
let hold_snm_mv = snm_mv
let read_disturb = abs(vq_read - vq_hold)
let read_snm_mv = snm_mv - (read_disturb * 1000.0)
let write_error = abs(vq_w1 - __VDD__)
let write_margin_mv = (__VDD__ - write_error) * 1000.0
let noise_proxy = __NOISE_SCALE__ * (read_disturb + __NOISE_WRITE_WEIGHT__ * write_error) / (__VDD__ + 1e-9)
let noise_sigma = noise_proxy
let read_fail = 1.0 / (1.0 + exp((read_snm_mv - 50.0) / 8.0))
let write_fail = 1.0 / (1.0 + exp((write_margin_mv - 50.0) / 8.0))
let ber_proxy = 1.0 / (1.0 + exp((snm_mv - __BER_CENTER_MV__) / __BER_SLOPE_MV__))
echo MEAS_CORNER=__CORNER__
echo MEAS_TEMP_K=__TEMP_K__
echo MEAS_VDD=__VDD__
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
