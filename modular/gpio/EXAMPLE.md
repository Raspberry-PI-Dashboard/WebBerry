// set pin mode to output
{
  "type": "pin",
  "action": "mode",
  "pin": 17,
  "mode": "output"
}

// response
{
  "ok": true,
  "type": "pin",
  "action": "mode",
  "pin": 17,
  "mode": "output"
}

_____________________________________

// set a digital output high
{
  "type": "pin",
  "action": "set",
  "pin": 17,
  "value": true
}

// response
{
  "ok": true,
  "type": "pin",
  "action": "set",
  "pin": 17,
  "value": true
}

_____________________________________

// toggle a digital output
{
  "type": "pin",
  "action": "toggle",
  "pin": 17
}

// response
{
  "ok": true,
  "type": "pin",
  "action": "toggle",
  "pin": 17,
  "value": false
}

_____________________________________

// read a pin value
{
  "type": "pin",
  "action": "read",
  "pin": 17
}

// response
{
  "ok": true,
  "type": "pin",
  "action": "read",
  "pin": 17,
  "mode": "output",
  "value": true
}

_____________________________________

// switch pin to PWM mode and set duty cycle
{
  "type": "pin",
  "action": "mode",
  "pin": 18,
  "mode": "pwm"
}
{
  "type": "pin",
  "action": "pwm_set",
  "pin": 18,
  "duty_cycle": 0.5,
  "frequency": 1000
}

// response
{
  "ok": true,
  "type": "pin",
  "action": "pwm_set",
  "pin": 18,
  "duty_cycle": 0.5,
  "frequency": 1000
}

_____________________________________

// stop PWM output
{
  "type": "pin",
  "action": "pwm_stop",
  "pin": 18
}

// response
{
  "ok": true,
  "type": "pin",
  "action": "pwm_stop",
  "pin": 18,
  "duty_cycle": 0.0,
  "frequency": 1000
}
