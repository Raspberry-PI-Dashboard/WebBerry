// scan 
{
  "type": "i2c",
  "action": "scan"
}

// response
{
  "ok": true,
  "type": "i2c",
  "action": "scan",
  "bus": 1,
  "addresses": [72, 80]
}

_____________________________________

// read register
{
  "type": "i2c",
  "action": "read_register",
  "address": 72,
  "register": 0
}

// response
{
  "ok": true,
  "type": "i2c",
  "action": "read_register",
  "bus": 1,
  "address": 72,
  "register": 0,
  "value": 66
}

_____________________________________

// write register
{
  "type": "i2c",
  "action": "write_register",
  "address": 72,
  "register": 16,
  "value": 255
}

// block read/write
{
  "type": "i2c",
  "action": "read_block",
  "address": 80,
  "register": 0,
  "length": 8
}
{
  "type": "i2c",
  "action": "write_block",
  "address": 80,
  "register": 16,
  "data": [1, 2, 3, 4]
}