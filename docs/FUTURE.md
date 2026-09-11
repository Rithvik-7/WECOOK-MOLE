# Future work — Team WE COOK / SIH26025

MOLE today is a **tabletop** demonstrator: two comparison nodes, laptop sklearn, a remote rover, and one local dashboard. Measurements can indicate **disturbance**. They do **not** prove a collapse or name its cause.

This file is what we are **thinking** as a team after the hackathon. It is a roadmap, not a claim that these features already exist.

## Keep honest (never “future-wash” the demo)

We will not present these as finished product:

- Collapse or subsidence **probability**
- “Roof will fail in N minutes” as a geotech forecast
- Certified-safe mine because the badge is green
- CO **ppm** from an uncalibrated MQ-7
- Autonomous drive or camera vision
- LoRa / mesh range we have not demonstrated
- DGMS-approved underground instrument

The **field path** for real mine subsidence prediction needs surveyed mounts, labelled events, and geotechnical partners. That is the long game. The hackathon proves the **loop**: monitor → latch → explain with named ML → inspect on command.

## Near term (this rig)

- Finish live hardware day: ESP-NOW range on the table, slider mechanics, motor polarity, echo divider, IR aiming, AP join on the demo laptop.
- Optional **live retrain** of Isolation Forest on quiet NORMAL after a real baseline (priors are quiet-tabletop, not the physical MPU).
- Tighter two-point crack cal and a mechanical zero that does not sit on ADC 0 if the pot is disconnected.
- Operator packing list: labelled boards, one data USB-C for the S3-Zero, motor battery + common GND.

## After SIH — product direction

1. **More comparison nodes**  
   Same ESP-NOW family, still laptop intelligence. Node B must never cancel Node A. Extra nodes are extra evidence, not a geology model.

2. **Supervised field trial (partnership)**  
   Place a small cluster on a surface analogue or an approved test gallery with a mine operator / research lab. Log timed tilt and crack with a human observer. Do **not** skip calibration or pretend hobby ESP32 is intrinsically safe.

3. **Better sensing, still honest**  
   Calibrated displacement (LVDT / draw-wire) instead of a 10 kΩ fader. Optional calibrated gas **after** a real span calibration — still not a methane certificate. Better ultrasonic aiming. IR stays a flag, not lidar.

4. **Radio and power for distance**  
   If we leave the tabletop, we will **re-freeze** pins and radio in `AGENTS.md` rather than silently adding LoRa. Battery life, watchdog, and “USB drop → UNKNOWN, never fake green” stay.

5. **Human workflow**  
   Keep rules as the latch. Keep Inspection done as the officer closing the loop. Export CSV for a geotech, not an LLM narrative. Optional multi-shift logbook. Still no accounts required for the core demo.

6. **Prediction that stays a sensor forecast**  
   Longer horizons only with published MAE and a written “not a collapse prediction” label. A later subsidence model would be a **new** trained artefact with labelled events — not a slider on today’s Ridge.

## Why this still answers SIH26025

The problem asks for AI-enabled **monitoring, prediction, and early warning**. We already ship:

- Monitoring: Node A vs Node B, timed, source-tagged
- Early warning: tabletop WATCH/ALERT latch
- Prediction: next **30 s of the same signals** + MAE
- Inspection: rover after the officer decides

Future work **extends** that loop. It does not replace it with a chatbot or a probability of disaster.
